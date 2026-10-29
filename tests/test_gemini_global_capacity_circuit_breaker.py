import unittest
from selenium_pipeline.gemini_global_capacity_circuit_breaker import capacity_circuit_state
class Circuit(unittest.TestCase):
 def test_three_verified_busy_signals_hold_off_batch(self):
  receipts=[dict(verified_terminal_utc=t,same_owned_session_verified=True,
                 category="SERVER_UNAVAILABLE_503") for t in (800,850,900)]
  x=capacity_circuit_state(terminal_receipts=receipts,now=1000)
  self.assertEqual(x["status"],"OPEN_CAPACITY_COOLDOWN")
  self.assertGreater(x["next_global_eligible_utc"],1000)
 def test_client_says_busy_but_no_verified_terminal_does_not_count(self):
  receipts=[dict(verified_terminal_utc=100,same_owned_session_verified=False,
                 category="SERVER_BUSY_429")] * 3
  self.assertEqual(capacity_circuit_state(terminal_receipts=receipts,now=200)
                   ["verified_capacity_failures_in_window"],0)
 def test_cooldown_expires_and_no_automatic_release(self):
  receipts=[dict(verified_terminal_utc=t,same_owned_session_verified=True,
                 category="SERVER_BUSY_429") for t in (90,95,100)]
  x=capacity_circuit_state(terminal_receipts=receipts,now=2000,window_s=3600)
  self.assertEqual(x["status"],"CLOSED_NO_CAPACITY_STOP")
  self.assertFalse(x["model_dispatch_authorized"])
