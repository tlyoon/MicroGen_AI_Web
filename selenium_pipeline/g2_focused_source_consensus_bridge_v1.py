"""Read-only merger of original G2 source AI consensus and distinct focused QA.

No original response is replayed, no original q/receipt is modified. A new
single-utterance two-pass agreement is admitted ONLY after independent raw
reply provenance, actual model/High identity, source geometry and mathematics
checks are rerun from saved bytes. It does not close acoustic/video or grant
human approval/publication. Writes a separate SHA-addressed audit receipt.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

from .academic_review_checkpoint import (
    _load, fingerprint, _neon_model_witness)
from .ai_academic_review_consensus import (
    reconcile_actual_review_queue, _independently_check_saved_pass,
    _actual_model_rows, _canonical_academic_rationale)
from .ai_academic_web_review import (
    review_instructions, validate_source_demoted_review)
from .figure_source_identity import _sha, require
from .g2_distinct_focused_source_review_v1 import (
    plan, REVIEW_ROOT_NAME)
from .series_gemini import decode_storyboard_response

REPORT_FOLDER="G2_FOCUSED_SOURCE_AGREEMENT_BRIDGE_V1"
_PATTERN=re.compile(r"s(\d{3})\.utterance\.\d{3}\Z")


def _read_model_pass(*,folder:Path,job:dict,checkpoint:Path,
                     mode:str)->tuple[dict,str]:
    require(checkpoint.is_dir() and not checkpoint.is_symlink(),
            "No immutable source reviewer checkpoint")
    state=_load(checkpoint)
    text=review_instructions(job,mode=mode)
    expected=fingerprint(
        request_text=text,
        source_hashes={
            "source.pdf":job["source_sha256"],
            "slides.pdf":job["slides_sha256"],
            "script.txt":job["script_sha256"]},
        review_mode=mode)
    raw_path=checkpoint/"model_response_untrusted.txt"
    claim=checkpoint/"dispatch_attempted.claim"
    require(state.get("status")=="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"
            and state.get("review_mode")==mode
            and state.get("request_fingerprint")==expected
            and state.get("prompt_sha256")==
                hashlib.sha256(text.encode("utf8")).hexdigest()
            and state.get("can_auto_retry") is False
            and all(state.get(k+"_sha256")==job[k+"_sha256"]
                    for k in ("source","slides","script"))
            and claim.is_file() and not claim.is_symlink()
            and claim.read_text("utf8").strip()==expected
            and raw_path.is_file() and not raw_path.is_symlink()
            and raw_path.stat().st_size<=1_800_000,
            "Source review claim, actual model text or original source changed")
    raw=raw_path.read_bytes().decode("utf8")
    sha=hashlib.sha256(raw.encode("utf8")).hexdigest()
    require(bool(raw.strip())
            and state.get("response_sha256")==sha
            and state.get("response_length_chars")==len(raw),
            "Original model-response bytes not identical to claimed result")
    _neon_model_witness(checkpoint,expected,
                        expected_response_sha256=sha)
    result=validate_source_demoted_review(
        folder=folder,job=job,response=decode_storyboard_response(raw),
        mode=mode)
    rows=_independently_check_saved_pass(
        folder=folder,job=job,record=result,mode=mode)
    require(_actual_model_rows(result,rows)==job["utterance_count"]==1,
            "Single-utterance response must come from the actual model")
    return result,sha


def _focused_evidence(*,folder:Path,queue_root:Path,scope:Path)->dict:
    report_file=scope/"two_pass_evidence.json"
    require(scope.is_dir() and not scope.is_symlink()
            and report_file.is_file() and not report_file.is_symlink()
            and report_file.stat().st_size<8000,
            "Missing or redirected focused two-pass receipt")
    record=json.loads(report_file.read_text("utf8"))
    require(type(record) is dict
            and record.get("schema_version")==1
            and record.get("status") in (
                "FOCUSED_TWO_PASS_SOURCE_AI_AGREEMENT_UNAPPROVED",
                "FOCUSED_TWO_PASS_DISPUTED_NO_PROMOTION")
            and type(record.get("utterance_id")) is str
            and _PATTERN.fullmatch(record["utterance_id"])
            and record.get("original_g2_segments_promoted")==0
            and record.get("human_academic_approval") is False
            and record.get("independent_acoustic_QA_complete") is False
            and record.get("student_publication_authorized") is False,
            "Untrusted focused science result")
    slide=int(_PATTERN.fullmatch(record["utterance_id"]).group(1))
    prepared=plan(folder=folder,queue_root=queue_root,
                  slide=slide,utterance_id=record["utterance_id"])
    require(scope.name==prepared["scope_sha256"]
            and record.get("scope_sha256")==prepared["scope_sha256"]
            and record.get("source_sha256")==prepared["source_sha256"]
            and record.get("original_historical_claim_sha256")==
                prepared["original_claim_sha256"],
            "Focused result is not the unique source-locked original claim")
    unit=prepared["job"]["slides"][0]["utterances"][0]
    require(record.get("spoken_sha256")==unit["spoken_sha256"],
            "Narration in original textbook claim changed")
    admission=scope/"admission.json"
    require(admission.is_file() and not admission.is_symlink()
            and admission.stat().st_size<9000,
            "Original distinct-task admission unavailable")
    admiss=json.loads(admission.read_text("utf8"))
    require(admiss.get("status")=="NEW_SUBSTANTIVE_SOURCE_QUOTE_CHECK_NOT_ORIGINAL_RETRY"
            and admiss.get("scope_sha256")==prepared["scope_sha256"]
            and admiss.get("old_claim_sha256")==prepared["original_claim_sha256"]
            and admiss.get("source_sha256")==prepared["source_sha256"]
            and admiss.get("prompt_sha256")==prepared["new_prompt_sha256"]
            and admiss.get("health_model_family")=="neon"
            and admiss.get("old_request_resubmitted") is False
            and admiss.get("student_publication_authorized") is False,
            "New review admission was not source/model authenticated")
    a,sha_a=_read_model_pass(
        folder=folder,job=prepared["job"],
        checkpoint=scope/"initial_request",mode="INITIAL_REVIEW")
    b,sha_b=_read_model_pass(
        folder=folder,job=prepared["job"],
        checkpoint=scope/"challenge_request",mode="INDEPENDENT_CHALLENGE")
    x,y=a["rows"][0],b["rows"][0]
    agreed=bool(
        x["verdict"]==y["verdict"]=="SUPPORTED"
        and x["target_id"]==y["target_id"] is not None
        and x["source_page"]==y["source_page"]
        and x["exact_textbook_quote_verified"] is True
        and y["exact_textbook_quote_verified"] is True
        and _canonical_academic_rationale(x["math_explanation"])
            !=_canonical_academic_rationale(y["math_explanation"]))
    require(sha_a!=sha_b
            and record.get("first_response_sha256")==sha_a
            and record.get("challenge_response_sha256")==sha_b
            and record.get("two_actual_model_review_passes") is True
            and record.get("two_distinct_review_modes") is True
            and record.get("source_quote_physically_witnessed_in_both") is True
            and record.get("source_math_AI_agreed") is agreed
            and (record["status"]==
                 ("FOCUSED_TWO_PASS_SOURCE_AI_AGREEMENT_UNAPPROVED"
                  if agreed else "FOCUSED_TWO_PASS_DISPUTED_NO_PROMOTION")),
            "Saved two-pass agreement cannot reproduce from original model bytes")
    return {
        "utterance_id":unit["id"],"spoken_sha256":unit["spoken_sha256"],
        "source_math_AI_agreed":agreed,
        "two_pass_receipt_sha256":_sha(report_file),
        "first_response_sha256":sha_a,
        "challenge_response_sha256":sha_b,
    }


def reconcile(*,folder:Path,queue_root:Path,
              output_parent:Path|None=None,
              original_consensus:dict|None=None)->dict:
    """No browser access, no API, no original-source/queue modifications.

    The production G2 supervisor may pass its already independently checked
    original consensus. Avoid duplicating an expensive 85-utterance PDF
    revalidation under the same source-locked supervisor owner.
    """
    folder,queue_root=Path(folder).absolute(),Path(queue_root).absolute()
    original=(reconcile_actual_review_queue(
        queue_root=queue_root,folder=folder)
        if original_consensus is None else original_consensus)
    require(original["status"]==
                "INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE"
            and original["AI_consensus_is_formal_math_proof"] is False
            and original["student_publication_authorized"] is False,
            "Full original G2 independent evidence not attested")
    accepted={r["utterance_id"] for r in original["accepted_ai_evidence"]}
    unresolved={r["utterance_id"] for r in original["unresolved"]}
    require(len(accepted)==original["agreed_source_witnessed_segments"]
            and len(accepted)+len(unresolved)==original["original_utterances"]
            and not accepted.intersection(unresolved),
            "Original source-grounded AI inventory inconsistent")
    focused_dir=queue_root.parent/REVIEW_ROOT_NAME
    new=[]
    observed=[]
    if focused_dir.exists():
        require(focused_dir.is_dir() and not focused_dir.is_symlink(),
                "Focused review root redirected")
        scopes=list(focused_dir.iterdir())
        require(len(scopes)<=200
                and all(s.is_dir() and not s.is_symlink()
                        and re.fullmatch("[a-f0-9]{64}",s.name)
                        for s in scopes),
                "Unexpected or unbounded source-focused review scope")
        for scope in scopes:
            record_path=scope/"two_pass_evidence.json"
            if not record_path.exists():
                continue  # pending first or second reviewer; do not claim
            outcome=_focused_evidence(
                folder=folder,queue_root=queue_root,scope=scope)
            observed.append(outcome)
            if outcome["source_math_AI_agreed"]:
                uid=outcome["utterance_id"]
                require(uid in accepted or uid in unresolved,
                        "Focused unit is absent from original source inventory")
                if uid in unresolved:
                    require(uid not in new,
                            "Duplicate focused AI math reviewer evidence")
                    new.append(uid)
    combined=len(accepted)+len(new)
    require(0<=combined<=original["original_utterances"],
            "Focused evidence cannot expand original 85-utterance inventory")
    report={
        "schema_version":1,
        "status":"G2_ORIGINAL_AND_FOCUSED_SOURCE_AI_EVIDENCE_RECONCILED_NO_RELEASE",
        "source_sha256":_sha(folder/"source.pdf"),
        "original_total_utterances":original["original_utterances"],
        "original_two_pass_source_AI_agreements":len(accepted),
        "additional_distinct_two_pass_source_AI_agreements":len(new),
        "combined_source_AI_agreements":combined,
        "pending_or_disputed_source_AI":original["original_utterances"]-combined,
        "new_focused_utterance_ids":sorted(new),
        "focused_evidence_sha256":sorted(
            r["two_pass_receipt_sha256"] for r in observed),
        "original_G2_claims_modified":False,
        "original_source_PDF_modified":False,
        "new_provider_requests":0,
        "all_85_academic_reviewed":combined==original["original_utterances"],
        "AI_consensus_is_formal_math_proof":False,
        "independent_acoustic_QA_complete":False,
        "G3_acceptance_complete":False,
        "student_publication_authorized":False,
    }
    root=Path(output_parent or (queue_root.parent/REPORT_FOLDER)).absolute()
    require(not root.is_relative_to(folder)
            and not root.is_relative_to(queue_root)
            and not root.is_symlink(),
            "G2 reconciler must not mutate original publisher or historic queue")
    root.mkdir(parents=True,exist_ok=True)
    serialized=json.dumps(report,indent=2,sort_keys=True)+"\n"
    receipt=root/(hashlib.sha256(serialized.encode()).hexdigest()[:32]+".json")
    require(not receipt.is_symlink(),"Cannot use redirected G2 audit receipt")
    if receipt.exists():
        require(receipt.is_file() and receipt.read_text("utf8")==serialized,
                "Previously verified original+focused G2 report modified")
    else:
        with receipt.open("x",encoding="utf8") as writer:
            writer.write(serialized)
            writer.flush();os.fsync(writer.fileno())
    return {**report,"receipt":str(receipt)}
