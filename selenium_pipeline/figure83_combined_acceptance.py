"""Consolidate source-bound figure review and physical WAV integrity, fail closed."""
from __future__ import annotations
import json,re
from pathlib import Path
from .figure_source_identity import _sha,require
from .figure83_source_review_packet import audit_original_files
from .figure83_element_audio_integrity import inspect_element_wav_claims

def evaluate_combined_preflight(packet:dict,audio:dict)->dict:
    require(type(packet) is dict and packet.get("status")=="ORIGINAL_FIGURE83_REVIEW_ONLY"
            and type(audio) is dict and audio.get("status")=="ELEMENT_AUDIO_PHYSICAL_INTEGRITY_ONLY"
            and packet.get("paid_tts_authorized") is False
            and packet.get("student_publication_authorized") is False
            and audio.get("production_video_authorized") is False
            and audio.get("spoken_element_timing_verified") is False,
            "Only technically bounded review and integrity evidence can enter the preflight")
    sha=[packet.get(key) for key in ("source_sha256","slides_sha256","script_sha256")]
    require(all(type(v) is str and bool(re.fullmatch(r"[0-9a-f]{64}",v)) for v in sha),
            "Source/slide/script fingerprints must be complete")
    utterances=packet.get("review_utterances")
    require(type(utterances) is list and 0<len(utterances)<=100,
            "Expected actual bounded narration review manifest")
    seen=set()
    resolved=0
    for u in utterances:
        require(type(u) is dict and type(u.get("utterance_id")) is str
                and u["utterance_id"] not in seen
                and u.get("source_math_approved") is False
                and u.get("actual_spoken_timing_approved") is False,
                "Untrusted duplicated or prematurely approved utterance")
        seen.add(u["utterance_id"])
        resolved+=u.get("candidate_full_expression_pdf_bbox_pt") is not None
    count=audio.get("integrity_checked_clip_count")
    require(type(count) is int and 0<=count<=len(utterances),
            "Physical audio inventory exceeds original utterances")
    receipts=audio.get("element_audio_integrity_receipts")
    require(type(receipts) is list and len(receipts)==count
            and all(entry.get("physical_audio_integrity_verified") is True
                    and entry.get("spoken_words_mapped_to_visual_element_verified") is False
                    and entry.get("utterance_id") in seen for entry in receipts),
            "Invalid bounded integrity-only WAV receipts")
    blockers=["COMPLETE_FIGURE_MATHEMATICS_UNVERIFIED",
              "NARRATED_WORD_TO_ELEMENT_TIMING_UNVERIFIED",
              "ELEMENT_WAV_INTEGRITY_NOT_SEMANTIC_AUDIO_APPROVAL",
              "HUMAN_ACADEMIC_AND_LISTENING_QA_PENDING"]
    if resolved<len(utterances):
        blockers.append("UNRESOLVED_NARRATION_TO_FIGURE_HYPOTHESES")
    if count<len(utterances):
        blockers.append("ORIGINAL_UTTERANCES_LACK_INDEPENDENT_ELEMENT_WAVS")
    return {"status":"FIGURE83_COMBINED_PRODUCTION_ACCEPTANCE_BLOCKED",
            "source_sha256":sha[0],"slides_sha256":sha[1],"script_sha256":sha[2],
            "original_utterance_count":len(utterances),
            "candidate_math_review_anchor_count":resolved,
            "physically_verified_element_clip_count":count,
            "genuine_spoken_element_alignment_verified":False,
            "encoded_sub600_production_release_authorized":False,
            "paid_tts_authorized":False,"student_publication_authorized":False,
            "remaining_blockers":blockers}

def audit_original_lecture(*,source:Path,slides:Path,script:Path)->dict:
    originals=[Path(f).absolute() for f in (source,slides,script)]
    before=[_sha(f) for f in originals]
    packet=audit_original_files(source=originals[0],slides=originals[1],script=originals[2])
    integrity=inspect_element_wav_claims(packet,[])  # no fabricated element jobs
    receipt=evaluate_combined_preflight(packet,integrity)
    require([_sha(f) for f in originals]==before,
            "Original teaching source altered during combined audit")
    return receipt
