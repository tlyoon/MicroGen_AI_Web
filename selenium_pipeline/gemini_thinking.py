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
_OVERLAY_SIGNATURE="THINKING_EXPANDER_MISSING_AFTER_OWNED_PICKER_OPEN_NO_SEND"
_OVERLAY_MECHANISM="CLOSE_OWNED_PICKER_AND_RETRY_FINITE_PRESEND_DISCOVERY_NO_SEND"


def _owned_overlay_recovery_registered()->bool:
    try:
        from .recovery_registry import lookup_mechanism
        return (lookup_mechanism("presend_capability_repair",
                 _OVERLAY_SIGNATURE)==_OVERLAY_MECHANISM)
    except (ValueError,OSError):
        return False

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
    """Choose per-task effort, never below the verified task minimum.

    Each worker's active generation task determines the default. A caller
    may explicitly request stronger effort, but not secretly weaken a
    source-bound independent scientific challenge to Low/Medium.
    Unknown stages retain the previous Medium compatibility default.
    """
    explicit = os.getenv("MICROGEN_GEMINI_THINKING_LEVEL", "").strip().casefold()
    if explicit and explicit not in LEVELS:
        raise GeminiThinkingError(
            "MICROGEN_GEMINI_THINKING_LEVEL must be low, medium or high")
    stage = os.getenv("MICROGEN_ACTIVE_GENERATION_STAGE", "").strip().casefold()
    from .gemini_dynamic_task_router import STAGES,task_policy
    if stage not in STAGES:
        return explicit or "medium"
    policy = task_policy(stage)
    level = explicit or policy["preferred_thinking"]
    if (level not in LEVELS or
            ("minimum_thinking" in policy and
             ("low","medium","high").index(level) <
             ("low","medium","high").index(policy["minimum_thinking"]))):
        raise GeminiThinkingError(
            "PRE_SEND_TASK_THINKING_BELOW_REGISTERED_MINIMUM_NO_SEND")
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


def _await_owned_nested_thinking_options(driver, handle, level, *, deadline):
    """Recover late submenu hydration without a new picker click or Send.

    The model menu and Thinking expander are already positively identified
    on this exact owned Gemini tab. Re-read only the SAME nested options for
    at most 0.8s, under the existing caller deadline. An unregistered or
    ambiguous UI must remain blocked.
    """
    from .recovery_registry import lookup_mechanism
    if lookup_mechanism(
        "presend_capability_repair",
        "OWNED_THINKING_SUBMENU_OPTIONS_HYDRATE_AFTER_EXPANDER_NO_SEND",
    ) != "BOUNDED_SAME_OWNED_THINKING_SUBMENU_RECHECK_NO_SEND":
        raise GeminiThinkingError(
            "PRE_SEND_NESTED_THINKING_HYDRATION_RECOVERY_NOT_REGISTERED_NO_SEND")
    for attempt in range(5):
        _owned(driver, handle)
        options = _thinking_options(driver, level)
        if len(options) > 1:
            raise GeminiThinkingError(
                "PRE_SEND_AMBIGUOUS_THINKING_LEVEL_MENU")
        if options:
            return options
        remaining = min(0.2, deadline-time.monotonic())
        if attempt == 4 or remaining <= 0:
            break
        time.sleep(remaining)
    return []


def _checked(item) -> bool:
    """Only explicit ARIA selection state counts for release evidence."""
    return (
        (item.get_attribute("aria-checked") or "").casefold() == "true"
        or (item.get_attribute("aria-selected") or "").casefold() == "true"
    )


def _registered_owned_picker_click_fallback()->bool:
    """Only a code-reviewed alternate click on the SAME exact owned picker."""
    try:
        from .recovery_registry import lookup_mechanism
        return lookup_mechanism(
            "presend_capability_repair",
            "OWNED_PRO_MODEL_PICKER_NATIVE_CLICK_NO_EFFECT_NO_SEND")==(
            "EXACT_SAME_OWNED_MODEL_PICKER_SINGLE_JS_CLICK_THEN_VERIFY_NO_SEND")
    except (ValueError,OSError):
        return False


def _open_owned_mode_picker_with_verified_fallback(driver,handle,picker,*,
                                                   allow_model_switch=False):
    """One native click; if *proven inert*, one exact-button DOM click.

    The fallback is allowed only when no model options were rendered after
    the native click and the exact picker label matches the configured model.
    It never discovers or clicks a Send control or changes a model selection.
    """
    from .gemini_model import _matches_mode,configured_ui_mode,MODEL_SPECS
    from .gemini_ui_adaptive_protocol import normalized_family
    from .gemini_ui_semantic_controls import snapshot_options

    def expanded():
        _owned(driver,handle)
        return (picker.get_attribute("aria-expanded") or "").lower()=="true"

    if expanded():
        return
    picker.click()
    deadline=time.monotonic()+0.5
    while time.monotonic()<deadline:
        if expanded():
            return
        time.sleep(0.05)
    if expanded():
        return
    # An accessible menu may be present even when its outer aria-expanded is
    # stale. Do not toggle it closed with a duplicate click in that case.
    visible=snapshot_options(driver)
    if visible:
        return
    # Older Gemini/Chrome drivers may not expose an aria-expanded
    # attribute, and some offline drivers do not implement atomic JS
    # snapshots. A positively visible, individually selectable model menu
    # is stronger evidence than absent aria state. Do not mislabel an
    # already-open menu as an inert click or attempt a second click.
    from .gemini_model import _visible_model_options
    if _visible_model_options(driver):
        return
    label=(picker.get_attribute("aria-label") or "")
    current=label.partition("currently ")[2]
    exact=(normalized_family(current) in MODEL_SPECS if allow_model_switch
           else _matches_mode(label,configured_ui_mode()))
    if ((picker.get_attribute("aria-expanded") or "").lower()!="false"
            or not exact
            or not _registered_owned_picker_click_fallback()):
        raise GeminiThinkingError(
            "PRE_SEND_MODE_PICKER_NATIVE_CLICK_INERT_UNVERIFIED_NO_SEND")
    _owned(driver,handle)
    try:
        used=driver.execute_script(r"""
            const e=arguments[0];
            if(!e||e.tagName.toLowerCase()!=='button')return false;
            const a=e.getAttribute('aria-label')||'';
            if(!/^Open mode picker, currently (?:Flash|Pro|\d+(?:\.\d+)?\s+(?:Hydrogen|Argon|Carbon|Neon))/i.test(a))
                return false;
            const rect=e.getBoundingClientRect();
            if(rect.width<=0||rect.height<=0||e.disabled)return false;
            e.click(); return true;
        """,picker)
    except Exception as exc:
        raise GeminiThinkingError(
            "PRE_SEND_MODE_PICKER_JS_FALLBACK_NOT_VERIFIED_NO_SEND") from exc
    # A click alone is never proof: the menu must actually open.
    if used is not True:
        raise GeminiThinkingError(
            "PRE_SEND_MODE_PICKER_JS_FALLBACK_NOT_VERIFIED_NO_SEND")
    deadline=time.monotonic()+0.7
    while time.monotonic()<deadline:
        if expanded():
            return
        time.sleep(0.05)
    visible=snapshot_options(driver)
    if not visible:
        raise GeminiThinkingError(
            "PRE_SEND_MODE_PICKER_STILL_CLOSED_NO_SEND")


def _expand_for_thinking(driver, handle):
    from .gemini_model import _owned_picker
    _owned(driver, handle)
    picker = _owned_picker(driver, handle)
    try:
        _open_owned_mode_picker_with_verified_fallback(driver,handle,picker)
        parent = _thinking_expander(driver)
        if (parent.get_attribute("aria-expanded") or "").casefold() != "true":
            parent.click()
        _owned(driver, handle)
        return picker
    except Exception:
        # If the expander discovery fails after opening the outer picker,
        # the caller never receives 'picker' and cannot close it in finally.
        # This historically left stale overlays open across attempts. It is
        # safe to close only the already identified owned menu, never Send.
        _close_picker(driver, handle, picker)
        raise


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
        if not options:
            options = _await_owned_nested_thinking_options(
                driver, handle, level, deadline=time.monotonic()+0.85)
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
    saw_reachable_expander = False
    saw_other_selectable_levels = False
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
                if not _owned_overlay_recovery_registered():
                    raise GeminiThinkingError(
                        "PRE_SEND_THINKING_OVERLAY_RECOVERY_NOT_REGISTERED_NO_SEND") from exc
                time.sleep(.25)
                continue
            saw_reachable_expander = True
            choices = _thinking_options(driver, level)
            if not choices:
                choices = _await_owned_nested_thinking_options(
                    driver, handle, level,
                    deadline=min(deadline, time.monotonic()+0.85))
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
            # A hidden/empty semantic menu is not proof that the requested
            # level is actually absent. Only another positively witnessed,
            # selectable Thinking radio can establish true unavailability.
            # This distinction was missing in the real Account B failure.
            offered = visible_offered_thinking_levels(driver)
            if offered:
                saw_other_selectable_levels = True
            _close_picker(driver, handle, picker)
            picker = None
            time.sleep(.25)
        if not saw_reachable_expander:
            raise GeminiThinkingError(
                "PRE_SEND_THINKING_EXPANDER_NOT_UNIQUE_OR_MISSING")
        if not saw_other_selectable_levels:
            raise GeminiThinkingError(
                "PRE_SEND_THINKING_OPTIONS_NOT_DISCOVERABLE_NO_SEND")
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
                from .gemini_dynamic_task_router import (
                    STAGES,select_task_thinking,DynamicGeminiRouteError)
                if active in STAGES:
                    from .gemini_model import configured_ui_mode
                    chosen=select_task_thinking(
                        active,offered,mode=configured_ui_mode(),
                        requested=level)
                else:
                    chosen=choose_thinking(
                        requested=level,offered=offered,stage=active)
            except (GeminiAdaptivePolicyError,DynamicGeminiRouteError) as exc:
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
