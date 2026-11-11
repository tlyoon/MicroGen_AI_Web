"""Stateful, source-free Gemini UI drift and thinking-level regressions.

Model names/descriptions, picker markup, submenu roles, option ordering, and
selected-state attributes may change independently. No Selenium live browser,
no provider Send, no API, no original source, no release authorization.
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from selenium_pipeline.gemini_model import (
    GeminiModelError, _matches_mode, _eligible_mode_menu_text,
    select_owned_gemini_mode, assert_owned_gemini_mode,
)
from selenium_pipeline.gemini_thinking import (
    GeminiThinkingError, configured_thinking_level, _level_item,
    assert_owned_gemini_thinking_level, select_owned_gemini_thinking_level,
)


class Control:
    def __init__(self, browser, role, text, key):
        self.b=browser
        self.role=role
        self.text=text
        self.id=key

    def is_displayed(self):
        return True

    def get_attribute(self, name):
        if name=="role":
            return self.role
        if name=="aria-label":
            if self.id=="picker":
                return self.b.picker_label()
            return ""
        if name=="data-test-id":
            return "bard-mode-menu-button" if self.id=="picker" else None
        if name=="aria-expanded":
            return str(self.b.menu_open if self.id=="picker"
                       else self.b.thinking_open).lower()
        if name in ("aria-checked","aria-selected"):
            if self.id.startswith("thinking-"):
                if self.b.radio_attr==name:
                    return str(self.b.level==self.id.split("-",1)[1]).lower()
                return None
            if self.id.startswith("model-") and name=="aria-checked":
                return str(self.b.mode==self.id.split("-",1)[1]).lower()
            return None
        if name=="aria-disabled":
            return "false"
        return None

    def click(self):
        self.b.events.append("click:"+self.id)
        if self.id=="picker":
            self.b.menu_open=not self.b.menu_open
            self.b.thinking_open=False if not self.b.menu_open else self.b.thinking_open
        elif self.id=="thinking-expander":
            self.b.thinking_open=not self.b.thinking_open
        elif self.id.startswith("thinking-"):
            self.b.level=self.id.split("-",1)[1]
            self.b.menu_open=False
            self.b.thinking_open=False
        elif self.id.startswith("model-"):
            self.b.mode=self.id.split("-",1)[1]
            self.b.menu_open=False
            self.b.thinking_open=False


class AdaptiveBrowser:
    def __init__(self, *, mode="flash-lite", level="low",
                 picker_variant="normal", thinking_role="menuitem",
                 radio_role="menuitemradio", radio_attr="aria-checked",
                 missing_medium=False, duplicate_medium=False,
                 reordered=False):
        self.current_window_handle="owned"
        self.current_url="https://gemini.google.com/app"
        self.mode=mode
        self.level=level
        self.picker_variant=picker_variant
        self.thinking_role=thinking_role
        self.radio_role=radio_role
        self.radio_attr=radio_attr
        self.missing_medium=missing_medium
        self.duplicate_medium=duplicate_medium
        self.reordered=reordered
        self.menu_open=False
        self.thinking_open=False
        self.events=[]
        self.picker=Control(self, "button", mode, "picker")
        self.expander=Control(self, thinking_role, "Thinking level","thinking-expander")
        self.mode_rows=[
            Control(self,radio_role,"Quick answers\n3.5 Flash-Lite","model-flash-lite"),
            Control(self,radio_role,"All-around help\n3.8 Flash","model-flash"),
            Control(self,radio_role,"Detailed research\n3.1 Pro","model-pro"),
        ]
        self.level_rows=[
            Control(self,radio_role,"Low\nFast and efficient","thinking-low"),
            Control(self,radio_role,"Medium\nBalanced depth","thinking-medium"),
            Control(self,radio_role,"High\nExtra thorough","thinking-high"),
        ]
        if missing_medium:
            self.level_rows=[x for x in self.level_rows if x.id!="thinking-medium"]
        if duplicate_medium:
            self.level_rows.append(Control(
                self,radio_role,"Medium\nBalanced depth","thinking-medium-alt"))
        if reordered:
            self.mode_rows=list(reversed(self.mode_rows))
            self.level_rows=list(reversed(self.level_rows))

    def picker_label(self):
        family={"flash-lite":"Flash-Lite","flash":"Flash","pro":"Pro"}[self.mode]
        if self.picker_variant=="normal":
            return "Open mode picker, currently " + family
        if self.picker_variant=="renamed":
            return "Current model: "+family
        if self.picker_variant=="testid_only":
            return ""
        if self.picker_variant=="unsupported":
            return "Unknown control"
        return "Open mode picker, currently " + family

    def find_elements(self, by, selector):
        if selector=='button[aria-label^="Open mode picker"]':
            return [self.picker] if self.picker_variant=="normal" else []
        if selector=='[data-test-id="bard-mode-menu-button"]':
            return [] if self.picker_variant=="unsupported" else [self.picker]
        if selector in ('[aria-label*="model"]','[aria-label*="mode"]',
                        'button[aria-haspopup="menu"]',
                        '[role="button"][aria-haspopup="menu"]'):
            return [self.picker] if self.picker_variant!="unsupported" else []
        if not self.menu_open:
            return []
        elements=self.mode_rows[:]+[self.expander]
        if self.thinking_open:
            elements+=self.level_rows
        if selector=="gem-menu-item":
            return elements
        if selector=="[aria-expanded]":
            return [self.picker,self.expander]
        if selector=="button":
            return [self.picker]
        if selector.startswith("[aria-"):
            return [x for x in elements if x.role==self.radio_role]
        if 'role=' in selector:
            import re
            marker=re.search(r'role="([^"]+)"',selector)
            role=marker.group(1) if marker else None
            return [x for x in elements if x.role==role]
        return []

    def execute_script(self,*args):
        raise AssertionError("Semantic role+state lookup should not inject DOM events")


class AdaptiveGeminiUiTests(unittest.TestCase):
    def test_config_defaults_to_medium_and_rejects_invalid(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(configured_thinking_level(),"medium")
        with patch.dict(os.environ,{"MICROGEN_GEMINI_THINKING_LEVEL":"high"}):
            self.assertEqual(configured_thinking_level(),"high")
        with patch.dict(os.environ,{"MICROGEN_GEMINI_THINKING_LEVEL":"medium-ish"}):
            with self.assertRaises(GeminiThinkingError):
                configured_thinking_level()

    def test_both_current_options_and_future_description_text(self):
        self.assertTrue(_level_item("Medium\nBalanced depth","medium"))
        self.assertTrue(_level_item("Medium\nWhatever the next description is","medium"))
        self.assertFalse(_level_item("Low\nMedium is not selected","medium"))
        self.assertFalse(_level_item("High / Medium", "medium"))
        self.assertTrue(_eligible_mode_menu_text("Gemini Flash", "flash"))
        self.assertTrue(_eligible_mode_menu_text(
            "All-around help\n3.8 Flash", "flash"))
        self.assertFalse(_eligible_mode_menu_text(
            "3.5 Flash-Lite\n3.8 Flash", "flash"))
        self.assertFalse(_eligible_mode_menu_text(
            "3.8 Flash\n3.1 Pro", "flash"))

    def test_real_current_menu_flash_then_medium_positive_verification(self):
        browser=AdaptiveBrowser()
        selected=select_owned_gemini_mode(browser,"owned",mode="flash",timeout=1)
        self.assertEqual(selected,"Open mode picker, currently Flash")
        level=select_owned_gemini_thinking_level(
            browser,"owned",level="medium",timeout=1)
        self.assertEqual(level,"medium")
        self.assertEqual(browser.level,"medium")
        self.assertEqual(assert_owned_gemini_thinking_level(
            browser,"owned","medium"),"medium")
        self.assertEqual(assert_owned_gemini_mode(browser,"owned"),selected)
        self.assertFalse(browser.menu_open)
        self.assertEqual(browser.events.count("click:thinking-medium"),1)

    def test_renamed_picker_text_and_reordered_options_still_work(self):
        browser=AdaptiveBrowser(picker_variant="renamed",reordered=True,
                                radio_role="option",radio_attr="aria-selected",
                                thinking_role="button")
        self.assertIn("currently Flash",select_owned_gemini_mode(
            browser,"owned",mode="flash",timeout=1))
        self.assertEqual(select_owned_gemini_thinking_level(
            browser,"owned",level="medium",timeout=1),"medium")
        self.assertEqual(assert_owned_gemini_thinking_level(
            browser,"owned","medium"),"medium")

    def test_dedicated_testid_and_button_text_fallback(self):
        browser=AdaptiveBrowser(mode="flash",picker_variant="testid_only",
                                level="medium")
        browser.picker.text="Flash"
        self.assertIn("currently Flash",assert_owned_gemini_mode(
            browser,"owned",mode="flash"))
        self.assertEqual(assert_owned_gemini_thinking_level(
            browser,"owned","medium"),"medium")

    def test_semantic_thinking_expander_rename_keeps_medium_verifiable(self):
        browser=AdaptiveBrowser(mode="flash",level="low")
        browser.expander.text="Reasoning effort"
        self.assertEqual(select_owned_gemini_thinking_level(
            browser,"owned",level="medium",timeout=1),"medium")
        self.assertEqual(assert_owned_gemini_thinking_level(
            browser,"owned","medium"),"medium")

    def test_production_vendor_send_boundary_requires_both_flash_and_medium(self):
        from selenium_pipeline.series_gemini import _vendor_module
        from selenium_pipeline import gemini_selenium_only_policy as policy
        vendor=_vendor_module()
        client=vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        browser=AdaptiveBrowser(mode="flash",level="medium")
        client.driver=browser
        client._automation_tab="owned"
        sent=[]
        with patch.dict(os.environ,{
                "MICROGEN_SINGLE_PROVIDER_SEND":"1",
                "MICROGEN_GEMINI_UI_MODE":"flash",
                "MICROGEN_GEMINI_THINKING_LEVEL":"medium"}), \
             patch.object(policy,"click_one_owned_gemini_send",
                          side_effect=lambda *a:sent.append("ONE_CLICK") or True), \
             patch.object(policy,"owned_gemini_send_baseline",
                          return_value={"safe":True}), \
             patch.object(policy,"observe_gemini_send_registration",
                          return_value={"status":"NEW_USER_TURN_AND_COMPOSER_CLEARED",
                                        "registered":True}):
            self.assertTrue(client.click_send_with_fallbacks(retries=1))
        self.assertEqual(sent,["ONE_CLICK"])
        self.assertEqual(browser.mode,"flash")
        self.assertEqual(browser.level,"medium")

    def test_production_vendor_send_refuses_missing_medium_without_any_click(self):
        from selenium_pipeline.series_gemini import _vendor_module
        from selenium_pipeline import gemini_selenium_only_policy as policy
        vendor=_vendor_module()
        client=vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        browser=AdaptiveBrowser(mode="flash",level="low")
        client.driver=browser
        client._automation_tab="owned"
        with patch.dict(os.environ,{
                "MICROGEN_SINGLE_PROVIDER_SEND":"1",
                "MICROGEN_GEMINI_UI_MODE":"flash",
                "MICROGEN_GEMINI_THINKING_LEVEL":"medium"}), \
             patch.object(policy,"click_one_owned_gemini_send",
                          side_effect=AssertionError("NEVER_SEND")):
            with self.assertRaisesRegex(
                    GeminiThinkingError,"NOT_VERIFIED_NO_SEND"):
                client.click_send_with_fallbacks(retries=1)

    def test_wrong_model_cannot_be_equated_to_flash(self):
        browser=AdaptiveBrowser()
        with self.assertRaisesRegex(
            GeminiModelError,"FAMILY_MISMATCH"):
            assert_owned_gemini_mode(browser,"owned","flash")
        self.assertFalse(_matches_mode(
            "Open mode picker, currently Flash-Lite","flash"))

    def test_no_medium_or_ambiguous_medium_fails_without_send(self):
        for kwargs in ({"missing_medium":True},{"duplicate_medium":True}):
            browser=AdaptiveBrowser(mode="flash",**kwargs)
            with self.assertRaises(GeminiThinkingError):
                select_owned_gemini_thinking_level(
                    browser,"owned",level="medium",timeout=1)
            self.assertEqual(browser.level,"low")

    def test_foreign_tab_and_unknown_picker_never_guess(self):
        browser=AdaptiveBrowser(mode="flash",picker_variant="unsupported")
        with self.assertRaises(GeminiModelError):
            assert_owned_gemini_mode(browser,"owned","flash")
        browser=AdaptiveBrowser(mode="flash")
        browser.current_window_handle="foreign"
        with self.assertRaises(GeminiThinkingError):
            select_owned_gemini_thinking_level(
                browser,"owned",level="medium",timeout=1)
        self.assertEqual(browser.level,"low")

    def test_changing_new_chat_level_must_be_reverified(self):
        browser=AdaptiveBrowser(mode="flash",level="medium")
        self.assertEqual(assert_owned_gemini_thinking_level(
            browser,"owned","medium"),"medium")
        browser.level="low"
        with self.assertRaisesRegex(GeminiThinkingError,"NOT_VERIFIED"):
            assert_owned_gemini_thinking_level(
                browser,"owned","medium")
        self.assertEqual(select_owned_gemini_thinking_level(
            browser,"owned",level="medium",timeout=1),"medium")
        self.assertEqual(browser.level,"medium")


if __name__=="__main__":
    unittest.main()
