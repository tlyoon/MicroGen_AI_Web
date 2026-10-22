"""Read-only verified-vs-missing acceptance gate for original narration stages.

This is a precise diagnostic, never a standalone student-release approval.
"""
from pathlib import Path
from .review_queue_source_audit import inspect_source_bound_queue
from .ai_academic_review_consensus import reconcile_actual_review_queue
def summarize_original_review_readiness(*,queue_root:Path,folder:Path)->dict:
    q=Path(queue_root);f=Path(folder)
    original=inspect_source_bound_queue(q)
    consensus=reconcile_actual_review_queue(queue_root=q,folder=f)
    count=original["original_utterances"]
    if (count!=consensus.get("original_utterances") or
        consensus.get("agreed_source_witnessed_segments",0)+consensus.get("pending_or_disputed",-1)!=count or
        consensus.get("student_publication_authorized") is not False):
        raise ValueError("Original queue vs source-consensus accounting drift")
    accepted=consensus["agreed_source_witnessed_segments"]
    pending=consensus["pending_or_disputed"]
    return {"status":"SOURCE_AND_MATH_AND_MEDIA_RELEASE_REVIEW_REQUIRED",
        "original_utterances":count,
        "source_validated_ai_math_agreements":accepted,
        "source_math_pending_or_disputed":pending,
        "source_coverage_sha256":original["source_sha256"],
        "actual_per_utterance_pcm_validated_here":False,
        "decoded_element_highlight_video_validated_here":False,
        "independent_human_academic_or_listening_review_complete":False,
        "student_publication_authorized":False,
        "next_blocking_stage":("INDEPENDENT_SOURCE_MATH_REVIEW"
                               if pending else "ACTUAL_TTS_AND_ELEMENT_VIDEO_AND_HUMAN_QA")}
