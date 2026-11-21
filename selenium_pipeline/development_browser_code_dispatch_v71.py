"""Explicit, bounded, single-owner Selenium coding-job inbox (not the offline daemon).

The offline MicroGen continuity daemon remains model-free. This standalone
controller processes a finite queue of independently authorized source-pinned
jobs. Its dispatch claim is durable BEFORE invoking the one-Send browser worker.
A restart may reconcile only the original saved model response; never replay
a possibly consumed browser request. It cannot publish, merge or edit lectures.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import json

from .development_continuity_executor_v71 import (
    _atomic_json, _exclusive, _read_json, _sha,
)
from .development_authorized_patch_handoff_v71 import ensure
from .development_browser_code_transport_v71 import (
    run_one, validate_job,
)
from .recovery_registry import lookup_mechanism

SIG = "V71_SINGLE_OWNER_SOURCE_PINNED_BROWSER_CODE_INBOX"
MECHANISM = "CLAIM_DISPATCH_ONCE_RECONCILE_ORIGINAL_REPLY_NO_RESEND"
KIN = "bounded_coding_dispatch"
ENTRY = re.compile(r"dispatch_([a-z][a-z0-9_-]{3,60})\.json\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_INBOX = 8
MAX_PER_CYCLE = 3
ALLOWED_FINAL = frozenset({
    "CODE_CANDIDATE_VERIFIED",
    "MODEL_REPLY_UNSAFE_QUARANTINED",
    "TEST_FAILED_QUARANTINED",
    "SEND_UNCERTAIN_NO_REPLAY",
    "CHANGED_ENROLLMENT_QUARANTINED",
    "WORKER_DISPATCH_UNCERTAIN_NO_REPLAY",
    "INVALID_PINNED_JOB_QUARANTINED",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _registered() -> None:
    ensure(lookup_mechanism(KIN, SIG) == MECHANISM,
           "Unregistered separate coding dispatcher, NO SEND")


def _paths(root: Path, identifier: str) -> tuple[Path, Path, Path]:
    root = Path(root).absolute()
    job_dir = root / "jobs" / identifier
    return job_dir / "job.json", job_dir / "repo", job_dir / "state"


def _admit(entry_file: Path, root: Path) -> dict:
    ensure(entry_file.is_file() and not entry_file.is_symlink()
           and 12 <= entry_file.stat().st_size <= 4000,
           "Invalid bounded coding inbox enrollment")
    match = ENTRY.fullmatch(entry_file.name)
    ensure(match is not None, "Unsafe coding inbox filename")
    identifier = match.group(1)
    raw = _read_json(entry_file)
    ensure(set(raw) == {
        "schema_version", "project", "dispatch_id", "authorized",
        "job_sha256", "model_transport", "max_browser_claims",
        "paid_gemini_api", "student_release_authorized",
    } and type(raw["schema_version"]) is int
       and raw["schema_version"] == 1
       and raw["project"] == "MicroGen_AI_Web"
       and raw["dispatch_id"] == identifier
       and raw["authorized"] is True
       and raw["model_transport"] == "gemini_selenium"
       and type(raw["max_browser_claims"]) is int
       and raw["max_browser_claims"] == 1
       and raw["paid_gemini_api"] is False
       and raw["student_release_authorized"] is False
       and type(raw["job_sha256"]) is str
       and SHA64.fullmatch(raw["job_sha256"]),
       "Ineligible/unauthorized coding dispatch")
    jobfile, repo, state = _paths(root, identifier)
    jobdir = jobfile.parent
    ensure(jobdir.is_dir() and not jobdir.is_symlink()
           and jobdir.resolve(strict=True).parent ==
               (root / "jobs").resolve(strict=True)
           and jobfile.is_file() and not jobfile.is_symlink()
           and repo.is_dir() and not repo.is_symlink()
           and not state.is_symlink()
           and _sha(jobfile) == raw["job_sha256"],
           "Changed, redirected or linked source-pinned coding job; NO SEND")
    job = _read_json(jobfile)
    validate_job(job, repo)
    ensure(job["job_id"] == identifier
           and job["authorized"] is True
           and job["transport"] == "gemini_selenium",
           "Coding job identity does not match signed enrollment")
    return {
        "dispatch_id": identifier,
        "enrollment_sha256": _sha(entry_file),
        "job_sha256": raw["job_sha256"],
        "jobfile": jobfile, "repo": repo, "state": state,
    }


def _load_ledger(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1,
                "status": "BOUNDED_BROWSER_CODE_DISPATCH_V71",
                "entries": {}}
    ensure(path.is_file() and not path.is_symlink()
           and path.stat().st_size <= 120000,
           "Corrupt coding dispatcher ledger")
    obj = _read_json(path)
    ensure(type(obj) is dict
           and set(obj) == {"schema_version", "status", "entries"}
           and obj["schema_version"] == 1
           and obj["status"] == "BOUNDED_BROWSER_CODE_DISPATCH_V71"
           and type(obj["entries"]) is dict
           and len(obj["entries"]) <= 80,
           "Untrusted coding dispatcher history")
    return obj


def _original_reply_status(state_dir: Path) -> str:
    state_file = state_dir / "browser_coding_state.json"
    reply_file = state_dir / "model_response_untrusted.txt"
    if not state_file.exists():
        return "MISSING_WORKER_CLAIM"
    ensure(state_file.is_file() and not state_file.is_symlink(),
           "Unsafe worker checkpoint path")
    state = _read_json(state_file)
    if state.get("status") == "CODE_CANDIDATE_VERIFIED":
        ensure(type(state.get("candidate_source_sha256")) is str
               and SHA64.fullmatch(state["candidate_source_sha256"])
               and type(state.get("tests_passed")) is list
               and len(state["tests_passed"]) == 1
               and type(state["tests_passed"][0]) is str
               and re.fullmatch(r"tests/test_[a-z0-9_]{5,80}\.py",
                                state["tests_passed"][0]),
               "Completed browser coding claim lacks real test evidence")
        target = state_dir.parent / "repo" / state["tests_passed"][0]
        ensure(target.is_file() and not target.is_symlink()
               and _sha(target) == state["candidate_source_sha256"],
               "Completed candidate source SHA no longer matches")
        return "CODE_CANDIDATE_VERIFIED"
    if state.get("status") == "TEST_FAILED_QUARANTINED":
        return "TEST_FAILED_QUARANTINED"
    if (reply_file.is_file() and not reply_file.is_symlink()
        and 30 <= reply_file.stat().st_size <= 50000
        and state.get("response_sha256") == _sha(reply_file)
        and state.get("status") in {
            "MODEL_PROPOSAL_REJECTED",
            "SEND_CLAIMED_UNCERTAIN",
            "MODEL_REPLY_CAPTURED_UNTRUSTED",
        }):
        return "ORIGINAL_REPLY_AVAILABLE_NO_SEND"
    return "SEND_UNCERTAIN_NO_REPLAY"


def _safe_original_status(state_dir: Path) -> str:
    """One corrupt child cannot abort independent jobs or authorize a resend."""
    try:
        return _original_reply_status(state_dir)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError):
        return "CORRUPT_WORKER_CLAIM_NO_REPLAY"


def _reconcile(item: dict) -> dict:
    return run_one(job_path=item["jobfile"],
                   repo=item["repo"], state_dir=item["state"],
                   reconcile_only=True)


def scan(*, queue_root: Path, allow_one_browser_send: bool = False,
         max_jobs: int = MAX_PER_CYCLE, inspect_only: bool = False,
         sender=None, fault_after_dispatch_claim: bool = False) -> dict:
    """Process independent authorized jobs, never more than one claimed Send each.

    Passing sender is reserved for isolated deterministic tests; the CLI never
    accepts this argument. Every job must be in the queue's own jobs directory.
    """
    _registered()
    root = Path(queue_root).absolute()
    ensure(root.is_dir() and not root.is_symlink()
           and (root / "inbox").is_dir()
           and not (root / "inbox").is_symlink()
           and (root / "jobs").is_dir()
           and not (root / "jobs").is_symlink()
           and type(allow_one_browser_send) is bool
           and type(inspect_only) is bool
           and type(max_jobs) is int
           and 1 <= max_jobs <= MAX_PER_CYCLE,
           "Unsafe source-bound coding dispatcher root or request")
    # Protect the daemon and its own main repo from the separate sender.
    ensure("live_state" not in root.parts
           and "repo" != root.name
           and "V71_MAIN_AFTER_PR592_20261121" not in root.parts,
           "Coding dispatcher cannot own the offline daemon checkpoint")
    inbox = sorted(x for x in (root / "inbox").iterdir()
                   if x.name.startswith("dispatch_"))
    ensure(len(inbox) <= MAX_INBOX, "Unbounded browser coding inbox")
    results = []
    # Even a read-only scan uses the same OS lock. A concurrent invocation
    # must fail closed rather than racing to claim the same provider request.
    with _exclusive(root / "dispatch_control"):
        ledger_file = root / "dispatch_control" / "ledger.json"
        ledger = _load_ledger(ledger_file)
        processed = 0
        new_claims = 0
        for entry_file in inbox:
            # Completed, rejected and invalid jobs must not consume this
            # cycle's finite slots: otherwise one old item can starve later
            # independent eligible development jobs forever.
            name = entry_file.name
            match = ENTRY.fullmatch(name)
            if not match:
                results.append({"entry": name,
                                "status": "INVALID_ENROLLMENT_NO_SEND"})
                continue
            identifier = match.group(1)
            prior = ledger["entries"].get(identifier)
            try:
                item = _admit(entry_file, root)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                results.append({"entry": name,
                                "status": "INVALID_PINNED_JOB_NO_SEND",
                                "error_class": type(exc).__name__})
                continue
            if prior and (prior.get("job_sha256") != item["job_sha256"]
                          or prior.get("enrollment_sha256") !=
                          item["enrollment_sha256"]):
                results.append({"entry": name,
                                "status": "CHANGED_ENROLLMENT_QUARANTINED"})
                continue
            if inspect_only:
                results.append({"entry": name,
                                "status": prior.get("status", "READY_NEW_JOB")
                                if prior else "READY_NEW_JOB",
                                "model_sends": 0})
                continue
            if prior is not None and prior.get("status") in ALLOWED_FINAL:
                status = prior["status"]
                if status == "CODE_CANDIDATE_VERIFIED":
                    if _safe_original_status(item["state"]) != status:
                        status = "MODEL_REPLY_UNSAFE_QUARANTINED"
                        prior["status"] = status
                        _atomic_json(ledger_file, ledger)
                results.append({"entry": name, "status": status,
                                "new_browser_claims": 0})
                continue
            if prior is None and not allow_one_browser_send:
                results.append({"entry": name,
                                "status": "ELIGIBLE_SEND_NOT_DISPATCHED"})
                continue
            if processed >= max_jobs:
                results.append({"entry": name,
                                "status": "DEFERRED_FINITE_CYCLE_LIMIT"})
                continue
            processed += 1
            if prior is None:
                # Before any invocation, mark that the provider claim may be
                # consumed. A crash now with no child receipt never resends.
                prior = {"job_sha256": item["job_sha256"],
                         "enrollment_sha256": item["enrollment_sha256"],
                         "status": "WORKER_DISPATCH_CLAIMED_UNCERTAIN",
                         "claimed_utc": _now(), "browser_claims": 1,
                         "paid_api_requests": 0,
                         "student_publication_authorized": False}
                ledger["entries"][identifier] = prior
                _atomic_json(ledger_file, ledger)
                new_claims += 1
                if fault_after_dispatch_claim:
                    raise RuntimeError("INJECTED_POST_DISPATCH_CLAIM_NO_SEND")
                should_send = True
            else:
                should_send = False
            try:
                if should_send:
                    result = run_one(
                        job_path=item["jobfile"], repo=item["repo"],
                        state_dir=item["state"], sender=sender,
                    )
                else:
                    found = _safe_original_status(item["state"])
                    if found == "CODE_CANDIDATE_VERIFIED":
                        prior["status"] = "CODE_CANDIDATE_VERIFIED"
                        prior["completed_utc"] = _now()
                        _atomic_json(ledger_file, ledger)
                        results.append({"entry": name,
                                        "status": prior["status"],
                                        "new_browser_claims": 0})
                        continue
                    if found == "ORIGINAL_REPLY_AVAILABLE_NO_SEND":
                        result = _reconcile(item)
                    else:
                        prior["status"] = (
                            "TEST_FAILED_QUARANTINED"
                            if found == "TEST_FAILED_QUARANTINED"
                            else "SEND_UNCERTAIN_NO_REPLAY"
                            if found != "MISSING_WORKER_CLAIM"
                            else "WORKER_DISPATCH_UNCERTAIN_NO_REPLAY"
                        )
                        _atomic_json(ledger_file, ledger)
                        results.append({"entry": name,
                                        "status": prior["status"],
                                        "new_browser_claims": 0})
                        continue
                ensure(result.get("status") == "CODE_CANDIDATE_VERIFIED"
                       and result.get("model_requests_claimed") == 1
                       and result.get("paid_api_requests") == 0
                       and result.get("student_release") is False
                       and result.get("host_codex_policy_cleared") is False,
                       "Invalid or unsafe model coding worker result")
                prior["status"] = "CODE_CANDIDATE_VERIFIED"
                prior["candidate_sha256"] = result["candidate_source_sha256"]
                prior["completed_utc"] = _now()
                _atomic_json(ledger_file, ledger)
                results.append({"entry": name,
                                "status": "CODE_CANDIDATE_VERIFIED",
                                "new_browser_claims": int(should_send),
                                "candidate_sha256": result["candidate_source_sha256"]})
            except (ValueError, RuntimeError, OSError, KeyError,
                    TimeoutError, UnicodeError) as exc:
                found = _safe_original_status(item["state"])
                if found == "ORIGINAL_REPLY_AVAILABLE_NO_SEND":
                    # The only automatic repair is ORIGINAL saved-response
                    # offline reconciliation. Never another Selenium Send.
                    try:
                        outcome = _reconcile(item)
                    except (ValueError, RuntimeError, OSError, KeyError,
                            UnicodeError):
                        outcome = None
                    if outcome and outcome.get("status") == "CODE_CANDIDATE_VERIFIED":
                        prior["status"] = "CODE_CANDIDATE_VERIFIED"
                        prior["candidate_sha256"] = outcome[
                            "candidate_source_sha256"]
                        prior["completed_utc"] = _now()
                        _atomic_json(ledger_file, ledger)
                        results.append({"entry": name,
                                        "status": prior["status"],
                                        "new_browser_claims": int(should_send),
                                        "reconciled_original_reply": True})
                        continue
                prior["status"] = ("TEST_FAILED_QUARANTINED"
                                   if found == "TEST_FAILED_QUARANTINED"
                                   else "MODEL_REPLY_UNSAFE_QUARANTINED"
                                   if found == "ORIGINAL_REPLY_AVAILABLE_NO_SEND"
                                   else "SEND_UNCERTAIN_NO_REPLAY")
                prior["error_class"] = type(exc).__name__
                _atomic_json(ledger_file, ledger)
                results.append({"entry": name, "status": prior["status"],
                                "error_class": type(exc).__name__,
                                "new_browser_claims": int(should_send)})
    return {
        "schema_version": 1,
        "status": "BOUNDED_BROWSER_CODING_DISPATCH_RECONCILED",
        "scanned": len(inbox), "processed": processed,
        "new_browser_claims": new_claims, "jobs": results,
        "paid_api_requests": 0,
        "student_publication_authorized": False,
        "codex_host_policy_modified": False,
        "offline_v71_daemon_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-root", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect", action="store_true",
                      help="No checkpoint writes, no provider sends")
    mode.add_argument("--dispatch", action="store_true",
                      help="Only already-captured jobs unless --allow-one-browser-send")
    parser.add_argument("--allow-one-browser-send", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=1)
    args = parser.parse_args(argv)
    ensure(args.dispatch or not args.allow_one_browser_send,
           "Inspect mode cannot send provider requests")
    result = scan(queue_root=args.queue_root,
                  allow_one_browser_send=args.allow_one_browser_send,
                  max_jobs=args.max_jobs, inspect_only=args.inspect)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
