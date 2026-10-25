"""Validate genuinely supplied ORIGINAL Slide4 five-utterance WAV bytes.

No TTS request, Whisper, historical source-folder audio enumeration, billing
or voice-acoustic/content acceptance. Never call with untrusted receipt paths
outside an authorized workspace without the owner's explicit selection.
"""
from __future__ import annotations

import argparse
import json
import hashlib
import math
from pathlib import Path
import wave

from .figure_source_identity import require,_sha
from .ai_academic_web_review import build_review_job
from .original_slide4_audio_eligibility import inspect_original_slide4_audio_readiness
from .external_tts_delivery_proof import verify_external_tts_delivery


def verify_original_slide4_external_audio(*,readiness:dict,job:dict,
                                          receipts:list,original_folder:Path)->dict:
    """Read only five explicitly listed distinct external WAVs, never glob."""
    require(type(readiness) is dict and type(job) is dict
            and job.get("status")=="SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED"
            and job.get("utterance_count")==5
            and len(job.get("slides",[]))==1
            and job["slides"][0].get("slide")==4
            and all(readiness.get(n)==job.get(n)
                    for n in ("source_sha256","slides_sha256","script_sha256"))
            and readiness.get("original_slide_utterances")==5
            and readiness.get("visual_candidate_utterances")==5
            and readiness.get("unmapped_visual_utterances")==0
            and readiness.get("real_speech_timing_evidence_accepted") is False
            and readiness.get("student_publication_authorized") is False,
            "Exact original and full review-only visual witness required")
    require(type(receipts) is list and len(receipts)==5,
            "Exactly five owner-supplied external audio receipts required")
    original=Path(original_folder).absolute()
    seen_paths=set()
    seen_exec=set()
    segments=[]
    rate=None
    begin=0
    for utterance,receipt in zip(job["slides"][0]["utterances"],receipts):
        require(type(receipt) is dict
                and receipt.get("job_id")==utterance["id"]
                and receipt.get("spoken_text_sha256")==utterance["spoken_sha256"],
                "Audio receipt does not match the original exact utterance")
        verified=verify_external_tts_delivery(
            job={"job_id":utterance["id"],
                 "spoken_text_sha256":utterance["spoken_sha256"]},
            delivery=receipt,original_folder=original)
        path=Path(receipt["pcm_wav_path"]).absolute()
        require(path not in seen_paths
                and verified["provider_execution_id"] not in seen_exec,
                "One WAV or provider execution cannot satisfy multiple utterances")
        seen_paths.add(path);seen_exec.add(verified["provider_execution_id"])
        with wave.open(str(path),"rb") as audio:
            actual_rate=audio.getframerate()
            frames=audio.getnframes()
            raw=audio.readframes(frames)
            require(rate is None or actual_rate==rate,
                    "Multiple different sample clocks need explicit resampling QA")
            require(any(raw[i:i+2]!=bytes(2) for i in range(0,len(raw),2)),
                    "Silent WAV does not prove actual voiced narration")
        rate=actual_rate
        require(verified["sample_frames"]==frames
                and verified["sample_rate"]==rate
                and _sha(path)==verified["wav_sha256"],
                "External PCM source mutated or measured sample counts changed")
        segments.append({
            "original_utterance_id":utterance["id"],
            "original_spoken_sha256":utterance["spoken_sha256"],
            "declared_model_and_voice_provenance_checked":True,
            "provider_execution_receipt_present":True,
            "measured_sample_rate":rate,
            "verified_wav_sha256":verified["wav_sha256"],
            "verified_pcm_frame_count":frames,
            "proposed_concatenation_start_sample":begin,
            "proposed_concatenation_end_sample":begin+frames,
            "measured_clip_duration_s":frames/rate,
            "source_text_audibly_spoken_verified":False,
            "Kore_voice_acoustically_verified":False,
            "frame_highlight_synchronized_to_spoken_math":False,
        })
        begin+=frames
    require(rate is not None and 0<begin/rate<540,
            "Original five WAVs exceed conservative 540s review-part cap")
    return {
        "status":"FIVE_ORIGINAL_SLIDE4_EXTERNAL_PCM_WAV_BYTES_CHECKED_REVIEW_ONLY",
        "original_source_sha256":job["source_sha256"],
        "original_slides_sha256":job["slides_sha256"],
        "original_script_sha256":job["script_sha256"],
        "external_pcm_clip_count":5,
        "provider_execution_claim_count":5,
        "sample_rate":rate,
        "total_sample_frames":begin,
        "measured_total_audio_duration_s":begin/rate,
        "byte_verified_audio_segments":segments,
        "source_script_spoken_content_verified":False,
        "Kore_acoustic_voice_id_verified":False,
        "speech_to_visual_highlight_verified":False,
        "original_mathematics_independently_agreed":False,
        "approved_sub_600_second_mp4_produced":False,
        "student_publication_authorized":False,
        "new_paid_or_web_provider_request_sent":False,
    }


def inspect_supplied_original_slide4_wavs(*,folder:Path,queue_root:Path,
                                          manifest:Path)->dict:
    folder=Path(folder).absolute()
    manifest=Path(manifest).absolute()
    require(manifest.is_file() and not manifest.is_symlink()
            and manifest.suffix.lower()==".json"
            and manifest.stat().st_size<=40_000
            and not manifest.is_relative_to(folder),
            "Explicit external 40KB receipt manifest required")
    before=tuple(_sha(folder/p) for p in ("source.pdf","slides.pdf","script.txt"))
    data=json.loads(manifest.read_text(encoding="utf-8-sig"))
    require(type(data) is dict
            and data.get("status")=="OWNER_SUPPLIED_EXTERNAL_AUDIO_EVIDENCE_NOT_DISPATCHED"
            and type(data.get("deliveries")) is list,
            "Owner-supplied receipt manifest must be explicit and unmodified")
    readiness=inspect_original_slide4_audio_readiness(
        folder=folder,queue_root=queue_root)
    job=build_review_job(folder=folder,slide_numbers=[4])
    report=verify_original_slide4_external_audio(
        readiness=readiness,job=job,receipts=data["deliveries"],
        original_folder=folder)
    require(tuple(_sha(folder/p) for p in ("source.pdf","slides.pdf","script.txt"))==before
            and (report["original_source_sha256"],
                 report["original_slides_sha256"],
                 report["original_script_sha256"])==before,
            "Original teaching source identity changed during byte verification")
    report["manifest_sha256"]=_sha(manifest)
    return report


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    p.add_argument("--queue-root",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    a=p.parse_args(argv)
    print(json.dumps(inspect_supplied_original_slide4_wavs(
        folder=a.folder,queue_root=a.queue_root,manifest=a.manifest),
        indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
