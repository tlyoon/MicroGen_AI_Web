import unittest
from unittest.mock import MagicMock, patch

from selenium_pipeline.gemini_model import GeminiModelError, ensure_pro


class ModelSelectorTests(unittest.TestCase):
    def setup_driver(self, label="Open mode picker, currently Flash Extended", items=None):
        driver = MagicMock()
        picker = MagicMock()
        picker.is_displayed.return_value = True
        picker.get_attribute.return_value = label
        driver.find_elements.side_effect = lambda by, selector: (
            [picker] if "Open mode picker" in selector else (items or [])
        )
        return driver, picker

    @patch("selenium.webdriver.Chrome")
    def test_already_pro(self, chrome):
        driver, picker = self.setup_driver("Open mode picker, currently Pro Extended")
        chrome.return_value = driver
        self.assertIn("Pro", ensure_pro())
        picker.click.assert_not_called()
        driver.quit.assert_called_once()

    @patch("selenium.webdriver.Chrome")
    def test_selects_pro_menu_item(self, chrome):
        item = MagicMock()
        item.text = "3.1 Pro\nAdvanced reasoning"
        item.is_displayed.return_value = True
        item.get_attribute.return_value = "false"
        driver, picker = self.setup_driver(items=[item])
        picker.get_attribute.side_effect = [
            "Open mode picker, currently Flash Extended",
            "Open mode picker, currently Pro Extended",
        ]
        chrome.return_value = driver
        self.assertIn("Pro", ensure_pro())
        item.click.assert_called_once()
        driver.quit.assert_called_once()

    @patch("selenium.webdriver.Chrome")
    def test_missing_pro_fails_closed(self, chrome):
        driver, picker = self.setup_driver(items=[])
        chrome.return_value = driver
        with patch("selenium_pipeline.gemini_model.time.monotonic", side_effect=[0, 100]):
            with self.assertRaises(GeminiModelError):
                ensure_pro(timeout=1)
        driver.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
