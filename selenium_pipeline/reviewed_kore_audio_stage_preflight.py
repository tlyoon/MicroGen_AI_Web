"""Independent minimal safety gate before attempting original-source Kore TTS.

This is NOT a billable TTS authorization or substitute for academic QA.
"""
from pathlib import Path
from .original_math_audio_release_ledger import summarize_original_review_readiness
from .nonbilled_kore_source_handoff_audit import audit_nonbilled_kore_handoff
def preflight_genuine_kore_stage(*,queue_root:Path,folder:Path,
                                 nonbilled_manifest:dict|None)->dict:
 source=summarize_original_review_readiness(queue_root=queue_root,folder=folder)
 if source["source_math_pending_or_disputed"]:
  return {"status":"BLOCKED_INDEPENDENT_SOURCE_MATH_REVIEW",
          "remaining_original_utterances":source["source_math_pending_or_disputed"],
          "provider_call_authorized":False,"student_publication_authorized":False}
 if nonbilled_manifest is None:
  return {"status":"BLOCKED_MISSING_SOURCE_HASHED_KORE_MANIFEST",
          "provider_call_authorized":False,"student_publication_authorized":False}
 audit=audit_nonbilled_kore_handoff(folder=folder,report=nonbilled_manifest)
 if audit["unresolved_review"] or audit["source_math_agreed_jobs"]!=source["original_utterances"]:
  raise ValueError("Incomplete reviewed source-to-audio manifest")
 return {"status":"NONBILLED_ORIGINAL_VERBATIM_KORE_MANIFEST_READY_FOR_SEPARATE_APPROVAL",
         "reviewed_units":audit["source_math_agreed_jobs"],
         "provider_call_authorized":False,"actual_audio_generated":False,
         "student_publication_authorized":False}
