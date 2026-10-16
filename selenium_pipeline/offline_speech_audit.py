"""Local offline Whisper cross-check; strictly REVIEW ONLY, never academic approval.

A downloaded model is pinned by SHA256 of its files. The recording is supplied
WITHOUT the expected spoken text, preserving true independent model evidence.
An ASR match is probabilistic, not verbatim proof or a physics correctness check.
"""
from __future__ import annotations
import argparse,hashlib,io,json,os,re,wave
from pathlib import Path
from .independent_speech_audit import distance,check_wav,sha,write_x

BACKEND="faster-whisper-small.en-cpu-int8"
SOURCE_MODEL="gemini-3.8-flash-lite-tts"

def model_digest(path:Path)->str:
    path=Path(path).resolve()
    if not path.is_dir() or not (path/"model.bin").is_file() or not (path/"config.json").is_file():
        raise ValueError("Offline Whisper model weights and config missing")
    h=hashlib.sha256()
    files=sorted(p for p in path.rglob("*") if p.is_file() and not p.is_symlink()
                 and ".cache" not in p.relative_to(path).parts)
    if not files:raise ValueError("Empty model")
    for p in files:
        h.update(str(p.relative_to(path)).replace("\\","/").encode("utf8"))
        with p.open("rb") as stream:
            for chunk in iter(lambda:stream.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def whisper_version():
    try:
        from importlib.metadata import version
        return version("faster-whisper")
    except Exception:
        return "dependency-not-installed-in-test"


def whisper_transcriber(model):
    import numpy as np
    def transcribe(audio:bytes)->str:
        with wave.open(io.BytesIO(audio),"rb") as wav:
            if (wav.getnchannels()!=1 or wav.getsampwidth()!=2 or
                    wav.getframerate()!=24000):
                raise ValueError("Recorded source audio is not 24kHz mono PCM16")
            buf=wav.readframes(wav.getnframes())
        speech=np.frombuffer(buf,dtype="<i2").astype("float32")/32768.0
        # faster-whisper on numpy expects the model's 16kHz input signal.
        # Resample with deterministic scipy if available; otherwise use exact
        # 3-to-2 polyphase implementation via av.AudioResampler.
        import av
        frame=av.AudioFrame.from_ndarray((np.clip(speech,-1,1)*32767).astype("<i2").reshape(1,-1),format="s16",layout="mono")
        frame.sample_rate=24000
        resampler=av.AudioResampler(format="s16",layout="mono",rate=16000)
        output=resampler.resample(frame)+resampler.resample(None)
        pcm=np.concatenate([f.to_ndarray().reshape(-1) for f in output]).astype("float32")/32768.0
        segments,info=model.transcribe(pcm,language="en",beam_size=5,
            temperature=0,condition_on_previous_text=False,
            vad_filter=False,without_timestamps=True)
        text=" ".join(s.text.strip() for s in segments).strip()
        if len(text.split())<2:
            raise RuntimeError("Offline ASR returned no meaningful words")
        return text
    return transcribe

def run(*,plan:Path,audio:Path,out:Path,model_path:Path,
        max_clips:int=500,transcriber=None):
    plan=Path(plan).resolve()
    audio=Path(audio).resolve()
    out=Path(out).resolve()
    model_path=Path(model_path).resolve()
    if not plan.is_file() or not audio.is_dir() or not 1<=max_clips<=500:
        raise ValueError("Frozen plan and recorded audio required")
    if (out.is_relative_to(audio) or out==plan or
            out.is_relative_to(model_path)):
        raise ValueError("Refuse to write inside immutable source/audio/model files")
    data=json.loads(plan.read_text(encoding="utf8"))
    if data.get("status")!="author_specified_unapproved_element_narration":
        raise ValueError("Source-bound review-only narration plan required")
    events=[el for p in data["parts"] for slide in p["slides"] for el in slide["elements"]]
    if not events or len(events)>500 or len({x["wav"] for x in events})!=len(events):
        raise ValueError("Duplicate or empty narration elements")
    audio_job=json.loads((audio/"tts_synthesis_receipt.json").read_text(encoding="utf8"))
    if (audio_job.get("voice")!="Kore" or audio_job.get("model")!=SOURCE_MODEL or
            audio_job.get("same_declared_voice_all_segments") is not True):
        raise ValueError("Unexpected TTS original voice/model")
    model_sha=model_digest(model_path)
    ident={"schema_version":1,"status":"offline_machine_asr_review_only",
           "backend":"offline_faster_whisper",
           "model":BACKEND,"model_sha256":model_sha,
           "source_model":SOURCE_MODEL,
           "plan_sha256":sha(plan.read_bytes()),
           "tts_synthesis_receipt_sha256":sha((audio/"tts_synthesis_receipt.json").read_bytes()),
           "clips":[x["wav"] for x in events]}
    if not out.exists():out.mkdir()
    if not out.is_dir():raise ValueError("Output path is not a directory")
    job=out/"asr_job.json"
    if job.exists():
        if json.loads(job.read_text(encoding="utf8"))!=ident:
            raise ValueError("Existing ASR job is bound to another model or script")
    else:
        if list(out.iterdir()):raise ValueError("Output folder has unbound contents")
        write_x(job,ident)
    from importlib.metadata import version
    results=[]
    failure=None
    for i,el in enumerate(events[:max_clips],1):
        name=el["wav"]
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+\.wav",name):
            raise ValueError("Unsafe audio filename")
        src=(audio/name).resolve()
        if not src.is_relative_to(audio) or not src.is_file() or src.is_symlink():
            raise ValueError("Missing/unsafe audio segment")
        pcm=check_wav(src)
        spoken=el["spoken_text"]
        transcript_sha=sha(spoken.encode("utf8"))
        row=out/(name+".asr.json")
        if row.exists():
            result=json.loads(row.read_text(encoding="utf8"))
            if (result["wav_sha256"]!=sha(pcm) or
                result["reference_sha256"]!=transcript_sha or
                result["asr_model"]!=BACKEND or
                result["model_sha256"]!=model_sha or
                result["transcript_sha256"]!=sha(result["transcript"].encode("utf8"))):
                raise ValueError("Existing offline transcript evidence stale/tampered")
        else:
            if transcriber is None:
                from faster_whisper import WhisperModel
                transcriber=whisper_transcriber(
                    WhisperModel(str(model_path),device="cpu",
                        compute_type="int8",cpu_threads=min(os.cpu_count() or 4,6)))
            try:
                recognized=transcriber(pcm)
                scores=distance(spoken,recognized)
                result={"status":("machine_asr_consistent_not_certified"
                            if scores["machine_asr_consistent"]
                            else "speech_review_required"),
                       "wav":name,"wav_sha256":sha(pcm),
                       "reference_sha256":transcript_sha,
                       "asr_model":BACKEND,"backend":"offline_faster_whisper",
                       "model_sha256":model_sha,
                       "recognizer_version":whisper_version(),
                       "model_distinct_from_tts":True,
                       "same_vendor_not_human_independent":False,
                       "transcript":recognized,
                       "transcript_sha256":sha(recognized.encode("utf8")),
                       "metrics":scores,
                       "audible_word_fidelity_certified":False,
                       "academic_approval":False}
                write_x(row,result)
            except Exception as exc:
                failure=type(exc).__name__
                print("OFFLINE_ASR_FAILURE",i,name,failure,flush=True)
                break
        results.append(result)
        print("OFFLINE_ASR",i,len(events),name,
              "WER",result["metrics"]["wer"],result["status"],flush=True)
    summary={"status":("OFFLINE_ASR_INCOMPLETE" if failure else
              "OFFLINE_ASR_REVIEW_ONLY_NOT_PRODUCTION_APPROVAL"),
             "model":BACKEND,"model_sha256":model_sha,
             "provider_error_type":failure,
             "total_elements":len(events),"examined":len(results),
             "unexamined":len(events)-len(results),
             "consistent":sum(r["metrics"]["machine_asr_consistent"] for r in results),
             "flagged":sum(not r["metrics"]["machine_asr_consistent"] for r in results),
             "all_clips_model_checked":len(results)==len(events),
             "audible_word_fidelity_certified":False,
             "human_listening_review_complete":False}
    (out/"asr_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf8")
    return summary

def main():
    p=argparse.ArgumentParser()
    for x in ("plan","audio","output","model-dir"):
        p.add_argument("--"+x,required=True,type=Path)
    p.add_argument("--max-clips",type=int,default=500)
    args=p.parse_args()
    result=run(plan=args.plan,audio=args.audio,out=args.output,
            model_path=args.model_dir,max_clips=args.max_clips)
    print(json.dumps(result,indent=2))
    if result["provider_error_type"]:raise SystemExit(2)

if __name__=="__main__":main()
