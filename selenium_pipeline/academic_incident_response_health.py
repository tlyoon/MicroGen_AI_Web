"""Source-free, incident-scoped Gemini recovery after newer uncertain source Sends.

An older successful daily diagnostic does NOT unblock a source request claimed
after that diagnostic. Instead, a NEW incident gets a distinct nonce, once per
attempt; two probes/day maximum across incidents, with an inter-probe cooldown.
The exact original academic request is never replayed. All proof is stored
outside the publisher/source/queue and every result is verified before reuse.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import time
from datetime import datetime, timezone

from .academic_provider_requalification import (
    AcademicProbeError, _REGISTERED, _is_exact,
)

ROOT = ".microgen_g2_incident_response_health_v2"
MAX_PROBES_PER_UTC_DAY = 2
MIN_PROBE_SPACING_SECONDS = 900
MAX_FILE_BYTES = 4096


def _must(ok, reason):
    if not ok:
        raise AcademicProbeError(reason)


def incident_identity(claim: dict, *, source_sha: str, family: str) -> str:
    """Tie a diagnostic to the newest *different* immutable academic claim."""
    _must(re.fullmatch(r"[0-9a-f]{64}", source_sha) is not None
          and family in ("flash", "pro")
          and re.fullmatch(r"[0-9a-f]{64}", claim["request_fingerprint"]) is not None
          and re.fullmatch(
              r"slide_[0-9]{3}_(?:initial_review|independent_challenge)_attempt_0[1-3]_request",
              claim["checkpoint_name"]) is not None,
          "Unsafe original academic health incident identity")
    raw = "|".join([source_sha, family, claim["checkpoint_name"],
                    claim["request_fingerprint"]])
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _scope(parent: Path, source_sha: str, family: str) -> Path:
    parent = Path(parent).absolute()
    _must(parent.is_dir() and not parent.is_symlink()
          and re.fullmatch(r"[0-9a-f]{64}", source_sha) is not None
          and family in ("flash", "pro"),
          "Invalid incident diagnostic parent/source/family")
    root = parent / ROOT
    scoped = root / source_sha / family
    _must(not root.is_symlink() and not scoped.is_symlink()
          and not scoped.parent.is_symlink(),
          "Linked incident health history")
    return scoped


def _day(now: float) -> str:
    _must(type(now) in (float, int) and 0 <= now <= 4102444800,
          "Invalid diagnostic time")
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y%m%d")


def _expected(source_sha: str, family: str, incident: str,
              day: str, ordinal: int):
    seed = f"microgen-g2-incident-health-v2:{source_sha}:{family}:{incident}:{day}:{ordinal}"
    nonce = hashlib.sha256(seed.encode("ascii")).hexdigest()[:20]
    prompt = (
        "MicroGen Gemini browser transport check. This synthetic request "
        "contains no lecture, source PDF, scientific question or attachments. "
        "Return precisely this JSON and nothing else: "
        + json.dumps({"microgen_health": "ok", "nonce": nonce},
                     sort_keys=True, separators=(",", ":"))
    )
    return prompt, nonce


def _read(path: Path) -> dict:
    _must(path.is_file() and not path.is_symlink()
          and 0 < path.stat().st_size <= MAX_FILE_BYTES,
          "Missing, linked or oversized incident diagnostic receipt")
    obj = json.loads(path.read_text(encoding="utf8"))
    _must(type(obj) is dict and obj.get("schema_version") == 2,
          "Invalid incident diagnostic receipt version")
    return obj


def _sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slot(scoped: Path, incident: str, day: str, ordinal: int) -> Path:
    _must(re.fullmatch(r"[0-9a-f]{64}", incident) is not None
          and re.fullmatch(r"20[0-9]{6}", day) is not None
          and 1 <= ordinal <= MAX_PROBES_PER_UTC_DAY,
          "Invalid incident diagnostic slot")
    slot = scoped / day / incident / f"attempt_{ordinal:02d}"
    _must(not slot.is_symlink() and not slot.parent.is_symlink()
          and not slot.parent.parent.is_symlink(),
          "Linked incident diagnostic slot")
    return slot


def verify_result(*, checkpoint_parent: Path, source_sha: str,
                  family: str, incident: str, path: Path) -> dict:
    scoped = _scope(checkpoint_parent, source_sha, family)
    path = Path(path).absolute()
    _must(path.name == "result.json"
          and path.is_relative_to(scoped)
          and len(path.relative_to(scoped).parts) == 4,
          "Unrelated diagnostic proof path")
    day, actual_incident, attempt_name, _ = path.relative_to(scoped).parts
    _must(actual_incident == incident
          and re.fullmatch(r"attempt_0[12]", attempt_name) is not None,
          "Incident diagnostic proof identity mismatch")
    ordinal = int(attempt_name[-2:])
    claim_path = path.parent / "claim.json"
    claim = _read(claim_path)
    receipt = _read(path)
    prompt, nonce = _expected(source_sha, family, incident, day, ordinal)
    _must(claim.get("source_sha256") == source_sha
          and claim.get("model_family") == family
          and claim.get("incident_sha256") == incident
          and claim.get("utc_day") == day
          and claim.get("attempt") == ordinal
          and claim.get("thinking_level") == "medium"
          and claim.get("no_source_attached") is True
          and claim.get("academic_request_replayed") is False
          and claim.get("prompt_sha256") ==
              hashlib.sha256(prompt.encode("utf8")).hexdigest()
          and type(claim.get("last_uncertain_source_claim_unix")) in (float, int)
          and receipt.get("source_sha256") == source_sha
          and receipt.get("model_family") == family
          and receipt.get("incident_sha256") == incident
          and receipt.get("utc_day") == day
          and receipt.get("attempt") == ordinal
          and receipt.get("claim_sha256") == _sha(claim_path)
          and receipt.get("thinking_level") == "medium"
          and receipt.get("no_original_source_uploaded") is True
          and receipt.get("G2_approved") is False
          and receipt.get("student_publication_authorized") is False
          and receipt.get("model_sends_possible") == 1
          and type(receipt.get("observed_unix")) in (float, int)
          and claim["last_uncertain_source_claim_unix"] < receipt["observed_unix"]
          and receipt["observed_unix"] <= 4102444800,
          "Incident health receipt/claim unverified or stale")
    if receipt.get("status") == "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED":
        _must(receipt.get("gemini_new_user_turn_verified") is True
              and receipt.get("gemini_send_registration_status") in _REGISTERED
              and _is_exact(receipt.get("response_text"), nonce),
              "No attributable synthetic model response")
    else:
        _must(receipt.get("status") == "NO_VERIFIED_SOURCE_FREE_RESPONSE"
              and receipt.get("response_text") is None
              and receipt.get("gemini_new_user_turn_verified") is False,
              "Unknown incident health status")
    return receipt


def latest_incident_success(*, checkpoint_parent: Path, source_sha: str,
                            family: str, incident: str, after_unix: float,
                            now: float) -> dict | None:
    scoped = _scope(checkpoint_parent, source_sha, family)
    if not scoped.exists():
        return None
    _must(scoped.is_dir() and not scoped.is_symlink(), "Invalid health history")
    results = list(scoped.glob(f"*/{incident}/attempt_*/result.json"))
    _must(len(results) <= 800, "Unbounded diagnostic evidence")
    verified = [verify_result(checkpoint_parent=checkpoint_parent,
                              source_sha=source_sha, family=family,
                              incident=incident, path=path)
                for path in results]
    valid = [r for r in verified if
             r["status"] == "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"
             and after_unix < r["observed_unix"] <= now]
    return max(valid, key=lambda r: r["observed_unix"]) if valid else None


def probe_incident_once(*, checkpoint_parent: Path, source_sha: str,
                        family: str, incident: str, after_unix: float,
                        now: float | None = None, chrome_port: int = 9222,
                        browser_request=None) -> dict:
    """One NEW nonce only when the finite daily budget and cooldown permit."""
    instant = float(time.time() if now is None else now)
    _must(type(chrome_port) is int and 1 <= chrome_port <= 65535
          and after_unix < instant
          and os.getenv("MICROGEN_GEMINI_UI_MODE", "").lower() == family
          and os.getenv("MICROGEN_GEMINI_THINKING_LEVEL", "").lower() == "medium",
          "Incident diagnostic model, time or Gemini port not verified")
    scoped = _scope(checkpoint_parent, source_sha, family)
    _must(re.fullmatch(r"[0-9a-f]{64}", incident) is not None,
          "Invalid incident identity")
    # Direct callers are also restart-idempotent: a previous successful
    # immutable incident response is reused rather than starting a new probe.
    previous_good = latest_incident_success(
        checkpoint_parent=checkpoint_parent, source_sha=source_sha,
        family=family, incident=incident, after_unix=after_unix, now=instant)
    if previous_good is not None:
        return {**previous_good, "reused_immutable_probe": True,
                "new_provider_requests": 0}
    day = _day(instant)
    today = scoped / day
    _must(not today.is_symlink(), "Unsafe health day")
    if today.exists():
        _must(today.is_dir(), "Invalid health day")
    claims = sorted(today.glob("*/attempt_*/claim.json"))
    _must(len(claims) <= MAX_PROBES_PER_UTC_DAY,
          "Diagnostic daily budget exceeded")
    prior = []
    for claim_path in claims:
        c = _read(claim_path)
        _must(c.get("source_sha256") == source_sha
              and c.get("model_family") == family
              and c.get("utc_day") == day
              and c.get("attempt") in (1, 2),
              "Foreign or modified incident diagnostic")
        result_path = claim_path.parent / "result.json"
        if result_path.exists():
            verified = verify_result(checkpoint_parent=checkpoint_parent,
                source_sha=source_sha, family=family,
                incident=c["incident_sha256"], path=result_path)
            prior.append(verified["observed_unix"])
        else:
            prior.append(c["claimed_unix"])
    if claims and instant - max(prior) < MIN_PROBE_SPACING_SECONDS:
        return {"status": "INCIDENT_SOURCE_FREE_PROBE_COOLDOWN",
                "new_provider_requests": 0, "new_source_review_send_allowed": False}
    this_incident = [c for c in claims
                     if c.parent.parent.name == incident]
    if len(claims) >= MAX_PROBES_PER_UTC_DAY:
        return {"status": "INCIDENT_DAILY_DIAGNOSTIC_BUDGET_EXHAUSTED",
                "new_provider_requests": 0, "new_source_review_send_allowed": False}
    ordinal = len(this_incident) + 1
    slot = _slot(scoped, incident, day, ordinal)
    _must(not slot.exists() and not slot.is_symlink(),
          "Untracked incident diagnostic attempt")
    slot.mkdir(parents=True)
    prompt, nonce = _expected(source_sha, family, incident, day, ordinal)
    claim = {
        "schema_version": 2, "source_sha256": source_sha,
        "model_family": family, "thinking_level": "medium",
        "incident_sha256": incident, "utc_day": day,
        "attempt": ordinal, "claimed_unix": instant,
        "last_uncertain_source_claim_unix": after_unix,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf8")).hexdigest(),
        "no_source_attached": True, "academic_request_replayed": False,
    }
    claim_path = slot / "claim.json"
    with claim_path.open("x", encoding="utf8") as out:
        json.dump(claim, out, sort_keys=True, indent=2)
        out.write("\n"); out.flush(); os.fsync(out.fileno())
    response = None
    registered = None
    error_type = None
    try:
        if browser_request is None:
            from .series_gemini import _browser_request
            received = _browser_request(prompt, [], port=chrome_port,
                     wait_cap_s=90, min_chars=16,
                     accept_fn=lambda s: _is_exact(s, nonce))
        else:
            received = browser_request(prompt, chrome_port)
        from .series_gemini import OwnedGeminiResponse
        _must(isinstance(received, OwnedGeminiResponse)
              and received.gemini_new_user_turn_verified is True
              and received.gemini_send_registration_status in _REGISTERED
              and _is_exact(str(received), nonce),
              "Unattributable Gemini diagnostic output")
        response = str(received)
        registered = received.gemini_send_registration_status
    except Exception as exc:
        error_type = type(exc).__name__
    observed = float(time.time() if now is None else instant + 0.01)
    receipt = {
        "schema_version": 2, "source_sha256": source_sha,
        "model_family": family, "thinking_level": "medium",
        "incident_sha256": incident, "utc_day": day,
        "attempt": ordinal, "claim_sha256": _sha(claim_path),
        "observed_unix": observed,
        "status": ("SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"
                   if response is not None else "NO_VERIFIED_SOURCE_FREE_RESPONSE"),
        "response_text": response,
        "gemini_new_user_turn_verified": response is not None,
        "gemini_send_registration_status": registered,
        "model_sends_possible": 1, "new_provider_requests": 1,
        "no_original_source_uploaded": True,
        "error_type": error_type, "G2_approved": False,
        "student_publication_authorized": False,
    }
    with (slot / "result.json").open("x", encoding="utf8") as out:
        json.dump(receipt, out, sort_keys=True, indent=2)
        out.write("\n"); out.flush(); os.fsync(out.fileno())
    return verify_result(checkpoint_parent=checkpoint_parent,
                         source_sha=source_sha, family=family,
                         incident=incident, path=slot / "result.json")
