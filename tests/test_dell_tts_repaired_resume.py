"""Source-safe, one-time explicit repair epoch after observed TTS outage."""
import unittest
from selenium_pipeline.windows_sourcebound_e2e_orchestrator import (
    _recover_exhausted_tts_after_code_fix, SourceboundE2EError, PHASES)

def state():
    return {"phases":{
        "source_content":{"outcome":"stage_pass"},
        "narrated_audio":{"outcome":"stage_failed","return_code":124,
                         "attempt":3,"transient":True,
                         "log":"old-preserved-attempt3.log"}},
        "published_to_students":False}

class RecoveryCheckpointTests(unittest.TestCase):
    def test_three_actual_transient_attempts_required_and_old_logs_preserved(self):
        s=_recover_exhausted_tts_after_code_fix(state())
        self.assertEqual(s["repair_epoch"],1)
        self.assertNotIn("narrated_audio",s["phases"])
        self.assertEqual(len(s["repair_history"]),1)
        self.assertEqual(s["repair_history"][0]["old_phase_receipt"]["log"],
                         "old-preserved-attempt3.log")
        self.assertTrue(s["repair_history"][0]["old_logs_retained"])
        self.assertEqual(_recover_exhausted_tts_after_code_fix(s),s)
    def test_cannot_reset_unobserved_or_fewer_than_three_failures(self):
        for changed in [{"attempt":2},{"return_code":2},{"transient":False},
                        {"outcome":"stage_pass"}]:
            s=state()
            s["phases"]["narrated_audio"].update(changed)
            with self.assertRaises(SourceboundE2EError):
                _recover_exhausted_tts_after_code_fix(s)
    def test_no_second_or_published_repair_epoch(self):
        s=state();s["repair_history"]=[{"prior":"record"}]
        with self.assertRaises(SourceboundE2EError):
            _recover_exhausted_tts_after_code_fix(s)
        s=state();s["published_to_students"]=True
        with self.assertRaises(SourceboundE2EError):
            _recover_exhausted_tts_after_code_fix(s)
    def test_coherent_upper_tts_deadline(self):
        self.assertGreaterEqual(next(p[2] for p in PHASES if p[0]=="narrated_audio"),5400)
if __name__=="__main__":unittest.main()
