"""Actual Gemini Selenium owned-tab model selection and no-Send regression.

Reproduces Serway 7.6: parent selected Flash, but copied vendor workers
falsely accepted or selected "Flash-Lite" in their freshly owned tabs.
No browser connection, credentials, paid API or model Send in these tests.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from selenium_pipeline.gemini_model import (
    GeminiModelError, _matches_mode, _eligible_mode_menu_text,
    select_owned_gemini_mode, assert_owned_gemini_mode,
)
from selenium_pipeline.series_gemini import _vendor_module


class FakePicker:
    def __init__(self, browser):
        self.browser=browser
        self.id="picker"
    def is_displayed(self):
        return True
    def get_attribute(self,name):
        return ("Open mode picker, currently "+self.browser.mode
                if name=="aria-label" else None)
    def click(self):
        self.browser.menu_open=True
        self.browser.events.append("picker-open")


class FakeOption:
    def __init__(self,browser,label):
        self.browser=browser
        self.text=label
        self.id="option_"+label
    def is_displayed(self):
        return True
    def get_attribute(self,name):
        return None
    def click(self):
        # New Gemini menus contain a description and a distinct model
        # sublabel; the selected family is defined by that sublabel.
        if "3.8 Flash" in self.text:
            self.browser.mode="Flash"
        elif "3.5 Flash-Lite" in self.text:
            self.browser.mode="Flash-Lite"
        else:
            self.browser.mode=self.text
        self.browser.menu_open=False
        self.browser.events.append("selected:"+self.browser.mode)


class FakeNewChat:
    def __init__(self,browser):
        self.browser=browser
    def is_displayed(self):
        return True
    def click(self):
        # What current Gemini sometimes does after a fresh New chat.
        self.browser.mode="Flash-Lite"
        self.browser.events.append("new-chat-reset-to-lite")


class FakeSend:
    def is_enabled(self):
        return True


class FakeOwnedBrowser:
    def __init__(self,mode="Flash-Lite",menu=("Flash-Lite","Flash","3.1 Pro")):
        self.mode=mode
        self.menu_options=menu
        self.menu_open=False
        self.current_window_handle="owned"
        self.current_url="https://gemini.google.com/app"
        self.events=[]
        self.switch_to=SimpleNamespace(window=self.switch_window)
    def switch_window(self,handle):
        if handle!="owned":
            raise AssertionError("Never borrow a foreign tab")
    def get(self,url):
        assert url.startswith("https://gemini.google.com/")
        self.current_url=url
        self.events.append("navigate-new-owned-tab")
    def find_elements(self,by,selector):
        if selector=='button[aria-label^="Open mode picker"]':
            return [FakePicker(self)]
        if selector in ('[role="menuitem"]',
                        'gem-menu-item[role="menuitem"]'):
            return [FakeOption(self,text) for text in self.menu_options] if self.menu_open else []
        if selector=='a[aria-label="New chat"], [data-test-id="side-nav-sparkle-button"]':
            return [FakeNewChat(self)]
        if selector.startswith("//button[@aria-label='Send message'"):
            return [FakeSend()]
        if selector=='[contenteditable="true"][role="textbox"]':
            return [object()]
        if selector=='button[aria-label="Upload & tools"]':
            return []
        return []
    def execute_script(self,*args,**kwargs):
        raise AssertionError("No DOM-injection/fallback allowed in this fixture")


class LiveMenuShapeOwnedBrowser(FakeOwnedBrowser):
    """The actual November 11 Dell-115 gem-menu-item role=menuitemradio."""
    def __init__(self):
        super().__init__(mode="Flash-Lite", menu=(
            "Quick answers\n3.5 Flash-Lite",
            "All-around help\n3.8 Flash",
            "Detailed research\n3.1 Pro",
        ))

    def find_elements(self,by,selector):
        if selector in ('[role="menuitemradio"]',
                        'gem-menu-item[role="menuitemradio"]'):
            return [FakeOption(self,text) for text in self.menu_options] if self.menu_open else []
        if selector in ('[role="menuitem"]',
                        'gem-menu-item[role="menuitem"]'):
            return []
        return super().find_elements(by,selector)


class G2OwnedFlashModelTests(unittest.TestCase):
    def setUp(self):
        # These older tests isolate Flash-family and one-Send behavior.
        # Thinking radio behavior is independently tested in the UI
        # capability suite with actual stateful menu mocks.
        self.thinking = patch(
            "selenium_pipeline.gemini_thinking.select_owned_gemini_thinking_level",
            return_value="medium")
        self.thinking.start()
        self.addCleanup(self.thinking.stop)
        self.thinking_verify = patch(
            "selenium_pipeline.gemini_thinking.assert_owned_gemini_thinking_level",
            return_value="medium")
        self.thinking_verify.start()
        self.addCleanup(self.thinking_verify.stop)

    def test_canonical_flash_classifier_never_accepts_flash_lite_or_pro(self):
        for label in (
            "Open mode picker, currently Flash-Lite",
            "Open mode picker, currently Flash Lite",
            "Open mode picker, currently Flash / Pro",
            "Open mode picker, currently Pro",
            "Open mode picker, currently Not selected"):
            self.assertFalse(_matches_mode(label,"flash"),label)
        for label in ("Open mode picker, currently Flash",
                      "Open mode picker, currently Flash High",
                      "Open mode picker, currently Flash Fast"):
            self.assertTrue(_matches_mode(label,"flash"),label)
        for label in ("Flash-Lite", "Flash Lite", "Flash Pro",
                      "Flash / Pro"):
            self.assertFalse(_eligible_mode_menu_text(label,"flash"))
        self.assertTrue(_eligible_mode_menu_text("Flash\nFast mode","flash"))

    def test_actual_november_2026_radio_menu_selects_only_38_flash(self):
        self.assertTrue(_eligible_mode_menu_text(
            "All-around help\n3.8 Flash", "flash"))
        self.assertFalse(_eligible_mode_menu_text(
            "Quick answers\n3.5 Flash-Lite", "flash"))
        self.assertFalse(_eligible_mode_menu_text(
            "Quick answers\n3.5 Flash-Lite\nAll-around help\n3.8 Flash"
            "\nDetailed research\n3.1 Pro", "flash"))
        driver=LiveMenuShapeOwnedBrowser()
        label=select_owned_gemini_mode(driver,"owned",mode="flash",timeout=1)
        self.assertEqual(label,"Open mode picker, currently Flash")
        self.assertEqual(driver.events,["picker-open","selected:Flash"])
        self.assertEqual(assert_owned_gemini_mode(driver,"owned"),label)

    def test_parent_ensure_flash_uses_same_live_radio_selector(self):
        from selenium import webdriver as selenium_webdriver
        from selenium_pipeline.gemini_model import ensure_flash
        driver=LiveMenuShapeOwnedBrowser()
        driver.window_handles=["owned"]
        driver.quit=lambda:None
        with patch.object(selenium_webdriver,"Chrome",return_value=driver):
            label=ensure_flash(timeout=0.1)
        self.assertEqual(label,"Open mode picker, currently Flash")
        self.assertEqual(driver.events,["picker-open","selected:Flash"])

    def test_reproduced_old_lite_picker_is_corrected_to_real_flash(self):
        driver=FakeOwnedBrowser()
        label=select_owned_gemini_mode(driver,"owned",mode="flash",timeout=1)
        self.assertEqual(label,"Open mode picker, currently Flash")
        self.assertEqual(driver.mode,"Flash")
        self.assertEqual(driver.events,["picker-open","selected:Flash"])
        self.assertEqual(assert_owned_gemini_mode(driver,"owned"),
                         "Open mode picker, currently Flash")
        self.assertEqual(len([e for e in driver.events if "send" in e]),0)

    def test_new_chat_can_reset_flash_lite_and_pipeline_corrects_again(self):
        driver=FakeOwnedBrowser()
        select_owned_gemini_mode(driver,"owned",mode="flash",timeout=1)
        FakeNewChat(driver).click()
        self.assertEqual(driver.mode,"Flash-Lite")
        second=select_owned_gemini_mode(driver,"owned",mode="flash",timeout=1)
        self.assertIn("currently Flash",second)
        self.assertEqual(driver.events.count("selected:Flash"),2)

    def test_no_genuine_flash_menu_fails_pre_send_without_lite_fallback(self):
        driver=FakeOwnedBrowser(menu=("Flash-Lite","3.1 Pro"))
        with self.assertRaisesRegex(
                GeminiModelError,"PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE"):
            select_owned_gemini_mode(driver,"owned",mode="flash",timeout=1)
        self.assertEqual(driver.mode,"Flash-Lite")
        self.assertNotIn("selected:Flash-Lite",driver.events)

    def test_foreign_tab_or_wrong_mode_refused_before_send(self):
        driver=FakeOwnedBrowser(mode="Flash-Lite")
        with self.assertRaisesRegex(GeminiModelError,"MISMATCH_NO_SEND"):
            assert_owned_gemini_mode(driver,"owned",mode="flash")
        driver.current_window_handle="borrowed"
        with self.assertRaises(GeminiModelError):
            select_owned_gemini_mode(driver,"owned",mode="flash",timeout=1)
        self.assertEqual(driver.events,[])

    def test_real_vendor_open_clean_chat_selects_flash_twice_and_not_lite(self):
        vendor=_vendor_module()
        client=vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        driver=FakeOwnedBrowser(mode="Flash-Lite")
        client.driver=driver
        client.cfg=SimpleNamespace(gemini_url="https://gemini.google.com/app")
        client._automation_tab="owned"
        client._owned_tab_focus_emulated=False
        client.ensure_driver_is_alive=lambda:None
        client._ensure_owned_tab_visible=lambda:"owned_visible"
        client._clear_prompt_safely=lambda:None
        with patch.object(vendor,"_rotate_owned_gemini_tab",return_value="owned"), \
             patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash",
                                  "MICROGEN_MODEL_PHASE":"development"}):
            client.open_clean_gemini_chat()
        self.assertEqual(driver.mode,"Flash")
        self.assertEqual(driver.events.count("selected:Flash"),2)
        self.assertIn("new-chat-reset-to-lite",driver.events)

    def test_real_vendor_provider_send_gate_blocks_wrong_flash_lite(self):
        vendor=_vendor_module()
        from selenium_pipeline import gemini_selenium_only_policy as sends
        client=vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        client.driver=FakeOwnedBrowser(mode="Flash-Lite")
        client._automation_tab="owned"
        with patch.dict(os.environ,{"MICROGEN_SINGLE_PROVIDER_SEND":"1",
                                  "MICROGEN_GEMINI_UI_MODE":"flash"}), \
             patch.object(sends,"click_one_owned_gemini_send",
                          side_effect=AssertionError("MUST NOT SEND")):
            with self.assertRaisesRegex(GeminiModelError,"MISMATCH_NO_SEND"):
                client.click_send_with_fallbacks(retries=1)

    def test_real_vendor_provider_send_gate_accepts_flash_for_one_send(self):
        vendor=_vendor_module()
        from selenium_pipeline import gemini_selenium_only_policy as sends
        client=vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        client.driver=FakeOwnedBrowser(mode="Flash")
        client._automation_tab="owned"
        calls=[]
        def fake_send(*args,**kwargs):
            calls.append("ONE_CLICK")
            return True
        with patch.dict(os.environ,{"MICROGEN_SINGLE_PROVIDER_SEND":"1",
                                  "MICROGEN_GEMINI_UI_MODE":"flash"}), \
             patch.object(sends,"click_one_owned_gemini_send",side_effect=fake_send), \
             patch.object(sends,"owned_gemini_send_baseline",return_value={"safe":True}), \
             patch.object(sends,"observe_gemini_send_registration",return_value={
                 "registered":True,"status":"NEW_USER_TURN_AND_COMPOSER_CLEARED"}):
            self.assertTrue(client.click_send_with_fallbacks(retries=1))
        self.assertEqual(calls,["ONE_CLICK"])

    def test_normal_vendor_imports_one_canonical_selector_not_substring(self):
        source=(Path(__file__).resolve().parents[1]/"selenium_pipeline"/
                "vendor_template_v2"/"selenium.py").read_text(encoding="utf8")
        self.assertIn("select_owned_gemini_mode(",source)
        self.assertIn("assert_owned_gemini_mode(",source)
        self.assertNotIn('"currently" in label_l and target_mode in label_l',source)


if __name__=="__main__":
    unittest.main()
