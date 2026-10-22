import tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.original_math_audio_release_ledger import summarize_original_review_readiness
from selenium_pipeline.ai_academic_review_queue import prepare_resumable_review
from test_original_packet_evidence_audit import fixture
class ReleaseBlockers(unittest.TestCase):
 def setup(self,root):
    r=Path(root);f=r/"src";fixture(f)
    (f/"script.txt").write_text("**Slide 1 [1 sec]:\nA visible equation**\n")
    with wave.open(str(f/"slide1.wav"),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
        w.writeframes(b"\x01\x02"*24000)
    q=r/"queue";prepare_resumable_review(folder=f,output_root=q,slide_numbers=[1])
    return f,q
 def test_genuine_unreviewed_original_not_publishable(self):
    with tempfile.TemporaryDirectory() as d:
        f,q=self.setup(d);a=summarize_original_review_readiness(queue_root=q,folder=f)
        self.assertEqual((a["original_utterances"],a["source_math_pending_or_disputed"]),(1,1))
        self.assertFalse(a["student_publication_authorized"])
        self.assertEqual(a["next_blocking_stage"],"INDEPENDENT_SOURCE_MATH_REVIEW")
 def test_original_script_drift_not_accepted(self):
    with tempfile.TemporaryDirectory() as d:
        f,q=self.setup(d);(f/"script.txt").write_text("fabricated rewrite")
        with self.assertRaises(Exception):summarize_original_review_readiness(queue_root=q,folder=f)
