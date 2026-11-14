"""One owned Gemini tab: adaptive Thinking level selection and verification.

A model-family picker and the nested Thinking level selector have different
semantics. Never confuse Medium with a model name, guess from menu order,
or submit a model request when the requested thinking level is unverified.

Only pre-Send model-menu interactions are allowed. No navigation, text input,
response copying, uploads, model Send, retries of model submissions, API calls.
"""
from __future__ import annotations

import os
import re
import time

LEVELS = frozenset(("low", "medium", "high"))

# In-process, owned-tab-only, very short-lived proof. The *first* proof
# always comes from the actual checked Thinking radio, not picker wording.
# A later pre-Send check may avoid reopening an overlay only while the
# same tab, same selected picker label and verified level are unchanged.
_VERIFIED_THINKING_BY_TAB = {}
_PROOF_TTL_SECONDS = 60


def _tab_key(driver, handle):
    return (id(driver), getattr(driver, "session_id", None), handle)


def _read_only_reuse_verified_level(driver, handle, level):
    from .gemini_model import _owned_picker
    _owned(driver, handle)
    entry = _VERIFIED_THINKING_BY_TAB.get(_tab_key(driver, handle))
    if not entry:
        return False
    old_level, old_label, observed = entry
    if old_level != level or time.monotonic() - observed > _PROOF_TTL_SECONDS:
        return False
    picker = _owned_picker(driver, handle)
    label = (picker.get_attribute("aria-label") or "").strip()
    # The label is a change detector, not the original proof.
    return bool(old_label and old_label == label and
                re.search("(?i)(?<![A-Za-z])" + re.escape(level) + "(?![A-Za-z])", label))


def _remember_level_verified_by_radio(driver, handle, level):
    from .gemini_model import _owned_picker
    _owned(driver, handle)
    picker = _owned_picker(driver, handle)
    label = (picker.get_attribute("aria-label") or "").strip()
    if label and re.search("(?i)(?<![A-Za-z])" + re.escape(level) + "(?![A-Za-z])", label):
        _VERIFIED_THINKING_BY_TAB[_tab_key(driver, handle)] = (
            level, label, time.monotonic())


class GeminiThinkingError(RuntimeError):
    pass


def configured_thinking_level() -> str:
    """Medium is the Flash lecture default, unless explicitly overridden."""
    level = os.getenv("MICROGEN_GEMINI_THINKING_LEVEL", "medium").strip().casefold()
    if level not in LEVELS:
        raise GeminiThinkingError(
            "MICROGEN_GEMINI_THINKING_LEVEL must be low, medium or high")
    return level


def _level_item(text: str, requested: str) -> bool:
    """Match an option's own leading label, not its changing explanation."""
    if requested not in LEVELS or not isinstance(text, str):
        return False
    lines = [x.strip().casefold() for x in text.splitlines() if x.strip()]
    if not lines or len(lines) > 4:
        return False
    # Gemini currently renders 'Medium / Balanced depth' on separate
    # components, concatenated by Selenium as 'Medium Balanced depth'.
    # Future explanatory text may change; the first label must remain exact.
    head = re.split(r"\s+|[:\u2014\-]", lines[0], maxsplit=1)[0]
    return head == requested


def _owned(driver, handle: str) -> None:
    if (not handle or driver.current_window_handle != handle
            or not str(driver.current_url).startswith(
                "https://gemini.google.com/")):
        raise GeminiThinkingError(
            "PRE_SEND_THINKING_FOREIGN_OR_UNVERIFIED_OWNED_TAB")


def _visible_unique(driver, selectors: tuple[str, ...], predicate):
    from selenium.webdriver.common.by import By
    found = {}
    for selector in selectors:
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            if not element.is_displayed() or not predicate(element):
                continue
            # The *same* WebElement may occur under multiple selectors.
            key = element.id
            found[key] = element
    return list(found.values())


def _thinking_expander(driver):
    # Canonical snapshot first: if the reasoning submenu changes tag names,
    # visible accessible labels can still identify its unique control.
    from .gemini_ui_semantic_controls import snapshot_options
    atomic=snapshot_options(driver)
    if atomic is not None:
        valid={
            "thinking level","thinking effort","thinking depth",
            "reasoning level","reasoning effort","reasoning depth",
            "effort level","thinking budget","inference effort",
        }
        found={}
        for option in atomic:
            name=option.label.splitlines()[0].strip().casefold()
            if name in valid and not option.disabled:
                el=option.element
                found[getattr(el,"id",None) or id(el)]=el
        if len(found)==1:
            return next(iter(found.values()))
        if len(found)>1:
            raise GeminiThinkingError(
                "PRE_SEND_AMBIGUOUS_THINKING_EXPANDER_NO_SEND")
        # Some accessible buttons expose no menu item role; try the
        # legacy semantic route only when no atomic candidate is present.
    selectors = (
        '[role="menuitem"]', '[role="menuitemradio"]',
        'gem-menu-item', '[role="button"]',
        '[aria-expanded]', 'button',
    )
    def is_thinking(element):
        text = (element.text or "").strip().casefold()
        aria = (element.get_attribute("aria-label") or "").strip().casefold()
        test = (element.get_attribute("data-test-id") or "").casefold()
        labels = (
            "thinking level", "thinking effort", "thinking depth",
            "reasoning level", "reasoning effort", "reasoning depth",
        )
        return (text in labels or aria in labels
                or (("thinking" in test or "reasoning" in test)
                    and ("level" in test or "effort" in test)))
    matches = _visible_unique(driver, selectors, is_thinking)
    if len(matches) != 1:
        raise GeminiThinkingError(
            "PRE_SEND_THINKING_EXPANDER_NOT_UNIQUE_OR_MISSING")
    return matches[0]


def _thinking_options(driver, requested):
    # A single atomic, read-only DOM snapshot avoids element-ID drift while
    # Gemini hydrates a nested Thinking menu (including open Shadow DOM).
    # Only an individual visible option whose own text names the requested
    # level qualifies; parent menu descriptions do not count.
    from .gemini_ui_semantic_controls import snapshot_options
    snapshot=snapshot_options(driver)
    if snapshot is not None:
        found={}
        for choice in snapshot:
            if _level_item(choice.label,requested):
                item=choice.element
                found[getattr(item,"id",None) or id(item)]=item
        return list(found.values())
    # Role/host variants remain supported for older Selenium/test drivers.
    selectors = (
        '[role="menuitemradio"]', '[role="radio"]', '[role="option"]',
        '[role="menuitemcheckbox"]', '[role="menuitem"]',
        'gem-menu-item[role="menuitemradio"]', 'gem-menu-item[role="radio"]',
        '[data-test-id*="thinking"]', '[aria-checked]', '[aria-selected]',
    )
    def match(element):
        return _level_item(
            (element.text or "") or
            (element.get_attribute("aria-label") or ""), requested)
    return _visible_unique(driver, selectors, match)


def _checked(item) -> bool:
    """Only explicit ARIA selection state counts for release evidence."""
    return (
        (item.get_attribute("aria-checked") or "").casefold() == "true"
        or (item.get_attribute("aria-selected") or "").casefold() == "true"
    )


def _expand_for_thinking(driver, handle):
    from .gemini_model import _owned_picker
    _owned(driver, handle)
    picker = _owned_picker(driver, handle)
    if (picker.get_attribute("aria-expanded") or "").casefold() != "true":
        picker.click()
    parent = _thinking_expander(driver)
    if (parent.get_attribute("aria-expanded") or "").casefold() != "true":
        parent.click()
    _owned(driver, handle)
    return picker


def _close_picker(driver, handle, picker) -> None:
    _owned(driver, handle)
    try:
        if (picker.get_attribute("aria-expanded") or "").casefold() == "true":
            picker.click()
    except Exception:
        # A detached picker can be replaced by Angular after a selection.
        # Never click a different control or submit a prompt as a workaround.
        pass


def assert_owned_gemini_thinking_level(driver, handle: str,
                                       level: str = "medium") -> str:
    """Verify the selected radio without changing the selected level.

    May open/close only the model and Thinking menus. No provider call.
    """
    if level not in LEVELS:
        raise GeminiThinkingError("Unsupported thinking level")
    # After the same owned tab's radio has been genuinely verified once,
    # reopening its menu after multiple uploads can hit a hidden Angular
    # overlay. Only reuse a short-lived radio proof when the same owned
    # picker retains its exact visible model + thinking label. This never
    # infers the thinking level solely from the picker wording.
    if _read_only_reuse_verified_level(driver, handle, level):
        return level
    picker = None
    try:
        picker = _expand_for_thinking(driver, handle)
        options = _thinking_options(driver, level)
        if len(options) != 1 or not _checked(options[0]):
            raise GeminiThinkingError(
                "PRE_SEND_THINKING_LEVEL_NOT_VERIFIED_NO_SEND")
        _remember_level_verified_by_radio(driver, handle, level)
        return level
    finally:
        if picker is not None:
            _close_picker(driver, handle, picker)


def select_owned_gemini_thinking_level(driver, handle: str, *,
                                       level: str = "medium",
                                       timeout: float = 15) -> str:
    """Change only the owned Thinking radio in a bounded pre-Send phase."""
    if level not in LEVELS or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 30:
        raise GeminiThinkingError("Invalid thinking selector parameters")
    deadline = time.monotonic() + timeout
    picker = None
    try:
        while time.monotonic() < deadline:
            try:
                picker = _expand_for_thinking(driver, handle)
            except GeminiThinkingError as exc:
                # An Angular menu may hydrate a moment after its picker.
                # Retry only this pre-Send UI discovery, never a model Send,
                # never a wrong tab or ambiguous named option.
                if "EXPANDER_NOT_UNIQUE_OR_MISSING" not in str(exc):
                    raise
                time.sleep(.25)
                continue
            choices = _thinking_options(driver, level)
            if len(choices) > 1:
                raise GeminiThinkingError("PRE_SEND_AMBIGUOUS_THINKING_LEVEL_MENU")
            if len(choices) == 1:
                if _checked(choices[0]):
                    # Already-selected radio is equally strong evidence.
                    # Preserve it for a later no-click pre-Send check.
                    _remember_level_verified_by_radio(driver, handle, level)
                    return level
                if (choices[0].get_attribute("aria-disabled") or "").casefold() == "true":
                    raise GeminiThinkingError(
                        "PRE_SEND_REQUESTED_THINKING_LEVEL_DISABLED_NO_SEND")
                choices[0].click()
                picker = None  # UI often re-renders after radio selection.
                remaining = max(.5, deadline - time.monotonic())
                while time.monotonic() < deadline:
                    try:
                        return assert_owned_gemini_thinking_level(
                            driver, handle, level)
                    except GeminiThinkingError as exc:
                        if "FOREIGN" in str(exc):
                            raise
                    time.sleep(min(0.2, remaining))
                raise GeminiThinkingError(
                    "PRE_SEND_THINKING_SELECTION_NOT_CONFIRMED_NO_SEND")
            _close_picker(driver, handle, picker)
            picker = None
            time.sleep(.25)
        raise GeminiThinkingError(
            "PRE_SEND_REQUESTED_THINKING_LEVEL_UNAVAILABLE_NO_SEND")
    finally:
        if picker is not None:
            _close_picker(driver, handle, picker)


def visible_offered_thinking_levels(driver) -> list[str]:
    """Enumerate ONLY explicit visible selectable radio/option labels."""
    from selenium.webdriver.common.by import By
    from .gemini_ui_semantic_controls import snapshot_options
    found=set()
    atomic=snapshot_options(driver)
    if atomic is not None:
        rows=[(x.label,x.disabled) for x in atomic]
    else:
        selectors=(
            '[role="menuitemradio"]','[role="radio"]',
            '[role="option"]','[role="menuitemcheckbox"]',
            '[aria-checked]','[aria-selected]',
            'gem-menu-item[role="menuitemradio"]',
        )
        seen=set()
        rows=[]
        for selector in selectors:
            try:
                matches=driver.find_elements(By.CSS_SELECTOR,selector)
            except Exception:
                continue
            for element in matches:
                try:
                    key=getattr(element,"id",None) or id(element)
                    if key in seen or not element.is_displayed():
                        continue
                    seen.add(key)
                    rows.append((
                        (element.text or "") or
                        (element.get_attribute("aria-label") or ""),
                        (element.get_attribute("aria-disabled") or "").lower()=="true"))
                except Exception:
                    continue
    for label,disabled in rows:
        if not disabled:
            for level in LEVELS:
                if _level_item(label,level):
                    found.add(level)
    return sorted(found)


def select_owned_gemini_thinking_with_recovery(
        driver, handle: str, *, level: str = "medium",
        stage: str | None = None, timeout: float = 15,
        allow_fallback: bool = True) -> str:
    """Non-downgrading pre-Send effort adaptation on the SAME owned tab.

    Only an observed, selectable, named option may replace an absent level.
    'Balanced', 'Auto', etc. are not assumed equivalent to 'Medium'.
    """
    from .gemini_ui_adaptive_protocol import (
        choose_thinking, GeminiAdaptivePolicyError)
    try:
        return select_owned_gemini_thinking_level(
            driver,handle,level=level,timeout=timeout)
    except GeminiThinkingError as error:
        if not allow_fallback or str(error) not in (
                "PRE_SEND_REQUESTED_THINKING_LEVEL_UNAVAILABLE_NO_SEND",
                "PRE_SEND_REQUESTED_THINKING_LEVEL_DISABLED_NO_SEND"):
            raise
        active=(stage or
                os.getenv("MICROGEN_ACTIVE_GENERATION_STAGE","") or
                os.getenv("MICROGEN_GEMINI_INTERACTION_STAGE","")
                ).strip().casefold()
        picker=None
        try:
            picker=_expand_for_thinking(driver,handle)
            offered=visible_offered_thinking_levels(driver)
            if not offered or level in offered:
                raise GeminiThinkingError(
                    "PRE_SEND_THINKING_FALLBACK_WITHOUT_POSITIVE_ABSENCE")
            try:
                chosen=choose_thinking(
                    requested=level,offered=offered,stage=active)
            except GeminiAdaptivePolicyError as exc:
                raise GeminiThinkingError(str(exc)) from error
        finally:
            if picker is not None:
                _close_picker(driver,handle,picker)
        chosen=select_owned_gemini_thinking_level(
            driver,handle,level=chosen,timeout=timeout)
        os.environ["MICROGEN_GEMINI_THINKING_LEVEL"]=chosen
        os.environ["MICROGEN_THINKING_ROUTE_REASON"]=(
            "REQUESTED_LEVEL_UNAVAILABLE_VERIFIED_NON_DOWNGRADING")
        os.environ["MICROGEN_THINKING_ROUTE_REQUESTED"]=level
        os.environ["MICROGEN_THINKING_ROUTE_OFFERED"]=",".join(sorted(offered))
        return chosen
