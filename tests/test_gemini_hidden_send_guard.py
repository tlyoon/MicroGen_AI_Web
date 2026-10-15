"""Reject a persistently hidden Gemini Send button without submission."""
import unittest
from unittest.mock import patch
from selenium_pipeline.series_gemini import _vendor_module
from tests.test_gemini_send_recovery import DummyGeminiDriver

class StateDriver(DummyGeminiDriver):
    def __init__(self,states):
        super().__init__()
        self.states=list(states)
        self.reads=0
    def execute_script(self,script,*args):
        if "MICROGEN_SEND_VISIBILITY_GUARD_V1" in script:
            self.reads+=1
            return self.states.pop(0) if self.states else None
        return super().execute_script(script,*args)

def client(driver):
    module=_vendor_module()
    instance=module.GeminiSeleniumClient.__new__(module.GeminiSeleniumClient)
    instance.driver=driver
    return instance

class HiddenSendGuardTests(unittest.TestCase):
    def test_stable_hidden_fails_without_click(self):
        state={"composer_chars":50,"send_count":1,"hidden_count":1}
        driver=StateDriver([state,state])
        with patch("time.sleep",lambda _:None):
            self.assertFalse(client(driver).click_send_with_fallbacks(retries=3))
        self.assertEqual(driver.reads,2)
        self.assertFalse(driver.dom_clicked)
        self.assertEqual(driver.cdp_calls,0)

    def test_transient_hidden_keeps_verified_click(self):
        hidden={"composer_chars":50,"send_count":1,"hidden_count":1}
        visible={"composer_chars":50,"send_count":1,"hidden_count":0}
        driver=StateDriver([hidden,visible])
        with patch("time.sleep",lambda _:None):
            self.assertTrue(client(driver).click_send_with_fallbacks(retries=1))
        self.assertTrue(driver.dom_clicked)

    def test_empty_editor_does_not_block_by_opacity_only(self):
        driver=StateDriver([{"composer_chars":0,"send_count":1,"hidden_count":1}])
        with patch("time.sleep",lambda _:None):
            self.assertTrue(client(driver).click_send_with_fallbacks(retries=1))

    def test_unreadable_state_keeps_previous_fallback(self):
        driver=StateDriver([None])
        with patch("time.sleep",lambda _:None):
            self.assertTrue(client(driver).click_send_with_fallbacks(retries=1))

    def test_multiple_hidden_buttons_are_rejected(self):
        state={"composer_chars":22,"send_count":2,"hidden_count":2}
        driver=StateDriver([state,state])
        with patch("time.sleep",lambda _:None):
            self.assertFalse(client(driver).click_send_with_fallbacks(retries=2))
        self.assertFalse(driver.dom_clicked)

if __name__=="__main__":
    unittest.main()
