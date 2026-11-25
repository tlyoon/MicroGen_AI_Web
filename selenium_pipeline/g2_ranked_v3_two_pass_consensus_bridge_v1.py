"""Admit ONLY genuine two-pass source-validated G2 V3 reviewer replies.

Original Serway G2 §1.3 has 27 original, two V1 focused accepted source-AI
units, while nine separately ranked physical V3 tasks are merely prepared.
This independent read-only reconciler cannot count a V3 source task, a
claimed Send, a one-pass response, unverified model text, or duplicate
legacy utterance as scientific agreement. It verifies exact raw persisted
Neon/High first+challenge model responses via the existing independent V1
source review validator, and creates a new, immutable G2+V1+V3 source
acceptance receipt only for physically textbook-backed genuine agreements.
Scientific double-pass source-AI is not human formal math/audio/video QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from .ai_academic_review_consensus import reconcile_actual_review_queue
from .ai_academic_review_consensus import _canonical_academic_rationale
from .figure_source_identity import _sha,require
from .g2_focused_source_consensus_bridge_v1 import (
    _read_model_pass, reconcile as verify_existing_v1,
    REPORT_FOLDER as V1_ROOT)
from .g2_ranked_source_review_candidate_v3 import ROOT as CANDIDATE_ROOT
from .g2_ranked_v3_owned_selenium_handoff_v1 import (
    _verify,ROOT as REVIEW_ROOT)
from .recovery_registry import lookup_mechanism

KIND="g2_ranked_v3_two_pass_consensus"
SIGNATURE="G2_RANKED_V3_INITIAL_CHALLENGE_EVIDENCE_NOT_IN_SOURCE_AI_LEDGER"
MECHANISM="REVALIDATE_ACTUAL_V3_TWO_MODEL_PASSES_AND_COUNT_ONLY_NEW_AGREEMENTS"
ROOT="G2_RANKED_V3_INDEPENDENT_CONSENSUS_V1"
SCOPE_PATTERN=re.compile(r"[0-9a-f]{64}\Z")
PASS_STATUS="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"
AI_AGREE="G2_RANKED_V3_TWO_PASS_SOURCE_AI_AGREEMENT_UNAPPROVED"
AI_DISPUTE="G2_RANKED_V3_TWO_PASS_SOURCE_AI_DISPUTED_UNAPPROVED"
SUMMARY_STATUS="G2_ORIGINAL_V1_V3_INDEPENDENT_SOURCE_AI_RECONCILED_NO_RELEASE"


def _canonical(data:dict)->bytes:
    return (json.dumps(data,sort_keys=True,ensure_ascii=False,
                       separators=(",",":"),allow_nan=False)+"\n").encode("utf8")


def _claim_ready(folder:Path)->bool:
    """Both model replies must be durable. Uncertain/partial are NEVER Sends."""
    from .academic_review_checkpoint import _load
    if not folder.is_dir() or folder.is_symlink():
        return False
    request=folder/"request_state.json"
    raw=folder/"model_response_untrusted.txt"
    if not request.is_file() or not raw.is_file():
        return False
    require(not request.is_symlink() and not raw.is_symlink(),
            "Redirected G2 V3 model reply claim")
    current=_load(folder)
    return current.get("status")==PASS_STATUS


def _validate_two_pass(*,folder:Path,queue:Path,scope:Path)->dict|None:
    """Verify actual source-model bytes and distinct math before one promotion."""
    require(scope.is_dir() and not scope.is_symlink()
            and SCOPE_PATTERN.fullmatch(scope.name),
            "Untrusted V3 science model scope")
    candidate=queue.parent/CANDIDATE_ROOT/(scope.name+".json")
    require(candidate.is_file() and not candidate.is_symlink(),
            "V3 science response cannot inherit an unrelated source task")
    row,job=_verify(
        folder=folder,queue_root=queue,candidate_file=candidate)
    require(row["scope_sha256"]==scope.name
            and row["original_utterance_id"]==
                job["slides"][0]["utterances"][0]["id"],
            "G2 ranked source task changed before two-pass reconciliation")
    initial=scope/"initial_request"
    challenge=scope/"challenge_request"
    if not _claim_ready(initial) or not _claim_ready(challenge):
        return None
    a,sha_a=_read_model_pass(folder=folder,job=job,
                            checkpoint=initial,mode="INITIAL_REVIEW")
    b,sha_b=_read_model_pass(folder=folder,job=job,
                            checkpoint=challenge,mode="INDEPENDENT_CHALLENGE")
    require(sha_a!=sha_b and len(a["rows"])==len(b["rows"])==1,
            "G2 ranked science reviewers not genuinely independent")
    x,y=a["rows"][0],b["rows"][0]
    unit=job["slides"][0]["utterances"][0]
    require(x["utterance_id"]==y["utterance_id"]==unit["id"]
            and x["spoken_sha256"]==y["spoken_sha256"]==
                unit["spoken_sha256"],
            "Original G2 spoken unit changed between V3 review passes")
    actual_target=row["corrected_ranked_physical_target_id"]
    agreed=bool(
        x["verdict"]==y["verdict"]=="SUPPORTED"
        and x["target_id"]==y["target_id"]==actual_target
        and x["source_page"]==y["source_page"]
        and x["exact_textbook_quote_verified"] is True
        and y["exact_textbook_quote_verified"] is True
        and _canonical_academic_rationale(x["math_explanation"])!=
            _canonical_academic_rationale(y["math_explanation"]))
    record={
        "schema_version":1,
        "status":AI_AGREE if agreed else AI_DISPUTE,
        "scope_sha256":scope.name,
        "original_utterance_id":row["original_utterance_id"],
        "original_spoken_sha256":unit["spoken_sha256"],
        "original_publisher_pdf_sha256":row[
            "original_source_inputs_sha256"]["source.pdf"],
        "ranked_original_physical_target_id":actual_target,
        "ranked_source_candidate_sha256":_sha(candidate),
        "initial_actual_model_response_sha256":sha_a,
        "challenge_actual_model_response_sha256":sha_b,
        "two_distinct_actual_source_model_passes":True,
        "initial_and_challenge_prompts_SHA_different":(
            row["new_initial_prompt_sha256"]!=row[
                "new_challenge_prompt_sha256"]),
        "source_math_AI_agreed":agreed,
        "independent_formal_math_proof":False,
        "human_academic_approval":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "student_publication_authorized":False,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
    }
    path=scope/"two_pass_evidence.json"
    require(not path.is_symlink(),"Redirected V3 immutable two-pass result")
    content=_canonical(record)
    if path.exists():
        require(path.is_file() and path.read_bytes()==content,
                "Old V3 two-pass evidence mutated on restart")
    else:
        with path.open("xb") as sink:
            sink.write(content);sink.flush();os.fsync(sink.fileno())
    return record


def reconcile(*,folder:Path,queue_root:Path,
              base_v1_receipt:Path,output_root:Path|None=None,
              v1_validator=None,original_consensus_reader=None)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "G2 V3 independent actual-model consensus bridge not registered")
    folder,queue_root,base_v1_receipt=(
        Path(folder).absolute(),Path(queue_root).absolute(),
        Path(base_v1_receipt).absolute())
    require(folder.is_dir() and queue_root.is_dir()
            and not folder.is_symlink() and not queue_root.is_symlink()
            and not queue_root.is_relative_to(folder)
            and base_v1_receipt.parent==queue_root.parent/V1_ROOT
            and base_v1_receipt.is_file()
            and not base_v1_receipt.is_symlink(),
            "Original existing independently revalidated G2 V1 bridge required")
    # Historical V1 used text-mode JSON writes on Windows: the filename was
    # SHA256 of LF-serialized JSON, while its ON-DISK bytes became CRLF.
    # Reconstruct that exact canonical V1 filename formula, and separately
    # ensure the decoded saved document is unchanged. Do not "repair" or
    # rewrite the original receipt to change its raw evidence SHA.
    saved_text=base_v1_receipt.read_text("utf8")
    prior=json.loads(saved_text)
    canonical_v1=json.dumps(prior,indent=2,sort_keys=True)+"\n"
    require(saved_text==canonical_v1 and base_v1_receipt.stem==
                hashlib.sha256(canonical_v1.encode("utf8")).hexdigest()[:32],
            "Original V1 source consensus canonical evidence changed")
    # A hash-looking V1 receipt is NOT sufficient by itself; independently
    # rebuild V1's math/source verdicts from original raw model responses.
    current=(v1_validator or verify_existing_v1)(
        folder=folder,queue_root=queue_root)
    require(Path(current["receipt"]).absolute()==base_v1_receipt
            and current["combined_source_AI_agreements"]==
                prior["combined_source_AI_agreements"]
            and current["new_focused_utterance_ids"]==
                prior["new_focused_utterance_ids"],
            "Existing V1 agreement receipt is stale or not revalidated")
    original=json.loads((queue_root/"queue.json").read_text("utf8"))
    required=original["expected_utterances"]
    require(prior["status"]==
            "G2_ORIGINAL_AND_FOCUSED_SOURCE_AI_EVIDENCE_RECONCILED_NO_RELEASE"
            and prior["source_sha256"]==_sha(folder/"source.pdf")
            and prior["original_total_utterances"]==required
            and prior["combined_source_AI_agreements"]<=required
            and prior["new_provider_requests"]==0
            and prior["student_publication_authorized"] is False
            and isinstance(prior["new_focused_utterance_ids"],list),
            "Original G2 independently sourced V1 consensus not authoritative")
    src=_sha(folder/"source.pdf")
    root=queue_root.parent/REVIEW_ROOT
    require(not root.is_symlink(),"Redirected V3 original reviewer evidence")
    complete=[]
    attempted=0
    if root.exists():
        require(root.is_dir(),"V3 original reviewer root is not a folder")
        scopes=sorted(root.iterdir())
        require(len(scopes)<=128
                and all(x.is_dir() and not x.is_symlink()
                        and SCOPE_PATTERN.fullmatch(x.name)
                        for x in scopes),
                "Unexpected G2 V3 saved model response scope")
        for scope in scopes:
            attempted+=1
            result=_validate_two_pass(
                folder=folder,queue=queue_root,scope=scope)
            if result is not None:
                require(result["original_publisher_pdf_sha256"]==src
                        and result["new_browser_sends"]==0
                        and result["human_academic_approval"] is False,
                        "Unapproved V3 science result cannot be promoted")
                complete.append(result)
    count_new=0
    if any(row["source_math_AI_agreed"] for row in complete):
        # This expensive 85-unit independent recheck is needed only when
        # actual new two-pass V3 model replies exist; avoid overhead otherwise.
        historic=(original_consensus_reader or
            reconcile_actual_review_queue)(
                queue_root=queue_root,folder=folder)
        require(historic["original_utterances"]==required
                and historic["agreed_source_witnessed_segments"]==
                    prior["original_two_pass_source_AI_agreements"]
                and historic["AI_consensus_is_formal_math_proof"] is False
                and historic["student_publication_authorized"] is False,
                "Original source-AI agreement drift before V3 admission")
        old={x["utterance_id"] for x in historic["accepted_ai_evidence"]}
        old.update(prior["new_focused_utterance_ids"])
        new=set()
        for row in complete:
            if not row["source_math_AI_agreed"]:
                continue
            uid=row["original_utterance_id"]
            if uid in old:
                continue
            require(uid not in new,
                    "Duplicate original G2 unit counted via two V3 scopes")
            new.add(uid)
        count_new=len(new)
    combined=prior["combined_source_AI_agreements"]+count_new
    require(0<=combined<=required,
            "G2 independently accepted source-AI count exceeds original units")
    record={
        "schema_version":1,"status":SUMMARY_STATUS,
        "source_sha256":src,
        "original_queue_sha256":_sha(queue_root/"queue.json"),
        "original_V1_bridge_receipt_sha256":_sha(base_v1_receipt),
        "original_total_utterances":required,
        "original_V1_two_pass_source_AI_agreements":
            prior["combined_source_AI_agreements"],
        "saved_V3_model_scopes_seen":attempted,
        "genuine_V3_two_pass_records":len(complete),
        "new_V3_independent_source_AI_agreements":count_new,
        "new_V3_source_AI_utterance_ids":sorted(new) if count_new else [],
        "combined_source_AI_agreements":combined,
        "pending_or_disputed_source_AI":required-combined,
        "actual_V3_two_pass_receipt_sha256":sorted(
            _sha(root/x["scope_sha256"]/"two_pass_evidence.json")
            for x in complete),
        "new_provider_requests":0,"paid_gemini_API_calls":0,
        "all_85_source_AI_agreements_observed":combined==required,
        "all_independent_acoustic_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "formal_human_math_approval":False,
        "student_publication_authorized":False,
    }
    out=Path(output_root or queue_root.parent/ROOT).absolute()
    require(not out.is_symlink()
            and not out.is_relative_to(folder)
            and not out.is_relative_to(queue_root),
            "G2 V3 independent consensus output is not an original source")
    out.mkdir(parents=True,exist_ok=True)
    scope=hashlib.sha256(_canonical(record)).hexdigest()
    dest=out/(scope+".json")
    require(not dest.is_symlink(),"Redirected V3 actual source consensus")
    body=_canonical(record)
    if dest.exists():
        require(dest.is_file() and dest.read_bytes()==body,
                "Original G2 V3 consensus altered after source acceptance")
    else:
        with dest.open("xb") as writer:
            writer.write(body);writer.flush();os.fsync(writer.fileno())
    return {**record,"receipt":str(dest),"scope_sha256":scope}


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    p.add_argument("--queue-root",required=True,type=Path)
    p.add_argument("--base-v1-receipt",required=True,type=Path)
    args=p.parse_args(argv)
    print(json.dumps(reconcile(
        folder=args.folder,queue_root=args.queue_root,
        base_v1_receipt=args.base_v1_receipt),
        indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
