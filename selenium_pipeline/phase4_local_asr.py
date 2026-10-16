"""Offline, explicitly model-pinned ASR QA. Never downloads or calls a model API.

Run only against a preinstalled local CTranslate2 Whisper directory, with
separate, immutable per-WAV ASR proof and the exact source narration hashes.
No AI transcription certifies scholarly accuracy or spoken pronunciation.
"""
from __future__ import annotations
import argparse,hashlib,json,re,time
from pathlib import Path
from typing import Callable
from .tts_quality_gate import word_error_rate,tokens
from .independent_speech_audit import check_wav,sha,write_x

MODELS={
    "base.en":"faster-whisper-base.en-cpu-int8",
    "small.en":"faster-whisper-small.en-cpu-int8",
}
REQUIRED_MODEL_FILES=("model.bin","config.json","tokenizer.json")

def filehash(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def model_identity(model_path:Path,model_size:str)->dict:
    if model_size not in MODELS:raise ValueError("Unsupported offline model size")
    model_path=Path(model_path).resolve()
    if not model_path.is_dir() or model_path.is_symlink():
        raise ValueError("No local model directory; online loading is forbidden")
    files={}
    for filename in REQUIRED_MODEL_FILES:
        p=model_path/filename
        if not p.is_file() or p.is_symlink() or p.stat().st_size==0:
            raise ValueError("Missing or unsafe local model: "+filename)
        files[filename]=filehash(p)
    digest=sha(json.dumps(files,sort_keys=True).encode("utf8"))
    return {"model_id":MODELS[model_size],
            "model_size":model_size,"model_sha256":digest,
            "files_sha256":files}

def _read(p:Path)->dict:return json.loads(p.read_text(encoding="utf8"))

def _engine(model_dir:Path)->Callable[[Path],str]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Offline faster-whisper is not installed; no API fallback") from exc
    engine=WhisperModel(str(model_dir),device="cpu",compute_type="int8",
                        num_workers=1,local_files_only=True)
    def recognize(wav:Path)->str:
        segments,_=engine.transcribe(str(wav),beam_size=5,language="en",
                      temperature=0.0,condition_on_previous_text=False,
                      vad_filter=False)
        response=" ".join(x.text.strip() for x in segments).strip()
        if len(tokens(response))<2:
            raise ValueError("Offline speech recognition found no intelligible words")
        return response
    return recognize

def run(*,plan:Path,audio:Path,model_dir:Path,model_size:str,
        out:Path,max_new:int=2,recognizer=None,
        include_wavs:list[str]|None=None)->dict:
    if not 1<=max_new<=500:raise ValueError("Invalid bounded max_new")
    plan,audio,out=(Path(x).resolve() for x in (plan,audio,out))
    if (not plan.is_file() or not audio.is_dir() or
            out.is_relative_to(audio) or out==plan.parent or
            out.is_relative_to(Path(model_dir).resolve())):
        raise ValueError("ASR evidence must stay away from source audio and model")
    authored=_read(plan)
    if authored.get("status")!="author_specified_unapproved_element_narration":
        raise ValueError("Authored narration plan required")
    scenes=[el for part in authored["parts"] for sl in part["slides"]
            for el in sl["elements"]]
    names=[el["wav"] for el in scenes]
    if not 1<=len(names)<=500 or len(set(names))!=len(names) or not all(
            re.fullmatch(r"[A-Za-z0-9_.-]+\.wav",n) for n in names):
        raise ValueError("Unsafe/duplicated filenames or empty plan")
    # Select a targeted mathematical sample without changing the frozen
    # full-lecture ASR job identity. The next run can resume other clips.
    selection=set(include_wavs) if include_wavs is not None else None
    if selection is not None and (
            not selection or len(selection)!=len(include_wavs)
            or not selection.issubset(set(names))):
        raise ValueError("Requested benchmark clips must be unique WAVs in the plan")
    identity=model_identity(model_dir,model_size)
    signature={"schema_version":1,"status":"independent_model_asr_review_only",
       "plan_sha256":filehash(plan),"model":identity["model_id"],
       "source_model":"gemini-3.8-flash-lite-tts","clips":names,
       "backend":"local_cpu_ctranslate2_no_network",
       "model_sha256":identity["model_sha256"],
       "model_file_hashes":identity["files_sha256"],
       "download_allowed":False,"api_calls_allowed":False}
    if not out.exists():out.mkdir()
    if not out.is_dir():raise ValueError("Output is not a directory")
    job=out/"asr_job.json"
    if job.exists():
        if _read(job)!=signature:
            raise ValueError("Model/plan/audio job identity changed")
    else:
        if any(out.iterdir()):raise ValueError("Nonempty unbound output")
        write_x(job,signature)
    new=0; reused=0; failed=None
    recognize=recognizer
    for el in scenes:
        if selection is not None and el["wav"] not in selection:
            continue
        name,expected=el["wav"],el["spoken_text"]
        wav=audio/name
        if not wav.is_file() or wav.is_symlink():
            raise ValueError("Unsafe or missing WAV in plan")
        audio_bytes=check_wav(wav)
        wav_sha=sha(audio_bytes);ref_sha=sha(expected.encode("utf8"))
        receipt=out/(name+".asr.json")
        if receipt.is_file():
            rec=_read(receipt)
            if (rec.get("wav")!=name or rec.get("wav_sha256")!=wav_sha
                or rec.get("reference_sha256")!=ref_sha
                or rec.get("asr_model")!=identity["model_id"]
                or rec.get("model_sha256")!=identity["model_sha256"]
                or rec.get("transcript_sha256")!=
                       sha(str(rec.get("transcript","")).encode("utf8"))):
                raise ValueError("Existing local ASR transcript stale or tampered")
            reused+=1
            continue
        if new>=max_new:break
        try:
            if recognize is None:recognize=_engine(Path(model_dir).resolve())
            transcript=recognize(wav)
            if not isinstance(transcript,str) or len(tokens(transcript))<2:
                raise ValueError("No intelligible local ASR transcript")
            score=word_error_rate(expected,transcript)
            rec={"status":("machine_asr_consistent_not_certified" if score<=.20
                            else "speech_review_required"),
                 "wav":name,"wav_sha256":wav_sha,
                 "reference_sha256":ref_sha,"asr_model":identity["model_id"],
                 "model_sha256":identity["model_sha256"],
                 "transcript":transcript,
                 "transcript_sha256":sha(transcript.encode("utf8")),
                 "metrics":{"wer":score,"reference_words":len(tokens(expected)),
                   "asr_words":len(tokens(transcript)),
                   "machine_asr_consistent":score<=.20},
                 "backend":"local_cpu_ctranslate2_no_network",
                 "voice_quality_human_approved":False,
                 "model_independent_of_gemini":True,
                 "audible_word_fidelity_certified":False,
                 "academic_approval":False}
            write_x(receipt,rec);new+=1
            print(f"LOCAL_ASR {new}/{max_new} {name}: WER {score:.3f}",flush=True)
        except Exception as exc:
            failed=type(exc).__name__
            print(f"LOCAL_ASR stopped at {name}: {failed}",flush=True)
            break
    completed=len(list(out.glob("*.wav.asr.json")))
    result={"status":("OFFLINE_ASR_INCOMPLETE_ERROR" if failed else
                      "OFFLINE_ASR_REVIEW_ONLY"),
            "model":identity["model_id"],
            "model_sha256":identity["model_sha256"],
            "total_clips":len(scenes),
            "selected_in_this_run":len(selection) if selection is not None else len(scenes),
            "completed_receipts":completed,
            "remaining":len(scenes)-completed,"new_receipts":new,
            "reused":reused,"error_type":failed,
            "network_model_fetch_performed":False,
            "api_calls_performed":False,
            "human_approved":False,"production_approved":False}
    state=out/"offline_asr_state.json"
    tmp=out/".offline_asr_state.partial"
    tmp.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    tmp.replace(state)
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("plan","audio","model-dir","output"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--model-size",choices=sorted(MODELS),required=True)
    p.add_argument("--max-new",type=int,default=2)
    p.add_argument("--include-wav",action="append",
                   help="Exact authored WAV filename; repeat for targeted sample")
    args=p.parse_args()
    result=run(plan=args.plan,audio=args.audio,
               model_dir=args.model_dir,model_size=args.model_size,
               out=args.output,max_new=args.max_new,
               include_wavs=args.include_wav)
    print(json.dumps(result,indent=2))
    if result["error_type"]:raise SystemExit(2)

if __name__=="__main__":main()
