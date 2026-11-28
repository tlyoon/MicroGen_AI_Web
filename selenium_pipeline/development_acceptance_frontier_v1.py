"""Evidence-driven G2/G3 development stall recovery, never academic acceptance.

Observe genuine immutable completion receipts and original Selenium source
quarantines. Classify loss of progress and stage one SHA-pinned *engineering*
repair assignment. No model Send, paid API, evidence manufacture or release.

A healthy watchdog and an unchanged acceptance ledger are NOT progress.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid

from .recovery_registry import lookup_mechanism

KIND = "academic_evidence_frontier_recovery"
SIGNATURE = "G2G3_TECHNICAL_QUEUE_EXHAUSTED_WITH_OPEN_INDEPENDENT_ACCEPTANCE_GATES"
MECHANISM = "TRACK_VERIFIED_ACCEPTANCE_DELTA_AND_STAGE_ONE_SHA_PINNED_RECOVERY"
GATES = (
    "G2_INDEPENDENT_SOURCE_AI",
    "G2_INDEPENDENT_ACOUSTIC_QA",
    "G3_INDEPENDENT_SCIENCE",
    "G3_INDEPENDENT_ACOUSTIC_QA",
    "G3_ORIGINAL_VIDEO_PAGE_TECHNICAL",
    "G3_WITHIN_SLIDE_VISUAL_HIGHLIGHT_QA",
    "G3_SECOND_SUBSECTION_ACCEPTANCE",
    "END_TO_END_PRODUCTION_RELEASE",
)
QUARANTINED = (
    "g3_caption_integrity_v1",
    "g3_narration_page_index_v1",
    "g3_png_asset_coverage_v1",
)
HEX = re.compile(r"[a-f0-9]{64}\Z")


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def read_json(path: Path, limit: int = 240_000) -> tuple[dict, str]:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= limit,
            "Missing, linked or oversized real academic evidence")
    body = path.read_bytes()
    value = json.loads(body.decode("utf8"))
    require(type(value) is dict, "Academic evidence must be JSON object")
    return value, digest(body)


def _atomic_json(path: Path, body: dict):
    require(not path.is_symlink(), "Recovery checkpoint redirected")
    text = (json.dumps(body, sort_keys=True, indent=2) + "\n").encode("utf8")
    tmp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    try:
        with tmp.open("xb") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _acceptance(receipt: dict) -> tuple[dict, list]:
    require(receipt.get("schema_version") == 1
            and receipt.get("student_publication_authorized") is False
            and receipt.get("original_historical_requests_replayed") is False
            and type(receipt.get("new_browser_sends")) is int
            and 0 <= receipt["new_browser_sends"] <= 10000
            and type(receipt.get("paid_gemini_API_calls")) is int
            and 0 <= receipt["paid_gemini_API_calls"] <= 10000
            and type(receipt.get("academically_accepted_gates")) is int
            and type(receipt.get("all_G2_G3_requirements_accepted")) is bool,
            "Receipt has unverified historical or provider side effects")
    gates = receipt.get("acceptance_gates")
    require(type(gates) is list and len(gates) == len(GATES)
            and tuple(row.get("gate_id") for row in gates
                      if type(row) is dict) == GATES,
            "Academic gate order or identity not independently attested")
    for row in gates:
        require(type(row.get("accepted")) is bool
                and type(row.get("status")) is str
                and type(row.get("next_action")) is str
                and len(row["next_action"]) >= 20,
                "Invalid reviewed academic requirement")
    academic_count = sum(row["accepted"] for row in gates
                         if row["gate_id"] != "G3_ORIGINAL_VIDEO_PAGE_TECHNICAL")
    require(receipt["academically_accepted_gates"] == academic_count
            and receipt["all_G2_G3_requirements_accepted"] ==
                (academic_count == len(GATES) - 1),
            "Technical-only pass or missing reviewer proof cannot count as academic acceptance")
    g2 = receipt.get("actions", {}).get("G2_SOURCE", {})
    g3 = receipt.get("actions", {}).get("G3_SCIENCE", {})
    accepted, total = (g2.get("total_two_pass_AI_agreements"),
                       g2.get("original_total"))
    spent, cap = (g3.get("original_possible_model_sends_reserved"),
                  g3.get("original_immutable_campaign_send_cap"))
    require(all(type(x) is int for x in (accepted,total,spent,cap))
            and 0 <= accepted <= total <= 10000
            and 0 <= spent <= cap <= 10000
            and (g3.get("remaining_source_science_tasks") is None
                 or type(g3["remaining_source_science_tasks"]) is int),
            "Unattributed G2 count or G3 immutable request budget")
    metrics = {
        "g2_two_pass_agreements": accepted,
        "g2_required": total,
        "g2_remaining": total - accepted,
        "g3_original_send_cap": cap,
        "g3_original_sends_reserved": spent,
        "g3_science_remaining": g3.get("remaining_source_science_tasks"),
        "independent_academic_gates_accepted": academic_count,
        "technical_only_gates_passed":
            receipt.get("technical_only_gates_passed"),
    }
    return metrics, gates


def _quarantines(backlog_root: Path, current_repo: Path) -> list:
    """Only original, SHA-witnessed, nonreplayable coding artifacts qualify."""
    result = []
    for job_id in QUARANTINED:
        inbox = backlog_root / "inbox" / (job_id + ".json")
        checkpoint = (backlog_root / "state" / job_id / "coding_state.json")
        reply = (backlog_root / "state" / job_id / "original_model_reply.txt")
        if not all(p.is_file() and not p.is_symlink()
                   for p in (inbox, checkpoint, reply)):
            continue
        job, job_sha = read_json(inbox)
        state, _ = read_json(checkpoint)
        if state.get("status") != "UNSAFE_MODEL_REPLY_QUARANTINED":
            continue
        require(job.get("job_id") == job_id
                and state.get("job_id") == job_id
                and state.get("job_sha256") == job_sha
                and state.get("model_claims") == 1
                and state.get("model_sends") == 1
                and state.get("paid_api_requests") == 0
                and state.get("student_publication_authorized") is False
                and type(state.get("model_reply_sha256")) is str
                and HEX.fullmatch(state["model_reply_sha256"])
                and digest(reply.read_bytes()) ==
                    state["model_reply_sha256"],
                "Original quarantined one-Send identity changed: no replay")
        # Recovering a quarantined reply is a NEW source-only engineering
        # implementation from the original independent test, NOT parser bypass.
        target = current_repo / job["target"]
        main_test = current_repo / job["test"]
        # A source file appearing in Git is not itself a certified repair:
        # require the SAME original SHA-pinned independent test in reviewed
        # protected main, otherwise the quarantine remains unresolved.
        if (target.is_file() and not target.is_symlink()
                and main_test.is_file() and not main_test.is_symlink()
                and digest(main_test.read_bytes()) ==
                    job.get("test_sha256")):
            continue
        source = Path(job["repo"])
        independent = source / job["test"]
        if not (source.is_dir() and not source.is_symlink()
                and independent.is_file() and not independent.is_symlink()
                and digest(independent.read_bytes()) ==
                    job.get("test_sha256")
                and job.get("paid_api") is False
                and job.get("student_publication") is False):
            continue
        result.append({
            "job_id": job_id,
            "classification": "PINNED_UNSAFE_REPLY_NEEDS_NEW_TESTED_CODE",
            "original_reply_sha256": state["model_reply_sha256"],
            "independent_test_sha256": job["test_sha256"],
            "independent_test": str(independent),
            "target": job["target"],
            "source_job_manifest_sha256": job_sha,
            "new_model_send_authorized": False,
            "academic_acceptance_authorized": False,
        })
    return result


def assess(*, acceptance_root: Path, backlog_root: Path,
           control_root: Path, repo_root: Path, current_main_sha: str) -> dict:
    """Observe once per development cycle; stage ONLY genuine owned work."""
    require(lookup_mechanism(KIND, SIGNATURE) == MECHANISM,
            "Acceptance-driven recovery not in executable registry")
    acceptance_root, backlog_root, control_root, repo_root = (
        Path(p).absolute() for p in
        (acceptance_root, backlog_root, control_root, repo_root))
    require(all(p.is_dir() and not p.is_symlink()
                for p in (acceptance_root, backlog_root,
                          control_root, repo_root))
            and len(set((acceptance_root, backlog_root,
                         control_root, repo_root))) == 4,
            "Acceptance recovery must use separate owned source and state")
    require(re.fullmatch(r"[a-f0-9]{40}", current_main_sha)
            and not (repo_root / ".git").is_symlink(),
            "No certified clean main identity for recovery")
    candidates = sorted(
        (p for p in acceptance_root.glob("*.json")
         if p.is_file() and not p.is_symlink()),
        key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
    require(candidates, "No genuine independent academic acceptance receipt")
    receipt_path = candidates[0]
    receipt, receipt_sha = read_json(receipt_path, 2_000_000)
    metrics, gates = _acceptance(receipt)
    fingerprint = digest(json.dumps({
        "scope_sha256": receipt.get("scope_sha256"),
        "metrics": metrics,
        "gate_states": [(x["gate_id"], x["status"], x["accepted"])
                        for x in gates],
    }, sort_keys=True).encode("utf8"))
    state_file = control_root / "academic_progress_watch_v1.json"
    if state_file.exists() or state_file.is_symlink():
        previous, _ = read_json(state_file)
        require(previous.get("schema_version") == 1
                and previous.get("student_publication_authorized") is False,
                "Invalid previous academic progress cursor")
        unchanged = previous.get("unchanged_cycles", 0) + 1 if (
            previous.get("academic_fingerprint") == fingerprint) else 0
        require(type(unchanged) is int and 0 <= unchanged <= 1_000_000,
                "Academic progress cursor corrupt")
        prior_metrics = previous.get("academic_metrics")
        require(type(prior_metrics) is dict
                and (metrics["g2_two_pass_agreements"] >=
                     prior_metrics.get("g2_two_pass_agreements", 0))
                and (metrics["independent_academic_gates_accepted"] >=
                     prior_metrics.get("independent_academic_gates_accepted", 0)),
                "Previously accepted academic evidence regressed: audit required")
    else:
        unchanged = 0
    rejected = _quarantines(backlog_root, repo_root)
    unfinished = [row for row in gates if not row["accepted"]]
    # A technical code repair can be done without replaying original model
    # Sends. A scientific/acoustic/video gate requires fresh actual evidence.
    if rejected:
        next_job = rejected[0]
        work = {
            "schema_version": 1,
            "classification": "SOURCE_TEST_REPAIR_REQUIRED_NO_MODEL_REPLAY",
            "academic_receipt_sha256": receipt_sha,
            "protected_main_sha": current_main_sha,
            **next_job,
            "provider_sends": 0,
            "paid_api_requests": 0,
            "student_publication_authorized": False,
        }
        work_root = control_root / "academic_recovery_work_items_v1"
        work_root.mkdir(exist_ok=True)
        require(not work_root.is_symlink(),
                "Academic recovery work items redirected")
        work_file = work_root / (next_job["job_id"] + ".json")
        if work_file.exists() or work_file.is_symlink():
            prior, _ = read_json(work_file)
            # Original reply and independent test are immutable; new GitHub
            # main and newer academic receipts may legitimately change.
            require(prior["original_reply_sha256"] ==
                    work["original_reply_sha256"]
                    and prior["independent_test_sha256"] ==
                    work["independent_test_sha256"],
                    "Historical quarantined reply or test changed")
        else:
            _atomic_json(work_file, work)
        action = "REPAIR_ORIGINAL_SHA_PINNED_SOURCE_WITH_INDEPENDENT_TEST"
        status = "ACADEMIC_STALL_REPAIRABLE_SOURCE_JOB_IDENTIFIED"
    elif unfinished:
        next_job = {
            "gate_id": unfinished[0]["gate_id"],
            "academic_gate_status": unfinished[0]["status"],
            "required_evidence": unfinished[0]["next_action"],
        }
        action = "REQUIRE_GENUINE_INDEPENDENT_ACADEMIC_EVIDENCE"
        status = "ACADEMIC_STALL_EXTERNAL_EVIDENCE_REQUIRED"
    else:
        next_job = {}
        action = "VERIFY_INDEPENDENT_ACADEMIC_ACCEPTANCE"
        status = "ACADEMIC_ACCEPTANCE_RECONCILIATION_REQUIRED"
    cursor = {
        "schema_version": 1,
        "status": status,
        "academic_fingerprint": fingerprint,
        "academic_receipt": str(receipt_path),
        "academic_receipt_sha256": receipt_sha,
        "observed_at_epoch": int(time.time()),
        "protected_main_sha": current_main_sha,
        "unchanged_cycles": unchanged,
        "stall_escalation": unchanged >= 2,
        "academic_metrics": metrics,
        "remaining_gates": [r["gate_id"] for r in unfinished],
        "next_action": action,
        "next_work": next_job,
        "unresolved_quarantined_source_jobs": len(rejected),
        "provider_sends": 0,
        "paid_api_requests": 0,
        "student_publication_authorized": False,
    }
    _atomic_json(state_file, cursor)
    return cursor
