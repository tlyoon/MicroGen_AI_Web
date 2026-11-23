"""Fail-closed Gemini Selenium recovery controller and durable decision receipts.

Normal transport already performs bounded pre-Send preparation and same-owned-tab
observation. This layer records the independently justified NEXT action once
those mechanisms are exhausted. It never sends, changes model, reads another
user's tab, grants new review identity, or promotes source/academic acceptance.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from .recovery_registry import lookup_mechanism

KIND = "gemini_failure_controller"
SIGNATURE = "GEMINI_SELENIUM_FAILED_REQUEST_NEEDS_DURABLE_SAFE_CONTINUATION"
REPAIR = "CLASSIFY_SOURCE_BOUND_FAILURE_AND_HOLD_UNCERTAIN_SEND_NO_REPLAY"
STAGES = frozenset({
    "figures", "slides", "narration", "rich_mapping", "academic_review",
    "storyboard", "source_review", "code_authoring",
})
PHASE = re.compile(r"[A-Z][A-Z0-9_]{2,95}\Z")
MAX_FILE_BYTES = 300_000_000


def _sha(path: Path) -> str:
    if (not path.is_file() or path.is_symlink()
            or path.stat().st_size > MAX_FILE_BYTES):
        raise ValueError("Unverified request attachment")
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def request_identity(instruction: str, attachments: list[Path]) -> dict:
    """Hash actual original prompt and ordered immutable attached bytes.

    Never persist the prompt, filenames, paths, PDF contents or credentials.
    A missing/swapped attachment fails the complete identity test; never
    substitute a guessed source ID for a missing file.
    """
    if not isinstance(instruction, str) or not isinstance(attachments, list):
        raise ValueError("Invalid source review request")
    if any(not isinstance(p, Path) for p in attachments):
        raise ValueError("Invalid source attachments")
    parts = [hashlib.sha256(instruction.encode("utf8")).hexdigest()]
    parts.extend(_sha(p) for p in attachments)
    canonical = json.dumps(parts, separators=(",", ":"))
    return {
        "request_sha256": hashlib.sha256(canonical.encode("ascii")).hexdigest(),
        "source_identity_verified": True,
        "attachments": len(attachments),
    }


def decide(*, phase: str, possible_send: bool,
           new_turn_verified: bool, attempts_used: int = 0,
           identity_verified: bool = True,
           quarantine: dict | None = None) -> dict:
    """Return actions which DO NOT authorize any additional provider Send."""
    if (type(possible_send) is not bool
            or type(new_turn_verified) is not bool
            or type(identity_verified) is not bool
            or type(attempts_used) is not int or not 0 <= attempts_used <= 3):
        raise ValueError("Untrusted Gemini failure state")
    stage_code = phase if isinstance(phase, str) and PHASE.fullmatch(phase) else "UNCLASSIFIED_FAILURE"
    valid_capture = (isinstance(quarantine, dict)
                     and quarantine.get("status") in {
                         "EMPTY_ORIGINAL_CAPTURE_VERIFIED_NO_REPLAY",
                         "NONEMPTY_UNTRUSTED_CAPTURE_NEEDS_SOURCE_REVIEW",
                     })
    if not identity_verified:
        action = "HOLD_UNVERIFIED_SOURCE_IDENTITY_NO_REPLAY"
    elif possible_send and valid_capture and (
            quarantine["status"] == "EMPTY_ORIGINAL_CAPTURE_VERIFIED_NO_REPLAY"):
        # No bytes exist to reconcile; never keep rediscovering the same
        # impossible recovery as though a usable reply were pending.
        action = "PRESERVE_EMPTY_CAPTURE_ADVANCE_INDEPENDENT_WORK"
    elif possible_send and valid_capture:
        action = "VERIFY_UNTRUSTED_SAVED_CAPTURE_OFFLINE_NO_REPLAY"
    elif possible_send and new_turn_verified:
        action = "OBSERVE_ORIGINAL_OWNED_CONVERSATION_ONLY_NO_REPLAY"
    elif possible_send:
        action = "QUARANTINE_UNKNOWN_SEND_ADVANCE_INDEPENDENT_WORK"
    elif stage_code == "AUTHENTICATION_OR_BROWSER_VERIFICATION_REQUIRED":
        action = "HOLD_FOR_AUTHENTICATED_OWNED_SESSION_NO_SEND"
    else:
        # Existing Selenium prepare_with_bounded_retries has already
        # consumed its finite budget. Never restart the SAME job here.
        action = "REQUALIFY_PRESEND_FOR_FUTURE_DISTINCT_WORK_ONLY"
    return {
        "status": "GEMINI_SELENIUM_FAILURE_RECOVERY_DECISION_V1",
        "failure_phase": stage_code,
        "action": action,
        "possible_provider_submission": possible_send,
        "original_new_user_turn_verified": new_turn_verified,
        "source_identity_verified": identity_verified,
        "presend_prepare_attempts_used": attempts_used,
        "quarantine_capture_status": (
            quarantine.get("status") if isinstance(quarantine, dict) else None),
        "recovered_scientific_response": False,
        "automatic_same_request_retry_authorized": False,
        "new_provider_requests": 0,
        "paid_api_fallback_authorized": False,
        "new_independent_review_identity_authorized": False,
        "academic_scientific_acceptance": False,
        "student_publication_authorized": False,
    }


def persist(*, decision: dict, request_sha256: str, stage: str, port: int,
            root: Path | None = None) -> Path:
    """Idempotent SHA-addressed write-once receipt with interrupted-write repair.

    This only persists a deterministic decision under an existing owner lock;
    the normal browser route already holds the per-port LocalInstanceLock.
    """
    if lookup_mechanism(KIND, SIGNATURE) != REPAIR:
        raise ValueError("Gemini recovery controller not registered")
    if not re.fullmatch("[0-9a-f]{64}", request_sha256):
        raise ValueError("Unverified request fingerprint")
    if (type(port) is not int or not 9222 <= port <= 9323
            or type(stage) is not str):
        raise ValueError("Unverified owned browser stage")
    safe_stage = stage if stage in STAGES else "unspecified"
    if not isinstance(decision, dict) or decision.get("status") != (
            "GEMINI_SELENIUM_FAILURE_RECOVERY_DECISION_V1"):
        raise ValueError("Unverified recovery decision")
    # Re-evaluate the entire safety decision before writing; the caller may
    # not insert retry/approval flags into a fabricated payload.
    expected = decide(
        phase=decision.get("failure_phase"),
        possible_send=decision.get("possible_provider_submission"),
        new_turn_verified=decision.get("original_new_user_turn_verified"),
        attempts_used=decision.get("presend_prepare_attempts_used"),
        identity_verified=decision.get("source_identity_verified"),
        quarantine=({"status": decision["quarantine_capture_status"]}
                    if decision.get("quarantine_capture_status") else None))
    if decision != expected:
        raise ValueError("Recovery decision changed outside its safety rules")
    receipt = {
        "schema_version": 1,
        "stage": safe_stage,
        "port": port,
        "request_sha256": request_sha256,
        **expected,
    }
    serialized = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2)+"\n"
    directory = Path(root or (Path(os.getenv("LOCALAPPDATA") or
                                      (Path.home() / ".cache")) /
                                "Microvid" / "gemini_failure_recovery_v1"))
    if directory.is_symlink():
        raise ValueError("Linked recovery checkpoint directory")
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Unsafe recovery checkpoint directory")
    name = hashlib.sha256(serialized.encode("utf8")).hexdigest()[:32]
    target = directory / (name + ".json")
    staged = directory / (name + ".stage")
    if target.is_symlink() or staged.is_symlink():
        raise ValueError("Linked recovery checkpoint")
    if target.exists():
        if not target.is_file() or target.read_text(encoding="utf8") != serialized:
            raise ValueError("Original recovery receipt mutated")
        return target
    if staged.exists():
        if (not staged.is_file() or
                staged.read_text(encoding="utf8") != serialized):
            raise ValueError("Interrupted recovery stage mutated")
    else:
        with staged.open("x", encoding="utf8") as file:
            file.write(serialized)
            file.flush()
            os.fsync(file.fileno())
    os.replace(staged, target)
    return target


def handle_failed_request(*, instruction: str, attachments: list[Path],
                          phase: str, possible_send: bool,
                          new_turn_verified: bool, attempts_used: int,
                          stage: str, port: int,
                          quarantine_path: Path | None = None,
                          pre_send_request_sha256: str | None = None,
                          root: Path | None = None) -> dict:
    """Entry point for the shared Selenium transport's exceptional exit.

    A bad attachment still produces only a HOLD; never claim identity matches.
    Original exception semantics are preserved by the caller.
    """
    from .historical_quarantine_evidence_v1 import inspect_historical_quarantine
    try:
        identity = request_identity(instruction, attachments)
    except (ValueError, OSError, UnicodeError):
        identity = {
            "request_sha256": hashlib.sha256(
                ("unverified-attachments:" +
                 hashlib.sha256(instruction.encode("utf8")).hexdigest())
                .encode("ascii")).hexdigest(),
            "source_identity_verified": False,
        }
    # A post-Send file change must never masquerade as the bytes present
    # immediately before the original click. Pre-Send failures may safely
    # identify their current source inputs without that extra comparison.
    if possible_send:
        original_sha = (
            pre_send_request_sha256
            if isinstance(pre_send_request_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", pre_send_request_sha256)
            else None)
        identity["source_identity_verified"] = bool(
            identity["source_identity_verified"]
            and original_sha is not None
            and identity["request_sha256"] == original_sha)
        # If files changed after the click, preserve the actual original
        # pre-Send fingerprint rather than mislabeling the changed input as
        # the possible provider submission. Still fail closed.
        if original_sha is not None:
            identity["request_sha256"] = original_sha
    evidence = (inspect_historical_quarantine(
        "untrusted response quarantined at " + str(quarantine_path))
        if quarantine_path is not None else None)
    decision = decide(
        phase=phase, possible_send=possible_send,
        new_turn_verified=new_turn_verified, attempts_used=attempts_used,
        identity_verified=identity["source_identity_verified"],
        quarantine=evidence)
    output = persist(decision=decision,
                     request_sha256=identity["request_sha256"],
                     stage=stage, port=port, root=root)
    return {
        "action": decision["action"], "receipt": str(output),
        "possible_provider_submission": possible_send,
        "new_provider_requests": 0,
        "retry_authorized": False,
        "scientific_acceptance": False,
        "student_publication_authorized": False,
    }
