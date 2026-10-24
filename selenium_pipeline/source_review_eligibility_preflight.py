"""Non-dispatching, source-bound scope planner for original textbook AI review.

Read-only evidence cannot authorize an academic model request. Historical
failure receipts are not proof a provider never received an earlier send.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .ai_academic_review_queue import _check_queue
from .ai_academic_web_review import build_review_job
from .review_retry_plan import plan_manual_review_attempt
from .figure_source_identity import _sha


def inspect_original_review_eligibility(*, folder: Path, queue_root: Path,
                                         slide: int) -> dict:
    original = Path(folder).absolute()
    q = Path(queue_root).absolute()
    if (type(slide) is not int or not 1 <= slide <= 200
        or not q.is_dir() or q.is_symlink() or q.is_relative_to(original)):
        raise ValueError("Isolated, original slide-specific review queue required")
    original_hashes = {name: _sha(original / name)
                       for name in ("source.pdf", "slides.pdf", "script.txt")}
    row = _check_queue(queue_root=q, folder=original, slide=slide,
                       mode="INITIAL_REVIEW")
    job = build_review_job(folder=original, slide_numbers=[slide])
    if (row["utterance_count"] != job["utterance_count"]
        or job["source_sha256"] != original_hashes["source.pdf"]
        or job["slides_sha256"] != original_hashes["slides.pdf"]
        or job["script_sha256"] != original_hashes["script.txt"]):
        raise ValueError("Original review job diverged from queued source")
    queue_hash = _sha(q / "queue.json")
    modes = {}
    for mode in ("INITIAL_REVIEW", "INDEPENDENT_CHALLENGE"):
        stem = f"slide_{slide:03d}_{mode.lower()}"
        # Check *all* matching review attempt filenames, not just 1..3.
        # The legacy retry planner scans only the supported first three.
        for entry in q.glob(stem + "_attempt_*.json"):
            if (entry.is_symlink() or not entry.is_file()
                or not re.fullmatch(re.escape(stem) + r"_attempt_0[1-3]\.json",
                                    entry.name)):
                raise ValueError("Unaccounted or redirected review attempt")
        attempt = plan_manual_review_attempt(q, slide=slide, mode=mode)
        modes[mode] = {
            "recorded_status": attempt["status"],
            "observed_attempts": attempt.get("observed_attempts", 0),
            "next_possible_attempt_number": attempt.get("next_possible_attempt"),
            "confirmed_unsubmitted_prior_provider_attempts": False,
            "no_automatic_provider_retry": True,
        }
    next_mode = ("INDEPENDENT_CHALLENGE" if
                 modes["INITIAL_REVIEW"]["recorded_status"]
                 == "ALREADY_COMPLETED_NO_RESUBMISSION"
                 else "INITIAL_REVIEW")
    observed = modes[next_mode]
    if observed["recorded_status"] == "NEW_ATTEMPT_REQUIRES_EXPLICIT_REQUEST":
        state = "NO_PENDING_RECEIPT_BUT_SCOPED_CONSENT_NOT_PROVEN"
    elif observed["recorded_status"] == "ALREADY_COMPLETED_NO_RESUBMISSION":
        state = "EXISTING_PASS_MUST_NOT_BE_REPEATED"
    elif observed["recorded_status"] == "MAX_THREE_ATTEMPTS_EXHAUSTED":
        state = "EXHAUSTED_NO_MORE_REQUESTS"
    else:
        state = "RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND"
    if (original_hashes !=
        {name: _sha(original / name) for name in original_hashes}
        or queue_hash != _sha(q / "queue.json")):
        raise ValueError("Source or immutable queue changed during review preflight")
    return {
        "status": "SOURCE_BOUND_ACADEMIC_REVIEW_SCOPE_PREFLIGHT_NO_SEND",
        "planning_result": state,
        "original_source_sha256": original_hashes["source.pdf"],
        "original_slides_sha256": original_hashes["slides.pdf"],
        "original_script_sha256": original_hashes["script.txt"],
        "original_review_queue_sha256": queue_hash,
        "slide": slide,
        "original_utterance_count_on_slide": job["utterance_count"],
        "review_stages": modes,
        "suggested_next_stage": next_mode,
        "new_slide_specific_consent_verified": False,
        "historical_slide1_special_window_reusable": False,
        "independent_source_mathematics_approved": False,
        "browser_worker_ownership_verified": False,
        "review_model_request_sent": False,
        "automatic_retry_authorized": False,
        "paid_tts_authorized": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", required=True, type=Path)
    p.add_argument("--queue-root", required=True, type=Path)
    p.add_argument("--slide", required=True, type=int)
    args = p.parse_args(argv)
    output = inspect_original_review_eligibility(
        folder=args.folder, queue_root=args.queue_root, slide=args.slide)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
