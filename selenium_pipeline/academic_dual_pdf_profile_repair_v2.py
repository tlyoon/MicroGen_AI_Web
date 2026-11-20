"""Exactly one NEW two-PDF modality experiment after a distinct browser-profile repair.

This is NOT a retry of v1 or a source-textbook send. The v1 claim/result stays
untouched. A unique pair of synthetic PDFs and a new once-ever claim test the
repaired, authenticated Pro/Medium owned Chrome path. No success is assumed.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import re
import time

from .academic_dual_pdf_capability import (
    _sha, _new, _load, _exact, _create_pdf, _verify_unsafe_source_claims,
    existing_outcome as v1_outcome, ROOT as V1_ROOT,
)
from .academic_provider_requalification import _REGISTERED
from .figure_source_identity import require

ROOT = ".microgen_g2_dual_pdf_after_profile_repair_v2"
SIGNATURE = "SYNTHETIC_DUAL_PDF_AFTER_VERIFIED_PRIMARY_PROFILE_REPAIR"
MECHANISM = "ONE_FRESH_TWO_PDF_OWNED_READBACK_AFTER_DISTINCT_PROFILE_REPAIR"
SENTINEL = "MicroGen-Profile-Repaired-Independent-TwoPDF-v2"


def _prior(*, queue_root, checkpoint_parent, source_sha, prior_slides, family):
    require(family == "pro", "Profile-repair diagnostic is Pro/Medium only")
    prior = v1_outcome(queue_root=queue_root, checkpoint_parent=checkpoint_parent,
                       source_sha=source_sha, prior_slides=prior_slides, family=family)
    require(prior is not None
            and prior.get("status") == "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED"
            and prior.get("new_source_review_send_allowed") is False
            and prior.get("new_provider_requests") == 0,
            "Retired unsuccessful v1 incident required; never replay v1")
    incident, last_source = _verify_unsafe_source_claims(
        queue_root=queue_root, source_sha=source_sha,
        prior_slides=prior_slides, family=family)
    from .recovery_registry import lookup_mechanism
    require(lookup_mechanism("selection_action", SIGNATURE) == MECHANISM,
            "Versioned post-repair PDF experiment is not registered")
    # Tie v2 to the exact result bytes of v1; do not reset a failed budget by
    # changing the day or merely creating an arbitrary new incident identifier.
    v1_result = (Path(checkpoint_parent) / V1_ROOT / source_sha /
                 family / incident / "result.json")
    require(v1_result.is_file() and not v1_result.is_symlink(),
            "Prior one-shot PDF result must be immutable")
    return incident, last_source, _sha(v1_result.read_bytes())


def _home(parent, source_sha, family, incident):
    home = Path(parent).absolute() / ROOT / source_sha / family / incident
    require(not any(p.is_symlink() for p in [home, *list(home.parents)[:4]]),
            "Linked v2 provider receipt directories forbidden")
    return home


def _expected(source_sha, family, incident, prior_result_sha):
    salt = f"{SENTINEL}|{source_sha}|{family}|{incident}|{prior_result_sha}"
    v = lambda suffix: hashlib.sha256((salt + "|" + suffix).encode("ascii")).hexdigest()
    return {"probe": v("nonce")[:18],
            "a": v("SyntheticA")[:18].upper(),
            "b": v("SyntheticB")[:18].upper()}


def _prompt(probe):
    return (
        "Independent MicroGen browser-profile-repair transport diagnostic. "
        "These two attachments are NEW, synthetically generated one-page PDFs "
        "and contain NO textbook or user source text. Read BOTH files. Extract "
        "the PDF_CODE from SyntheticA.pdf and SyntheticB.pdf separately, and "
        "return only strict JSON with exact keys probe, a, b: "
        '{"probe":"' + probe + '","a":"<code from A>","b":"<code from B>"}. '
        "If either file is not readable, answer with an error instead. "
        "Do not guess. Do not add markdown."
    )


def _read(*, queue_root, checkpoint_parent, source_sha, prior_slides, family):
    incident, last_source, prior_hash = _prior(
        queue_root=queue_root, checkpoint_parent=checkpoint_parent,
        source_sha=source_sha, prior_slides=prior_slides, family=family)
    home = _home(checkpoint_parent, source_sha, family, incident)
    if not home.exists():
        return None, (incident, last_source, prior_hash, home)
    require(home.is_dir() and not home.is_symlink(), "Invalid existing v2 claim")
    claim_file, result_file = home / "claim.json", home / "result.json"
    require(claim_file.is_file() and not claim_file.is_symlink(),
            "Incomplete v2 claim is never replayable")
    claim = _load(claim_file)
    expected = _expected(source_sha, family, incident, prior_hash)
    require(claim.get("schema_version") == 1
            and claim.get("source_sha256") == source_sha
            and claim.get("model_family") == family
            and claim.get("incident_sha256") == incident
            and claim.get("v1_result_sha256") == prior_hash
            and claim.get("last_uncertain_claim_unix") == last_source
            and claim.get("prompt_sha256") == _sha(_prompt(expected["probe"]).encode())
            and claim.get("original_source_uploaded") is False
            and claim.get("one_send_only") is True
            and claim.get("repair_signature") == SIGNATURE
            and claim.get("two_synthetic_pdf_attachments") is True
            and claim.get("claimed_unix", 0) > last_source,
            "Mismatched v2 source, incident or prior failed probe")
    for letter in ("a", "b"):
        file = home / ("SyntheticA.pdf" if letter == "a" else "SyntheticB.pdf")
        require(file.is_file() and not file.is_symlink()
                and _sha(file.read_bytes()) == claim["pdf_" + letter + "_sha256"],
                "Synthetic attachment identity has changed")
    if not result_file.exists():
        return {"status": "PRIOR_REPAIRED_PDF_SEND_UNCERTAIN_NO_RESEND",
                "new_provider_requests": 0,
                "new_source_review_send_allowed": False}, (incident, last_source, prior_hash, home)
    receipt = _load(result_file)
    require(receipt.get("claim_sha256") == _sha(claim_file.read_bytes())
            and receipt.get("v1_result_sha256") == prior_hash
            and receipt.get("source_sha256") == source_sha
            and receipt.get("incident_sha256") == incident
            and receipt.get("model_family") == family
            and receipt.get("original_source_uploaded") is False
            and receipt.get("academic_approval") is False
            and receipt.get("paid_operations_authorized") is False
            and receipt.get("observed_unix", 0) >= claim["claimed_unix"],
            "Forged or stale profile-repair modality receipt")
    success = receipt.get("status") == "DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED"
    require((success and receipt.get("model_response_json") == expected
             and receipt.get("gemini_new_user_turn_verified") is True
             and receipt.get("send_registration_status") in _REGISTERED)
            or (not success and
                receipt.get("status") == "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED"
                and receipt.get("model_response_json") is None
                and receipt.get("gemini_new_user_turn_verified") is False),
            "Untrusted or unowned v2 PDF result cannot qualify")
    return {**receipt, "new_provider_requests": 0,
            "new_source_review_send_allowed": success}, (incident, last_source, prior_hash, home)


def existing_outcome(**kw):
    return _read(**kw)[0]


def qualifying_proof(*, now=None, **kw):
    # The source-review health gate supplies a fixed observation clock.
    # Look for a real v2 claim FIRST: legacy v1-only incidents must return
    # None, not be promoted or rejected by an unrelated v2 inspection.
    incident, _ = _verify_unsafe_source_claims(
        queue_root=kw["queue_root"],source_sha=kw["source_sha"],
        prior_slides=kw["prior_slides"],family=kw["family"])
    home=_home(kw["checkpoint_parent"],kw["source_sha"],
               kw["family"],incident)
    if not home.exists():
        return None
    evidence, _ = _read(**kw)
    if (evidence is None or evidence.get("new_source_review_send_allowed") is not True):
        return None
    if now is not None and (type(now) not in (int,float)
                            or evidence["observed_unix"] > float(now)+3):
        return None
    return evidence


def newly_eligible(**kw) -> bool:
    evidence, _ = _read(**kw)
    return evidence is None


def probe_once(*, queue_root, checkpoint_parent, source_sha, prior_slides,
               family, transport=None):
    evidence, details = _read(
        queue_root=queue_root, checkpoint_parent=checkpoint_parent,
        source_sha=source_sha, prior_slides=prior_slides, family=family)
    if evidence is not None:
        return evidence
    incident, last_source, prior_hash, home = details
    require(time.time() > last_source, "Invalid source-claim chronology")
    if transport is None:
        # No claim consumed if authenticated Pro/Medium cannot be positively
        # verified on the PRIMARY owned session before a provider Send.
        from .academic_queue_fresh_send_health import _full_family_scope
        from .academic_gemini_presend_preflight import select_ready_existing_session
        try:
            with _full_family_scope(family):
                presend = select_ready_existing_session(
                    primary_port=9222, allow_active_alternate=False)
            require(presend.get("verified_port") == 9222
                    and presend.get("model_family") == "pro"
                    and presend.get("thinking_level") == "medium"
                    and presend.get("gemini_requests_submitted") == 0
                    and presend.get("files_uploaded") == 0,
                    "Current primary Pro/Medium transport unverified")
        except Exception:
            return {"status": "REPAIRED_PRIMARY_PRESEND_UNVERIFIED_NO_CLAIM",
                    "new_source_review_send_allowed": False,
                    "new_provider_requests": 0}
    # One exclusive immutable claim per exact prior original incident.
    home.mkdir(parents=True, exist_ok=False)
    expected = _expected(source_sha, family, incident, prior_hash)
    a, b = home / "SyntheticA.pdf", home / "SyntheticB.pdf"
    a_sha = _create_pdf(a, expected["a"], "A")
    b_sha = _create_pdf(b, expected["b"], "B")
    prompt = _prompt(expected["probe"])
    require(expected["a"] not in prompt and expected["b"] not in prompt,
            "Synthetic PDF secrets cannot appear in prompt")
    claimed = time.time()
    _new(home / "claim.json", {
        "schema_version": 1, "source_sha256": source_sha,
        "model_family": family, "incident_sha256": incident,
        "v1_result_sha256": prior_hash,
        "last_uncertain_claim_unix": last_source,
        "repair_signature": SIGNATURE, "claimed_unix": claimed,
        "prompt_sha256": _sha(prompt.encode()),
        "pdf_a_sha256": a_sha, "pdf_b_sha256": b_sha,
        "original_source_uploaded": False,
        "two_synthetic_pdf_attachments": True, "one_send_only": True})
    valid, registration, error = False, None, None
    try:
        if transport is None:
            from .academic_queue_fresh_send_health import _full_family_scope
            from .series_gemini import _browser_request
            with _full_family_scope(family):
                response = _browser_request(
                    prompt, [a, b], port=9222, wait_cap_s=160,
                    min_chars=20, accept_fn=lambda s: _exact(s, expected))
        else:
            response = transport(prompt, [a, b])
        from .series_gemini import OwnedGeminiResponse
        valid = (isinstance(response, OwnedGeminiResponse)
                 and response.gemini_new_user_turn_verified is True
                 and response.gemini_send_registration_status in _REGISTERED
                 and _exact(str(response), expected))
        if valid:
            registration = response.gemini_send_registration_status
    except Exception as exc:
        error = type(exc).__name__
    receipt = {"schema_version": 1, "claim_sha256": _sha(
                   (home / "claim.json").read_bytes()),
               "v1_result_sha256": prior_hash, "source_sha256": source_sha,
               "incident_sha256": incident, "model_family": family,
               "observed_unix": time.time(),
               "status": ("DUAL_SYNTHETIC_PDF_RESPONSE_VERIFIED" if valid else
                          "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED"),
               "send_registration_status": registration,
               "gemini_new_user_turn_verified": valid,
               "model_response_json": expected if valid else None,
               "error_type": error, "original_source_uploaded": False,
               "academic_approval": False, "paid_operations_authorized": False}
    _new(home / "result.json", receipt)
    result, _ = _read(
        queue_root=queue_root, checkpoint_parent=checkpoint_parent,
        source_sha=source_sha, prior_slides=prior_slides, family=family)
    require(result is not None, "Missing newly persisted v2 outcome")
    return {**result, "new_provider_requests": 1}
