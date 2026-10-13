"""Regression for Gemini UI transition where XPath misses an enabled Send button.

The mocked browser represents the observed HP Gemini DOM (13 October 2026).
The real HP submission was also accepted by positive new-user-turn evidence.
"""
import unittest

from selenium_pipeline.series_gemini import _vendor_module


class DummyGeminiDriver:
    current_url="https://gemini.google.com/app"

    def __init__(self):
        self.dom_clicked=False
        self.cdp_calls=0

    def find_elements(self,by,selector):
        # Current Angular Gemini can expose the exact Send message control
        # to querySelectorAll even if legacy Selenium XPath misses it.
        return []

    def execute_script(self,script,*args):
        if "buttons[0].click()" in script:
            # Match exact button, nonempty editor, one visible enabled target.
            assert "Send message" in script and "buttons.length!==1" in script
            assert "if(!text)" in script
            self.dom_clicked=True
            return True
        if "const beforeUsers=" in script:
            return "new-user-turn+composer-cleared" if self.dom_clicked else ""
        if "return [users.size, models, stop, text]" in script:
            return [0,0,False,"Approved storyboard candidate prompt"]
        raise AssertionError("Unexpected Selenium browser operation: "+script[:90])

    def execute_cdp_cmd(self,*args,**kwargs):
        self.cdp_calls+=1
        raise AssertionError("No synthetic CDP Enter should be needed")


class GeminiSendRecoveryTests(unittest.TestCase):
    def test_dom_exact_send_fallback_with_positive_turn_evidence(self):
        vendor=_vendor_module()
        obj=vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        obj.driver=DummyGeminiDriver()
        self.assertTrue(obj.click_send_with_fallbacks(retries=1))
        self.assertTrue(obj.driver.dom_clicked)
        self.assertEqual(obj.driver.cdp_calls,0)

    def test_long_model_response_uses_caller_timeout_in_fallback(self):
        from unittest.mock import patch
        vendor=_vendor_module()
        class SnapshotDriver:
            def execute_script(self,*_):
                return [1,1,False,""]  # model turn exists; no false early abort
        waited=[]
        def fake_dom(driver,preset,overrides):
            waited.append(overrides["max_wait"])
            return "A"*300+"END"
        with patch.object(vendor,"_wait_until_generation_finishes",lambda *a,**kw:None), \
             patch.object(vendor,"_copy_via_toolbar_copy_button",lambda *a:""), \
             patch.object(vendor,"_copy_via_more_menu",lambda *a:""), \
             patch.object(vendor,"adaptive_wait_and_copy_full",fake_dom), \
             patch.object(vendor.time,"sleep",lambda n:None):
            result=vendor.capture_gemini_response_like_manual_copy(
                SnapshotDriver(),wait_cap=420,prefer_latex_doc=False,
                retries=1,min_chars=200,accept_fn=lambda s:s.endswith("END"),
            )
        self.assertTrue(result.endswith("END"))
        self.assertEqual(waited,[420])


if __name__=="__main__":
    unittest.main()
