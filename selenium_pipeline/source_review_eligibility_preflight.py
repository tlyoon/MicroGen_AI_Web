"""Non-dispatching, source-bound QA planner for the standing autonomous workflow.

Routine internal, no-new-cost Gemini Selenium scientific reviews are already
within the owner's MicroGen_AI_Web development authority. Do not reinterpret
this read-only planner's absence of a *per-slide* consent receipt as a request
for human intervention. It still never sends a model request, changes assets
or grants paid TTS/API, provider challenge bypass or publication permission.
An ambiguous historical send or changed source remains terminal.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .ai_academic_review_queue import _check_queue
from .ai_academic_web_review import build_review_job, review_instructions
from .review_retry_plan import plan_manual_review_attempt
from .figure_source_identity import _sha


def _owned_request_window(queue_root: Path, slide: int, mode: str) -> tuple[str | None, bool]:
    """Inspect real dispatch claims even when no attempt JSON was persisted.

    The historical retry planner intentionally counts attempt receipts, but a
    crashed external Send may leave only a request window. This immutable
    evidence must prevent 'fresh' preflight admission.
    """
    checkpoint = queue_root / (
        f"slide_{slide:03d}_{mode.lower()}_attempt_01_request")
    if not checkpoint.exists() and not checkpoint.is_symlink():
        return None, False
    if not checkpoint.is_dir() or checkpoint.is_symlink():
        raise ValueError("Unsafe historical academic request window")
    from .academic_review_checkpoint import _load
    previous = _load(checkpoint)
    status = previous.get("status")
    if type(status) is not str:
        raise ValueError("Unattributable historical request state")
    dispatch = checkpoint / "dispatch_attempted.claim"
    if dispatch.exists() or dispatch.is_symlink():
        if not dispatch.is_file() or dispatch.is_symlink():
            raise ValueError("Unsafe historical academic dispatch claim")
    return status, dispatch.is_file()


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
            "confirmed_unsubmitted_prior_provider_attempts": (
                attempt.get("certified_presend_count", 0) > 0),
            "certified_presend_count": attempt.get("certified_presend_count", 0),
            "no_automatic_provider_retry": True,
        }
    next_mode = ("INDEPENDENT_CHALLENGE" if
                 modes["INITIAL_REVIEW"]["recorded_status"]
                 == "ALREADY_COMPLETED_NO_RESUBMISSION"
                 else "INITIAL_REVIEW")
    observed = modes[next_mode]
    previous_status, previous_dispatch = _owned_request_window(
        q, slide, next_mode)
    if previous_status is not None:
        observed["historical_request_window_status"] = previous_status
        observed["historical_dispatch_claim_present"] = previous_dispatch
    # A checkpoint with an uncertain Send is authoritative even when the
    # JSON retry planner reports zero observed attempts. This is distinct
    # from a verified PREPARED_NOT_SENT claim with no dispatch marker.
    if observed["recorded_status"] == "CERTIFIED_PRESEND_ORIGINAL_CLAIM_SAME_WINDOW_RECOVERY":
        from .academic_review_checkpoint import _load, fingerprint, _verify_certified_unsent
        request = q / (f"slide_{slide:03d}_{next_mode.lower()}_attempt_01_request")
        original_claim = _load(request)
        expected = fingerprint(
            request_text=review_instructions(job, mode=next_mode),
            source_hashes={
                "source.pdf": job["source_sha256"],
                "slides.pdf": job["slides_sha256"],
                "script.txt": job["script_sha256"],
            },
            review_mode=next_mode)
        if (original_claim["request_fingerprint"] != expected
            or original_claim["source_sha256"] != original_hashes["source.pdf"]
            or _verify_certified_unsent(request, original_claim) !=
                observed["certified_presend_count"]):
            raise ValueError("Certified pre-Send does not match exact original G2 source/prompt")
        state = "CERTIFIED_PRESEND_SAME_CLAIM_RECOVERY_READY"
    elif (observed["recorded_status"] == "NEW_ATTEMPT_REQUIRES_EXPLICIT_REQUEST"
        and observed["observed_attempts"] == 0
        and previous_status is not None
        and (previous_status != "PREPARED_NOT_SENT" or previous_dispatch)):
        from .recovery_registry import lookup_mechanism
        if lookup_mechanism(
            "source_review_claim",
            "G2_PREFLIGHT_FALSE_FRESH_WITH_HISTORICAL_REQUEST_WINDOW"
        ) != "RECONCILE_OWNED_CLAIM_BEFORE_ANY_NEW_SOURCE_SEND":
            raise ValueError("No verified recovery for historical G2 claim")
        if (previous_status in {"SUBMITTED_OR_UNCERTAIN",
                                "NO_RESPONSE_UNRESOLVED",
                                "LEGACY_SENT_NO_RESPONSE"} or
            (previous_status == "PREPARED_NOT_SENT" and previous_dispatch)):
            state = "AMBIGUOUS_OLD_SEND_NO_RESUBMISSION"
        else:
            state = "RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND"
    elif (observed["recorded_status"] == "NEW_ATTEMPT_REQUIRES_EXPLICIT_REQUEST"
          and observed["observed_attempts"] == 0):
        state = "FRESH_INTERNAL_SELENIUM_QA_READY_UNDER_STANDING_CONTRACT"
    elif observed["recorded_status"] == "ALREADY_COMPLETED_NO_RESUBMISSION":
        state = "EXISTING_PASS_MUST_NOT_BE_REPEATED"
    elif observed["recorded_status"] == "MAX_THREE_ATTEMPTS_EXHAUSTED":
        state = "EXHAUSTED_NO_MORE_REQUESTS"
    elif (observed["recorded_status"] ==
          "BLOCKED_INVALID_SOURCE_EVIDENCE_NO_SILENT_RETRY"):
        state = "SOURCE_MATH_QUOTE_EVIDENCE_REJECTED_NO_SAME_REQUEST_REPEAT"
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
        # The owner already authorized autonomous internal academic QA:
        # a new per-slide human consent is neither a product requirement nor
        # a legitimate blocker. Never confuse this with permission for a
        # different machine, paid API, retry, unknown Send or publication.
        "standing_autonomous_internal_qa_scope_applies": True,
        "separate_per_slide_owner_approval_required": False,
        "fresh_claimed_internal_selenium_review_ready": (
            state == "FRESH_INTERNAL_SELENIUM_QA_READY_UNDER_STANDING_CONTRACT"),
        "certified_presend_same_claim_recovery_ready": (
            state == "CERTIFIED_PRESEND_SAME_CLAIM_RECOVERY_READY"),
        "live_browser_ownership_must_be_verified_at_dispatch": True,
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
