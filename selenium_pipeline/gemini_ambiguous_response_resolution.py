"""Offline decision support for unresolved requests; never dispatches Gemini."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from .gemini_review_backoff_checkpoint import inspect
def assess_unresolved_owned_reply(*,checkpoint:Path,original_folder:Path,
                                  receipt:Path|None, owned_session_proven:bool,
                                  completed_in_owned_tab:bool)->dict:
 state=inspect(checkpoint=checkpoint,original_folder=original_folder)
 if not state["requires_reconciliation"]:
  return {"status":"NO_UNRESOLVED_OWNED_REQUEST","auto_retry_authorized":False}
 if not owned_session_proven or not completed_in_owned_tab or receipt is None:
  return {"status":"UNKNOWN_OUTCOME_RECONCILIATION_REQUIRED",
          "auto_retry_authorized":False}
 receipt=Path(receipt).absolute()
 if (receipt.is_symlink() or not receipt.is_file() or
     receipt.is_relative_to(Path(original_folder).absolute()) or
     receipt.suffix.lower()!=".json" or receipt.stat().st_size>250000):
  raise ValueError("Unowned, unsafe or unbounded reply evidence")
 raw=receipt.read_bytes()
 try:model=json.loads(raw)
 except (ValueError,UnicodeError):
  return {"status":"INCOMPLETE_UNTRUSTED_REPLY","auto_retry_authorized":False}
 if not isinstance(model,dict) or not model:
  return {"status":"INCOMPLETE_UNTRUSTED_REPLY","auto_retry_authorized":False}
 return {"status":"POSSIBLE_OWNED_RESPONSE_REQUIRES_SCIENTIFIC_VALIDATION",
         "response_sha256":hashlib.sha256(raw).hexdigest(),
         "auto_retry_authorized":False,"mathematically_verified":False,
         "student_publication_authorized":False}
