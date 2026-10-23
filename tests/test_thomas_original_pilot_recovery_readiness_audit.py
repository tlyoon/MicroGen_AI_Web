import tempfile,unittest
from pathlib import Path
from selenium_pipeline import gemini_review_backoff_checkpoint as b
from selenium_pipeline.thomas_original_pilot_recovery_readiness_audit import audit_original_pilot_state
from test_original_math_audio_release_ledger import ReleaseBlockers
class PilotAudit(unittest.TestCase):
 def test_blocked_original_review_cannot_appear_production_ready(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=ReleaseBlockers().setup(d);cp=Path(d)/"state.json"
   b.initialize(checkpoint=cp,original_folder=f,job_id="slide_diagnostic",now=0)
   out=audit_original_pilot_state(checkpoint=cp,queue_root=q,folder=f)
   self.assertEqual(out["source_math_pending"],1)
   self.assertFalse(out["student_publication_authorized"])
   self.assertFalse(out["genuine_kore_pcm_proven_here"])
 def test_original_script_changed_causes_fail_closed_audit(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=ReleaseBlockers().setup(d);cp=Path(d)/"state.json"
   b.initialize(checkpoint=cp,original_folder=f,job_id="slide_diagnostic",now=0)
   (f/"script.txt").write_text("changed")
   with self.assertRaises(ValueError):
    audit_original_pilot_state(checkpoint=cp,queue_root=q,folder=f)
