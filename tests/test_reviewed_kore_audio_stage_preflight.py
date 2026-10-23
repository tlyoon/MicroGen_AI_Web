import tempfile,unittest
from pathlib import Path
from selenium_pipeline.reviewed_kore_audio_stage_preflight import preflight_genuine_kore_stage
from test_original_math_audio_release_ledger import ReleaseBlockers
class AudioGate(unittest.TestCase):
 def test_real_fixture_cannot_stage_unreviewed_kore_audio(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=ReleaseBlockers().setup(d)
   x=preflight_genuine_kore_stage(queue_root=q,folder=f,nonbilled_manifest=None)
   self.assertEqual(x["status"],"BLOCKED_INDEPENDENT_SOURCE_MATH_REVIEW")
   self.assertFalse(x["provider_call_authorized"])
 def test_original_source_drift_is_not_silently_repaired(self):
  with tempfile.TemporaryDirectory() as d:
   f,q=ReleaseBlockers().setup(d);(f/"script.txt").write_text("changed")
   with self.assertRaises(Exception):
    preflight_genuine_kore_stage(queue_root=q,folder=f,nonbilled_manifest=None)
