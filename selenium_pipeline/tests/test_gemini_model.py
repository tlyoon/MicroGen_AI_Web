import unittest
from unittest.mock import MagicMock, patch
from selenium import webdriver as selenium_webdriver

from selenium_pipeline.gemini_model import (
    GeminiModelError,
    configured_ui_mode,
    ensure_flash,
    ensure_mode,
    ensure_pro,
    _eligible_mode_menu_text,
)


class ModelSelectorTests(unittest.TestCase):
    def setup_driver(self, label="Open mode picker, currently Gemini Flash", items=None):
        driver = MagicMock()
        driver.window_handles = ["gemini"]
        driver.current_url = "https://gemini.google.com/app"
        picker = MagicMock()
        picker.is_displayed.return_value = True
        picker.get_attribute.return_value = label

        def find_elements(_by, selector):
            if "Open mode picker" in selector:
                return [picker]
            if "menuitem" in selector:
                return items or []
            return []

        driver.find_elements.side_effect = find_elements
        return driver, picker

    @patch.dict("os.environ", {}, clear=True)
    def test_development_defaults_to_flash(self):
        self.assertEqual(configured_ui_mode(), "flash")

    @patch.dict("os.environ", {"MICROGEN_MODEL_PHASE": "production"}, clear=True)
    def test_production_phase_still_defaults_to_flash(self):
        self.assertEqual(configured_ui_mode(), "flash")

    @patch.dict("os.environ", {"MICROGEN_GEMINI_UI_MODE": "pro"}, clear=True)
    def test_explicit_override_can_select_pro(self):
        self.assertEqual(configured_ui_mode(), "pro")

    @patch.object(selenium_webdriver, "Chrome")
    def test_already_flash(self, chrome):
        driver, picker = self.setup_driver("Open mode picker, currently Gemini Flash")
        chrome.return_value = driver
        self.assertIn("Flash", ensure_flash())
        picker.click.assert_not_called()
        driver.quit.assert_called_once()

    @patch.object(selenium_webdriver, "Chrome")
    def test_selects_flash_menu_item(self, chrome):
        item = MagicMock()
        item.text = "3.8 Flash\nAll-around help"
        item.is_displayed.return_value = True
        item.get_attribute.return_value = "false"
        driver, picker = self.setup_driver(
            "Open mode picker, currently Gemini Pro", items=[item]
        )
        picker.get_attribute.side_effect = [
            "Open mode picker, currently Gemini Pro",
            "Open mode picker, currently Gemini Flash",
        ]
        chrome.return_value = driver
        self.assertIn("Flash", ensure_mode(mode="flash"))
        item.click.assert_called_once()
        driver.quit.assert_called_once()

    def test_flash_menu_filter_does_not_select_lite(self):
        for name in ("Flash-Lite","Gemini Flash Lite","3.8 Flash-Lite",
                     "Flash Pro","Pro Flash","Gemini Pro"):
            self.assertFalse(_eligible_mode_menu_text(name,"flash"),name)
        for name in ("3.8 Flash\nAll-around help","Flash High","Gemini Flash"):
            self.assertTrue(_eligible_mode_menu_text(name,"flash"),name)

    @patch.object(selenium_webdriver, "Chrome")
    def test_prefers_flash_over_flash_lite_even_if_lite_listed_first(self,chrome):
        wrong=MagicMock()
        wrong.text="Flash-Lite\nQuick answers"
        wrong.is_displayed.return_value=True
        right=MagicMock()
        right.text="Flash High\nAll-around help"
        right.is_displayed.return_value=True
        right.get_attribute.return_value="false"
        driver,picker=self.setup_driver(
            "Open mode picker, currently Flash-Lite",items=[wrong,right])
        picker.get_attribute.side_effect=[
            "Open mode picker, currently Flash-Lite",
            "Open mode picker, currently Flash High",
        ]
        chrome.return_value=driver
        observed=ensure_mode(mode="flash",timeout=2)
        self.assertEqual(observed,"Open mode picker, currently Flash High")
        wrong.click.assert_not_called()
        right.click.assert_called_once()

    @patch.object(selenium_webdriver, "Chrome")
    def test_only_flash_lite_available_fails_without_wrong_selection(self,chrome):
        wrong=MagicMock()
        wrong.text="Flash-Lite\nQuick"
        wrong.is_displayed.return_value=True
        driver,_=self.setup_driver(
            "Open mode picker, currently Flash-Lite",items=[wrong])
        chrome.return_value=driver
        with self.assertRaises(GeminiModelError):
            ensure_mode(mode="flash",timeout=0.05)
        wrong.click.assert_not_called()
        driver.quit.assert_called_once()

    @patch.object(selenium_webdriver, "Chrome")
    def test_explicit_pro_compatibility(self, chrome):
        driver, picker = self.setup_driver("Open mode picker, currently Gemini Pro")
        chrome.return_value = driver
        self.assertIn("Pro", ensure_pro())
        picker.click.assert_not_called()
        driver.quit.assert_called_once()

    @patch.object(selenium_webdriver, "Chrome")
    def test_missing_target_fails_closed(self, chrome):
        driver, _picker = self.setup_driver(
            "Open mode picker, currently Gemini Pro", items=[]
        )
        chrome.return_value = driver
        with self.assertRaises(GeminiModelError):
            ensure_mode(mode="flash", timeout=0.05)
        driver.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
