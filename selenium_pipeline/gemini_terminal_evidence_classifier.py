"""Classify only verifiable owned-tab *terminal* Gemini failure metadata.

Never infer 429/503 from prompt text, timeout, inactivity or copied HTML.
No browser access and no model dispatch in this module.
"""
from __future__ import annotations
import re
def classify_terminal_capture(evidence:dict,*,expected_owned_tab:str)->dict:
 if type(evidence) is not dict or type(expected_owned_tab) is not str or not expected_owned_tab:
  raise ValueError("Trusted owned-tab identity required")
 if evidence.get("tab_id")!=expected_owned_tab or evidence.get("tab_current") is not True:
  return {"status":"RECONCILIATION_REQUIRED","retry_authorized":False}
 if evidence.get("generation_active") is not False or evidence.get("request_submitted") is not True:
  return {"status":"RECONCILIATION_REQUIRED","retry_authorized":False}
 # transport_status only from structured provider-backed error observations.
 # Free-form strings may be model output or prompt injection.
 status=evidence.get("verified_transport_http_status")
 official=evidence.get("verified_terminal_ui_error") is True
 if type(status) is int and status in (429,503) and official:
  return {"status":"VERIFIED_TERMINAL_FAILURE","category":
          "SERVER_BUSY_429" if status==429 else "SERVER_UNAVAILABLE_503",
          "retry_authorized":True}
 if official and evidence.get("verified_error_kind")=="TERMINAL_ERROR":
  return {"status":"VERIFIED_TERMINAL_FAILURE",
          "category":"VERIFIED_TERMINAL_ERROR","retry_authorized":True}
 return {"status":"RECONCILIATION_REQUIRED","retry_authorized":False}
