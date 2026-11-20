"""One source-free Neon/High two-PDF qualification AFTER retired Pro attempts.

Original Serway source and slides are never uploaded. The two Pro diagnostic
claims and source-review claims are immutable. One new owned Neon/High attempt
is permitted only after registered recovery, source/old-incident verification,
and a real source-free model/Thinking preflight. A possibly consumed Send is
never retried. Success proves only PDF response transport, NOT G2 science.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time

from .academic_dual_pdf_capability import (
    _verify_unsafe_source_claims, _create_pdf, _exact, _new,
    existing_outcome as original_pdf_outcome, ROOT as V1_ROOT,
)
from .academic_dual_pdf_profile_repair_v2 import (
    existing_outcome as repaired_pdf_outcome, ROOT as V2_ROOT,
)
from .academic_provider_requalification import _REGISTERED
from .figure_source_identity import require
from .recovery_registry import lookup_mechanism

ROOT = ".microgen_g2_neon_high_distinct_two_pdf_v1"
SIGNATURE = "G2_NEW_NEON_HIGH_MODEL_AFTER_RETIRED_PRO_PDF_CLAIMS"
MECHANISM = "ONE_NEW_IMMUTABLE_NEON_HIGH_TWO_PDF_SEND_THEN_SOURCE_ONLY_RECONCILIATION"
STATUS_OK = "NEON_HIGH_TWO_PDF_SOURCE_FREE_RESPONSE_VERIFIED"
STATUS_BAD = "NEON_HIGH_TWO_PDF_SOURCE_FREE_RESPONSE_UNVERIFIED"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _legacy(*, queue_root: Path, checkpoint_parent: Path, source_sha: str,
            prior_slides: list[int]) -> tuple[str, float, str, str]:
    incident, last = _verify_unsafe_source_claims(
        queue_root=queue_root, source_sha=source_sha,
        prior_slides=prior_slides, family="pro")
    kw=dict(queue_root=queue_root, checkpoint_parent=checkpoint_parent,
            source_sha=source_sha, prior_slides=prior_slides, family="pro")
    first=original_pdf_outcome(**kw)
    second=repaired_pdf_outcome(**kw)
    require(first is not None and second is not None
            and first.get("status") == "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED"
            and second.get("status") == "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED"
            and first.get("new_source_review_send_allowed") is False
            and second.get("new_source_review_send_allowed") is False,
            "Both previous one-Send Pro PDF diagnostics must be retired")
    root=Path(checkpoint_parent).absolute()
    v1=root/V1_ROOT/source_sha/"pro"/incident/"result.json"
    v2=root/V2_ROOT/source_sha/"pro"/incident/"result.json"
    require(v1.is_file() and v2.is_file()
            and not v1.is_symlink() and not v2.is_symlink(),
            "Missing immutable historical Pro diagnostic results")
    require(lookup_mechanism("presend_capability_repair",SIGNATURE) == MECHANISM,
            "New Neon modality recovery is not registered")
    return incident,last,_sha(v1.read_bytes()),_sha(v2.read_bytes())


def _path(checkpoint_parent: Path, source_sha: str, incident: str) -> Path:
    root=Path(checkpoint_parent).absolute()
    require(root.is_dir() and not root.is_symlink()
            and re.fullmatch(r"[0-9a-f]{64}",source_sha) is not None
            and re.fullmatch(r"[0-9a-f]{64}",incident) is not None,
            "Invalid source-locked Neon checkpoint root")
    slot=root/ROOT/source_sha/incident
    require(not any(x.is_symlink() for x in (root/ROOT,
        root/ROOT/source_sha,slot)), "No linked Neon diagnostic directory")
    return slot


def _expected(source_sha: str, incident: str, v1_sha: str, v2_sha: str) -> dict:
    seed=f"MicroGen-distinct-Neon-High-Two-PDF-v1|{source_sha}|{incident}|{v1_sha}|{v2_sha}"
    nonce=_sha((seed+"|nonce").encode("ascii"))[:18]
    a=_sha((seed+"|new-A").encode("ascii"))[:18].upper()
    b=_sha((seed+"|new-B").encode("ascii"))[:18].upper()
    return {"probe":nonce,"a":a,"b":b}


def _prompt(nonce: str) -> str:
    return (
        "Independent source-free Neon High two-PDF transport qualification. "
        "These are two NEW synthetic diagnostic documents with NO textbook, "
        "student or user source content. Read BOTH attached one-page PDFs. "
        "Find the PDF_CODE in SyntheticA.pdf and SyntheticB.pdf separately. "
        "Return exactly one compact JSON object with no markdown or explanation: "
        '{"probe":"' + nonce + '","a":"<PDF_CODE from A>","b":"<PDF_CODE from B>"}. '
        "If any attachment is unreadable, answer with an error, not a guess."
    )


def _read(*, checkpoint_parent: Path, source_sha: str, incident: str,
          after: float, v1_sha: str, v2_sha: str) -> dict | None:
    slot=_path(checkpoint_parent,source_sha,incident)
    if not slot.exists():
        return None
    require(slot.is_dir() and not slot.is_symlink(),
            "Invalid previously claimed Neon transport directory")
    claim_path=slot/"claim.json"
    if not claim_path.is_file():
        # A crash after an exclusive mkdir or PDF creation cannot reset budget.
        return {"status":"PRIOR_NEON_HIGH_PDF_CLAIM_INTERRUPTED_NO_RESEND",
                "new_provider_requests":0,"new_source_review_send_allowed":False}
    require(not claim_path.is_symlink() and claim_path.stat().st_size<=9000,
            "Unsafe prior Neon claim")
    claim=json.loads(claim_path.read_text(encoding="utf8"))
    expected=_expected(source_sha,incident,v1_sha,v2_sha)
    prompt=_prompt(expected["probe"])
    require(claim.get("schema_version")==1
            and claim.get("source_sha256")==source_sha
            and claim.get("original_incident_sha256")==incident
            and claim.get("previous_v1_sha256")==v1_sha
            and claim.get("previous_v2_sha256")==v2_sha
            and claim.get("model_family")=="neon"
            and claim.get("thinking_level")=="high"
            and claim.get("original_source_uploaded") is False
            and claim.get("two_synthetic_pdf_attachments") is True
            and claim.get("one_send_only") is True
            and claim.get("prompt_sha256")==_sha(prompt.encode("utf8"))
            and claim.get("prior_latest_source_claim_unix")==after
            and claim.get("claimed_unix",0)>after
            and claim.get("recovery_signature")==SIGNATURE,
            "Neon claim identity differs from retired Pro source and PDF claims")
    for letter in ("a","b"):
        p=slot/("Synthetic"+letter.upper()+".pdf")
        require(p.is_file() and not p.is_symlink()
                and _sha(p.read_bytes())==claim["pdf_"+letter+"_sha256"],
                "Prior Neon synthetic PDF changed or missing")
    result_path=slot/"result.json"
    if not result_path.exists():
        return {"status":"PRIOR_NEON_HIGH_PDF_SEND_UNCERTAIN_NO_RESEND",
                "new_provider_requests":0,"new_source_review_send_allowed":False}
    require(result_path.is_file() and not result_path.is_symlink()
            and result_path.stat().st_size<=9000,
            "Invalid recorded one-shot Neon PDF result")
    receipt=json.loads(result_path.read_text(encoding="utf8"))
    require(receipt.get("schema_version")==1
            and receipt.get("claim_sha256")==_sha(claim_path.read_bytes())
            and receipt.get("source_sha256")==source_sha
            and receipt.get("original_incident_sha256")==incident
            and receipt.get("model_family")=="neon"
            and receipt.get("thinking_level")=="high"
            and receipt.get("original_source_uploaded") is False
            and receipt.get("academic_approval") is False
            and receipt.get("student_publication_authorized") is False
            and receipt.get("new_original_source_send_allowed") is False
            and type(receipt.get("observed_unix")) in (int,float)
            and claim["claimed_unix"]<=receipt["observed_unix"],
            "Foreign or tampered Neon model-response evidence")
    if receipt.get("status")==STATUS_OK:
        require(receipt.get("model_response_json")==expected
                and receipt.get("gemini_new_user_turn_verified") is True
                and receipt.get("registration_status") in _REGISTERED
                and receipt.get("verified_model_family")=="neon"
                and receipt.get("verified_thinking_level")=="high",
                "Unattributed or wrong-family Neon PDF qualification")
        return {**receipt,"new_provider_requests":0,
                "source_free_neon_pdf_capability_verified":True,
                "new_source_review_send_allowed":False}
    require(receipt.get("status")==STATUS_BAD
            and receipt.get("model_response_json") is None
            and receipt.get("gemini_new_user_turn_verified") is False,
            "Unverified Neon response must never qualify")
    return {**receipt,"new_provider_requests":0,
            "source_free_neon_pdf_capability_verified":False,
            "new_source_review_send_allowed":False}


def qualifying_proof(*, queue_root: Path, checkpoint_parent: Path,
                     source_sha: str, prior_slides: list[int]) -> dict | None:
    incident,last,v1,v2=_legacy(
        queue_root=queue_root,checkpoint_parent=checkpoint_parent,
        source_sha=source_sha,prior_slides=prior_slides)
    r=_read(checkpoint_parent=checkpoint_parent,source_sha=source_sha,
            incident=incident,after=last,v1_sha=v1,v2_sha=v2)
    return r if r is not None and r.get("status")==STATUS_OK else None


def probe_once(*, queue_root: Path, checkpoint_parent: Path,
               source_sha: str, prior_slides: list[int],
               transport=None, presend=None) -> dict:
    """Execute no more than ONE Neon/High PDF Send for the exact old incident.

    The only injectable alternatives are for offline/fault-injection tests.
    Runtime requires the same real owned Gemini port, fresh matched preflight,
    and strict post-Send model/effort/response attribution.
    """
    from .three_pc_worker import LocalInstanceLock
    checkpoint_parent=Path(checkpoint_parent).absolute()
    lockdir=checkpoint_parent/".microgen_neon_qualification_locks"
    require(not lockdir.is_symlink(),"Linked Neon diagnostic lock root")
    lockdir.mkdir(exist_ok=True)
    with LocalInstanceLock("neon_high_pdf_"+source_sha[:20],lockdir):
        incident,last,v1,v2=_legacy(
            queue_root=queue_root,checkpoint_parent=checkpoint_parent,
            source_sha=source_sha,prior_slides=prior_slides)
        old=_read(checkpoint_parent=checkpoint_parent,source_sha=source_sha,
                  incident=incident,after=last,v1_sha=v1,v2_sha=v2)
        if old is not None:
            return old
        if presend is None:
            from .academic_queue_fresh_send_health import _full_family_scope
            from .academic_gemini_presend_preflight import (
                inspect,AcademicGeminiPreSendBlocked)
            try:
                with _full_family_scope("pro"):
                    evidence=inspect(port=9222,
                                     allow_source_free_neon_probe=True)
            except AcademicGeminiPreSendBlocked as err:
                return {"status":"NEON_HIGH_PDF_PRESEND_UNAVAILABLE_NO_CLAIM",
                        "failure_phase":err.failure_phase,
                        "new_provider_requests":0,
                        "new_source_review_send_allowed":False}
        else:
            evidence=presend()
        if not (type(evidence) is dict
                and evidence.get("status")==
                    "EXACT_NEON_HIGH_SOURCE_FREE_PDF_PROBE_ONLY_READY_NO_SEND"
                and evidence.get("model_family")=="neon"
                and evidence.get("thinking_level")=="high"
                and evidence.get("verified_port")==9222
                and evidence.get("gemini_requests_submitted")==0
                and evidence.get("files_uploaded")==0
                and evidence.get("new_source_review_send_allowed") is False
                and evidence.get("student_publication_authorized") is False):
            return {"status":"NEON_HIGH_PDF_PRESEND_EVIDENCE_MISMATCH_NO_CLAIM",
                    "new_provider_requests":0,
                    "new_source_review_send_allowed":False}
        slot=_path(checkpoint_parent,source_sha,incident)
        slot.mkdir(parents=True,exist_ok=False)
        expected=_expected(source_sha,incident,v1,v2)
        prompt=_prompt(expected["probe"])
        require(expected["a"] not in prompt and expected["b"] not in prompt,
                "The two secret codes must only exist in attached PDFs")
        a,b=slot/"SyntheticA.pdf",slot/"SyntheticB.pdf"
        a_sha=_create_pdf(a,expected["a"],"A")
        b_sha=_create_pdf(b,expected["b"],"B")
        _new(slot/"claim.json",{
            "schema_version":1,"source_sha256":source_sha,
            "original_incident_sha256":incident,
            "previous_v1_sha256":v1,"previous_v2_sha256":v2,
            "model_family":"neon","thinking_level":"high",
            "prior_latest_source_claim_unix":last,
            "claimed_unix":time.time(),"prompt_sha256":_sha(prompt.encode("utf8")),
            "pdf_a_sha256":a_sha,"pdf_b_sha256":b_sha,
            "recovery_signature":SIGNATURE,
            "original_source_uploaded":False,
            "two_synthetic_pdf_attachments":True,"one_send_only":True})
        valid=False;registration=None;error_type=None
        try:
            if transport is None:
                from .academic_queue_fresh_send_health import _full_family_scope
                from .series_gemini import _browser_request
                with _full_family_scope("pro"):
                    reply=_browser_request(
                        prompt,[a,b],port=9222,wait_cap_s=160,
                        min_chars=20,accept_fn=lambda s:_exact(s,expected),
                        expected_runtime_family="neon",
                        expected_thinking_level="high")
            else:
                reply=transport(prompt,[a,b],
                                expected_runtime_family="neon",
                                expected_thinking_level="high")
            from .series_gemini import OwnedGeminiResponse
            valid=(isinstance(reply,OwnedGeminiResponse)
                   and reply.gemini_new_user_turn_verified is True
                   and reply.gemini_send_registration_status in _REGISTERED
                   and reply.gemini_verified_model_family=="neon"
                   and reply.gemini_verified_thinking_level=="high"
                   and _exact(str(reply),expected))
            if valid:registration=reply.gemini_send_registration_status
        except Exception as exc:
            error_type=type(exc).__name__
        receipt={
            "schema_version":1,"claim_sha256":_sha(
                (slot/"claim.json").read_bytes()),
            "source_sha256":source_sha,
            "original_incident_sha256":incident,
            "observed_unix":time.time(),
            "model_family":"neon","thinking_level":"high",
            "status": STATUS_OK if valid else STATUS_BAD,
            "registration_status":registration,
            "gemini_new_user_turn_verified":valid,
            "verified_model_family":"neon" if valid else None,
            "verified_thinking_level":"high" if valid else None,
            "model_response_json":expected if valid else None,
            "error_type":error_type,
            "original_source_uploaded":False,
            "academic_approval":False,
            "new_original_source_send_allowed":False,
            "student_publication_authorized":False,
        }
        _new(slot/"result.json",receipt)
        observed=_read(checkpoint_parent=checkpoint_parent,source_sha=source_sha,
                       incident=incident,after=last,v1_sha=v1,v2_sha=v2)
        require(observed is not None,"Neon source-free result must persist")
        return {**observed,"new_provider_requests":1}


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--queue-root",type=Path,required=True)
    p.add_argument("--checkpoint-parent",type=Path,required=True)
    p.add_argument("--execute",action="store_true")
    args=p.parse_args(argv)
    from .windows_g2_autonomous_qa_supervisor import _is_verified_folder
    _,files=_is_verified_folder(args.folder,args.queue_root)
    args.checkpoint_parent=args.checkpoint_parent.absolute()
    sha=files["source.pdf"]
    slides=[10,11]
    if args.execute:
        result=probe_once(queue_root=args.queue_root,
                          checkpoint_parent=args.checkpoint_parent,
                          source_sha=sha,prior_slides=slides)
    else:
        incident,last,v1,v2=_legacy(
            queue_root=args.queue_root,checkpoint_parent=args.checkpoint_parent,
            source_sha=sha,prior_slides=slides)
        result=_read(checkpoint_parent=args.checkpoint_parent,source_sha=sha,
                     incident=incident,after=last,v1_sha=v1,v2_sha=v2) or {
            "status":"NEW_NEON_HIGH_PDF_DIAGNOSTIC_ELIGIBLE_NOT_STARTED",
            "new_provider_requests":0,"new_source_review_send_allowed":False,
        }
    safe={k:result.get(k) for k in (
        "status","new_provider_requests","new_source_review_send_allowed",
        "source_free_neon_pdf_capability_verified","failure_phase",
        "verified_model_family","verified_thinking_level","error_type")}
    safe["original_source_uploaded"]=False
    safe["academic_approval"]=False
    safe["student_publication_authorized"]=False
    print(json.dumps(safe,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
