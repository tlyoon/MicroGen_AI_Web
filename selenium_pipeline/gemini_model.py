"""Fail-closed Gemini web mode selection for the Selenium debug session."""
from __future__ import annotations

import time


class GeminiModelError(RuntimeError):
    pass


def ensure_pro(port: int = 9222, timeout: float = 15) -> str:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    driver = webdriver.Chrome(options=options)
    try:
        deadline = time.monotonic() + timeout
        picker = None
        while time.monotonic() < deadline:
            found = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label^="Open mode picker"]')
            if found and found[0].is_displayed():
                picker = found[0]
                break
            time.sleep(0.4)
        if picker is None:
            raise GeminiModelError("Gemini mode picker unavailable; check authentication and active Gemini tab.")
        current = picker.get_attribute("aria-label") or ""
        if "currently Pro" in current:
            return current
        picker.click()
        target = None
        while time.monotonic() < deadline:
            for item in driver.find_elements(By.CSS_SELECTOR, 'gem-menu-item[role="menuitem"]'):
                if "3.1 Pro" in item.text and item.is_displayed():
                    target = item
                    break
            if target is not None:
                break
            time.sleep(0.25)
        if target is None or target.get_attribute("aria-disabled") == "true":
            raise GeminiModelError("Gemini 3.1 Pro is unavailable or disabled in this account.")
        target.click()
        while time.monotonic() < deadline:
            found = driver.find_elements(By.CSS_SELECTOR, 'button[aria-label^="Open mode picker"]')
            if found:
                current = found[0].get_attribute("aria-label") or ""
                if "currently Pro" in current:
                    return current
            time.sleep(0.4)
        raise GeminiModelError(f"Model selection not confirmed; UI reports {current!r}")
    finally:
        driver.quit()
