import unittest
from selenium_pipeline.gemini_terminal_evidence_classifier import classify_terminal_capture
class Terminal(unittest.TestCase):
 def base(self):
  return dict(tab_id="owned",tab_current=True,generation_active=False,
              request_submitted=True,verified_terminal_ui_error=True,
              verified_transport_http_status=503)
 def test_proven_429_503_only(self):
  e=self.base()
  self.assertEqual(classify_terminal_capture(e,expected_owned_tab="owned")["category"],"SERVER_UNAVAILABLE_503")
  e["verified_transport_http_status"]=429
  self.assertEqual(classify_terminal_capture(e,expected_owned_tab="owned")["category"],"SERVER_BUSY_429")
 def test_live_or_wrong_tab_and_text_503_are_unknown(self):
  for change in ({"generation_active":True},{"tab_id":"another"},
                 {"verified_terminal_ui_error":False},
                 {"verified_transport_http_status":"503 busy"}):
   e=self.base();e.update(change)
   self.assertFalse(classify_terminal_capture(e,expected_owned_tab="owned")["retry_authorized"])
 def test_timeout_without_explicit_terminal_evidence_is_not_retryable(self):
  e=self.base();e.pop("verified_terminal_ui_error");e["request_timeout_s"]=120
  self.assertEqual(classify_terminal_capture(e,expected_owned_tab="owned")["status"],"RECONCILIATION_REQUIRED")
