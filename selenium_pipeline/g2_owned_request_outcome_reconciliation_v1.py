"""Original G2 owned-request evidence disposition: immutable, zero-Send.

A saved SUBMITTED_OR_UNCERTAIN claim is an irreversible provider boundary.
Even a zero-byte Gemini quarantine is NOT proof the original Send failed.
Read only the exact source-pinned, historical request windows and existing
quarantine-integrity mechanism. Produce a durable receipt that distinguishes
empty response capture, unresolved independent challenge and unsafe source
identity. Never retry, reset a budget, generate reviewer text, or accept science.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from .academic_review_checkpoint import _load, CLAIM_NAME, STATE_NAME
from .historical_quarantine_evidence_v1 import inspect_historical_quarantine
from .development_g2g3_eligible_dispatch_v1 import _verified_source_config, CONFIG_NAME
from .recovery_registry import lookup_mechanism

KIND = "g2_owned_request_outcome_reconciliation"
SIGNATURE = "G2_UNCERTAIN_ORIGINAL_REQUEST_MISTAKEN_FOR_FRESH_SEND"
MECHANISM = "PIN_OLD_SEND_AND_ZERO_CAPTURE_HOLD_REVIEW_NO_REPLAY"
STATUS = "G2_ORIGINAL_REQUEST_DISPOSITION_PRESERVED_NO_REPLAY"
MAX_SLIDES = 16
MAX_QUEUE = 120_000
MAX_ATTEMPT = 10_000
SOURCE_NAMES = ("source.pdf", "slides.pdf", "script.txt")
MODES = ("INITIAL_REVIEW", "INDEPENDENT_CHALLENGE")


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def sha(file: Path) -> str:
    need(file.is_file() and not file.is_symlink(),
         "Missing, linked or redirected original G2 evidence")
    h = hashlib.sha256()
    with file.open("rb") as stream:
        for data in iter(lambda: stream.read(65536), b""):
            h.update(data)
    return h.hexdigest()


def read(file: Path, limit: int) -> dict:
    need(file.is_file() and not file.is_symlink()
         and 2 <= file.stat().st_size <= limit,
         "Unbounded or redirected original evidence")
    result = json.loads(file.read_text(encoding="utf8"))
    need(type(result) is dict, "Original evidence must be a JSON object")
    return result


def canonical(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf8")


def _window(*, queue: Path, slide: int, mode: str,
            original_hashes: dict, quarantine_root: Path) -> tuple[dict, dict]:
    stem = f"slide_{slide:03d}_{mode.lower()}"
    root = queue / (stem + "_attempt_01_request")
    need(root.is_dir() and not root.is_symlink(),
         "No attributable original request window; hold this scope")
    state_path = root / STATE_NAME
    state = _load(root)
    need(state.get("review_mode") == mode
         and state.get("source_sha256") == original_hashes["source.pdf"]
         and state.get("slides_sha256") == original_hashes["slides.pdf"]
         and state.get("script_sha256") == original_hashes["script.txt"],
         "Old original request does not match source/review mode")
    need(state["status"] in {
        "SUBMITTED_OR_UNCERTAIN", "NO_RESPONSE_UNRESOLVED",
        "LEGACY_SENT_NO_RESPONSE", "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED",
        "MODEL_REPLY_OBSERVED_UNVALIDATED", "REJECTED_RESPONSE_UNTRUSTED"},
        "Not a consumed historical request for this evidence-only handler")
    claim = root / CLAIM_NAME
    need(claim.is_file() and not claim.is_symlink()
         and claim.read_text(encoding="utf8") ==
             state["request_fingerprint"] + "\n",
         "Original submit claim and exact request fingerprint mismatch")
    window_hashes = {
        STATE_NAME: sha(state_path), CLAIM_NAME: sha(claim)}
    evidence_path = root / "model_response_identity.json"
    if evidence_path.exists() or evidence_path.is_symlink():
        need(evidence_path.is_file() and not evidence_path.is_symlink(),
             "Unsafe original response identity evidence")
        window_hashes[evidence_path.name] = sha(evidence_path)
    raw_response = root / "model_response_untrusted.txt"
    if raw_response.exists() or raw_response.is_symlink():
        need(raw_response.is_file() and not raw_response.is_symlink(),
             "Unsafe original untrusted response file")
        window_hashes[raw_response.name] = sha(raw_response)
    attempt_file = queue / (stem + "_attempt_01.json")
    attempt = None
    if attempt_file.exists() or attempt_file.is_symlink():
        attempt = read(attempt_file, MAX_ATTEMPT)
        need(attempt.get("slide") == slide and attempt.get("mode") == mode
             and attempt.get("attempt") == 1
             and attempt.get("status") ==
             "FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
             and attempt.get("manual_retry_eligible") is False,
             "Attempt identity or no-replay policy mismatched")
        window_hashes[attempt_file.name] = sha(attempt_file)

    if state["status"] == "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED":
        outcome = "ORIGINAL_ONE_PASS_SAVED_SECOND_INDEPENDENT_PASS_REQUIRED"
    elif attempt and attempt.get("provider_submission_state") != (
            "UNKNOWN_AFTER_POSSIBLE_SUBMISSION"):
        outcome = "ORIGINAL_REPLY_REJECTED_OR_UNVERIFIED_NO_REPLAY"
    else:
        outcome = "SUBMITTED_OR_UNCERTAIN_HISTORICAL_SEND_NO_REPLAY"

    quarantine = inspect_historical_quarantine(
        attempt.get("reason") if attempt else None,
        quarantine_root=quarantine_root)
    if outcome == "SUBMITTED_OR_UNCERTAIN_HISTORICAL_SEND_NO_REPLAY" and (
            quarantine["status"] == "EMPTY_ORIGINAL_CAPTURE_VERIFIED_NO_REPLAY"):
        outcome = "EMPTY_QUARANTINE_BUT_SEND_STILL_UNCERTAIN_NO_REPLAY"
    result = {
        "slide": slide, "mode": mode,
        "disposition": outcome,
        "original_request_status": state["status"],
        "request_fingerprint_sha256": state["request_fingerprint"],
        "original_request_hashes": window_hashes,
        "original_quarantine": quarantine,
        "provider_send_failed_proven": False,
        "old_request_replay_authorized": False,
        "fresh_model_send_authorized": False,
        "accepted_scientific_review": False,
        "new_model_requests": 0,
    }
    quarantine_pins = {}
    filename = quarantine.get("filename")
    if filename is not None:
        for name in (filename, filename.replace(".raw.txt", ".meta.json")):
            file = quarantine_root / name
            if file.is_file() and not file.is_symlink():
                quarantine_pins[str(file)] = sha(file)
    return result, {str(state_path): sha(state_path),
                    str(claim): sha(claim),
                    **{str(root / name): digest for name, digest
                       in window_hashes.items()
                       if name not in (STATE_NAME, CLAIM_NAME,
                                       attempt_file.name)},
                    **({str(attempt_file): sha(attempt_file)}
                       if attempt is not None else {}),
                    **quarantine_pins}


def reconcile(*, original_folder: Path, queue_root: Path,
              quarantine_root: Path, state_root: Path,
              source_backlog: Path, slides: list[int]) -> dict:
    need(lookup_mechanism(KIND, SIGNATURE) == MECHANISM,
         "Historical G2 no-replay recovery mechanism not registered")
    original_folder = Path(original_folder).absolute()
    queue_root = Path(queue_root).absolute()
    quarantine_root = Path(quarantine_root).absolute()
    state_root = Path(state_root).absolute()
    source_backlog = Path(source_backlog).absolute()
    need(source_backlog.name == CONFIG_NAME and not source_backlog.is_symlink()
         and source_backlog.is_file() and not source_backlog.parent.is_symlink(),
         "Only the original source-pinned G2/G3 backlog may admit this audit")
    config = _verified_source_config(source_backlog.parent)
    need(config is not None
         and Path(config["g2_queue"]).absolute() == queue_root
         and Path(config["g2_source"]).absolute() == original_folder,
         "Original source and queue not owned by immutable G2/G3 backlog")
    need(all(sha(original_folder / name) == config["g2_inputs_sha256"][name]
             for name in SOURCE_NAMES)
         and sha(queue_root / "queue.json") == config["g2_queue_sha256"]
         and sha(Path(config["g3_progress"])) == config["g3_progress_sha256"],
         "Historical G2 or G3 source/config identity changed")
    need(all(x.is_dir() and not x.is_symlink()
             for x in (original_folder, queue_root, quarantine_root))
         and not state_root.is_symlink()
         and state_root.parent.is_dir()
         and not state_root.parent.is_symlink()
         and len({str(x.resolve()) for x in (
             original_folder, queue_root, quarantine_root,
             state_root.parent)}) == 4
         and not state_root.is_relative_to(original_folder)
         and not state_root.is_relative_to(queue_root)
         and not state_root.is_relative_to(quarantine_root),
         "Sources, original queue, quarantine and new receipts must be isolated")
    need(type(slides) is list and 1 <= len(slides) <= MAX_SLIDES
         and all(type(s) is int and 1 <= s <= 200 for s in slides)
         and slides == sorted(set(slides)),
         "Use a bounded unique ordered original slide subset")
    queue_path = queue_root / "queue.json"
    original_queue = read(queue_path, MAX_QUEUE)
    need(original_queue.get("original_source_folder") == str(original_folder)
         and original_queue.get("provider_requests_performed") == 0
         and original_queue.get("student_publication_authorized") is False
         and type(original_queue.get("slide_jobs")) is list,
         "Source-identity-preserving G2 queue required")
    hashes = {name: sha(original_folder / name) for name in SOURCE_NAMES}
    expected = {row["slide"]: row for row in original_queue["slide_jobs"]}
    need(all(slide in expected for slide in slides),
         "Requested slide not in the original G2 queue")
    need(all(row.get("original_source_sha256") == hashes["source.pdf"]
             and row.get("original_slides_sha256") == hashes["slides.pdf"]
             and row.get("original_script_sha256") == hashes["script.txt"]
             for row in (expected[s] for s in slides)),
         "Queued slide identity differs from original textbook inputs")
    protected = {str(queue_path): sha(queue_path),
                 str(source_backlog): sha(source_backlog),
                 str(Path(config["g3_progress"])): config["g3_progress_sha256"],
                 **{str(original_folder / name): value
                    for name, value in hashes.items()}}
    inspected = []
    for slide in slides:
        # If a validated initial review exists, inspect its original
        # independent challenge request instead of redoing initial review.
        initial = queue_root / f"slide_{slide:03d}_initial_review.json"
        mode = ("INDEPENDENT_CHALLENGE" if initial.is_file()
                and not initial.is_symlink() else "INITIAL_REVIEW")
        need(not initial.is_symlink(), "Redirected saved original review")
        if mode == "INDEPENDENT_CHALLENGE":
            protected[str(initial)] = sha(initial)
        row, pins = _window(queue=queue_root, slide=slide, mode=mode,
                            original_hashes=hashes,
                            quarantine_root=quarantine_root)
        inspected.append(row)
        protected.update(pins)
    # No source or request window can change while admitting a receipt.
    need(all(sha(Path(path)) == identity
             for path, identity in protected.items()),
         "Original G2 evidence changed during no-replay reconciliation")
    report = {
        "schema_version": 1,
        "status": STATUS,
        "original_source_hashes": hashes,
        "original_queue_sha256": protected[str(queue_path)],
        "slides": inspected,
        "slides_requiring_independent_qa": slides,
        "original_requests_replayed": False,
        "independent_scientific_QA_complete": False,
        "independent_acoustic_QA_complete": False,
        "student_publication_authorized": False,
        "new_browser_sends": 0,
        "new_paid_gemini_API_calls": 0,
    }
    payload = canonical(report)
    digest = hashlib.sha256(payload).hexdigest()
    state_root.mkdir(parents=True, exist_ok=True)
    path = state_root / (digest + ".json")
    need(not path.is_symlink(), "Unsafe historical disposition receipt")
    if path.exists():
        need(path.is_file() and path.read_bytes() == payload,
             "Historical G2 request disposition receipt was modified")
    else:
        try:
            with path.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            need(path.is_file() and path.read_bytes() == payload,
                 "Another owner wrote a different historical disposition")
    return {
        "status": STATUS,
        "receipt": str(path),
        "receipt_sha256": digest,
        "slides_inspected": slides,
        "dispositions": {str(row["slide"]): row["disposition"]
                         for row in inspected},
        "new_browser_sends": 0,
        "new_paid_gemini_API_calls": 0,
        "student_publication_authorized": False,
        "independent_scientific_QA_complete": False,
    }


def auto_audit_completed_handoff(*, handoff_dir: Path, state_dir: Path) -> dict:
    """Bridge a VERIFIED G2 offline handoff into a historic no-replay receipt.

    Does not dispatch a worker, call Gemini or change the original plan.
    Admission is based on the exact existing v7.1 immutable plan/ledger pair.
    """
    from .development_continuity_executor_v71 import _plan
    from .gemini_response_recovery import default_quarantine_dir

    handoff_dir = Path(handoff_dir).absolute()
    state_dir = Path(state_dir).absolute()
    config = _verified_source_config(handoff_dir)
    if config is None:
        return {"status": "HISTORICAL_G2_AUDIT_NOT_CONFIGURED",
                "new_browser_sends": 0}
    stem = "next_g2_source_preflight_" + config["g2_queue_sha256"][:16]
    plan_file = handoff_dir / (stem + ".json")
    ledger_file = state_dir / "handoff_intake_v1.json"
    if not ledger_file.is_file() or not plan_file.is_file():
        return {"status": "AWAIT_G2_SOURCE_PREFLIGHT_HANDOFF",
                "new_browser_sends": 0}
    ledger = read(ledger_file, 100_000)
    need(ledger.get("schema_version") == 1
         and ledger.get("status") == "SOURCE_PINNED_GLOBAL_OFFLINE_HANDOFF"
         and type(ledger.get("plans")) is dict,
         "Original G2 source handoff ledger not valid")
    saved = ledger["plans"].get(stem)
    if saved is None or saved.get("status") != "VERIFIED_TASK_PLAN_COMPLETE":
        return {"status": "AWAIT_VERIFIED_G2_PREFLIGHT_RECEIPT",
                "new_browser_sends": 0}
    need(saved.get("sha256") == sha(plan_file)
         and saved.get("project_complete") is True,
         "Historical G2 handoff plan was altered or not complete")
    plan = _plan(plan_file)
    tasks = plan["tasks"]
    need(1 <= len(tasks) <= MAX_SLIDES
         and saved.get("worker_starts") == len(tasks),
         "Original G2 preflight receipts missing or duplicated")
    completed = read(state_dir / "handoffs" / stem / "state.json",
                     200_000)
    need(completed.get("project_complete") is True,
         "Original owned G2 preflight checkpoint not complete")
    slides = []
    for task in tasks:
        value = task.get("params", {})
        slide = value.get("slide")
        need(task.get("id") == f"g2_original_source_preflight_{slide:03d}"
             and task.get("action") == "g2_review_preflight"
             and task.get("authorized") is True
             and value.get("queue_root") == config["g2_queue"]
             and value.get("folder") == config["g2_source"]
             and completed["tasks"].get(task["id"],{}).get("status") == "passed",
             "G2 original work item was not an actually passed source preflight")
        slides.append(slide)
    need(slides == sorted(set(slides)),
         "Original handoff contains duplicated or unordered G2 slides")
    return reconcile(
        original_folder=Path(config["g2_source"]),
        queue_root=Path(config["g2_queue"]),
        quarantine_root=default_quarantine_dir(),
        state_root=state_dir / "g2_owned_no_replay_dispositions_v1",
        source_backlog=handoff_dir / CONFIG_NAME,
        slides=slides)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-folder", required=True, type=Path)
    p.add_argument("--queue-root", required=True, type=Path)
    p.add_argument("--quarantine-root", required=True, type=Path)
    p.add_argument("--state-root", required=True, type=Path)
    p.add_argument("--source-backlog", required=True, type=Path)
    p.add_argument("--slides", type=int, nargs="+", required=True)
    a = p.parse_args(argv)
    print(json.dumps(reconcile(
        original_folder=a.original_folder, queue_root=a.queue_root,
        quarantine_root=a.quarantine_root, state_root=a.state_root,
        source_backlog=a.source_backlog, slides=a.slides), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
