"""Encode a real-original-WAV singly narrated Thomas slide with correct highlight.

This is a truthful real-media *pilot*: single source-cited AI pass, recorded
original slide WAV copied by SHA into isolated workspace, independently decoded
actual MP4 frame and audio. No per-element TTS provider or final academic QA.
"""
from __future__ import annotations
import json,shutil
from pathlib import Path
from .figure_source_identity import require,_sha
from .ai_academic_web_review import build_review_job
from .incremental_element_review_encoder import encode_segment_highlight_review
from .encoded_audio_fingerprint_audit import audit_muxed_audio_segment_fingerprints

def render_original_single_utterance_review(*,folder:Path,job:dict,
                                             ai_first_pass:dict,
                                             destination:Path)->dict:
    folder,destination=Path(folder).absolute(),Path(destination).absolute()
    require(destination.parent.is_dir() and not destination.exists()
            and not destination.is_relative_to(folder)
            and job.get("status")=="SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED"
            and job.get("utterance_count")==1 and len(job["slides"])==1
            and ai_first_pass.get("status")=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
            and ai_first_pass.get("mode")=="INITIAL_REVIEW"
            and len(ai_first_pass.get("rows",[]))==1,
            "Only actual 1:1 original recorded narration can use original slide WAV")
    slide=job["slides"][0]["slide"]
    actual=build_review_job(folder=folder,slide_numbers=[slide])
    require(actual["source_sha256"]==job["source_sha256"]
            and actual["slides_sha256"]==job["slides_sha256"]
            and actual["script_sha256"]==job["script_sha256"]
            and actual["slides"]==job["slides"],
            "Unverified stale source narration to slide identity")
    unit=job["slides"][0]["utterances"][0]
    choice=ai_first_pass["rows"][0]
    require(choice["utterance_id"]==unit["id"] and
            choice["spoken_sha256"]==unit["spoken_sha256"]
            and choice["verdict"]=="SUPPORTED"
            and choice["exact_textbook_quote_verified"] is True
            and choice["target_id"] in {t["id"] for t in job["slides"][0]["visual_targets"]}
            and type(choice["text_target_pdf_bbox_pt"]) is list,
            "Genuine first-pass original textbook/source review evidence required")
    raw=folder/f"slide{slide}.wav"
    require(raw.is_file() and not raw.is_symlink(),"Original recorded speech WAV missing")
    original_hashes={k:_sha(folder/k) for k in ("source.pdf","slides.pdf","script.txt")}
    original_audio_sha=_sha(raw)
    staged=destination.parent/("_"+destination.name+"_source_audio_copy.wav")
    require(not staged.exists(),"Cannot overwrite prior original WAV derivative")
    with staged.open("xb") as out:
        with raw.open("rb") as inp:shutil.copyfileobj(inp,out)
    require(_sha(staged)==original_audio_sha,"Historical narration WAV copy differs")
    render_jobs={"status":"REVIEWED_ELEMENT_CHUNK_REQUESTS_NOT_YET_DISPATCHED",
                 "slides_sha256":job["slides_sha256"],
                 "paid_tts_execution_authorized":False,
                 "student_publication_authorized":False,
                 "voice":"Kore",
                 "chunk_jobs":[{"job_id":unit["id"],"target_slide_index":slide,
                                "target_pdf_page_bbox_pt":choice["text_target_pdf_bbox_pt"]}]}
    clips=[{"job_id":unit["id"],"voice_id":"Kore",
            "wav_path":str(staged),"wav_sha256":original_audio_sha}]
    encoded=encode_segment_highlight_review(
        slides=folder/"slides.pdf",jobs=render_jobs,
        clips=clips,destination=destination)
    mp4=destination/"element_highlight_review.mp4"
    sound=audit_muxed_audio_segment_fingerprints(mp4=mp4,wavs=[staged])
    require(sound["source_element_count"]==1
            and encoded["decoded_highlight_midpoint_samples_verified"] is True
            and encoded["actual_encoded_duration_s"]<600
            and _sha(mp4)==encoded["encoded_review_sha256"]
            and _sha(raw)==original_audio_sha
            and all(_sha(folder/k)==v for k,v in original_hashes.items()),
            "Actual independently decoded 1-to-1 original audio/video acceptance failed")
    receipt={"status":"REAL_ORIGINAL_SINGLE_UTTERANCE_ELEMENT_HIGHLIGHT_REVIEW_ONLY",
             "original_slide":slide,"original_utterance_id":unit["id"],
             "original_audio_sha256":original_audio_sha,
             "encoded_mp4_sha256":encoded["encoded_review_sha256"],
             "actual_encoded_duration_s":encoded["actual_encoded_duration_s"],
             "original_source_asset_sha256":original_hashes,
             "decoded_correct_element_highlight_at_audio_midpoint":True,
             "decoded_original_audio_spectrum_verified":True,
             "verified_pcm_spectral_similarity":sound["spectral_similarity"],
             "ai_math_source_review_one_pass_only":True,
             "independent_second_ai_review_pass_complete":False,
             "same_voice_proven_acoustically":False,
             "original_WAV_is_new_element_TTS":False,
             "all_multielement_lecture_complete":False,
             "student_publication_authorized":False}
    with (destination/"source_aware_pilot_receipt.json").open("x",encoding="utf8") as f:
        json.dump(receipt,f,indent=2);f.write("\n")
    return receipt
