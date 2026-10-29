"""One explicitly scoped ORIGINAL source-math challenge with durable capture.

Only the separately approved window's existing single-tick dispatcher may send.
No first-review queue mutation, automatic retries, TTS, publication or approval.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

from .scoped_original_math_review_window import (
    inspect_window, dispatch_single_approved_window_tick, historical_evidence,
)
from .ai_academic_review_queue import _check_queue
from .ai_academic_web_review import build_review_job, run_web_review
from .ai_academic_review_consensus import _independently_check_saved_pass


def capture_one_scoped_source_challenge(*, window_root: Path,
                                        transport=None, now: float | None=None) -> dict:
    w=Path(window_root).absolute()
    observed=inspect_window(window_root=w,now=now)
    if not observed["eligible_for_single_authorized_dispatch"]:
        return {
            "status":"NO_AUTHORIZED_SOURCE_REVIEW_TICK",
            "model_request_sent":False,
            "student_publication_authorized":False,
        }
    m_path=w/"window_manifest.json"
    if not m_path.is_file() or m_path.is_symlink():
        raise ValueError("Existing approved source review window manifest unavailable")
    manifest=json.loads(m_path.read_text(encoding="utf8"))
    original=Path(manifest["original_folder"]).absolute()
    queue=Path(manifest["original_queue_root"]).absolute()
    slide=manifest["slide"]
    if slide != 1 or manifest["review_mode"]!="INDEPENDENT_CHALLENGE":
        raise ValueError("Only explicitly approved original slide-1 challenge supported")
    receipt=w/f"slide_{slide:03d}_newwindow_independent_challenge_captured.json"
    if receipt.exists() or receipt.is_symlink():
        return {"status":"EXISTING_SOURCE_RESPONSE_REQUIRES_RECONCILIATION",
                "model_request_sent":False,"student_publication_authorized":False}

    # Preflight all source, first-pass and prior attempt evidence BEFORE
    # claiming any new academic provider request.
    _check_queue(queue_root=queue,folder=original,slide=slide,
                 mode="INDEPENDENT_CHALLENGE")
    job=build_review_job(folder=original,slide_numbers=[slide])
    if job["utterance_count"]<1:
        raise ValueError("Real source review job has no original narration units")
    original_history=historical_evidence(queue_root=queue,
                                          original_folder=original,slide=slide)
    if original_history!=manifest["parent_historical"]:
        raise ValueError("Original history diverged from user-approved window")

    def send_once():
        # The original web transport's positive send return is based on both
        # registered user turn and cleared composer. It returns only after a
        # stopped, complete structured model response, otherwise raises.
        reviewed=run_web_review(
            folder=original,job=job,mode="INDEPENDENT_CHALLENGE",
            transport=transport)
        _independently_check_saved_pass(
            folder=original,job=job,record=reviewed,mode="INDEPENDENT_CHALLENGE")
        if historical_evidence(queue_root=queue,original_folder=original,
                               slide=slide)!=original_history:
            raise ValueError("Original first pass/history changed during review")
        if reviewed.get("student_publication_authorized") is not False:
            raise ValueError("Model may never self-authorize publication")
        # Save only the actually source-witnessed, STILL academically
        # unapproved independent candidate into the separate AppData window.
        with receipt.open("x",encoding="utf8") as handle:
            json.dump(reviewed,handle,sort_keys=True,indent=2,ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return {
            "outcome":"CONFIRMED_SUBMITTED",
            "user_turn_created":True,
            "composer_cleared":True,
            "captured_response_receipt":str(receipt),
        }

    result=dispatch_single_approved_window_tick(
        window_root=w,send_once=send_once,now=now)
    return {
        **result,
        "original_math_source_candidate_captured":
            result.get("status")=="RESPONSE_CAPTURED_UNVERIFIED",
        "independent_mathematics_agreed":False,
        "student_publication_authorized":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--window-root",required=True,type=Path)
    p.add_argument("--allow-one-original-academic-challenge",action="store_true")
    args=p.parse_args(argv)
    if not args.allow_one_original_academic_challenge:
        out={"mode":"READ_ONLY_NO_GEMINI_TRAFFIC",
             **inspect_window(window_root=args.window_root)}
    else:
        out=capture_one_scoped_source_challenge(window_root=args.window_root)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
