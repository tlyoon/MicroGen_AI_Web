from __future__ import annotations

import os
import re
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
    """Match *only* a currently selected UI family, not a token substring.

    In particular, Flash Lite and hybrid "Flash / Pro" selectors must never
    masquerade as the chosen Flash text-generation family.
    """
    if mode not in MODEL_SPECS or not isinstance(label, str):
        return False
    actual = re.search(r"\bcurrently\b\s+(.+)$", label, flags=re.I)
    if not actual:
        return False
    selected = actual.group(1).casefold()
    if mode == "flash":
        return (bool(re.search(r"\bflash\b", selected))
                and not re.search(r"\b(?:lite|pro)\b", selected))
    return (bool(re.search(r"\bpro\b", selected))
            and not re.search(r"\b(?:flash|lite)\b", selected))


def _eligible_mode_menu_text(text: str, mode: str) -> bool:
    """Choose the intended Flash family, never Flash-Lite or mixed menus."""
    if not isinstance(text,str) or mode not in MODEL_SPECS:
        return False
    # Nov 2026 Gemini uses a two-line model option:
    #   "All-around help" / "3.8 Flash"
    # in <gem-menu-item role="menuitemradio">, not a role=menuitem whose
    # first line is "Flash". Test *each exact sublabel*, never the whole
    # menu container (which lists Flash-Lite, Flash and Pro together).
    lines = [line.strip().casefold() for line in text.splitlines()
             if line.strip()]
    if not 1 <= len(lines) <= 4:
        return False
    if mode == "flash":
        pattern = r"(?:\d+(?:\.\d+)?\s+)?flash(?:\s+(?:high|fast))?"
    else:
        pattern = r"(?:\d+(?:\.\d+)?\s+)?pro"
    return any(re.fullmatch(pattern, line, flags=re.I) is not None
               for line in lines)


def assert_owned_gemini_mode(driver, owned_handle: str | None,
                             mode: str = "flash") -> str:
    """Read-only, source-worker-owned model-family check before any Send.

    Never accept "Flash-Lite" as Flash; never borrow a different tab's
    correctly selected model. A mismatch is a *pre-Send* failure, not a
    service outage or permission for another provider request.
    """
    from selenium.webdriver.common.by import By

    if (mode not in MODEL_SPECS or not owned_handle
            or driver.current_window_handle != owned_handle
            or not str(driver.current_url).startswith("https://gemini.google.com/")):
        raise GeminiModelError("PRE_SEND_OWNED_GEMINI_TAB_OR_MODEL_UNVERIFIED")
    pickers = [
        item for item in driver.find_elements(
            By.CSS_SELECTOR, 'button[aria-label^="Open mode picker"]'
        ) if item.is_displayed()
    ]
    if len(pickers) != 1:
        raise GeminiModelError("PRE_SEND_MODE_PICKER_NOT_UNIQUE_OR_MISSING")
    selected = pickers[0].get_attribute("aria-label") or ""
    if not _matches_mode(selected, mode):
        raise GeminiModelError(
            "PRE_SEND_GEMINI_MODEL_FAMILY_MISMATCH_NO_SEND: " + selected)
    return selected


def select_owned_gemini_mode(driver, owned_handle: str | None, *,
                             mode: str = "flash", timeout: float = 15) -> str:
    """Select exactly the requested UI family *inside the owned tab*.

    Limited to pre-submission model-picker interaction. Does not navigate,
    create tabs, type prompts, or click Send. Flash-Lite/Pro never qualify.
    """
    from selenium.webdriver.common.by import By

    if (mode not in MODEL_SPECS or not owned_handle
            or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 30):
        raise GeminiModelError("Invalid owned-tab model selection parameters")

    def owned_picker():
        if (driver.current_window_handle != owned_handle
                or not str(driver.current_url).startswith(
                    "https://gemini.google.com/")):
            raise GeminiModelError("PRE_SEND_OWNED_GEMINI_TAB_CHANGED")
        found = [
            item for item in driver.find_elements(
                By.CSS_SELECTOR, 'button[aria-label^="Open mode picker"]'
            ) if item.is_displayed()
        ]
        if len(found) != 1:
            raise GeminiModelError("PRE_SEND_MODE_PICKER_NOT_UNIQUE_OR_MISSING")
        return found[0]

    picker = owned_picker()
    current = picker.get_attribute("aria-label") or ""
    if _matches_mode(current, mode):
        return assert_owned_gemini_mode(driver, owned_handle, mode)
    try:
        picker.click()
    except Exception:
        driver.execute_script("arguments[0].click();", picker)
    deadline = time.monotonic() + timeout
    target = None
    while time.monotonic() < deadline:
        # The tab must remain ours throughout menu interaction.
        if driver.current_window_handle != owned_handle:
            raise GeminiModelError("PRE_SEND_OWNED_GEMINI_TAB_CHANGED")
        unique = {}
        for selector in ('[role="menuitemradio"]',
                         'gem-menu-item[role="menuitemradio"]',
                         '[role="menuitem"]',
                         'gem-menu-item[role="menuitem"]'):
            for item in driver.find_elements(By.CSS_SELECTOR, selector):
                if item.is_displayed() and _eligible_mode_menu_text(
                        item.text or "", mode):
                    unique[item.id] = item
        if len(unique) > 1:
            raise GeminiModelError("PRE_SEND_AMBIGUOUS_GEMINI_MODEL_MENU")
        if unique:
            target = next(iter(unique.values()))
            break
        time.sleep(0.2)
    if target is None or target.get_attribute("aria-disabled") == "true":
        raise GeminiModelError(
            "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND")
    try:
        target.click()
    except Exception:
        driver.execute_script("arguments[0].click();", target)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return assert_owned_gemini_mode(driver, owned_handle, mode)
        except GeminiModelError:
            # A changed/foreign tab must NEVER be waited out or borrowed.
            if driver.current_window_handle != owned_handle:
                raise
            time.sleep(0.2)
    raise GeminiModelError("PRE_SEND_GEMINI_MODEL_FAMILY_NOT_CONFIRMED_NO_SEND")


def browser_model_evidence(label: str, *, requested_mode: str,
                           requested_model_id: str) -> dict:
    """Honest UI-only provenance. No API/provider version claim.

    The authenticated UI mode picker can substantiate the selected *family*.
    It cannot independently substantiate the actual server model identifier
    or deployment/version. That needs separate provider-sourced evidence.
    """
    if not isinstance(requested_model_id, str) or not requested_model_id.strip():
        raise GeminiModelError("Missing explicitly requested model ID")
    named=requested_model_id.strip().casefold()
    if (requested_mode not in MODEL_SPECS
            or not re.search(r"\b"+requested_mode+r"\b", named)
            or (requested_mode == "flash" and re.search(r"\blite\b", named))):
        raise GeminiModelError("Requested API model ID contradicts selected UI family")
    if not _matches_mode(label, requested_mode):
        raise GeminiModelError("Current Gemini UI family does not match requested mode")
    return {
        "schema_version": 1,
        "requested_model_id": requested_model_id,
        "requested_ui_mode": requested_mode,
        "observed_ui_picker_label": label,
        "selected_family_verified": True,
        "exact_model_id_verified": False,
        "observed_provider_model_id": None,
        "verification_scope": "browser_ui_family_only",
        "student_or_academic_approval": False,
    }


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

        # The parent preflight and copied vendor workers must use the
        # exact SAME owned-tab selector and current Gemini menu structure.
        # A parent Flash label is not proof of the model in a later owned tab.
        return select_owned_gemini_mode(
            driver, driver.current_window_handle, mode=target_mode,
            timeout=max(1.0, min(float(timeout), 30.0)))
    finally:
        driver.quit()


def ensure_flash(port: int = 9222, timeout: float = 15) -> str:
    return ensure_mode(port=port, mode="flash", timeout=timeout)


def ensure_pro(port: int = 9222, timeout: float = 15) -> str:
    # Explicit compatibility/benchmark helper. Normal pipeline execution
    # defaults to Flash and never selects Pro merely because the phase is production.
    return ensure_mode(port=port, mode="pro", timeout=timeout)
