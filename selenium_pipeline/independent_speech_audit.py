"""Independent *model* ASR cross-check for element-level narration.

ASR sees ONLY WAV bytes and a fixed generic transcription request, never the
expected script. A distinct Gemini 3.1 Flash Lite model from TTS 3.8 Flash Lite
transcribes the recording. Same vendor: NOT independent human verification.
Any missing/corrupt/ambiguous result fails closed; no production approval.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,unicodedata,wave,time
from pathlib import Path
from difflib import SequenceMatcher

ASR_MODEL="gemini-3.5-flash"
ALLOWED_MODELS={"gemini-3.1-flash-lite","gemini-3.5-flash"}
REQUEST=("Transcribe all spoken English words in the supplied audio, verbatim. "
         "Do not paraphrase, explain, improve grammar or infer missing content. "
         "Return only the spoken text. If there is no intelligible speech "
         "return exactly [NO SPEECH].")

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def raw(path:Path)->bytes:
    return path.read_bytes()

def tokens(text:str)->list[str]:
    x=unicodedata.normalize("NFKC",text).casefold()
    x=x.replace("’","'").replace("−","-")
    x=re.sub(r"[^\w\s]+"," ",x,flags=re.UNICODE)
    return [w for w in x.split() if w]

def distance(reference:str,recognized:str)->dict:
    a,b=tokens(reference),tokens(recognized)
    if not a: raise ValueError("Expected script is empty")
    matches=SequenceMatcher(None,a,b,autojunk=False).get_opcodes()
    edit=sum(max(i2-i1,j2-j1) if op=="replace"
             else i2-i1 if op=="delete"
             else j2-j1 if op=="insert" else 0
             for op,i1,i2,j1,j2 in matches)
    wer=edit/len(a)
    return {"wer":round(wer,4),"reference_words":len(a),
            "asr_words":len(b),"edit_words":edit,
            "machine_asr_consistent":bool(b) and wer<=0.20}

def transcribe_bytes(audio:bytes, model:str=ASR_MODEL)->str:
    from .runner import load_microvid_env
    from gemini_keys import call_with_client_failover,create_gemini_client
    from google.genai import types
    load_microvid_env()
    os.environ.setdefault("MICROGEN_GEMINI_REQUEST_TIMEOUT_MS","90000")
    def operation(client):
        response=client.models.generate_content(
           model=model,
           contents=[types.Part.from_bytes(data=audio,mime_type="audio/wav"),REQUEST],
           config={"temperature":0})
        return str(response.text or "").strip()
    answer=None
    last_error=None
    for attempt in range(3):
        try:
            answer=call_with_client_failover(
                create_gemini_client,operation,label="independent_model_asr",
                max_retries=0)
            break
        except Exception as exc:
            # Retry only transient server failures, never invalid model or
            # bad permissions. Three bounded attempts do not prove availability.
            code=getattr(exc,"code",None)
            if code not in (429,500,502,503,504):
                raise
            last_error=exc
            if attempt<2:time.sleep(2*(2**attempt))
    if answer is None:
        raise RuntimeError("Independent ASR unavailable after bounded retries") from last_error
    if not answer or answer=="[NO SPEECH]" or len(tokens(answer))<2:
        raise RuntimeError("ASR did not return intelligible transcription")
    return answer

def check_wav(path:Path)->bytes:
    import wave
    with wave.open(str(path),"rb") as w:
        if (w.getcomptype()!="NONE" or w.getnframes()<=1000
                or w.getframerate()<8000 or w.getnchannels() not in (1,2)):
            raise ValueError("Invalid or silent-duration WAV metadata")
    return raw(path)

def write_x(path:Path,obj:dict):
    with path.open("x",encoding="utf8") as f:
        json.dump(obj,f,indent=2,ensure_ascii=False)
        f.write("\n")

def run(*,plan:Path,audio:Path,out:Path,max_clips:int,confirm:bool,
        transcriber=None,model:str=ASR_MODEL)->dict:
    if not confirm: raise ValueError("Live ASR requires --confirm-live")
    if model not in ALLOWED_MODELS:
        raise ValueError("Unsupported ASR model (cannot silently change provider)")
    if transcriber is None:
        transcriber=lambda contents: transcribe_bytes(contents,model=model)
    if not plan.is_file() or not audio.is_dir() or max_clips<1:
        raise ValueError("Required plan/audio not found or bad limit")
    plan=plan.resolve()
    out=out.resolve()
    if out.is_relative_to(audio.resolve()) or out.is_relative_to(plan.parent):
        raise ValueError("Audit may not overwrite original narration or plan folder")
    p=json.loads(plan.read_text(encoding="utf8"))
    if p.get("status")!="author_specified_unapproved_element_narration":
        raise ValueError("Not an explicit source-anchored authored plan")
    scene=[el for part in p["parts"] for sl in part["slides"] for el in sl["elements"]]
    if not scene or len(scene)>500: raise ValueError("Invalid clip count")
    if len({el["wav"] for el in scene})!=len(scene):
        raise ValueError("Duplicate WAV filename")
    digest=sha(raw(plan))
    if not out.exists():
        out.mkdir()
    if not out.is_dir(): raise ValueError("Audit output is not a directory")
    lock=out/"asr_job.json"
    ident={"schema_version":1,"status":"independent_model_asr_review_only",
           "plan_sha256":digest,"model":model,
           "source_model":"gemini-3.8-flash-lite-tts",
           "clips":[x["wav"] for x in scene]}
    if lock.exists():
        if json.loads(lock.read_text(encoding="utf8"))!=ident:
            raise ValueError("Existing ASR job bound to a different plan/model")
    else:
        if list(out.iterdir()):
            raise ValueError("Nonempty unbound ASR folder")
        write_x(lock,ident)
    results=[]
    examined=0
    provider_error=None
    for index,item in enumerate(scene,1):
        if examined>=max_clips:break
        filename=item["wav"]
        if (not re.fullmatch(r"[a-zA-Z0-9_.-]+\.wav",filename)
                or len(item["spoken_text"].split())<4):
            raise ValueError("Invalid speech segment input")
        recorded=(audio/filename).resolve()
        if not recorded.is_relative_to(audio.resolve()) or not recorded.is_file():
            raise ValueError("Missing/unsafe WAV")
        contents=check_wav(recorded)
        wav_sha=sha(contents)
        expected=item["spoken_text"]
        reference_sha=sha(expected.encode("utf8"))
        receipt=out/(filename+".asr.json")
        if receipt.is_file():
            result=json.loads(receipt.read_text(encoding="utf8"))
            if (result["wav_sha256"]!=wav_sha
                    or result["reference_sha256"]!=reference_sha
                    or result["asr_model"]!=model):
                raise ValueError("Stale/tampered ASR evidence")
        else:
            try:
                recognized=transcriber(contents)
            except Exception as exc:
                # Keep previous immutable receipts; do not synthesize evidence
                # or hammer the provider on repeated model outage.
                provider_error=type(exc).__name__
                print(f"ASR unavailable at clip {index}: {provider_error}; "
                      "incomplete review evidence preserved",flush=True)
                break
            scores=distance(expected,recognized)
            result={"status":"machine_asr_consistent_not_certified"
                        if scores["machine_asr_consistent"]
                        else "speech_review_required",
                    "wav":filename,"wav_sha256":wav_sha,
                    "reference_sha256":reference_sha,
                    "asr_model":model,
                    "model_distinct_from_tts":True,
                    "same_vendor_not_human_independent":True,
                    "transcript":recognized,
                    "transcript_sha256":sha(recognized.encode("utf8")),
                    "metrics":scores,
                    "audible_word_fidelity_certified":False,
                    "academic_approval":False}
            write_x(receipt,result)
        results.append(result)
        examined+=1
        print(f"ASR {examined}/{min(len(scene),max_clips)} {filename}: "
              f"WER={result['metrics']['wer']:.3f} {result['status']}",flush=True)
    summary={"status":("ASR_PROVIDER_UNAVAILABLE_INCOMPLETE"
                 if provider_error else "ASR_REVIEW_ONLY_NOT_PRODUCTION_APPROVAL"),
             "provider_error_type":provider_error,
             "model":model,"tts_model":"gemini-3.8-flash-lite-tts",
             "total_elements":len(scene),"examined":len(results),
             "unexamined":len(scene)-len(results),
             "consistent":sum(r["metrics"]["machine_asr_consistent"] for r in results),
             "flagged":sum(not r["metrics"]["machine_asr_consistent"] for r in results),
             "all_clips_model_checked":len(results)==len(scene),
             "audible_word_fidelity_certified":False,
             "human_listening_review_complete":False}
    (out/"asr_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf8")
    return summary

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--plan",required=True,type=Path)
    ap.add_argument("--audio",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    ap.add_argument("--max-clips",type=int,default=500)
    ap.add_argument("--model",default=ASR_MODEL,choices=sorted(ALLOWED_MODELS))
    ap.add_argument("--confirm-live",action="store_true")
    a=ap.parse_args()
    summary=run(plan=a.plan,audio=a.audio,out=a.output,
        max_clips=a.max_clips,confirm=a.confirm_live,model=a.model)
    print(json.dumps(summary,indent=2))
    if summary["provider_error_type"]:
        raise SystemExit(2)

if __name__=="__main__":main()
