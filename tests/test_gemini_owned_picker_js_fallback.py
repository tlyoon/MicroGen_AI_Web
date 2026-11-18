"""Proven inert native model-picker recovery, never a model request or Send.

This tests the exact registered one-click repair and the real selection entrypoint
under injected inert Angular events, UI drift and retired registry.
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from selenium_pipeline.gemini_thinking import (
    GeminiThinkingError, _open_owned_mode_picker_with_verified_fallback,
    select_owned_gemini_thinking_level,
)


class FakePicker:
    def __init__(self, *, label="Open mode picker, currently Pro",
                 expanded=False, inert=True):
        self.label=label
        self.expanded=expanded
        self.inert=inert
        self.native_calls=0

    def get_attribute(self, key):
        return {"aria-label":self.label,
                "aria-expanded":"true" if self.expanded else "false"}.get(key)

    def click(self):
        self.native_calls+=1
        if not self.inert:
            self.expanded=not self.expanded


class FakeDriver:
    current_window_handle="owned"
    current_url="https://gemini.google.com/app"
    def __init__(self,picker,*,js_opens=True,js_result=True):
        self.picker=picker
        self.js_opens=js_opens
        self.js_result=js_result
        self.js_calls=0
    def execute_script(self,source,*args):
        self.js_calls+=1
        if args!=(self.picker,):
            raise AssertionError("JS must use original model picker only")
        if "const e=arguments[0]" not in source or "e.click()" not in source:
            raise AssertionError("Unverified JS action")
        if self.js_opens:
            self.picker.expanded=True
        return self.js_result


class VerifiedPickerFallbackTests(unittest.TestCase):
    def exercise(self,driver):
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"pro"}),patch(
                "selenium_pipeline.gemini_ui_semantic_controls.snapshot_options",
                return_value=[]):
            return _open_owned_mode_picker_with_verified_fallback(
                driver,"owned",driver.picker)

    def test_registered_fallback_clicks_exact_picker_only_after_inert_native(self):
        picker=FakePicker()
        driver=FakeDriver(picker)
        self.exercise(driver)
        self.assertEqual(picker.native_calls,1)
        self.assertEqual(driver.js_calls,1)
        self.assertTrue(picker.expanded)

    def test_healthy_native_picker_is_never_js_clicked(self):
        picker=FakePicker(inert=False)
        driver=FakeDriver(picker)
        self.exercise(driver)
        self.assertEqual(picker.native_calls,1)
        self.assertEqual(driver.js_calls,0)
        self.assertTrue(picker.expanded)

    def test_retired_registry_denies_fallback_and_preserves_no_send(self):
        picker=FakePicker()
        driver=FakeDriver(picker)
        with patch("selenium_pipeline.gemini_thinking._registered_owned_picker_click_fallback",
                   return_value=False):
            with self.assertRaisesRegex(GeminiThinkingError,
                                        "NATIVE_CLICK_INERT_UNVERIFIED"):
                self.exercise(driver)
        self.assertEqual(driver.js_calls,0)
        self.assertFalse(picker.expanded)

    def test_wrong_family_and_foreign_tab_never_execute_script(self):
        for label in ("Open mode picker, currently Flash",
                      "Open mode picker, currently Flash-Lite",
                      "Send message","Unknown button"):
            with self.subTest(label=label):
                picker=FakePicker(label=label)
                driver=FakeDriver(picker)
                with self.assertRaises(GeminiThinkingError):
                    self.exercise(driver)
                self.assertEqual(driver.js_calls,0)
        picker=FakePicker()
        driver=FakeDriver(picker)
        driver.current_window_handle="foreign"
        with self.assertRaisesRegex(GeminiThinkingError,"FOREIGN"):
            self.exercise(driver)
        self.assertEqual(driver.js_calls,0)

    def test_js_refusal_or_inert_js_never_qualifies(self):
        for js_opens,js_result in ((False,True),(False,False)):
            with self.subTest(js_opens=js_opens,js_result=js_result):
                picker=FakePicker()
                driver=FakeDriver(picker,js_opens=js_opens,js_result=js_result)
                with self.assertRaisesRegex(GeminiThinkingError,
                                            "FALLBACK_NOT_VERIFIED|STILL_CLOSED"):
                    self.exercise(driver)
                self.assertEqual(driver.js_calls,1)
                self.assertFalse(picker.expanded)

    def test_visible_options_with_stale_aria_must_not_toggle_menu(self):
        picker=FakePicker()
        driver=FakeDriver(picker)
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"pro"}),patch(
                "selenium_pipeline.gemini_ui_semantic_controls.snapshot_options",
                return_value=["visible-semantic-option"]):
            _open_owned_mode_picker_with_verified_fallback(
                driver,"owned",picker)
        self.assertEqual(driver.js_calls,0)
        self.assertEqual(picker.native_calls,1)

    def test_real_new_model_menu_does_not_forge_medium_thinking_proof(self):
        from selenium_pipeline.gemini_ui_semantic_controls import Option
        from selenium_pipeline.gemini_thinking import (
            _thinking_expander,_level_item)
        picker=FakePicker(expanded=True)
        driver=FakeDriver(picker)
        driver.find_elements=lambda *args: []
        new_models=[
            Option(picker,"Everyday help\\n4 Hydrogen\\nNew",False,False),
            Option(picker,"Complex problems\\n4 Hydrogen Thinking",False,False),
            Option(picker,"Detailed research\\n3.1 Pro",True,False),
        ]
        with patch("selenium_pipeline.gemini_ui_semantic_controls.snapshot_options",
                   return_value=new_models):
            with self.assertRaisesRegex(
                    GeminiThinkingError,"EXPANDER_NOT_UNIQUE_OR_MISSING"):
                _thinking_expander(driver)
        self.assertFalse(_level_item("4 Hydrogen Thinking","medium"))
        self.assertFalse(_level_item("Complex problems\\n4 Hydrogen Thinking",
                                     "medium"))
        self.assertEqual(driver.js_calls,0)
        self.assertTrue(picker.expanded)

    def test_normal_thinking_selector_self_heals_in_same_no_send_attempt(self):
        from tests.test_gemini_adaptive_ui_thinking import AdaptiveBrowser
        browser=AdaptiveBrowser(mode="pro",level="low")
        originally_clicked=browser.picker.click
        calls={"n":0}
        def native_inert_once():
            calls["n"]+=1
            if calls["n"]==1:
                browser.events.append("native-inert-model-picker")
                return
            originally_clicked()
        browser.picker.click=native_inert_once
        def exact_js(source,*args):
            self.assertEqual(args,(browser.picker,))
            self.assertIn("e.click()",source)
            browser.events.append("one-owned-picker-js-click")
            originally_clicked()
            return True
        browser.execute_script=exact_js
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"pro"}),patch(
            "selenium_pipeline.gemini_ui_semantic_controls.snapshot_options",
            return_value=None):
            level=select_owned_gemini_thinking_level(
                browser,"owned",level="medium",timeout=3)
        self.assertEqual(level,"medium")
        self.assertEqual(browser.level,"medium")
        self.assertFalse(browser.menu_open)
        self.assertEqual(browser.events.count("one-owned-picker-js-click"),1)
        self.assertEqual(browser.events.count("click:thinking-medium"),1)


if __name__=="__main__":
    unittest.main()
