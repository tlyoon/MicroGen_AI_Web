"""One-shot source-bound original Slide4 Flash-Lite/Kore TTS candidate batch.

For each corrected utterance use exactly ONE direct Gemini 3.8 Interactions
provider attempt, one API key, zero SDK/local retries, and no Cloud fallback.
An existing verified utterance-1 WAV is imported from the earlier repaired
one-shot checkpoint, not silently re-generated.

NEVER promote PCM or claimed model/voice to verified audible words, independent
mathematics acceptance, synchronized media, or student publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone
import wave

from .offline_corrected_bundle_verify import (
    strict_json, verify_original_five_bundle,
)
from .original_replacement_video_handoff import _sha
from .gemini38_tts_interactions import APPROVED_VOICE, APPROVED_MODELS


class OneShotKoreBatchError(RuntimeError):
    pass


def require(condition:bool,why:str)->None:
    if not condition:raise OneShotKoreBatchError(why)


def now()->str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_receipt(path:Path,obj:dict)->None:
    temp=path.with_name(path.name+".tmp")
    require(not temp.exists(),"Prior uncommitted checkpoint; no resubmit")
    with temp.open("x",encoding="utf8") as f:
        json.dump(obj,f,indent=2,ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp,path)


def _source_hashes(root:Path)->dict[str,str]:
    return {name:_sha(root/name) for name in (
        "source.pdf","slides.pdf","script.txt","slide4.wav","slides.mp4")}


def _wave_receipt(path:Path)->dict:
    require(path.is_file() and not path.is_symlink()
            and 10000<=path.stat().st_size<=30000000,
            "Missing/symlinked/implausibly-sized real TTS WAV")
    with wave.open(str(path),"rb") as w:
        channels=w.getnchannels()
        width=w.getsampwidth()
        rate=w.getframerate()
        frames=w.getnframes()
        require(w.getcomptype()=="NONE" and channels==1 and width==2
                and rate==24000 and .25<frames/rate<150,
                "Expected mono 16-bit 24 kHz Gemini 3.8 WAV")
    return {
        "sha256":_sha(path),"duration_s":round(frames/rate,6),
        "frames":frames,"rate_hz":rate,
    }


def _single_gemini_key_environment()->dict[str,str]:
    from .runner import load_microvid_env
    from gemini_keys import get_gemini_api_keys
    from .tts_billing_guard import require_tts_cost_authorization

    load_microvid_env()
    require_tts_cost_authorization("gemini",routine_gemini=True)
    keys=get_gemini_api_keys()
    require(len(keys)>=1,"No authorized Gemini TTS credentials")
    env=dict(os.environ)
    for name in list(env):
        if name in ("GEMINI_API_KEY","GEMINI_API_KEYS") or (
                name.startswith("GEMINI_API_KEY_") and
                name[len("GEMINI_API_KEY_"):].isdigit()):
            env.pop(name,None)
    # Preserve ONLY the highest-priority existing authorized key; never log.
    env["GEMINI_API_KEY_1"]=keys[0]
    env.update({
        "MICROGEN_GEMINI_MAX_RETRIES":"0",
        "MICROGEN_GEMINI_TRANSIENT_RETRIES_PER_KEY":"1",
        "MICROGEN_GEMINI_SDK_RETRY_ATTEMPTS":"1",
        "MICROGEN_GEMINI_REQUEST_TIMEOUT_MS":"65000",
        "MICROGEN_GEMINI_BACKOFF_BASE_SECONDS":"1",
        "MICROGEN_GEMINI_BACKOFF_MAX_SECONDS":"1",
        "PYTHONIOENCODING":"utf8",
    })
    return env


def run_remaining_corrected_utterances(
    *,original:Path,bundle:Path,
    previous_one_shot:Path,out:Path,worker_python:Path,
    dispatch_one_request_per_utterance:bool=False,
)->dict:
    root=Path(original).absolute()
    source_bundle=Path(bundle).absolute()
    prior=Path(previous_one_shot).absolute()
    dest=Path(out).absolute()
    python=Path(worker_python).absolute()
    require(dest.parent.is_dir() and not dest.parent.is_symlink()
            and not dest.exists() and not dest.is_relative_to(root)
            and not dest.is_relative_to(source_bundle)
            and not dest.is_relative_to(prior),
            "Exclusive external output directory needed for actual new TTS")
    require(python.is_file() and not python.is_symlink(),
            "Separate pinned Windows modern-SDK Python interpreter required")
    # Fail WITHOUT touching a billable provider if caller forgot approval.
    require(dispatch_one_request_per_utterance,
            "Real paid routine TTS audition requires explicit dispatch flag")
    root_before=_source_hashes(root)
    visual=verify_original_five_bundle(original=root,bundle=source_bundle)
    doc=strict_json(source_bundle/"FIVE_CORRECTED_SEGMENTS_UNAPPROVED.json")
    require(visual["verified_image_count"]==5 and doc["segment_count"]==5
            and doc["source_sha256"]==root_before["source.pdf"]
            and doc["slides_sha256"]==root_before["slides.pdf"]
            and doc["script_sha256"]==root_before["script.txt"]
            and doc["historical_slide4_WAV_sha256"]==root_before["slide4.wav"]
            and doc["independent_two_pass_math_acceptance"] is False,
            "Source/pixel/academic status changed from source-verified handoff")

    first_report=strict_json(prior/"attempt_report.json")
    require(first_report.get("status")==
            "GENUINE_ONE_NEW_PCM_WAV_RECEIVED_AWAITING_SPEECH_QA"
            and first_report.get("source_originals_unchanged") is True
            and first_report.get("model")=="gemini-3.8-flash-lite-tts"
            and first_report.get("voice_requested")==APPROVED_VOICE
            and first_report.get("provider_evidence_outcome")=="success"
            and first_report.get("corrected_utterance_text_sha256")==
                doc["source_verified_tts_highlight_units"][0]["corrected_tts_text_sha256"],
            "Prior one-shot first utterance/source/model mismatch")
    previous_wav=prior/"new_Kore_utterance_001.wav"
    first=_wave_receipt(previous_wav)
    require(first["sha256"]==first_report.get("wav_sha256"),
            "First real original utterance WAV changed from old receipt")
    history={_sha(p) for sub in ("8.4","8.5","8.6")
             for p in (root.parent/sub).glob("slide*.wav")}
    require(first["sha256"] not in history,
            "First repaired WAV is identical to historical output")
    existing_digests={first["sha256"]}
    units=doc["source_verified_tts_highlight_units"]
    require(len(units)==5 and
            all(u["preferred_provider"]=="Gemini web Flash-Lite TTS"
                and u["preferred_voice"]==APPROVED_VOICE
                for u in units),
            "Source signed voice/provider identity mismatch")
    model="gemini-3.8-flash-lite-tts"
    require(model in APPROVED_MODELS,
            "Nonprimary model not authorized for initial TTS")
    # Validate pinned Windows interpreter is ready; NO client network call.
    preflight=subprocess.run(
        [str(python),"-c",(
            "from selenium_pipeline.gemini38_tts_interactions import "
            "require_modern_tts_sdk; print(require_modern_tts_sdk())")],
        capture_output=True,text=True,timeout=35,
    )
    require(preflight.returncode==0,
            "Local modern Gemini SDK preflight failed: no provider call")
    env=_single_gemini_key_environment()
    dest.mkdir()
    waves=dest/"candidates";waves.mkdir()
    copy=waves/"new_Kore_utterance_001.wav"
    with copy.open("xb") as fp:
        fp.write(previous_wav.read_bytes())
        fp.flush()
        os.fsync(fp.fileno())
    entries=[{
        "index":1,
        "utterance_id":units[0]["original_utterance_id"],
        "text_sha256":units[0]["corrected_tts_text_sha256"],
        "origin":"EXACT_PRIOR_SUCCESSFUL_ONE_SHOT_WITH_ORIGINAL_RECEIPT",
        "provider_worker_success_observed":True,
        "wave":first,
        "voice_Kore_audibly_verified":False,
        "spoken_content_verified":False,
    }]
    failed=None
    for i in range(2,6):
        unit=units[i-1]
        name=unit["tts_audio_relative_path_expected"]
        require(name==f"new_Kore_utterance_{i:03d}.wav",
                "Unregistered utterance/WAV filename")
        text=unit["corrected_tts_text"]
        text_sha=hashlib.sha256(text.encode("utf8")).hexdigest()
        require(text_sha==unit["corrected_tts_text_sha256"]
                and len(text)>30
                and text==text.strip(),
                "Corrected source narration bytes inconsistent with requested TTS")
        job=dest/f"one_shot_utterance_{i:03d}"
        job.mkdir()
        sound=job/name
        evidence=job/"provider_worker_evidence.json"
        state={
            "model":model,
            "voice_requested":"Kore",
            "requested_text_sha256":text_sha,
            "original_utterance_id":unit["original_utterance_id"],
            "original_source_sha256":root_before["source.pdf"],
            "academic_math_passes":0,
            "one_provider_request_max":1,
            "sdk_retry_attempts":1,
            "local_retry_attempts":0,
            "no_cloud_fallback":True,
            "status":"CLAIMED_POSSIBLE_SUBMISSION_NO_AUTOMATIC_RETRY",
            "submitted_at_utc":now(),
            "voice_audibly_verified":False,
            "speech_words_independently_verified":False,
            "student_publication_authorized":False,
        }
        claim=job/"request_was_possibly_sent.once"
        with claim.open("xb") as f:
            f.write((text_sha+"\n"+now()+"\n").encode("ascii"))
            f.flush()
            os.fsync(f.fileno())
        receipt=job/"request_state.json"
        _atomic_receipt(receipt,state)
        command=[
            str(python),"-m","selenium_pipeline.tts_worker",
            "--model",model,"--voice","Kore","--number",str(i),
            "--output",str(sound),"--evidence-output",str(evidence),
            "--confirm-gemini-api-cost",
        ]
        try:
            ran=subprocess.run(
                command,input=text,text=True,env=env,
                capture_output=True,timeout=95,
            )
            state["worker_exit_code"]=ran.returncode
            if ran.returncode==0:
                wav=_wave_receipt(sound)
                require(wav["sha256"] not in history and
                        wav["sha256"] not in existing_digests,
                        "Provider WAV is historical or duplicates another utterance")
                existing_digests.add(wav["sha256"])
                shutil.copyfile(sound,waves/name)
                state["wave_sha256"]=wav["sha256"]
                state["wave_duration_s"]=wav["duration_s"]
                state["status"]="ONE_GENUINE_PCM_WAV_RECEIVED_NOT_SPEECH_VERIFIED"
                entries.append({
                    "index":i,"utterance_id":unit["original_utterance_id"],
                    "text_sha256":text_sha,
                    "origin":"ONE_ACTUAL_FLASHLITE_KORE_WORKER_SUCCESS",
                    "provider_worker_success_observed":True,
                    "wave":wav,
                    "voice_Kore_audibly_verified":False,
                    "spoken_content_verified":False,
                })
            else:
                # Never write raw exceptions/keys/provider URLs to receipt.
                state["status"]="TTS_WORKER_FAILURE_NO_RETRY"
                failed=i
        except subprocess.TimeoutExpired:
            state["status"]="TTS_WORKER_TIMEOUT_NO_RETRY"
            failed=i
        if evidence.is_file():
            try:
                observed=strict_json(evidence)
                state["worker_outcome"]=observed.get("outcome")
                state["real_provider_request_id_present"]=bool(
                    observed.get("provider_request_id"))
            except (ValueError,OSError):
                state["worker_evidence_unreadable"]=True
        state["finished_at_utc"]=now()
        _atomic_receipt(job/"request_final.json",state)
        print("ONE_SHOT_CORRECTED_TTS",i,state["status"],flush=True)
        if failed is not None:
            break

    require(_source_hashes(root)==root_before,
            "Protected original source/video/WAV changed during TTS candidate batch")
    summary={
        "schema_version":1,
        "status":("FIVE_ACTUAL_PRIMARY_TTS_PCM_CANDIDATES_QUARANTINED"
                  if failed is None else
                  "PARTIAL_PRIMARY_TTS_BATCH_NO_AUTOMATIC_RETRY"),
        "original_source_sha256":root_before["source.pdf"],
        "source_slides_sha256":root_before["slides.pdf"],
        "original_script_sha256":root_before["script.txt"],
        "tts_model_requested":model,
        "tts_voice_requested":"Kore",
        "verified_PCM_candidate_count":len(entries),
        "requested_utterance_count":5,
        "failed_utterance_index":failed,
        "per_utterance_source_wav_evidence":entries,
        "independent_original_source_academic_review_passes":0,
        "provider_voice_identity_audibly_verified":False,
        "spoken_words_independently_verified":False,
        "audio_to_source_visual_semantic_sync_approved":False,
        "new_MP4_release_accepted":False,
        "student_publication_authorized":False,
        "originals_unchanged":True,
        "gemini_web_academic_request_resubmitted":False,
        "cloud_tts_fallback_sent":False,
    }
    _atomic_receipt(dest/"CANDIDATE_BATCH_SOURCE_BOUND_UNAPPROVED.json",summary)
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original",required=True,type=Path)
    parser.add_argument("--bundle",required=True,type=Path)
    parser.add_argument("--previous-first",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--worker-python",required=True,type=Path)
    parser.add_argument("--dispatch-one-attempt-each",action="store_true")
    args=parser.parse_args(argv)
    result=run_remaining_corrected_utterances(
        original=args.original,bundle=args.bundle,
        previous_one_shot=args.previous_first,out=args.out,
        worker_python=args.worker_python,
        dispatch_one_request_per_utterance=args.dispatch_one_attempt_each)
    print(json.dumps({
        "status":result["status"],
        "genuine_quarantined_pcm_candidates":result["verified_PCM_candidate_count"],
        "approved_spoken_words":False,"academic_review_passes":0,
        "student_publication":False,
    }))


if __name__=="__main__":
    main()
