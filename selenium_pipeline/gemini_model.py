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
    "flash-lite": {
        "menu_prefix": "Flash-Lite",
        "label_token": "flash-lite",
    },
}


def configured_ui_mode() -> str:
    """Return the explicitly requested browser model, otherwise Flash."""
    explicit = os.getenv("MICROGEN_GEMINI_UI_MODE", "").strip().lower()
    if explicit:
        if explicit not in MODEL_SPECS:
            raise GeminiModelError(
                "MICROGEN_GEMINI_UI_MODE must be 'flash-lite', 'flash' or 'pro'."
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
    # A changed label or model version is harmless. Choosing Flash-Lite,
    # Pro, Argon or Carbon under a Flash claim is NOT harmless.
    tokens = re.findall(
        r"(?<!\w)(?:flash[\s-]*lite|flash|pro|argon|carbon)(?!\w)",
        selected, flags=re.I)
    target = mode
    return (len(tokens) == 1 and tokens[0].casefold().replace(' ', '-') == target)


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
    flattened = " ".join(lines)
    # A wrapper that lists multiple modes must never masquerade as one
    # selectable option, even if it happens to include the requested mode.
    tokens = re.findall(
        r"(?<!\w)(?:flash[\s-]*lite|flash|pro|argon|carbon)(?!\w)",
        flattened, flags=re.I)
    if len(tokens) != 1:
        return False
    if tokens[0].casefold().replace(" ", "-") != mode:
        return False
    if mode == "flash":
        pattern = (r"(?:gemini\s+)?(?:\d+(?:\.\d+)?\s+)?"
                   r"flash(?:\s+(?:high|fast))?")
    elif mode == "flash-lite":
        pattern = (r"(?:gemini\s+)?(?:\d+(?:\.\d+)?\s+)?"
                   r"flash[ -]lite")
    else:
        pattern = r"(?:gemini\s+)?(?:\d+(?:\.\d+)?\s+)?pro"
    return any(re.fullmatch(pattern, line, flags=re.I) is not None
               for line in lines)


def _visible_model_options(driver):
    """Atomic accessible model options; separate exact option from wrappers.

    The runtime probe traverses open shadow roots once. Older/offline
    Selenium drivers retain the semantic role+test-id fallback. Duplicate
    selectors must never yield duplicate model choices.
    """
    from selenium.webdriver.common.by import By
    from .gemini_ui_semantic_controls import snapshot_options,Option
    from .gemini_ui_adaptive_protocol import normalized_family
    atomic=snapshot_options(driver)
    items=[]
    if atomic is not None:
        items=list(atomic)
    else:
        unique={}
        selectors=(
          '[role="menuitemradio"]','[role="radio"]',
          '[role="option"]','[role="menuitemcheckbox"]',
          '[role="menuitem"]','gem-menu-item[role="menuitem"]',
          'gem-menu-item[role="menuitemradio"]',
          '[data-test-id^="bard-mode-option"]',
          '[data-test-id*="model-option"]',
        )
        for selector in selectors:
            try:
                found=driver.find_elements(By.CSS_SELECTOR,selector)
            except Exception:
                continue
            for item in found:
                try:
                    if not item.is_displayed():
                        continue
                    key=getattr(item,"id",None) or id(item)
                    label="\n".join(filter(None,(
                        item.text or "",
                        item.get_attribute("aria-label") or "",
                        item.get_attribute("title") or "",
                    )))
                    if 0<len(label)<=230:
                        unique[key]=Option(
                            item,label,
                            (item.get_attribute("aria-checked")=="true"
                             or item.get_attribute("aria-selected")=="true"),
                            item.get_attribute("aria-disabled")=="true")
                except Exception:
                    continue
        items=list(unique.values())
    result=[]
    for candidate in items:
        family=normalized_family(candidate.label)
        if family and len(candidate.label)<=230:
            result.append((family,candidate))
    return result


def visible_offered_gemini_families(driver) -> list[str]:
    """Read positive known-family evidence from visible individual controls.

    Unknown models such as Hydrogen/Argon/Carbon are NOT presumed equivalent
    to Flash. An absent/ambiguous menu cannot justify any model fallback.
    """
    return sorted({family for family,option in _visible_model_options(driver)
                   if not option.disabled})


def _owned_picker(driver, owned_handle: str | None):
    """Behavior-based picker lookup with bounded, independently validated fallbacks.

    Markup roles, order, and mode descriptions can change. Discover a
    *unique* visible model control by semantic name or mode-control test id;
    never fall back to an arbitrary button or tab.
    """
    from selenium.webdriver.common.by import By
    if (not owned_handle or driver.current_window_handle != owned_handle
            or not str(driver.current_url).startswith(
                "https://gemini.google.com/")):
        raise GeminiModelError("PRE_SEND_OWNED_GEMINI_TAB_CHANGED")
    selectors = (
        'button[aria-label^="Open mode picker"]',
        '[data-test-id="bard-mode-menu-button"]',
        '[aria-label*="model"]',
        '[aria-label*="mode"]',
        'button[aria-haspopup="menu"]',
        '[role="button"][aria-haspopup="menu"]',
    )
    # A long editor prompt can trigger continuous Angular re-rendering.
    # Independent find_elements calls then see different Selenium element IDs
    # for the SAME logical model control and falsely report ambiguity. Use ONE
    # read-only, synchronous DOM snapshot so CSS alternatives are deduplicated
    # by underlying node identity, not by time-varying WebElement IDs.
    # No events, navigation, Send, model choice or prompt contents are read.
    try:
        atomic = driver.execute_script("""
            const selectors = [
              'button[aria-label^="Open mode picker"]',
              '[data-test-id="bard-mode-menu-button"]',
              '[aria-label*="model"]',
              '[aria-label*="mode"]',
              'button[aria-haspopup="menu"]',
              '[role="button"][aria-haspopup="menu"]'
            ];
            const nodes = new Set();
            // Retain the historical document.querySelectorAll probe, but
            // expand into open Shadow DOM roots for custom-element redesigns.
            const roots=[document], seenRoots=new Set();
            for (const root of roots) {
              if (seenRoots.has(root) || seenRoots.size>=80)continue;
              seenRoots.add(root);
              for (const selector of selectors) {
                for (const node of root.querySelectorAll(selector))
                  nodes.add(node);
              }
              for (const node of root.querySelectorAll('*')) {
                if (node.shadowRoot && !seenRoots.has(node.shadowRoot))
                  roots.push(node.shadowRoot);
              }
            }
            const visible = node => {
              const r = node.getBoundingClientRect();
              if (r.width <= 0 || r.height <= 0) return false;
              for (let p = node; p; p = p.parentElement) {
                const s = getComputedStyle(p);
                if (s.display === 'none' || s.visibility === 'hidden' ||
                    Number(s.opacity) <= 0.01) return false;
              }
              return true;
            };
            return [...nodes].filter(node => {
              if (!visible(node)) return false;
              const hint = ((node.getAttribute('aria-label') || '') + ' ' +
                            (node.getAttribute('data-test-id') || '')
                           ).toLowerCase();
              return (hint.includes('mode') || hint.includes('model')) &&
                     ['picker','select','choose','switch','change',
                      'menu','current','bard-mode'].some(x => hint.includes(x));
            });
        """)
    except (AttributeError, AssertionError, NotImplementedError):
        # Lightweight offline test drivers may not implement DOM JavaScript.
        # The historical semantic selector path remains available to them.
        atomic = None
    if isinstance(atomic, (list, tuple)):
        if len(atomic) != 1:
            raise GeminiModelError("PRE_SEND_MODE_PICKER_NOT_UNIQUE_OR_MISSING")
        return atomic[0]
    unique = {}
    for selector in selectors:
        for candidate in driver.find_elements(By.CSS_SELECTOR, selector):
            if not candidate.is_displayed():
                continue
            label = candidate.get_attribute("aria-label") or ""
            test = candidate.get_attribute("data-test-id") or ""
            hint = (label + " " + test).casefold()
            if not (("mode" in hint or "model" in hint)
                    and ("picker" in hint or "select" in hint
                         or "choose" in hint or "switch" in hint
                         or "change" in hint or "menu" in hint
                         or "current" in hint or "bard-mode" in hint)):
                continue
            unique[candidate.id] = candidate
    if len(unique) != 1:
        raise GeminiModelError(
            "PRE_SEND_MODE_PICKER_NOT_UNIQUE_OR_MISSING")
    return next(iter(unique.values()))


def _observed_picker_label(picker) -> str:
    """Require evidence from the dedicated control of its CURRENT family.

    Accessibility word order, model versions and text host can change. A
    generic 'Choose model' action label proves nothing about selection.
    """
    from .gemini_ui_adaptive_protocol import normalized_family
    for name in ("aria-label","title","aria-description"):
        label=str(picker.get_attribute(name) or "").strip()
        if not label:
            continue
        if re.search(
          r"\b(?:currently|current\s+(?:model|mode)|selected\s+(?:model|mode)|"
          r"using\s+(?:model\s+)?|active\s+(?:model|mode))\b",
          label,flags=re.I):
            if re.search(r"\bcurrently\b",label,flags=re.I):
                return label
            named=re.search(
                r"\b(?:current|selected|active)\s+(?:model|mode)\s*[:\-]\s*(.*)$",
                label,flags=re.I)
            return "Open mode picker, currently "+(
                named.group(1) if named else label)
    # The own text of a uniquely proved model selector is a selected
    # model label. Never infer it from the page body or any other tab.
    test=str(picker.get_attribute("data-test-id") or "").casefold()
    text=(getattr(picker,"text","") or "").strip()
    label=str(picker.get_attribute("aria-label") or "").casefold()
    if (("mode" in test or "model" in test or
         ("model" in label and "picker" in label))
        and normalized_family(text) is not None
        and len(text)<=90
        and len(text.splitlines())<=2):
        return "Open mode picker, currently "+text
    raise GeminiModelError("PRE_SEND_SELECTED_MODEL_FAMILY_UNOBSERVABLE")


def assert_owned_gemini_mode(driver, owned_handle: str | None,
                             mode: str = "flash", *,
                             wait_seconds: float = 0.0) -> str:
    """Read-only exact owned-model verification at the single Send boundary.

    A bounded *pre-Send-only* wait handles transient Angular rehydration or
    temporary missing/duplicated picker nodes. It NEVER changes the model,
    borrows another tab, retries a Send, or waits out a wrong-family label.
    """
    from selenium.common.exceptions import StaleElementReferenceException

    if (mode not in MODEL_SPECS or not owned_handle
            or not isinstance(wait_seconds, (int, float))
            or not 0 <= wait_seconds <= 10
            or driver.current_window_handle != owned_handle
            or not str(driver.current_url).startswith("https://gemini.google.com/")):
        raise GeminiModelError("PRE_SEND_OWNED_GEMINI_TAB_OR_MODEL_UNVERIFIED")
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            selected = _observed_picker_label(
                _owned_picker(driver, owned_handle))
        except (GeminiModelError, StaleElementReferenceException) as exc:
            transient = (
                isinstance(exc, StaleElementReferenceException)
                or str(exc) == "PRE_SEND_MODE_PICKER_NOT_UNIQUE_OR_MISSING"
            )
            if not transient or time.monotonic() >= deadline:
                raise
            # Ownership can change during an Angular update; each pass
            # re-checks the same exact tab and Gemini origin.
            time.sleep(0.2)
            continue
        if not _matches_mode(selected, mode):
            raise GeminiModelError(
                "PRE_SEND_GEMINI_MODEL_FAMILY_MISMATCH_NO_SEND: " + selected)
        return selected


def wait_owned_gemini_picker(driver, owned_handle: str | None, *,
                             timeout_seconds: float = 30) -> str:
    """Wait for the UNIQUE model picker in the exact owned Gemini tab.

    New chat resets Angular controls independently of the editor and model;
    an editable composer is NOT proof that the picker has rehydrated. Wait
    before trying to choose the family, never borrow a different visible
    Gemini tab, guess a CSS position, type a prompt, or click Send.
    """
    if (not isinstance(timeout_seconds,(int,float))
            or not 1<=timeout_seconds<=60
            or not owned_handle):
        raise GeminiModelError("Invalid bounded owned-picker wait")
    deadline=time.monotonic()+timeout_seconds
    last=None
    while True:
        if (driver.current_window_handle!=owned_handle
                or not str(driver.current_url).startswith(
                    "https://gemini.google.com/")):
            raise GeminiModelError(
                "PRE_SEND_OWNED_GEMINI_TAB_CHANGED_WHILE_HYDRATING")
        try:
            return _observed_picker_label(_owned_picker(driver,owned_handle))
        except GeminiModelError as error:
            if str(error)!="PRE_SEND_MODE_PICKER_NOT_UNIQUE_OR_MISSING":
                raise
            last=error
        except Exception as error:
            from selenium.common.exceptions import (
                StaleElementReferenceException)
            if not isinstance(error,StaleElementReferenceException):
                raise
            last=error
        if time.monotonic()>=deadline:
            raise GeminiModelError(
                "PRE_SEND_OWNED_MODEL_PICKER_NOT_REHYDRATED_NO_SEND") from last
        time.sleep(0.25)


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

    picker = _owned_picker(driver, owned_handle)
    current = _observed_picker_label(picker)
    if _matches_mode(current, mode):
        return assert_owned_gemini_mode(driver, owned_handle, mode)
    # A failed exact selection may leave the same model menu open. A retry
    # must NOT toggle an already-open menu shut before scanning its options.
    if (picker.get_attribute("aria-expanded") or "").casefold() != "true":
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
        for family, item in _visible_model_options(driver):
            if family != mode or item.disabled:
                continue
            element=item.element
            unique[getattr(element,"id",None) or id(element)]=element
        if len(unique) > 1:
            raise GeminiModelError("PRE_SEND_AMBIGUOUS_GEMINI_MODEL_MENU")
        if unique:
            target = next(iter(unique.values()))
            break
        time.sleep(0.2)
    if target is None or target.get_attribute("aria-disabled") == "true":
        offered=visible_offered_gemini_families(driver)
        # This is NOT a harmless DOM change: the currently authenticated
        # account's actual menu no longer offers the contracted model. Never
        # guess that Hydrogen/Pro/Flash-Lite is semantically equivalent.
        detail=("; requested="+mode+"; offered="+",".join(offered)
                if offered and mode not in offered else "")
        # Include only the dedicated picker's short current-family label for
        # diagnostics (never prompt text, account details, or page contents).
        detail+="; current="+str(current)[:100]
        raise GeminiModelError(
            "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND"+detail)
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


def select_owned_gemini_with_recovery(
        driver, owned_handle: str | None, *, mode: str = "flash",
        stage: str | None = None, timeout: float = 15,
        allow_fallback: bool = True) -> str:
    """Normal pre-Send route: prefer Flash, adapt only to verified absence.

    This deliberately reuses the EXACT low-level selector. A recognized
    fallback is a same-task model-family choice, never a new provider, API,
    alternate account, response retry or bypass of mathematical/source QA.

    Only when the positive visible model menu establishes that the
    contracted family is unavailable can the *stage policy* choose a
    verified family. Unknown marketing models are never guessed as Flash.
    """
    import os
    from .gemini_ui_adaptive_protocol import (
        choose_family, GeminiAdaptivePolicyError)
    try:
        return select_owned_gemini_mode(
            driver,owned_handle,mode=mode,timeout=timeout)
    except GeminiModelError as error:
        # An ambiguous selector, stale tab, missing selected-state proof or
        # changed UI is not evidence the model was removed. Do not silently
        # fallback in those cases. An academic no-Send source preflight can
        # also require the exact original family.
        if (not allow_fallback or not str(error).startswith(
            "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND")):
            raise
        active=(stage or os.getenv("MICROGEN_ACTIVE_GENERATION_STAGE","")
                or os.getenv("MICROGEN_GEMINI_INTERACTION_STAGE","")
                ).strip().casefold()
        offered=visible_offered_gemini_families(driver)
        if not offered or mode in offered:
            raise GeminiModelError(
                "PRE_SEND_MODEL_FALLBACK_NOT_AUTHORIZED_WITHOUT_EXACT_MENU_EVIDENCE"
            ) from error
        try:
            route=choose_family(requested=mode,offered=offered,stage=active)
        except GeminiAdaptivePolicyError as exc:
            raise GeminiModelError(str(exc)) from error
        if route.chosen == mode:
            raise
        selected=select_owned_gemini_mode(
            driver,owned_handle,mode=route.chosen,timeout=timeout)
        # Only verified chosen-mode controls may update this worker's
        # stage-local runtime contract. Parent runner/other child jobs are
        # untouched, and *every* subsequent pre-Send gate reads the update.
        model_ids={
            "flash":"gemini-3.8-flash",
            "flash-lite":"gemini-3.5-flash-lite",
            "pro":"gemini-3.1-pro",
        }
        os.environ["MICROGEN_GEMINI_UI_MODE"]=route.chosen
        os.environ["MICROGEN_LLM_MODEL"]=model_ids[route.chosen]
        os.environ["MICROGEN_MODEL_ROUTE_REASON"]=route.reason
        os.environ["MICROGEN_MODEL_ROUTE_REQUESTED"]=route.requested
        os.environ["MICROGEN_MODEL_ROUTE_OFFERED"]=",".join(route.offered)
        return selected


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
            or (requested_mode == "flash" and re.search(r"\blite\b", named))
            or (requested_mode == "flash-lite"
                and not re.search(r"\bflash[ -]lite\b", named))):
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
                    try:
                        picker = _owned_picker(driver, handle)
                        break
                    except GeminiModelError:
                        continue
                except Exception:
                    continue
            if picker is None:
                time.sleep(0.25)

        if picker is None and gemini_tab_seen and target_mode in ("flash", "flash-lite"):
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
                    try:
                        picker = _owned_picker(
                            driver, driver.current_window_handle)
                    except GeminiModelError:
                        picker = None
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
