"""Read-only current pilot status: quote actual failed math review and audio gaps."""
from pathlib import Path
from .gemini_review_backoff_checkpoint import inspect
from .original_math_audio_release_ledger import summarize_original_review_readiness
from .reviewed_kore_audio_stage_preflight import preflight_genuine_kore_stage
def audit_original_pilot_state(*,checkpoint:Path,queue_root:Path,folder:Path)->dict:
 state=inspect(checkpoint=checkpoint,original_folder=folder)
 original=summarize_original_review_readiness(queue_root=queue_root,folder=folder)
 stage=preflight_genuine_kore_stage(queue_root=queue_root,folder=folder,
                                    nonbilled_manifest=None)
 if original["original_utterances"]<1:raise ValueError("Not a real original narration scope")
 return {"status":"ORIGINAL_PILOT_PRODUCTION_NOT_YET_VERIFIED",
         "original_utterances":original["original_utterances"],
         "source_mathematics_agreed":original["source_validated_ai_math_agreements"],
         "source_math_pending":original["source_math_pending_or_disputed"],
         "checkpoint_status":state["status"],
         "confirmed_or_historical_attempts":state["confirmed_submissions"],
         "automatic_retry_eligible":state["eligible_for_single_authorized_dispatch"],
         "next_due_utc":state["next_due_unix_utc"],
         "audio_stage_status":stage["status"],
         "genuine_kore_pcm_proven_here":False,
         "decoded_highlight_alignment_proven_here":False,
         "academic_listening_qa_proven_here":False,
         "student_publication_authorized":False}
