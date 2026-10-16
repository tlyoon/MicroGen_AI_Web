"""Bounded, resumable, explicitly opted-in Gemini WEB-UI audio transcription.

Uses the isolated Selenium-owned Gemini browser tab; never calls Gemini APIs.
One immutable, SHA-bound transcript receipt per clip. Retries provider errors
with bounded backoff but does not hide mathematical transcript discrepancies.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from .independent_speech_audit import check_wav, distance, sha, write_x
from .phase4_browser_asr import (
    MODEL_ID, transcribe, AudioUnsupportedError,
    AmbiguousBrowserResponseError)

def _hash_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def _valid(ok:bool,detail:str)->None:
    if not ok:raise ValueError(detail)

def _read(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf8"))

def _atomic_state(path:Path,obj:dict)->None:
    tmp=path.with_name(f".{path.name}.{os.getpid()}.partial")
    with tmp.open("x",encoding="utf8") as stream:
        json.dump(obj,stream,indent=2,ensure_ascii=False);stream.write("\n")
    os.replace(tmp,path)

def _job(plan:Path,clips:list[str])->dict:
    return {"schema_version":1,
            "status":"independent_model_asr_review_only",
            "plan_sha256":_hash_file(plan),
            "model":MODEL_ID,
            "source_model":"gemini-3.8-flash-lite-tts",
            "clips":clips}

def recover(*,plan:Path,audio:Path,out:Path,confirmed:bool=False,
            max_new:int=2,retries:int=2,cooldown_s:float=5,
            port:int=9222,wait_cap_s:int=180,
            backend=None,sleep=time.sleep)->dict:
    if not confirmed:
        raise ValueError("Live browser ASR requires explicit --confirm-live")
    if not (1<=max_new<=500 and 1<=retries<=3 and 0<=cooldown_s<=60):
        raise ValueError("Out-of-range retry limit, clip limit, or cooldown")
    if not (30<=wait_cap_s<=420 and 1<=port<=65535):
        raise ValueError("Invalid browser wait or port")
    plan,audio,out=(Path(x).resolve() for x in (plan,audio,out))
    _valid(plan.is_file() and audio.is_dir(),"Missing original audio or authored plan")
    _valid(not out.is_relative_to(audio) and out!=plan.parent
           and out!=audio and out!=plan.parent,
           "Output must be isolated from original narration source")
    data=_read(plan)
    _valid(data.get("status")=="author_specified_unapproved_element_narration",
           "No valid source-bound authored plan")
    entries=[el for part in data["parts"] for sl in part["slides"]
             for el in sl["elements"]]
    files=[el["wav"] for el in entries]
    _valid(1<=len(entries)<=500 and len(set(files))==len(files),
           "Empty, duplicate or excessive clip manifest")
    _valid(all(re.fullmatch(r"[A-Za-z0-9_.-]+\.wav",v) for v in files),
           "Unsafe narration filename")
    signature=_job(plan,files)
    if not out.exists():
        out.mkdir()
    _valid(out.is_dir(),"ASR output must be a directory")
    existing=out/"asr_job.json"
    if existing.exists():
        _valid(_read(existing)==signature,
               "Previous browser job uses different model, plan or files")
    else:
        _valid(not list(out.iterdir()),"Refusing nonempty unbound ASR folder")
        write_x(existing,signature)
    attempted=0
    new=0
    outage=None
    consistent=0
    flagged=0
    saved=0
    for el in entries:
        wav=audio/el["wav"]
        _valid(wav.is_file() and not wav.is_symlink(),"Missing or unsafe WAV file")
        data_bytes=check_wav(wav)
        audio_sha=sha(data_bytes)
        expected=el["spoken_text"]
        script_sha=sha(expected.encode("utf8"))
        receipt=out/(el["wav"]+".asr.json")
        if receipt.is_file():
            r=_read(receipt)
            _valid(r.get("wav")==el["wav"]
                   and r.get("wav_sha256")==audio_sha
                   and r.get("reference_sha256")==script_sha
                   and r.get("asr_model")==MODEL_ID
                   and r.get("transcript_sha256")==
                           sha(r.get("transcript","").encode("utf8")),
                   "Existing transcription receipt is stale or tampered")
            saved+=1
        else:
            if new>=max_new:break
            r=None
            for attempt in range(1,retries+1):
                attempted+=1
                try:
                    recognized=(backend(wav) if backend is not None
                                else transcribe(wav,port=port,wait_cap_s=wait_cap_s))
                    _valid(isinstance(recognized,str) and len(recognized.split())>=2,
                           "No intelligible model transcription")
                    score=distance(expected,recognized)
                    r={"status":("machine_asr_consistent_not_certified"
                                 if score["machine_asr_consistent"]
                                 else "speech_review_required"),
                       "wav":el["wav"],"wav_sha256":audio_sha,
                       "reference_sha256":script_sha,
                       "asr_model":MODEL_ID,
                       "transcript":recognized,
                       "transcript_sha256":sha(recognized.encode("utf8")),
                       "metrics":score,
                       "backend":"selenium_flash_browser",
                       "exact_web_model_version_unverified":True,
                       "model_distinct_from_tts":False,
                       "model_difference_not_independently_verified":True,
                       "same_vendor_not_human_independent":True,
                       "audible_word_fidelity_certified":False,
                       "academic_approval":False}
                    write_x(receipt,r)
                    outage=None
                    new+=1
                    print(f"[Phase4] real browser ASR verified clip {el['wav']}: "
                          f"WER={score['wer']}",flush=True)
                    break
                except (AudioUnsupportedError,
                        AmbiguousBrowserResponseError) as exc:
                    # Unsupported audio cannot be cured by another prompt.
                    # Ambiguous completion must not be blindly re-submitted.
                    outage=type(exc).__name__
                    break
                except Exception as exc:
                    # Never skip a bad WAV or overwrite previous evidence.
                    outage=type(exc).__name__
                    if attempt<retries:
                        sleep(cooldown_s*attempt)
            if r is None:
                print(f"[Phase4] stop on browser outage at {el['wav']}: {outage}",
                      flush=True)
                break
        if r["metrics"]["machine_asr_consistent"]:
            consistent+=1
        else:
            flagged+=1
    all_receipts=list(out.glob("*.wav.asr.json"))
    state=("WEB_AUDIO_UNSUPPORTED_REVIEW_BLOCKED"
           if outage=="AudioUnsupportedError"
           else "WEB_RESPONSE_AMBIGUOUS_REVIEW_BLOCKED"
           if outage=="AmbiguousBrowserResponseError"
           else "WEB_ASR_INCOMPLETE_PROVIDER_ERROR" if outage
           else "WEB_ASR_REVIEW_ONLY_NOT_PRODUCTION_APPROVAL")
    report={"status":state,
            "total_clips":len(entries),
            "completed_receipts":len(all_receipts),
            "still_untranscribed":len(entries)-len(all_receipts),
            "reused_verified_receipts":saved,
            "newly_transcribed":new,
            "attempts_this_run":attempted,
            "provider_error_type":outage,
            "model":MODEL_ID,
            "plan_sha256":signature["plan_sha256"],
            "source_audio_unchanged":True,
            "api_calls_performed":False,
            "production_approved":False,
            "human_listening_approved":False}
    _atomic_state(out/"phase4_recovery_state.json",report)
    return report

def main():
    p=argparse.ArgumentParser()
    for arg in ("plan","audio","output"):
        p.add_argument("--"+arg,type=Path,required=True)
    p.add_argument("--max-new",type=int,default=2)
    p.add_argument("--retries",type=int,default=2)
    p.add_argument("--cooldown",type=float,default=5)
    p.add_argument("--port",type=int,default=9222)
    p.add_argument("--wait-cap",type=int,default=180)
    p.add_argument("--confirm-live",action="store_true")
    a=p.parse_args()
    data=recover(plan=a.plan,audio=a.audio,out=a.output,
                 confirmed=a.confirm_live,max_new=a.max_new,
                 retries=a.retries,cooldown_s=a.cooldown,port=a.port,
                 wait_cap_s=a.wait_cap)
    print(json.dumps(data,indent=2))
    if data["provider_error_type"]:
        raise SystemExit(2)

if __name__=="__main__":main()
