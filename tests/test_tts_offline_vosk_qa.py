"""Unprompted offline audio QA selection remains fail-closed and source bound."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline import tts_fidelity
from selenium_pipeline.tts_offline_vosk_fidelity import approved_assets,check_pcm

class OfflineVoskSourceAudioQATests(unittest.TestCase):
 def test_no_fabricated_offline_model(self):
  with patch.dict(os.environ,{"MICROGEN_TTS_QA_VOSK_MODEL":
      r"C:\unknown\not_official","MICROGEN_TTS_QA_VOSK_PACKAGES":
      r"C:\unknown"},clear=False):
   with self.assertRaisesRegex(RuntimeError,"model/packages"):
    approved_assets()
 def test_explicit_backend_requires_real_observation(self):
  with patch.dict(os.environ,{"MICROGEN_TTS_QA_BACKEND":"offline_vosk"},clear=False):
   with patch("selenium_pipeline.tts_offline_vosk_fidelity.unprompted_audio_review",
              return_value={"transcript":"real words","pronunciation_issues":[],
                            "critical_token_issues":[],"audio_defects":[]}) as reviewer:
    result=tts_fidelity.inspect_audio(Path("not_dispatched.wav"),"real words")
    reviewer.assert_called_once()
    self.assertEqual(result["transcript"],"real words")
 def test_unsupported_backend_does_not_fallback_silently(self):
  with patch.dict(os.environ,{"MICROGEN_TTS_QA_BACKEND":"autoapprove"},clear=False):
   with self.assertRaisesRegex(ValueError,"Unsupported"):
    tts_fidelity.inspect_audio(Path("a.wav"),"a mathematical sentence")
 def test_nonexistent_wav_cannot_pass_pcm_check(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(RuntimeError,"Missing"):
    check_pcm(Path(d)/"missing.wav")
 def test_sequential_failfast_does_not_submit_more_paid_queries(self):
  import tempfile
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   (root/"script.txt").write_text(
       "**Slide 1 [2 sec]:\nTest first.\n"
       "**Slide 2 [2 sec]:\nTest second.\n"
       "**Slide 3 [2 sec]:\nTest third.",encoding="utf8")
   with patch.dict(os.environ,{"MICROGEN_TTS_QA_WORKERS":"1"},clear=False), \
        patch("selenium_pipeline.tts_fidelity._evaluate_cached",
              side_effect=TimeoutError("first true provider timeout")) as qa:
    with self.assertRaises(TimeoutError):
     tts_fidelity.build_report(root)
    self.assertEqual(qa.call_count,1)
if __name__=="__main__":unittest.main()
