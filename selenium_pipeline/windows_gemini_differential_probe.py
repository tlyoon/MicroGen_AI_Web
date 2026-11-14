"""Windows Gemini generation/browsing differential diagnostic; no textbook PDF.

Read-only by default. Explicit fresh browser canary can distinguish an owned
browser response from an API content-generation response. API *generation*
may be billed and requires separate exact flag. A completed or ambiguous
canary attempt is immutable: NEVER silently re-send to either transport.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from .windows_gemini_provider_halt import (
    inspect_halt, inspect_completed_trials, record_stage, record_api_capacity,
)
from .windows_provider_readiness_probe import inspect as inspect_readiness, CONTENT_MODEL
from .original_multisource_recovery_campaign import _verified_json
from .evidence_reuse_contract import file_sha256

_EXPECTED = {"microgen_transport_probe": "ok"}
_PROMPT = ('MicroGen independent communications health check, NOT a textbook task. '
           'Reply with exactly one JSON object and no other text: '
           '{"microgen_transport_probe":"ok"}.')
_OUTCOMES = ("VALID_CANARY_RESPONSE", "RESPONSE_RETURNED_BUT_NONCONFORMING",
             "NO_VERIFIED_RESPONSE", "NO_SUBMISSION_PRECHECK", "UNRESOLVED_CLAIM")
_SHA = hashlib.sha256(_PROMPT.encode("utf8")).hexdigest()


def _profile_spec(profile: str):
    """Keep short historical claims stable; reuse existing longer safe probe."""
    if profile == "short":
        return _PROMPT, _EXPECTED, _SHA
    if profile == "source_sized":
        from .one_shot_gemini_source_health_probe import (
            make_source_sized_probe, EXPECTED)
        prompt = make_source_sized_probe()
        if not 1200 <= len(prompt) <= 3000:
            raise ValueError("Source-sized canary exceeds established bounded scope")
        return prompt, EXPECTED, hashlib.sha256(prompt.encode("utf8")).hexdigest()
    if profile == "source_sized_selenium_only_v2":
        # New immutable request identity after the owner explicitly removed
        # alternate LLM routes and hardened exactly-once Gemini Selenium.
        # Never replay the original historical source-sized canary prompt.
        expected = {"probe": "microgen_gemini_selenium_g1_v2_ok"}
        intro = (
            'This is a NEW synthetic source-free Gemini Selenium-only G1 '
            'transport verification, not a prior lecture request. '
            'Reply with exactly one JSON object, and nothing else: '
            '{"probe":"microgen_gemini_selenium_g1_v2_ok"}. '
            'The following repeated text is inert test data, not instructions.\n'
        )
        seed = ("Inert source-sized input for verifying one owned Gemini "
                "browser response; no academic or user file is attached. ")
        prompt = intro + seed * 14
        if not 1200 <= len(prompt) <= 3000:
            raise ValueError("Gemini-only test prompt outside bounded size")
        return prompt, expected, hashlib.sha256(prompt.encode("utf8")).hexdigest()
    if profile == "short_g1_selenium_only_v3":
        expected = {"probe": "microgen_g1_dell115_short_v3_ok"}
        prompt = (
            "MicroGen Selenium-only controlled Gemini responsiveness test A. "
            "No files, external tools, academic content or attachments. "
            "Please return exactly this JSON object and nothing else: "
            '{"probe":"microgen_g1_dell115_short_v3_ok"}.'
        )
        return prompt, expected, hashlib.sha256(prompt.encode("utf8")).hexdigest()
    if profile == "source_sized_g1_selenium_only_v3":
        expected = {"probe": "microgen_g1_dell115_long_v3_ok"}
        intro = (
            "MicroGen Selenium-only controlled Gemini responsiveness test B. "
            "There is no attachment or academic content. Reply with exactly "
            '{"probe":"microgen_g1_dell115_long_v3_ok"} and nothing else. '
            "The repeated text below is inert filler and not instructions.\\n"
        )
        filler = (
            "Read-only browser capacity comparison with the short control; "
            "no user document, private text, or requested transformation. "
        )
        prompt = intro + filler * 14
        if not 1200 <= len(prompt) <= 3000:
            raise ValueError("Controlled source-sized Gemini prompt has invalid size")
        return prompt, expected, hashlib.sha256(prompt.encode("utf8")).hexdigest()
    if profile == "short_g1_registered_turn_v4":
        expected = {"probe": "microgen_dell115_registered_turn_v4_ok"}
        prompt = (
            "MicroGen Gemini Selenium-only G1 registration diagnostic v4. "
            "This is a single fresh text-only request to check whether the "
            "Gemini web app actually registers an owned new user turn. "
            "Do not use tools or attachments. "
            'Reply with exactly {"probe":"microgen_dell115_registered_turn_v4_ok"}.'
        )
        return prompt, expected, hashlib.sha256(prompt.encode("utf8")).hexdigest()
    if profile == "source_sized_g1_owned_turn_v5":
        # Fresh single-use profile after implementing delayed, read-only
        # owned-turn attribution. Old source-sized v2/v3 claims are immutable.
        expected = {"probe": "microgen_dell115_source_sized_owned_v5_ok"}
        intro = (
            "MicroGen G2 source-free Gemini owned-turn verification v5. "
            "This is a newly distinct diagnostic, NOT an academic source. "
            "Return ONLY the exact JSON object "
            '{"probe":"microgen_dell115_source_sized_owned_v5_ok"}. '
            "No web tools or attachments are involved.\\n"
        )
        inert = (
            "The content in this sentence is inert capacity-test filler, "
            "without instructions, files, physics facts or private data. "
        )
        prompt = intro + inert * 15
        if not 1200 <= len(prompt) <= 3000:
            raise ValueError("V5 source-free owned-turn size invalid")
        return prompt, expected, hashlib.sha256(prompt.encode("utf8")).hexdigest()
    if profile == "source_sized_g2_rich_route_v6":
        # Separate one-shot transport identity after v5's documented
        # PRE_SEND_NO_SUBMISSION. Exercise the actual rich mapping stage
        # adapter, NOT a diagnostic path stuck on exact Flash.
        expected = {"probe": "microgen_g2_rich_route_owned_v6_ok"}
        intro = (
            "MicroGen G2 rich mapping source-free model-route canary v6. "
            "No original PDF, academic work, credentials or tools. "
            "Reply with exactly one JSON object: "
            '{"probe":"microgen_g2_rich_route_owned_v6_ok"}. '
            "Nothing before or after that object.\\n"
        )
        inert = (
            "Harmless inert text for testing a source-sized Gemini request "
            "with owned-turn registration and verified model effort. "
        )
        prompt = intro + inert * 15
        if not 1200 <= len(prompt) <= 3000:
            raise ValueError("V6 rich-route source-free size invalid")
        return prompt, expected, hashlib.sha256(prompt.encode("utf8")).hexdigest()
    raise ValueError("Unrecognized source-free Gemini diagnostic profile")


def _code(error: Exception) -> int | None:
    try:
        code = getattr(error, "code", None)
        code = code() if callable(code) else code
        code = int(code)
        return code if 100 <= code <= 599 else None
    except (ValueError, TypeError):
        return None


def _valid(raw: str, profile: str = "short") -> bool:
    if not isinstance(raw, str) or len(raw) > 5000:
        return False
    try:
        _, expected, _ = _profile_spec(profile)
        return json.loads(raw.strip()) == expected
    except (ValueError, UnicodeError):
        return False


def _local_only(path: Path) -> Path:
    local = os.getenv("LOCALAPPDATA")
    if not local:
        raise ValueError("Native Windows LOCALAPPDATA required")
    p = Path(path).absolute()
    base = Path(local).absolute()
    if (not p.is_relative_to(base) or p == base or p.is_symlink()
            or (p.exists() and not p.is_dir())
            or any(x.is_symlink() for x in (p.parent, base))):
        raise ValueError("Canary receipts require safe new LOCALAPPDATA folder")
    return p


def _write_new(path: Path, record: dict) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("Never replace prior Gemini canary evidence")
    with path.open("x", encoding="utf8") as file:
        json.dump(record, file, sort_keys=True, indent=2)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())


def _read(path: Path) -> dict | None:
    if not path.is_file():
        return None
    if path.is_symlink() or path.stat().st_size > 4096:
        raise ValueError("Unsafe existing Gemini canary proof")
    record = _verified_json(path)
    backend = record.get("backend")
    if (backend not in ("browser", "api")
            or record.get("schema_version") != 1
            or record.get("outcome") not in _OUTCOMES
            or record.get("student_publication_authorized") is not False):
        raise ValueError("Invalid existing Gemini canary record")
    claim = _verified_json(path.parent / f"{backend}_probe_started.json")
    profile = claim.get("probe_profile", "short")
    try:
        _, _, profile_sha = _profile_spec(profile)
    except ValueError as exc:
        raise ValueError("Unknown immutable canary claim profile") from exc
    if (claim.get("schema_version") != 1
            or claim.get("backend") != backend
            or claim.get("generic_prompt_sha256") != profile_sha
            or claim.get("content_model") != CONTENT_MODEL
            or claim.get("one_submission_only") is not True
            or record.get("probe_profile", "short") != profile):
        raise ValueError("Canary result has no matching immutable send intent")
    # Original PR502 browser canary has no claim_sha256. Validate its exact
    # independent physical claim without retroactively altering any bytes.
    if record.get("claim_sha256") is not None and (
            record["claim_sha256"] != file_sha256(
                path.parent / f"{backend}_probe_started.json")):
        raise ValueError("Canary claim/result SHA does not agree")
    return record


def _request_browser(prompt: str, *, profile: str = "short") -> str:
    from .series_gemini import _browser_request
    # Only the owned browser tab and its attributed response may be captured.
    # This longer-input check uses NO original source and no model/API retry.
    if profile == "source_sized_g2_rich_route_v6":
        from .rich_mapping_provider_dispatch import _real_transport
        # Reuse production Flash-first/Medium and positively verified
        # owned-tab Pro fallback, including the late Send registration.
        return _real_transport(
            "gemini",prompt,9222,150,
            accept_fn=lambda raw: _valid(raw,profile=profile))
    return _browser_request(
        prompt, [], port=9222,
        wait_cap_s=(150 if profile.startswith("source_sized") else 90),
        min_chars=8, accept_fn=lambda raw: _valid(raw, profile=profile),
    )


def _request_api(prompt: str) -> str:
    from google import genai
    from google.genai import types
    from gemini_keys import get_gemini_api_keys
    from .runner import load_microvid_env
    load_microvid_env()
    keys = get_gemini_api_keys()
    if not keys:
        raise ValueError("No Gemini API content key configured")
    # The independent diagnostic intentionally uses ONE key and ONE SDK
    # request, never normal TTS failover and never another provider retry.
    options = types.HttpOptions(
        timeout=30000, retry_options=types.HttpRetryOptions(attempts=1))
    client = genai.Client(api_key=keys[0], http_options=options)
    try:
        response = client.models.generate_content(
            model=CONTENT_MODEL, contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0, max_output_tokens=80))
    finally:
        client.close()
    candidates = getattr(response, "candidates", None) or []
    finish = str(getattr(candidates[0], "finish_reason", "")).upper() if candidates else ""
    if not finish.endswith("STOP"):
        raise RuntimeError("Gemini API response did not finish normally")
    return getattr(response, "text", None) or ""


def run_canary(*, checkpoint_dir: Path, backend: str,
               confirm_api_diagnostic_cost: bool = False,
               browser_transport=None, api_transport=None,
               browser_ready=None, profile: str = "short") -> dict:
    """One optional backend-specific new canary, no original files/TTS.

    Caller may inject *test-only* transports; CLI uses real owned services.
    """
    if sys.platform != "win32" or backend not in ("browser", "api"):
        raise ValueError("Native Windows browser/API diagnostic only")
    if backend == "api" and confirm_api_diagnostic_cost is not True:
        raise ValueError("Explicit --confirm-api-diagnostic-cost required")
    if confirm_api_diagnostic_cost and backend != "api":
        raise ValueError("API diagnostic cost consent never applies to browser")
    if profile != "short" and backend != "browser":
        raise ValueError("Source-sized diagnostic is browser-only, never paid API")
    prompt, _, prompt_sha = _profile_spec(profile)
    root = _local_only(checkpoint_dir)
    root.mkdir(parents=True, exist_ok=True)
    claim = root / f"{backend}_probe_started.json"
    result = root / f"{backend}_probe_result.json"
    if claim.exists() or claim.is_symlink():
        # A preclaim might have been partially written by an older crashed
        # worker. Never interpret that as a fresh sending opportunity.
        # Only *complete* trusted receipts require canonical immutable proof.
        saved_claim = None
        try:
            if (claim.is_file() and not claim.is_symlink()
                    and 0 < claim.stat().st_size <= 4096):
                saved_claim = json.loads(claim.read_text(encoding="utf8"))
        except (OSError, ValueError, UnicodeError, TypeError):
            pass
        if (type(saved_claim) is dict
                and saved_claim.get("probe_profile", "short") != profile):
            raise ValueError("Different canary profiles cannot reuse same Send claim")
        if result.is_file():
            previous = _read(result)
            return {**previous, "status": "PRIOR_CANARY_RECEIPT_REUSED"}
        return {
            "schema_version": 1, "backend": backend,
            "outcome": "UNRESOLVED_CLAIM",
            "status": "PRIOR_CANARY_MAY_HAVE_SUBMITTED_NO_RESEND",
            "new_model_generation_calls": 0,
            "student_publication_authorized": False,
        }
    if result.exists() or result.is_symlink():
        raise ValueError("Unexpected result without a pre-send canary claim")
    if backend == "browser":
        if browser_ready is None:
            from .rich_mapping_provider_readiness import inspect_provider
            ready = inspect_provider("gemini")
        else:
            ready = browser_ready()
        if ready.get("authenticated_ui_ready") is not True:
            return {
                "schema_version": 1, "backend": backend,
                "status": "BROWSER_NOT_AUTHENTICATED_NO_SEND",
                "outcome": "NO_SUBMISSION_PRECHECK",
                "new_model_generation_calls": 0,
                "student_publication_authorized": False,
            }
    elif api_transport is None:
        from .runner import load_microvid_env
        load_microvid_env()
        from gemini_keys import get_gemini_api_keys
        if not get_gemini_api_keys():
            return {
                "schema_version": 1, "backend": backend,
                "status": "API_CREDENTIAL_MISSING_NO_SEND",
                "outcome": "NO_SUBMISSION_PRECHECK",
                "new_model_generation_calls": 0,
                "student_publication_authorized": False,
            }
    # Claim is durably persisted before any API or browser submission.
    _write_new(claim, {
        "schema_version": 1, "backend": backend,
        "content_model": CONTENT_MODEL, "generic_prompt_sha256": prompt_sha,
        "probe_profile": profile,
        "one_submission_only": True,
        "explicit_api_content_cost": backend == "api",
        "no_original_source_attached": True,
        "student_publication_authorized": False,
    })
    answer = {
        "schema_version": 1, "backend": backend,
        "status": "GENERIC_CANARY_TERMINAL",
        "content_model": CONTENT_MODEL,
        "claim_sha256": file_sha256(claim),
        "generic_prompt_sha256": prompt_sha,
        "probe_profile": profile,
        "prompt_characters": len(prompt),
        "outcome": "NO_VERIFIED_RESPONSE",
        "error_type": None,
        "verified_api_http_status": None,
        "response_character_count": 0,
        "request_may_have_been_submitted": True,
        "new_model_generation_calls": 1,
        "paid_api_content_may_have_occurred": backend == "api",
        "source_pdf_transmitted": False,
        "student_publication_authorized": False,
        "existing_original_source_retry_permitted": False,
        "gemini_selenium_only": backend == "browser",
        "chatgpt_fallback_attempted": False,
        "gemini_api_fallback_attempted": False,
        "gemini_browser_failure_phase": None,
        "gemini_browser_presend_attempts_used": None,
        "gemini_send_registration_status": None,
        "gemini_new_user_turn_verified": None,
        "gemini_late_response_reconciled": None,
        "gemini_visible_model_chars_at_stop": None,
        "gemini_generation_active_at_stop": None,
        "gemini_selenium_stop_message": None,
    }
    try:
        transport = ((browser_transport or
                      (lambda text: _request_browser(text, profile=profile)))
                     if backend == "browser" else (api_transport or _request_api))
        raw = transport(prompt)
        answer["response_character_count"] = (
            min(len(raw), 5000) if isinstance(raw, str) else 0)
        answer["outcome"] = ("VALID_CANARY_RESPONSE" if _valid(raw, profile=profile)
                             else "RESPONSE_RETURNED_BUT_NONCONFORMING")
        if backend == "browser":
            # Successful replies MUST carry the same trusted, prompt-free
            # registration evidence as failure receipts. Plain injected test
            # strings retain null/unknown, never invented positive proof.
            status = getattr(raw, "gemini_send_registration_status", None)
            verified = getattr(raw, "gemini_new_user_turn_verified", None)
            late = getattr(raw, "gemini_late_response_reconciled", None)
            if (type(status) is str and 0 < len(status) < 80
                    and status.isupper() and
                    all(c.isupper() or c.isdigit() or c == "_" for c in status)):
                answer["gemini_send_registration_status"] = status
            if type(verified) is bool:
                answer["gemini_new_user_turn_verified"] = verified
            if type(late) is bool:
                answer["gemini_late_response_reconciled"] = late
    except Exception as error:
        # Never persist API key, exception .args, original prompt or raw
        # model text. Generic error type and structured HTTP status only.
        answer["error_type"] = type(error).__name__
        if backend == "browser":
            from .gemini_bridge_failure_triage import (
                classify_owned_gemini_failure)
            from .gemini_selenium_only_policy import temporary_failure_message
            # The real Selenium bridge exposes privacy-safe phase metadata.
            # A separately injected/legacy exception may not: UNKNOWN is
            # honest and preserves the no-resend invariant.
            possible = getattr(error, "gemini_send_boundary_entered", None)
            if type(possible) is bool:
                answer["request_may_have_been_submitted"] = possible
                if not possible:
                    answer["new_model_generation_calls"] = 0
            phase = getattr(error, "gemini_failure_phase", None)
            if (type(phase) is not str or not phase or len(phase) > 128):
                phase = classify_owned_gemini_failure(error)["stage"]
            attempts = getattr(error, "gemini_prepare_attempts_used", None)
            if type(attempts) is int and 1 <= attempts <= 3:
                answer["gemini_browser_presend_attempts_used"] = attempts
            answer["gemini_browser_failure_phase"] = (
                "PRE_SEND_NO_SUBMISSION" if possible is False else
                "AFTER_POSSIBLE_SEND" if possible is True else
                "UNKNOWN_SUBMISSION_OUTCOME")
            registration=getattr(error,"gemini_send_registration_status",None)
            if (isinstance(registration,str) and
                    0<len(registration)<80 and
                    registration.isupper() and
                    all(c.isupper() or c.isdigit() or c=="_"
                        for c in registration)):
                answer["gemini_send_registration_status"]=registration
            new_turn=getattr(error,"gemini_new_user_turn_verified",None)
            if type(new_turn) is bool:
                answer["gemini_new_user_turn_verified"]=new_turn
            chars=getattr(error,"gemini_visible_model_chars_at_stop",None)
            if type(chars) is int and 0<=chars<=1800000:
                answer["gemini_visible_model_chars_at_stop"]=chars
            generation=getattr(error,"gemini_generation_active_at_stop",None)
            if type(generation) is bool:
                answer["gemini_generation_active_at_stop"]=generation
            answer["browser_bridge_stage"] = phase
            answer["gemini_selenium_stop_message"] = (
                temporary_failure_message(
                    phase, may_have_submitted=possible is not False))
        answer["verified_api_http_status"] = (
            _code(error) if backend == "api" else None)
    _write_new(result, answer)
    return answer


def classify(*, browser: dict | None, api: dict | None,
             metadata_reachable: bool = False,
             browser_authenticated: bool | None = None) -> dict:
    """Qualitative differential; never confuses metadata with generation."""
    b = browser.get("outcome") if browser else None
    a = api.get("outcome") if api else None
    b_ok = b == "VALID_CANARY_RESPONSE"
    a_ok = a == "VALID_CANARY_RESPONSE"
    b_bad = b in ("NO_VERIFIED_RESPONSE", "RESPONSE_RETURNED_BUT_NONCONFORMING")
    a_bad = a in ("NO_VERIFIED_RESPONSE", "RESPONSE_RETURNED_BUT_NONCONFORMING")
    api_http_status = api.get("verified_api_http_status") if api else None
    if api_http_status in (429, 503, 504) and a_bad:
        label = ("API_REPORTED_CAPACITY_AND_BROWSER_FAILED"
                 if b_bad else "API_REPORTED_CAPACITY_GENERATION_UNAVAILABLE")
    elif api_http_status in (401, 403) and a_bad:
        label = "API_AUTH_OR_PERMISSION_FAILURE_NOT_PROVIDER_OUTAGE"
    elif b_ok and a_ok:
        label = "BOTH_GENERATION_TRANSPORTS_RESPOND_TO_SMALL_CANARY"
    elif a_ok and b_bad:
        label = "BROWSER_AUTOMATION_OR_RESPONSE_CAPTURE_SUSPECTED"
    elif b_ok and a_bad:
        label = "API_GENERATION_ROUTE_PROBLEM_SUSPECTED"
    elif b_bad and a_bad:
        label = "SERVICE_OR_NETWORK_OR_BOTH_TRANSPORTS_SUSPECTED"
    elif b_ok:
        label = (
            "BROWSER_SOURCE_SIZED_INPUT_CANARY_OK_FULL_LESSON_NOT_CERTIFIED"
            if str(browser.get("probe_profile", "short")).startswith("source_sized")
            else "BROWSER_SHORT_CANARY_WORKS_LONG_FORM_NOT_CERTIFIED"
        )
    elif a_ok and browser_authenticated is False:
        label = "BROWSER_AUTHENTICATION_OR_CAPTURE_PROBLEM"
    elif a_ok:
        label = "API_SMALL_CANARY_WORKS_BROWSER_NOT_TESTED"
    elif b_bad and not a:
        label = "INCONCLUSIVE_BROWSER_FAILURE_METADATA_NOT_GENERATION_PROOF"
    elif a_bad and not b:
        label = "INCONCLUSIVE_API_FAILURE_BROWSER_GENERATION_UNTESTED"
    elif browser_authenticated is False:
        label = "BROWSER_NOT_READY_GENERATION_UNTESTED"
    else:
        label = "INCONCLUSIVE_NO_COMPARATIVE_GENERATION_PROOFS"
    return {
        "status": label,
        "metadata_reachable_not_generation_proof": metadata_reachable,
        "api_structured_http_status": api_http_status,
        "browser_canary": b or "NOT_TESTED",
        "browser_canary_profile": (
            browser.get("probe_profile", "short") if browser else "NOT_TESTED"),
        "source_sized_text_input_response_verified": bool(
            b_ok and browser and str(browser.get("probe_profile")).startswith("source_sized")),
        "source_sized_input_is_not_full_lecture_generation": True,
        "api_canary": a or "NOT_TESTED",
        "provider_server_outage_proven": False,
        "cause_estimate_not_causal_proof": True,
        "no_automatic_retry_or_fallback": True,
        "new_api_content_cost_authorized": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inspect-browser", action="store_true")
    ap.add_argument("--probe-api-model-metadata-once", action="store_true")
    ap.add_argument("--browser-canary-once", action="store_true")
    ap.add_argument("--browser-canary-profile",
                    choices=("short", "source_sized",
                             "source_sized_selenium_only_v2"), default="short",
                    help="Source-sized profile sends 1.2-3k synthetic characters; never a PDF")
    ap.add_argument("--api-canary-once", action="store_true")
    ap.add_argument("--confirm-api-diagnostic-cost", action="store_true")
    ap.add_argument("--canary-root", type=Path)
    ap.add_argument("--register-api-capacity-from-canary", action="store_true",
                    help="Import only a prior structured 429/503, no new API call")
    ap.add_argument("--prior-trial", action="append", type=Path, default=[])
    ap.add_argument("--register-terminal-trial", action="append", type=Path,
                    default=[], help="Explicitly SHA-import prior real terminal receipts to shared health")
    ap.add_argument("--health-root", type=Path)
    args = ap.parse_args(argv)
    if args.api_canary_once and not args.confirm_api_diagnostic_cost:
        ap.error("API canary requires explicit --confirm-api-diagnostic-cost")
    if args.confirm_api_diagnostic_cost and not args.api_canary_once:
        ap.error("API cost consent without an explicit canary request is invalid")
    if args.browser_canary_profile != "short" and not args.browser_canary_once:
        ap.error("Source-sized profile requires a fresh explicit browser canary")
    if (args.browser_canary_once or args.api_canary_once
            or args.register_api_capacity_from_canary) and not args.canary_root:
        ap.error("Explicit external LOCALAPPDATA --canary-root required")
    if args.register_api_capacity_from_canary and (
            args.api_canary_once or args.browser_canary_once):
        ap.error("Import capacity evidence separately from new model generation")
    ready = inspect_readiness(
        metadata_probe=args.probe_api_model_metadata_once,
        inspect_gemini_browser=args.inspect_browser)
    browser = api = None
    if args.canary_root:
        root = _local_only(args.canary_root)
        browser = _read(root / "browser_probe_result.json")
        api = _read(root / "api_probe_result.json")
    if args.browser_canary_once:
        browser = run_canary(checkpoint_dir=args.canary_root, backend="browser",
                             profile=args.browser_canary_profile)
    if args.api_canary_once:
        api = run_canary(checkpoint_dir=args.canary_root, backend="api",
                         confirm_api_diagnostic_cost=True)
    capacity_registered = None
    if args.register_api_capacity_from_canary:
        capacity_registered = record_api_capacity(
            canary_root=args.canary_root, folder=args.health_root)
    registered = []
    for trial in args.register_terminal_trial:
        for stage in ("figures", "slides", "narration"):
            receipt = Path(trial) / ("figures_attempt_result.json" if stage == "figures"
                                     else f"stage_{stage}_result.json")
            if receipt.is_file():
                claim = Path(trial) / ("figures_attempt_started.json"
                    if stage == "figures" else f"stage_{stage}_started.json")
                intent = _verified_json(claim)
                backend = intent.get("communication_mode", "selenium")
                registered.append({
                    "trial": Path(trial).name, "stage": stage,
                    **record_stage(trial_dir=trial, stage=stage,
                                   backend=backend, folder=args.health_root)})
    conclusion = classify(
        browser=browser, api=api,
        metadata_reachable=ready.get("api_model_metadata") ==
        "VETTED_MODEL_METADATA_REACHABLE",
        browser_authenticated=(
            ready.get("browser_ui_readiness") == "AUTHENTICATED_COMPOSER_READY"
            if args.inspect_browser else None))
    # Source-independent evidence from the existing immutable attempts.
    # This is read-only, never triggers another model request. It records
    # separately whether local extraction, Chrome attach, and registered send
    # were observed, without claiming Gemini's service was down.
    from .windows_gemini_stage_transport_triage import diagnose
    prior_phase_triage = []
    for trial in args.prior_trial:
        for stage in ("figures", "slides", "narration"):
            name = ("figures_attempt_started.json" if stage == "figures"
                    else f"stage_{stage}_started.json")
            if (Path(trial) / name).exists() or (Path(trial) / name).is_symlink():
                prior_phase_triage.append(diagnose(trial_dir=trial, stage=stage))
    report = {
        "schema_version": 1,
        "readiness": ready,
        "comparison": conclusion,
        "prior_stage_observations": inspect_completed_trials(paths=args.prior_trial),
        "prior_stage_transport_phase_triage": prior_phase_triage,
        "registered_prior_terminal_health": registered,
        "registered_structured_api_capacity": capacity_registered,
        "browser_lane_halt": inspect_halt(folder=args.health_root, backend="selenium"),
        "api_lane_halt": inspect_halt(folder=args.health_root, backend="api"),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
