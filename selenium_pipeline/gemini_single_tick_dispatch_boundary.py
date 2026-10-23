"""One-shot checked model send boundary, for future separately authorized worker.

This module does not know Selenium or schedule anything. It only calls the
explicitly injected transport once after a durable claim, and it never
interprets an uncertain outcome as retryable.
"""
from pathlib import Path
from .gemini_review_backoff_checkpoint import (
    claim_due,submitted,unsent,ambiguous)
def one_authorized_tick(*,checkpoint:Path,original_folder:Path,
                        send_once,now:float)->dict:
 if not callable(send_once):
  raise ValueError("Explicit trusted owned-browser callback required")
 token=claim_due(checkpoint=checkpoint,original_folder=original_folder,now=now)
 if token is None:
  return {"status":"NOT_DUE_OR_EXHAUSTED","model_request_sent":False}
 try:
  proof=send_once()
 except Exception:
  # Exception could occur *after* server accepted; fail closed.
  ambiguous(checkpoint=checkpoint,original_folder=original_folder,claim=token,now=now)
  return {"status":"AMBIGUOUS_TRANSPORT_EXCEPTION",
          "auto_retry_authorized":False}
 if type(proof) is not dict or proof.get("outcome") not in (
     "VERIFIED_UNSENT","CONFIRMED_SUBMITTED"):
  ambiguous(checkpoint=checkpoint,original_folder=original_folder,claim=token,now=now)
  return {"status":"AMBIGUOUS_DELIVERY_EVIDENCE","auto_retry_authorized":False}
 if proof["outcome"]=="VERIFIED_UNSENT":
  # Refuse no-send classification if either submit indicator is positive.
  if proof.get("user_turn_created") is not False or proof.get("composer_cleared") is not False:
   ambiguous(checkpoint=checkpoint,original_folder=original_folder,claim=token,now=now)
   return {"status":"CONFLICTING_SUBMISSION_EVIDENCE","auto_retry_authorized":False}
  record=unsent(checkpoint=checkpoint,original_folder=original_folder,
                claim=token,reason="VERIFIED_NO_SUBMISSION",now=now)
  return {"status":record["status"],"model_request_sent":False}
 if proof.get("user_turn_created") is not True or proof.get("composer_cleared") is not True:
  ambiguous(checkpoint=checkpoint,original_folder=original_folder,claim=token,now=now)
  return {"status":"SUBMISSION_NOT_BOTH_VERIFIED","auto_retry_authorized":False}
 state=submitted(checkpoint=checkpoint,original_folder=original_folder,claim=token,
                 user_turn_created=True,composer_cleared=True,now=now)
 return {"status":state["status"],"model_request_sent":True,
         "review_validated":False,"student_publication_authorized":False}
