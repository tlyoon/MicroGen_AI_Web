"""Read-only original-source math consensus from an approved external review window.

Never write to original queue, infer human review, approve TTS, or publish.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from .scoped_original_math_review_window import inspect_window, historical_evidence
from .ai_academic_web_review import build_review_job
from .ai_academic_review_consensus import (
    _independently_check_saved_pass, _canonical_academic_rationale,
    reconcile_actual_review_queue,
)


def _sha(file: Path) -> str:
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def reconcile_approved_original_math_window(*, window_root:Path)->dict:
    w=Path(window_root).absolute()
    state=inspect_window(window_root=w)
    if (state["status"]!="RESPONSE_CAPTURED_UNVERIFIED"
        or state["new_window_confirmed_submissions"]!=1
        or state["requires_reconciliation"]):
        raise ValueError("No uniquely captured, review-pending original response")
    manifest_path=w/"window_manifest.json"
    cp=w/"separate_window_checkpoint.json"
    if (manifest_path.is_symlink() or cp.is_symlink()
        or not manifest_path.is_file() or not cp.is_file()):
        raise ValueError("Original user-approved scope unavailable")
    manifest=json.loads(manifest_path.read_text(encoding="utf8"))
    if (manifest["slide"]!=1
        or manifest["review_mode"]!="INDEPENDENT_CHALLENGE"
        or manifest["student_publication_authorized"] is not False
        or manifest["closed_to_main_original_queue_mutation"] is not True):
        raise ValueError("Untrusted original source-review scope")
    original=Path(manifest["original_folder"]).absolute()
    queue=Path(manifest["original_queue_root"]).absolute()
    current=historical_evidence(queue_root=queue,original_folder=original,slide=1)
    if current!=manifest["parent_historical"]:
        raise ValueError("The immutable original textbook/review history changed")

    first_file=queue/"slide_001_initial_review.json"
    second_file=w/"slide_001_newwindow_independent_challenge_captured.json"
    if (not second_file.is_file() or second_file.is_symlink()
        or second_file.stat().st_size<8 or second_file.stat().st_size>250000):
        raise ValueError("External independent source witness is unavailable")
    cp_state=json.loads(cp.read_text(encoding="utf8"))
    captures=[event for event in cp_state.get("history",[])
              if event.get("event")=="RESPONSE_CAPTURED_SOURCE_MATH_UNVERIFIED"]
    if (len(captures)!=1 or captures[0].get("receipt_sha256")!=_sha(second_file)
        or cp_state.get("active_claim") is not None):
        raise ValueError("Independent response does not match durable owned claim")

    first=json.loads(first_file.read_text(encoding="utf8"))
    second=json.loads(second_file.read_text(encoding="utf8"))
    job=build_review_job(folder=original,slide_numbers=[1])
    a=_independently_check_saved_pass(folder=original,job=job,record=first,
                                      mode="INITIAL_REVIEW")
    b=_independently_check_saved_pass(folder=original,job=job,record=second,
                                      mode="INDEPENDENT_CHALLENGE")
    if len(a)!=len(b) or _sha(first_file)==_sha(second_file):
        raise ValueError("Independent source reasoning not proven distinct")

    source_agreement=[]
    unresolved=[]
    for unit,x,y in zip(job["slides"][0]["utterances"],a,b):
        agreeing=(x["utterance_id"]==y["utterance_id"]==unit["id"]
            and x["spoken_sha256"]==y["spoken_sha256"]==unit["spoken_sha256"]
            and x["verdict"]==y["verdict"]=="SUPPORTED"
            and x["target_id"]==y["target_id"] and x["target_id"] is not None
            and x["source_page"]==y["source_page"]
            and x["exact_textbook_quote_verified"] is True
            and y["exact_textbook_quote_verified"] is True
            and x["text_target_pdf_bbox_pt"]==y["text_target_pdf_bbox_pt"]
            and _canonical_academic_rationale(x["math_explanation"]) !=
                _canonical_academic_rationale(y["math_explanation"]))
        if agreeing:
            source_agreement.append({
                "utterance_id":unit["id"],
                "spoken_sha256":unit["spoken_sha256"],
                "source_page":x["source_page"],
                "target_id":x["target_id"],
                "bbox_pdf_pt":x["text_target_pdf_bbox_pt"],
                "human_academic_approval":False,
            })
        else:
            unresolved.append(unit["id"])

    base=reconcile_actual_review_queue(queue_root=queue,folder=original)
    all_base_ids={x["utterance_id"] for x in base["accepted_ai_evidence"]}
    extra_ids={x["utterance_id"] for x in source_agreement}
    if all_base_ids.intersection(extra_ids):
        raise ValueError("Same utterance cannot be approved twice across scopes")
    total=base["original_utterances"]
    accepted=len(all_base_ids)+len(extra_ids)
    if accepted>total:
        raise ValueError("Untrusted source mathematics agreement count")
    return {
        "status":"ORIGINAL_SOURCE_TWO_PASS_AI_CONSENSUS_REVALIDATED",
        "original_utterances":total,
        "original_queue_ai_agreements":len(all_base_ids),
        "approved_separate_window_ai_agreements":len(extra_ids),
        "combined_independent_source_witnessed_ai_agreements":accepted,
        "combined_math_pending_or_disputed":total-accepted,
        "approved_window_disputed_utterances":unresolved,
        "approved_source_evidence":source_agreement,
        "original_source_sha256":current["source_sha256"],
        "first_pass_receipt_sha256":_sha(first_file),
        "challenge_receipt_sha256":_sha(second_file),
        "AI_consensus_is_formal_mathematical_proof":False,
        "authentic_human_academic_approval":False,
        "all_math_source_units_agreed":accepted==total,
        "genuine_Kore_TTS_authorized":False,
        "student_publication_authorized":False,
        "read_only_reconciled":True,
    }


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-root",type=Path,required=True)
    args=parser.parse_args(argv)
    print(json.dumps(reconcile_approved_original_math_window(
        window_root=args.window_root),indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
