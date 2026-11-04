"""Append-only, cross-task native Windows Gemini health and halt policy.

Only accepted original-source stage RECEIPTS may contribute health evidence.
A browser send with no accepted output is not proof of Gemini downtime.
Pausing NEW tasks never resends or revives an earlier ambiguous request.
Existing capacity (verified 429/503) and source-specific QA stay independent.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import time

from .original_multisource_recovery_campaign import _verified_json, _encode

HEALTH_FOLDER_NAME = "MicroGen_AI_Web_Gemini_Transport_Health"
WINDOW_SECONDS = 3600
THRESHOLD = 2
COOLDOWN_SECONDS = 1800
VALID_STAGES = frozenset(("figures", "slides", "narration"))
VALID_BACKENDS = frozenset(("selenium", "api"))
ACCEPTED = frozenset(("FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE",
                      "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND"))
FAILED = frozenset(("FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY",
                    "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY",
                    "FIGURES_EXECUTION_ERROR_NO_AUTO_RETRY",
                    "STAGE_FAILED_OR_OUTPUT_INCOMPLETE_NO_RETRY",
                    "STAGE_TIMEOUT_UNKNOWN_PROVIDER_SEND_NO_RETRY",
                    "STAGE_PROCESS_ERROR_NO_RETRY"))
# Only the shared vendor's positive submission evidence is counted; string
# matching on a user prompt, response, or a generic timeout is not reliable.
_SEND_PROOF = re.compile(
    r"(?m)^\s*(?:\[[^\r\n]+\]\s*)?\[INFO\]\s+"
    r"(?:Gemini submission registered via new-user-turn\+composer-cleared\.|"
    r"\[SEND-VERIFY\] exact DOM Send message click registered\.)"
)


def _root(folder: Path | None) -> Path:
    if folder is None:
        local = os.getenv("LOCALAPPDATA")
        if not local:
            raise ValueError("Native Windows LOCALAPPDATA required")
        folder = Path(local) / HEALTH_FOLDER_NAME
    p = Path(folder).absolute()
    if p.is_symlink() or (p.exists() and not p.is_dir()):
        raise ValueError("Unsafe shared Gemini health directory")
    return p


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _events(folder: Path) -> list[dict]:
    folder = _root(folder)
    if not folder.exists():
        return []
    directory = folder / "events"
    if not directory.exists():
        return []
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("Unsafe Gemini event directory")
    files = list(directory.iterdir())
    if len(files) > 2000:
        raise ValueError("Oversized Gemini event history needs offline archival")
    events = []
    for path in files:
        if path.suffix != ".json" or path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
            raise ValueError("Untrusted Gemini event record")
        item = _verified_json(path)
        stable_key = (str(item.get("source_sha256")) + "|" +
                      str(item.get("stage")) + "|" +
                      str(item.get("backend")) + "|" +
                      str(item.get("result_sha256")))
        required_filename = hashlib.sha256(stable_key.encode("ascii")).hexdigest()
        if (path.stem != required_filename
                or item.get("original_request_may_not_be_resent") is not True
                or item.get("provider_server_failure_proven") is not False):
            raise ValueError("Provider event identity or no-resend invariant failed")
        if (item.get("schema_version") != 1
                or item.get("stage") not in VALID_STAGES
                or item.get("backend") not in VALID_BACKENDS
                or item.get("outcome") not in
                    ("ACCEPTED", "SENT_BUT_NOT_ACCEPTED", "UNKNOWN_SUBMISSION")
                or type(item.get("observed_unix")) not in (int, float)
                or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("source_sha256", "")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(item.get("result_sha256", "")))
                or item.get("student_publication_authorized") is not False):
            raise ValueError("Untrusted Gemini stage evidence")
        events.append(item)
    return events


def inspect_halt(*, folder: Path | None = None, backend: str = "selenium",
                 now: float | None = None, threshold: int = THRESHOLD,
                 cooldown_seconds: int = COOLDOWN_SECONDS) -> dict:
    if backend not in VALID_BACKENDS or type(threshold) is not int or threshold < 2:
        raise ValueError("Supported provider and minimum failure count required")
    if type(cooldown_seconds) is not int or not 60 <= cooldown_seconds <= 86400:
        raise ValueError("Finite 60-86400s cooldown required")
    now = float(time.time() if now is None else now)
    recent = [x for x in _events(_root(folder))
              if x["backend"] == backend
              and 0 <= now - x["observed_unix"] <= WINDOW_SECONDS]
    recent.sort(key=lambda x: x["observed_unix"])
    last_good = max((x["observed_unix"] for x in recent
                     if x["outcome"] == "ACCEPTED"), default=-1.)
    unresolved = [x for x in recent
                  if x["outcome"] == "SENT_BUT_NOT_ACCEPTED"
                  and x["observed_unix"] > last_good]
    last_failure = max((x["observed_unix"] for x in unresolved), default=None)
    pause_until = (last_failure + cooldown_seconds
                   if len(unresolved) >= threshold and last_failure is not None
                   else None)
    paused = pause_until is not None and now < pause_until
    return {
        "schema_version": 1,
        "status": "HALT_NEW_GEMINI_TASKS" if paused else "NO_PROVIDER_HALT",
        "backend": backend,
        "sent_but_unaccepted_after_last_success": len(unresolved),
        "new_generation_dispatch_allowed_by_health_policy": not paused,
        "paused_until_unix_utc": pause_until if paused else None,
        "time_expiration_is_not_permission_to_retry_old_request": True,
        "provider_server_failure_proven": False,
        "existing_ambiguous_source_resubmission_authorized": False,
        "new_api_billing_authorized": False,
        "student_publication_authorized": False,
    }


def record_stage(*, trial_dir: Path, stage: str,
                 backend: str = "selenium", folder: Path | None = None,
                 now: float | None = None) -> dict:
    """Record exactly one immutable terminal stage, never a request itself."""
    if stage not in VALID_STAGES or backend not in VALID_BACKENDS:
        raise ValueError("No Gemini content task to observe")
    trial = Path(trial_dir).absolute()
    if not trial.is_dir() or trial.is_symlink():
        raise ValueError("No trusted immutable original-source trial")
    result_name = ("figures_attempt_result.json" if stage == "figures"
                   else "stage_" + stage + "_result.json")
    result_path = trial / result_name
    item = _verified_json(result_path)
    status = item.get("status")
    if status not in ACCEPTED | FAILED:
        raise ValueError("Not a terminal original-source stage receipt")
    contract = _verified_json(trial / "fresh_trial_contract.json")
    source_sha = contract.get("source_sha256")
    claim_file = (trial / "figures_attempt_started.json" if stage == "figures"
                  else trial / ("stage_" + stage + "_started.json"))
    claim = _verified_json(claim_file)
    actual_backend = claim.get("communication_mode", "selenium")
    if (claim.get("stage") != stage
            or claim.get("source_sha256") != source_sha
            or actual_backend not in VALID_BACKENDS
            or backend != actual_backend
            or (actual_backend == "api" and
                claim.get("paid_content_api_explicitly_authorized") is not True)):
        raise ValueError("Stage's authentic provider send intent does not match this lane")
    if (not re.fullmatch(r"[0-9a-f]{64}", str(source_sha))
        or (item.get("original_source_sha256") if stage == "figures"
            else item.get("source_sha256")) != source_sha
        or item.get("student_publication_authorized") is not False):
        raise ValueError("Stage source does not match immutable original receipt")
    # Never infer that the API definitively sent a request merely from a
    # timeout. Actual browser proof is the trusted owned-client log marker.
    log_name = ("figures_stage_stdout.raw.log" if stage == "figures"
                else "stage_" + stage + "_stdout.raw.log")
    log = trial / log_name
    if (not log.is_file() or log.is_symlink()
        or log.stat().st_size > 4_000_000):
        raise ValueError("Missing or unbounded original owned-stage raw log")
    raw = log.read_text(encoding="utf8", errors="replace")
    registered = (bool(_SEND_PROOF.search(raw))
                  if backend == "selenium" else False)
    category = ("ACCEPTED" if status in ACCEPTED
                else "SENT_BUT_NOT_ACCEPTED" if registered
                else "UNKNOWN_SUBMISSION")
    result_sha = _hash(result_path)
    original_key = f"{source_sha}|{stage}|{backend}|{result_sha}"
    key = hashlib.sha256(original_key.encode("ascii")).hexdigest()
    # Historical source attempts retain their actual terminal time: merely
    # importing old evidence today must not create a false new outage.
    at = float(result_path.stat().st_mtime if now is None else now)
    payload = {
        "schema_version": 1, "backend": backend, "stage": stage,
        "source_sha256": source_sha, "result_sha256": result_sha,
        "stage_result_status": status,
        "owned_browser_send_registered": registered,
        "outcome": category, "observed_unix": at,
        "provider_server_failure_proven": False,
        "original_request_may_not_be_resent": True,
        "student_publication_authorized": False,
    }
    folder = _root(folder)
    folder.mkdir(parents=True, exist_ok=True)
    directory = folder / "events"
    directory.mkdir(exist_ok=True)
    if folder.is_symlink() or directory.is_symlink():
        raise ValueError("Unsafe Gemini events folder")
    dest = directory / (key + ".json")
    if dest.exists() or dest.is_symlink():
        old = _verified_json(dest)
        if (old.get("source_sha256") != source_sha
            or old.get("result_sha256") != result_sha
            or old.get("backend") != backend
            or old.get("stage") != stage):
            raise ValueError("Immutable provider event conflict")
        return {"status": "PRIOR_STAGE_HEALTH_REUSED", "outcome": old["outcome"],
                "new_model_requests": 0}
    # Exclusive create: a second concurrent worker cannot overwrite the
    # first event, and bytes match the existing strict canonical decoder.
    with dest.open("x", encoding="utf8", newline="\n") as stream:
        stream.write(_encode(payload))
        stream.flush()
        os.fsync(stream.fileno())
    return {"status": "ORIGINAL_STAGE_HEALTH_RECORDED",
            "outcome": category, "new_model_requests": 0}


def inspect_completed_trials(*, paths: list[Path],
                             now: float | None = None) -> list[dict]:
    """Read-only diagnostics from prior tasks, without touching health state."""
    outcomes = []
    for directory in paths:
        d = Path(directory).absolute()
        for stage in VALID_STAGES:
            result_path = d / ("figures_attempt_result.json" if stage == "figures"
                               else f"stage_{stage}_result.json")
            if not result_path.is_file():
                continue
            item = _verified_json(result_path)
            log_path = d / ("figures_stage_stdout.raw.log" if stage == "figures"
                            else f"stage_{stage}_stdout.raw.log")
            if not log_path.is_file() or log_path.stat().st_size > 4_000_000:
                continue
            registered = bool(_SEND_PROOF.search(
                log_path.read_text(encoding="utf8", errors="replace")))
            outcomes.append({
                "trial": d.name, "stage": stage,
                "status": item.get("status"),
                "browser_send_registered": registered,
                "accepted_output": item.get("status") in ACCEPTED,
                "gemini_outage_proven": False,
                "no_automatic_resend": True,
            })
    return outcomes
