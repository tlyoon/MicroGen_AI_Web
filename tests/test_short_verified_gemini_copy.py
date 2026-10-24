"""A valid one-shot Gemini health canary is shorter than the old 60-char Copy floor."""
import json
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline import series_gemini
from selenium_pipeline.gemini_response_recovery import response_snapshot_with_scoped_copy
from selenium_pipeline.one_shot_gemini_source_health_probe import EXPECTED
from test_gemini_response_recovery import FakeDriver

CANARY=json.dumps(EXPECTED,separators=(",",":"))


class GeminiShortVerifiedCopy(unittest.TestCase):
    def test_short_complete_owned_json_can_replace_actual_11_char_placeholder(self):
        self.assertLess(len(CANARY),60)
        driver=FakeDriver(response="Gemini said")
        result=response_snapshot_with_scoped_copy(
            driver,"owned_tab",copy_response=lambda _:CANARY,
            accept_fn=series_gemini._looks_complete)
        self.assertEqual(result["text"],CANARY)
        self.assertEqual(result["capture_status"],"vendor_verified_response_copy")

    def test_short_prose_or_invalid_json_remains_untrusted(self):
        driver=FakeDriver(response="Gemini said")
        for candidate in ("I cannot comply", "This appears to be a response.",
                          "Gemini said", '{"probe":'):
            result=response_snapshot_with_scoped_copy(
                driver,"owned_tab",copy_response=lambda _,t=candidate:t,
                accept_fn=series_gemini._looks_complete)
            self.assertEqual(result["text"],"Gemini said")

    def test_copy_not_allowed_in_other_tab(self):
        driver=FakeDriver(handle="other_tab",response="Gemini said")
        calls=[]
        result=response_snapshot_with_scoped_copy(
            driver,"owned_tab",
            copy_response=lambda _:calls.append(1) or CANARY,
            accept_fn=series_gemini._looks_complete)
        self.assertFalse(result["text"])
        self.assertEqual(calls,[])

    def test_real_bridge_recovers_own_short_canary_without_second_send(self):
        with tempfile.TemporaryDirectory() as d:
            driver=FakeDriver(response="Gemini said",generating=False)
            seen={"send":0,"copy":0,"shutdown":0}
            def send(**_):
                seen["send"]+=1
                return True
            client=SimpleNamespace(
                driver=driver,_automation_tab="owned_tab",
                start=lambda **_:None,
                open_clean_gemini_chat=lambda:None,
                upload_files=lambda _:None,
                type_prompt_text=lambda *_,**kw:True,
                click_send_with_fallbacks=send,
                shutdown=lambda:seen.__setitem__("shutdown",seen["shutdown"]+1))
            def copy(_):
                seen["copy"]+=1
                return CANARY
            vendor=SimpleNamespace(
                Config=lambda **kw:SimpleNamespace(**kw),
                GeminiSeleniumClient=lambda cfg:client,
                capture_gemini_response_like_manual_copy=
                    lambda *_,**__:(_ for _ in ()).throw(TimeoutError("test")),
                _copy_via_toolbar_copy_button=copy)
            with (
                patch.object(series_gemini,"_vendor_module",return_value=vendor),
                patch("selenium_pipeline.three_pc_worker.LocalInstanceLock",
                      side_effect=lambda *a,**kw:nullcontext()),
                patch("selenium_pipeline.gemini_model.ensure_mode",
                      return_value="Open mode picker, currently Gemini Flash"),
                patch.dict("os.environ",{"LOCALAPPDATA":str(Path(d))}),
            ):
                response=series_gemini._browser_request(
                    "No original math review",[],port=9222,wait_cap_s=75,min_chars=8,
                    accept_fn=series_gemini._looks_complete)
            self.assertEqual(response,CANARY)
            self.assertEqual(seen["send"],1)
            self.assertEqual(seen["shutdown"],1)
            self.assertGreaterEqual(seen["copy"],1)


if __name__=="__main__":
    unittest.main()
