"""Explicit live Gemini per-element narration for REVIEW-only source-bound media.

Never invoked automatically by staging, tests, or the production runner.
The preview voice remains uniform: any failure aborts instead of mixing voices.
Resume requires an exact stable input-plan hash and identical provider identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import wave
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plan_hash(plan:dict)->str:
    return digest(json.dumps(plan,ensure_ascii=False,sort_keys=True,
        separators=(",",":"),allow_nan=False).encode("utf8"))


def emit(path:Path, data:dict)->None:
    # Exclusive creation for durable immutable receipts.
    with path.open("x",encoding="utf8") as out:
        json.dump(data,out,indent=2,ensure_ascii=False)
        out.write("\n")


def segments(plan):
    for part in plan["parts"]:
        for slide in part["slides"]:
            for event in slide["elements"]:
                yield event


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--authored-plan",type=Path,required=True)
    p.add_argument("--output-folder",type=Path,required=True)
    p.add_argument("--voice",default="Kore")
    p.add_argument("--model",default="gemini-3.8-flash-lite-tts")
    p.add_argument("--resume",action="store_true")
    p.add_argument("--confirm-live",action="store_true")
    args=p.parse_args(argv)
    if not args.confirm_live:
        p.error("No network/TTS request without --confirm-live")
    if args.model not in {"gemini-3.8-flash-lite-tts","gemini-3.8-flash-tts"}:
        p.error("Only explicitly supported Gemini TTS models allowed")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,30}",args.voice):
        p.error("Invalid voice identifier")
    src=args.authored_plan.resolve()
    folder=args.output_folder.resolve()
    if not src.is_file() or src.is_symlink():
        p.error("Missing non-symlink authored plan")
    plan=json.loads(src.read_text(encoding="utf8"))
    if (plan.get("schema_version")!=1 or
        plan.get("status")!="author_specified_unapproved_element_narration"):
        p.error("An explicit unapproved element-level plan is required")
    all_rows=list(segments(plan))
    if not 1<=len(all_rows)<=300:
        p.error("Invalid segment count")
    filenames=[]
    for row in all_rows:
        filename=row.get("wav")
        text=row.get("spoken_text")
        if (not isinstance(filename,str) or
            not re.fullmatch(r"[A-Za-z0-9_.-]+\.wav",filename) or
            not isinstance(text,str) or len(text.split())<4 or len(text)>2000):
            p.error("Unsafe filename or unusable speech text")
        filenames.append(filename)
    if len(filenames)!=len(set(filenames)):
        p.error("Duplicate element narration filenames")
    if src.is_relative_to(folder):
        p.error("TTS output must not be inside authored plan folder")
    voice_id=f"gemini_{args.model}_{args.voice}_REVIEW_ONLY"
    identity={"schema_version":1,"status":"review_tts_incomplete",
        "plan_sha256":plan_hash(plan),"provider":"gemini",
        "model":args.model,"voice":args.voice,"voice_id":voice_id,
        "segments":filenames}
    identity_path=folder/"tts_job_identity.json"
    if args.resume:
        if not folder.is_dir() or not identity_path.is_file():
            p.error("Resume requires existing bound job identity")
        existing=json.loads(identity_path.read_text(encoding="utf8"))
        if existing!=identity:
            p.error("Resume source/voice/segments differ from frozen job")
        if (folder/"tts_synthesis_receipt.json").exists():
            p.error("Completed live synthesis is immutable")
    else:
        if folder.exists() or not folder.parent.is_dir():
            p.error("Output folder must be new and its parent must exist")
        folder.mkdir()
        emit(identity_path,identity)

    from .runner import load_microvid_env
    from .tts import _gemini_say_with_watchdog
    from gemini_keys import get_gemini_api_keys
    load_microvid_env()
    if not get_gemini_api_keys():
        raise RuntimeError("Gemini keys not configured; no audio generated")

    fmt_reference=None
    rows=[]
    for index,record in enumerate(all_rows,1):
        filename=record["wav"]
        target=folder/filename
        words=record["spoken_text"]
        receipt_path=folder/(filename+".verified.json")
        receipt_expected={
            "plan_sha256":identity["plan_sha256"],
            "filename":filename,
            "spoken_text_sha256":digest(words.encode("utf8")),
            "model":args.model,"voice":args.voice,
        }
        if target.exists():
            if not args.resume or not target.is_file() or target.is_symlink():
                raise RuntimeError("Cannot overwrite existing audio: "+filename)
            if not receipt_path.is_file() or receipt_path.is_symlink():
                raise RuntimeError("Unverified existing WAV; refuse resume: "+filename)
            prior=json.loads(receipt_path.read_text(encoding="utf8"))
            for key,value in receipt_expected.items():
                if prior.get(key)!=value:
                    raise RuntimeError("Resumed WAV provenance mismatch: "+filename)
            if prior.get("wav_sha256")!=digest(target.read_bytes()):
                raise RuntimeError("Resumed WAV byte hash mismatch: "+filename)
            print(f"REUSE cryptographically verified {filename}",flush=True)
        else:
            if receipt_path.exists():
                raise RuntimeError("Orphaned WAV receipt present: "+filename)
            print(f"Gemini TTS element {index}/{len(all_rows)} {filename}",flush=True)
            payload=_gemini_say_with_watchdog(
                words,index,args.model,args.voice,
                attempts_override=1,allow_chunking=False,
                request_label=f"element_{index}")
            if not payload.startswith((b"RIFF",b"RF64")):
                raise RuntimeError("Provider returned non-WAV data")
            partial=folder/(filename+".partial")
            if partial.exists(): raise FileExistsError(partial)
            with partial.open("xb") as stream:
                stream.write(payload)
            partial.rename(target)
        with wave.open(str(target),"rb") as wav:
            fmt=(wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),
                 wav.getcomptype())
            duration=wav.getnframes()/wav.getframerate()
        if fmt[3]!="NONE" or fmt[0] not in (1,2) or fmt[1]!=2 or not .2<duration<120:
            raise RuntimeError("Invalid provider WAV spec: "+filename)
        if not receipt_path.exists():
            emit(receipt_path,{**receipt_expected,
                "wav_sha256":digest(target.read_bytes()),
                "sample_rate":fmt[2],"channels":fmt[0],
                "duration_s":round(duration,3)})
        if fmt_reference is None:fmt_reference=fmt
        elif fmt!=fmt_reference:
            raise RuntimeError("Inconsistent TTS audio format, refusing mixed media")
        rows.append({"filename":filename,
                     "spoken_text_sha256":digest(words.encode("utf8")),
                     "wav_sha256":digest(target.read_bytes()),
                     "audio_duration_seconds":round(duration,3),
                     "model":args.model,"voice":args.voice})
    copied=dict(plan)
    copied["voice_id"]=voice_id
    emit(folder/"gemini_test_voice_plan.json",copied)
    emit(folder/"tts_synthesis_receipt.json",{
        "status":"real_gemini_tts_generated_review_only_word_fidelity_unverified",
        "original_plan_sha256":identity["plan_sha256"],
        "provider":"gemini","model":args.model,"voice":args.voice,
        "same_declared_voice_all_segments":True,
        "perceptual_voice_identity_unverified":True,
        "source_academic_approval":False,
        "audible_word_fidelity_verified":False,
        "segments":rows,
    })
    print(json.dumps({"status":"review_only",
       "elements_synthesized":len(rows),"model":args.model,"voice":args.voice,
       "audio_seconds":round(sum(x["audio_duration_seconds"] for x in rows),3),
       "output":str(folder)},indent=2),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
