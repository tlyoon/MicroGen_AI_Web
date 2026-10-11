from __future__ import annotations

import os
import time


class GeminiModelError(RuntimeError):
    pass


MODEL_SPECS = {
    "flash": {
        "menu_prefix": "Flash",
        "label_token": "flash",
    },
    "pro": {
        "menu_prefix": "3.1 Pro",
        "label_token": "pro",
    },
}


def configured_ui_mode() -> str:
    """Return the explicitly requested browser model, otherwise Flash."""
    explicit = os.getenv("MICROGEN_GEMINI_UI_MODE", "").strip().lower()
    if explicit:
        if explicit not in MODEL_SPECS:
            raise GeminiModelError(
                "MICROGEN_GEMINI_UI_MODE must be 'flash' or 'pro'."
            )
        return explicit

    # Flash is the package-wide default. MICROGEN_MODEL_PHASE is retained for
    # diagnostics/compatibility but no longer changes the model implicitly.
    return "flash"


def _matches_mode(label: str, mode: str) -> bool:
    label_l = (label or "").lower()
    return "currently" in label_l and MODEL_SPECS[mode]["label_token"] in label_l


def ensure_mode(port: int = 9222, mode: str | None = None, timeout: float = 15) -> str:
    """Select and confirm the requested authenticated Gemini browser mode."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    target_mode = (mode or configured_ui_mode()).strip().lower()
    if target_mode not in MODEL_SPECS:
        raise GeminiModelError(f"Unsupported Gemini UI mode: {target_mode!r}")

    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    driver = webdriver.Chrome(options=options)
    try:
        deadline = time.monotonic() + timeout
        picker = None
        gemini_tab_seen = False

        # Find an authenticated Gemini tab by the real mode picker rather than
        # assuming the current Chrome tab is the controlled one.
        while time.monotonic() < deadline and picker is None:
            for handle in list(driver.window_handles):
                try:
                    driver.switch_to.window(handle)
                    if not driver.current_url.startswith("https://gemini.google.com/"):
                        continue
                    gemini_tab_seen = True
                    found = driver.find_elements(
                        By.CSS_SELECTOR, 'button[aria-label^="Open mode picker"]'
                    )
                    for item in found:
                        if item.is_displayed():
                            picker = item
                            break
                    if picker is not None:
                        break
                except Exception:
                    continue
            if picker is None:
                time.sleep(0.25)

        if picker is None and gemini_tab_seen and target_mode == "flash":
            # October 2026 regression: a retained old Gemini draft can leave a
            # page showing an editor but *no* mode picker. Opening a fresh tab
            # restored authenticated Flash without touching that draft.
            # Make one safe attempt, never clear/type into the old conversation.
            old_handle = driver.current_window_handle
            opened_tab = False
            try:
                driver.switch_to.new_window("tab")
                opened_tab = True
                driver.get("https://gemini.google.com/app")
                retry_until = time.monotonic() + min(max(timeout, 1), 12)
                while time.monotonic() < retry_until:
                    for item in driver.find_elements(
                        By.CSS_SELECTOR, 'button[aria-label^="Open mode picker"]'
                    ):
                        if item.is_displayed():
                            picker = item
                            break
                    if picker is not None:
                        break
                    time.sleep(0.25)
            except Exception:
                # An unavailable browser/login must remain a safe failure.
                pass
            finally:
                if picker is None and opened_tab:
                    try:
                        driver.close()
                        driver.switch_to.window(old_handle)
                    except Exception:
                        pass

        if picker is None:
            raise GeminiModelError(
                "Gemini mode picker unavailable, including safe fresh-tab "
                "recovery; check authentication before resuming."
            )

        current = picker.get_attribute("aria-label") or ""
        if _matches_mode(current, target_mode):
            return current

        try:
            picker.click()
        except Exception:
            driver.execute_script("arguments[0].click();", picker)

        target = None
        prefix = MODEL_SPECS[target_mode]["menu_prefix"]
        while time.monotonic() < deadline:
            items = []
            for selector in (
                '[role="menuitem"]',
                'gem-menu-item[role="menuitem"]',
            ):
                try:
                    items.extend(driver.find_elements(By.CSS_SELECTOR, selector))
                except Exception:
                    pass
            for item in items:
                try:
                    if item.is_displayed() and ((target_mode == "flash" and "flash" in (item.text or "").lower() and "pro" not in (item.text or "").lower()) or (target_mode != "flash" and (item.text or "").strip().startswith(prefix))):
                        target = item
                        break
                except Exception:
                    continue
            if target is not None:
                break
            time.sleep(0.20)

        if target is None or target.get_attribute("aria-disabled") == "true":
            raise GeminiModelError(
                f"Gemini {prefix} is unavailable or disabled in this account."
            )

        try:
            target.click()
        except Exception:
            driver.execute_script("arguments[0].click();", target)

        while time.monotonic() < deadline:
            try:
                found = driver.find_elements(
                    By.CSS_SELECTOR, 'button[aria-label^="Open mode picker"]'
                )
                for item in found:
                    if not item.is_displayed():
                        continue
                    current = item.get_attribute("aria-label") or ""
                    if _matches_mode(current, target_mode):
                        return current
            except Exception:
                pass
            time.sleep(0.25)

        raise GeminiModelError(
            f"Model selection not confirmed for {target_mode}; UI reports {current!r}"
        )
    finally:
        driver.quit()


def ensure_flash(port: int = 9222, timeout: float = 15) -> str:
    return ensure_mode(port=port, mode="flash", timeout=timeout)


def ensure_pro(port: int = 9222, timeout: float = 15) -> str:
    # Explicit compatibility/benchmark helper. Normal pipeline execution
    # defaults to Flash and never selects Pro merely because the phase is production.
    return ensure_mode(port=port, mode="pro", timeout=timeout)
