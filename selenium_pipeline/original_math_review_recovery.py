"""Non-dispatching recovery report for the explicitly approved original math-review window.

Reconciles immutable original mathematical evidence, source-review coverage,
Gemini transport readiness, and the separate worker-lock state. The result is
a point-in-time observation, NEVER a claim, model send, or student release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .original_math_audio_release_ledger import summarize_original_review_readiness
from .scoped_original_math_review_window import inspect_window


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
        return digest.hexdigest()


def reconcile_original_math_recovery(*, window_root: Path, now: float | None = None) -> dict:
    """Read only. Fail closed on source drift, active ownership, or inconsistent totals.

    No status in this report authorizes an automatic retry. A subsequent
    dispatcher must revalidate all identity/ownership/health evidence itself.
    """
    window = Path(window_root).absolute()
    manifest_path = window / "window_manifest.json"
    checkpoint_path = window / "separate_window_checkpoint.json"
    if (not window.is_dir() or window.is_symlink()
        or manifest_path.is_symlink() or checkpoint_path.is_symlink()):
        raise ValueError("Original review recovery window is missing or redirected")
    # Detect concurrent modification of the window while this report is built.
    original_manifest_digest = _sha256(manifest_path)
    original_checkpoint_digest = _sha256(checkpoint_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    if type(manifest) is not dict:
        raise ValueError("Untrusted approved review manifest")
    source_folder = Path(manifest["original_folder"]).absolute()
    queue_root = Path(manifest["original_queue_root"]).absolute()

    review = inspect_window(window_root=window, now=now)
    math = summarize_original_review_readiness(
        queue_root=queue_root, folder=source_folder)
    total = math["original_utterances"]
    agreed = math["source_validated_ai_math_agreements"]
    pending = math["source_math_pending_or_disputed"]
    if (type(total) is not int or type(agreed) is not int
        or type(pending) is not int or total < 1 or agreed < 0
        or pending < 0 or agreed + pending != total
        or total != manifest["parent_historical"]["original_utterances"]
        or math["student_publication_authorized"] is not False
        or review["student_publication_authorized"] is not False
        or review["original_folder"] != str(source_folder)):
        raise ValueError("Source mathematics review/queue totals or identity differ")

    # Never steal or clear unknown lock ownership. A lock may represent an
    # in-flight or crashed worker whose result still requires reconciliation.
    lock = Path(str(checkpoint_path) + ".lock")
    occupied = lock.exists() or lock.is_symlink()
    if (_sha256(manifest_path) != original_manifest_digest
        or _sha256(checkpoint_path) != original_checkpoint_digest):
        raise ValueError("Math review evidence changed during inspection")
    reasons = []
    if occupied:
        reasons.append("EXISTING_CLAIM_LOCK_REQUIRES_OWNER_INSPECTION")
    if review["requires_reconciliation"]:
        reasons.append("AMBIGUOUS_OR_IN_FLIGHT_RESPONSE_REQUIRES_RECONCILIATION")
    if not review["live_source_transport_health_verified"]:
        reasons.append("FRESH_VERIFIED_SAME_TAB_GEMINI_PROBE_MISSING")
    if not review["checkpoint_due_without_probe"]:
        reasons.append("CHECKPOINT_NOT_DUE_OR_BUDGET_EXHAUSTED")
    if pending == 0:
        reasons.append("NO_PENDING_ORIGINAL_MATH_REVIEW")
    single_tick_possible = bool(
        not reasons and review["eligible_for_single_authorized_dispatch"])
    return {
        "status": ("SINGLE_REVIEW_TICK_PRECONDITIONS_OBSERVED"
                   if single_tick_possible else "ORIGINAL_MATH_REVIEW_BLOCKED"),
        "scope": "ORIGINAL_MATH_INDEPENDENT_CHALLENGE",
        "slide": manifest["slide"],
        "original_utterances": total,
        "independently_agreed_source_math": agreed,
        "pending_or_disputed_source_math": pending,
        "historical_original_failed_attempt_receipts":
            manifest["parent_historical"]["historical_attempt_count"],
        "separate_window_confirmed_submissions":
            review["new_window_confirmed_submissions"],
        "checkpoint_status": review["status"],
        "checkpoint_requires_reconciliation": review["requires_reconciliation"],
        "checkpoint_lock_present": occupied,
        "fresh_verified_gemini_transport": review["live_source_transport_health_verified"],
        "non_dispatching_preconditions_satisfied": single_tick_possible,
        "blocking_reasons": reasons,
        "original_source_sha256": review["original_source_sha256"],
        "approved_manifest_sha256": original_manifest_digest,
        "checkpoint_sha256": original_checkpoint_digest,
        "report_is_point_in_time_only": True,
        "model_request_sent": False,
        "academic_or_listening_approval_granted": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--window-root", type=Path, required=True)
    args = p.parse_args(argv)
    print(json.dumps(
        reconcile_original_math_recovery(window_root=args.window_root),
        indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
