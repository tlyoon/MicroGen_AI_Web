"""Autonomously advance original-source rich PDF-to-narration AI review.

REUSE the existing Gemini Selenium browser source-binding and original
response quarantine. This worker is a finite on-demand orchestration layer,
not an alternate LLM, API transport, TTS synthesizer, or release approver.
"""
from __future__ import annotations

from contextlib import contextmanager
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

from .recovery_registry import lookup_mechanism
from .rich_element_model_alignment import (
    RichMappingError, assess_response, load_accepted_checkpoint,
    request_for_slide, parse_response, stable_hash,
)

KIND="g3_semantic_mapping_continuation"
SIGNATURE="HISTORICAL_RICH_MAPPING_WORKLIST_NOT_AUTOMATICALLY_DISPATCHED"
REPAIR="REUSE_SOURCE_PINNED_BROWSER_REVIEW_CLAIMS_RESUME_SAVED_REPLY"
STATUS="G3_HISTORICAL_SELENIUM_RICH_MAPPING_AUTOCONTINUATION_V1"
MAX_SENDS_PER_INVOCATION=3


def need(ok:bool,reason:str)->None:
    if not ok:
        raise RichMappingError(reason)


def _registered()->None:
    need(lookup_mechanism(KIND,SIGNATURE)==REPAIR,
         "G3 rich-source review continuation is not registered")


def _read(path:Path)->dict:
    need(path.is_file() and not path.is_symlink()
         and 0<path.stat().st_size<=3_000_000,
         "Unsafe, missing or oversized original mapping evidence")
    obj=json.loads(path.read_text(encoding="utf8"))
    need(type(obj) is dict,"Expected original model/worker JSON evidence")
    return obj


def _new_json(path:Path,data:dict)->None:
    need(not path.exists() and not path.is_symlink()
         and path.parent.is_dir() and not path.parent.is_symlink(),
         "Do not overwrite earlier G3 review evidence")
    with path.open("x",encoding="utf8") as out:
        json.dump(data,out,indent=2,ensure_ascii=False)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())


def _sha(path:Path)->str:
    need(path.is_file() and not path.is_symlink(),
         "Missing immutable original-model evidence")
    dig=hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda:stream.read(1024*1024),b""):
            dig.update(part)
    return dig.hexdigest()


@contextmanager
def _exclusive(root:Path):
    """OS-released lock: crashing the worker never requires manual unlock."""
    root=Path(root).absolute()
    need(root.is_dir() and not root.is_symlink(),
         "Independent existing review root required")
    lock=root/".g3_mapping_worker.lock"
    with lock.open("a+b") as handle:
        if handle.seek(0,2)==0:
            handle.write(b" ")
            handle.flush()
        handle.seek(0)
        if os.name=="nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as exc:
                raise RichMappingError("Another G3 source-review owner holds the queue") from exc
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            try:
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as exc:
                raise RichMappingError("Another G3 source-review owner holds the queue") from exc
            try:
                yield
            finally:
                fcntl.flock(handle,fcntl.LOCK_UN)


def prepare(*,source_folder:Path,checkpoint:Path,review_root:Path)->dict:
    _registered()
    source_folder=Path(source_folder).absolute()
    checkpoint=Path(checkpoint).absolute()
    root=Path(review_root).absolute()
    need(root.parent.is_dir() and not root.parent.is_symlink()
         and not root.is_symlink()
         and root!=source_folder and not root.is_relative_to(source_folder)
         and not source_folder.is_relative_to(root)
         and root!=checkpoint and not root.is_relative_to(checkpoint),
         "Source/model review must use external dedicated checkpoint storage")
    meta,_=load_accepted_checkpoint(folder=source_folder,checkpoint=checkpoint)
    expected={
        "schema_version":1,"status":STATUS,
        "source_folder":str(source_folder),
        "source_inputs_sha256":meta["source_inputs_sha256"],
        "original_mapping_checkpoint":str(checkpoint),
        "mapping_checkpoint_sha256":_sha(checkpoint/"mapping_checkpoint.json"),
        "original_slides":meta["slide_count"],
        "one_claim_per_slide":True,
        "source_review_model_transport":"selenium_browser_only",
        "paid_gemini_developer_api_requests":0,
        "tts_authorized":False,
        "independent_acoustic_review_complete":False,
        "scientific_approval":False,
        "student_publication_authorized":False,
    }
    if not root.exists():
        root.mkdir()
    need(root.is_dir() and not root.is_symlink(),
         "Source-bound review root changed to unsafe path")
    manifest=root/"g3_auto_mapping_identity.json"
    if manifest.exists() or manifest.is_symlink():
        need(_read(manifest)==expected,
             "Original-source or checkpoint identity changed; do not resume")
    else:
        _new_json(manifest,expected)
    for name in ("audited","original_model_responses"):
        sub=root/name
        if not sub.exists():
            sub.mkdir()
        need(sub.is_dir() and not sub.is_symlink(),
             "Source/model response directory is not a real safe directory")
    return expected


def _files(root:Path,n:int)->dict[str,Path]:
    name=f"slide_{n:03d}"
    return {
        "audit":root/"audited"/(name+".json"),
        "response":root/"original_model_responses"/(name+".json"),
        "claim":root/"audited"/(name+".submission_held.json"),
        "capture":root/"audited"/(name+".gemini_capture.txt"),
    }


def _verified_saved(*,source_folder:Path,checkpoint:Path,n:int,
                    files:dict)->dict:
    """Validate ORIGINAL saved bytes without ever creating another Gemini Send."""
    req=request_for_slide(
        source_folder=source_folder,checkpoint=checkpoint,slide_number=n)
    claim=_read(files["claim"])
    need(claim.get("request_sha256")==req["request_sha256"]
         and claim.get("status") in (
             "CAPTURED_SOURCE_AUDITED_REVIEW_ONLY",
             "CAPTURED_SOURCE_REJECTED_NO_REPLAY",
             "MAY_HAVE_SENT_AWAIT_RECONCILIATION",
         ),"Original provider Send claim/request does not match source")
    need(files["capture"].is_file() and not files["capture"].is_symlink()
         and 0<files["capture"].stat().st_size<=2_000_000,
         "Original owned-model response capture missing or unsafe")
    raw=files["capture"].read_text(encoding="utf8")
    parsed=parse_response(raw)
    need(parsed.get("request_sha256")==req["request_sha256"],
         "Raw browser model response did not match original request")
    model=files["response"]
    audit=files["audit"]
    if model.exists():
        need(_read(model)==parsed,
             "Saved parsed model reply changed from original capture")
    else:
        _new_json(model,parsed)
    checked=assess_response(source_folder=source_folder,checkpoint=checkpoint,
                            slide_number=n,proposed=parsed)
    if audit.exists():
        need(_read(audit)==checked,
             "Source-audited original response disagrees after restart")
    else:
        _new_json(audit,checked)
    if claim.get("status")=="CAPTURED_SOURCE_AUDITED_REVIEW_ONLY":
        need(claim.get("raw_model_response_sha256")==_sha(model)
             and claim.get("technical_audit_sha256")==_sha(audit),
             "Accepted original-model SHA witnesses not reproduced")
    return {"slide":n,"status":"SAVED_BROWSER_REVIEW_REVALIDATED_NO_SEND",
            "source_text_anchors":checked["text_source_and_author_anchors_passed"],
            "review_pending":checked["remaining_review_items"],
            "original_utterances":checked["utterances_total"],
            "new_model_requests":0,"scientific_approval":False,
            "student_publication_authorized":False}


def _verified_source_rejection(*,source_folder:Path,checkpoint:Path,n:int,
                               files:dict)->dict:
    """Recognize a REAL captured content rejection, not a failed provider Send.

    Never promote any rejected text anchor. Require the exact original
    request, original response bytes, parsed model bytes, and re-run the
    independent PDF grounding check to confirm this still rejects.
    """
    need(lookup_mechanism(
        "g3_rejected_content_continuation",
        "CAPTURED_REJECTED_PUBLISHER_QUOTE_COUNTED_AS_PROVIDER_UNCERTAINTY",
    )=="REVERIFY_ORIGINAL_REJECTED_BYTES_QUARANTINE_SLIDE_ADVANCE_OTHER_SLIDES",
         "No registered executable recovery for captured source rejection")
    claim=_read(files["claim"])
    need(claim.get("status")=="CAPTURED_SOURCE_REJECTED_NO_REPLAY"
         and claim.get("model_response_accepted") is False
         and claim.get("academic_approval") is False
         and claim.get("paid_tts_authorized") is False
         and claim.get("student_publication_authorized") is False,
         "Not an independently rejected source-grounded model reply")
    request=request_for_slide(source_folder=source_folder,
                              checkpoint=checkpoint,slide_number=n)
    need(claim.get("request_sha256")==request["request_sha256"]
         and claim.get("source_inputs_sha256")==request["source_inputs_sha256"],
         "Original rejected request and source identity differ")
    need(files["capture"].is_file() and not files["capture"].is_symlink()
         and 0<files["capture"].stat().st_size<=2_000_000
         and claim.get("verbatim_capture_sha256")==_sha(files["capture"])
         and claim.get("parsed_model_response_sha256")==_sha(files["response"]),
         "Original rejected response SHA provenance invalid")
    response=parse_response(files["capture"].read_text(encoding="utf8"))
    need(response.get("request_sha256")==request["request_sha256"]
         and _read(files["response"])==response,
         "Original captured rejected response disagrees with parsed evidence")
    need(not files["audit"].exists() and not files["audit"].is_symlink(),
         "Rejected model response has contradictory accepted source audit")
    reason=claim.get("source_rejection_reason")
    need(claim.get("source_rejection_type")=="RichMappingError"
         and type(reason) is str and bool(reason),
         "Original source rejection lacks an independently recorded reason")
    try:
        assess_response(source_folder=source_folder,checkpoint=checkpoint,
                        slide_number=n,proposed=response)
    except RichMappingError as exc:
        need(str(exc)[:250]==reason,
             "Revalidated publisher-source rejection reason changed")
    else:
        raise RichMappingError(
            "Original source-rejected model has become accepted without review")
    return {"slide":n,"status":"SOURCE_QUOTE_REJECTED_NO_REPLAY",
            "source_text_anchors":0,"review_pending":None,
            "new_model_requests":0,"scientific_approval":False,
            "student_publication_authorized":False}


def _inspect_one(*,source_folder:Path,checkpoint:Path,root:Path,n:int,
                 reconcile:bool=True)->dict:
    files=_files(root,n)
    for label,p in files.items():
        need(not p.is_symlink(),f"Linked or unsafe {label} review checkpoint")
    has_claim=files["claim"].exists()
    has_capture=files["capture"].exists()
    has_model=files["response"].exists()
    has_audit=files["audit"].exists()
    if not any((has_claim,has_capture,has_model,has_audit)):
        return {"slide":n,"status":"ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET",
                "source_text_anchors":0,"review_pending":None,
                "new_model_requests":0,"scientific_approval":False,
                "student_publication_authorized":False}
    if not has_claim:
        return {"slide":n,"status":"QUARANTINED_MODEL_EVIDENCE_WITHOUT_SEND_CLAIM",
                "source_text_anchors":0,"review_pending":None,
                "new_model_requests":0,"scientific_approval":False,
                "student_publication_authorized":False}
    if not has_capture:
        return {"slide":n,"status":"CLAIMED_OR_UNKNOWN_SEND_NO_REPLAY",
                "source_text_anchors":0,"review_pending":None,
                "new_model_requests":0,"scientific_approval":False,
                "student_publication_authorized":False}
    if not reconcile and (not has_model or not has_audit):
        return {"slide":n,"status":"SAVED_REPLY_RECONCILIATION_REQUIRED_NO_SEND",
                "source_text_anchors":0,"review_pending":None,
                "new_model_requests":0,"scientific_approval":False,
                "student_publication_authorized":False}
    try:
        claim=_read(files["claim"])
        if claim.get("status")=="CAPTURED_SOURCE_REJECTED_NO_REPLAY":
            return _verified_source_rejection(
                source_folder=source_folder,checkpoint=checkpoint,n=n,files=files)
        return _verified_saved(source_folder=source_folder,checkpoint=checkpoint,
                               n=n,files=files)
    except (ValueError,KeyError,TypeError,OSError,UnicodeError):
        return {"slide":n,"status":"SAVED_SOURCE_REPLY_UNTRUSTED_NO_REPLAY",
                "source_text_anchors":0,"review_pending":None,
                "new_model_requests":0,"scientific_approval":False,
                "student_publication_authorized":False}


def adopt_prior_owned_review(*,source_folder:Path,checkpoint:Path,
                             review_root:Path,slide:int,previous:dict)->dict:
    """Reuse an authentic completed browser review, not send the same task."""
    prepare(source_folder=source_folder,checkpoint=checkpoint,
            review_root=review_root)
    root=Path(review_root).absolute()
    with _exclusive(root):
        need(type(slide) is int and 1<=slide<=
             _read(root/"g3_auto_mapping_identity.json")["original_slides"],
             "Original slide out of range")
        new=_files(root,slide)
        # Reimport after a crash may find 1..4 files already copied. Admit
        # only exact SHA-identical original bytes; never delete or overwrite
        # an adopted/claimed artifact. Once all are present, return the same
        # reverified source audit without a browser Send.
        need(all(not p.is_symlink() for p in new.values()),
             "Linked or unsafe adopted source response evidence")
        need(set(previous)==set(new),
             "Adopt exactly four original owned browser evidence files")
        expected=request_for_slide(
            source_folder=source_folder,checkpoint=checkpoint,
            slide_number=slide)
        old={k:Path(v).absolute() for k,v in previous.items()}
        need(all(p.is_file() and not p.is_symlink() for p in old.values()),
             "Incomplete original owned browser provenance")
        claim=_read(old["claim"])
        need(claim.get("status")=="CAPTURED_SOURCE_AUDITED_REVIEW_ONLY"
             and claim.get("request_sha256")==expected["request_sha256"],
             "Historical source request lacks a verified owned Send receipt")
        original_model=_read(old["response"])
        need(parse_response(old["capture"].read_text(encoding="utf8"))==
             original_model,"Historical raw browser response mismatches parsed model")
        audit=assess_response(source_folder=source_folder,
                checkpoint=checkpoint,slide_number=slide,proposed=original_model)
        need(audit==_read(old["audit"])
             and _sha(old["response"])==claim["raw_model_response_sha256"]
             and _sha(old["audit"])==claim["technical_audit_sha256"],
             "Historical model/source SHA verification failed: no import")
        for kind,original in old.items():
            destination=new[kind]
            if destination.exists():
                need(destination.is_file() and not destination.is_symlink()
                     and _sha(destination)==_sha(original),
                     "Existing adoption conflicts with original browser evidence")
                continue
            with original.open("rb") as src, destination.open("xb") as dest:
                shutil.copyfileobj(src,dest)
                dest.flush()
                os.fsync(dest.fileno())
        return _verified_saved(source_folder=source_folder,checkpoint=checkpoint,
                               n=slide,files=new)


def run(*,source_folder:Path,checkpoint:Path,review_root:Path,
        max_new_sends:int=0,port:int=9222,wait_s:int=120)->dict:
    """One finite campaign step; model dispatch explicit, Selenium-only."""
    need(type(max_new_sends) is int and 0<=max_new_sends<=MAX_SENDS_PER_INVOCATION
         and type(port) is int and port in range(9222,9324)
         and type(wait_s) is int and 20<=wait_s<=180,
         "Unbounded model dispatch or unapproved browser transport")
    identity=prepare(source_folder=source_folder,checkpoint=checkpoint,
                     review_root=review_root)
    root=Path(review_root).absolute()
    with _exclusive(root):
        before=[
            _inspect_one(source_folder=source_folder,checkpoint=checkpoint,
                         root=root,n=n) for n in range(1,identity["original_slides"]+1)
        ]
        sends=0
        failures=[]
        # Circuit breaker persists across restarts. Two original unreturned
        # browser submissions already consume source-review transport trust;
        # an interrupted process may not reset the budget by starting anew.
        uncertain=sum(x["status"] in {
            "CLAIMED_OR_UNKNOWN_SEND_NO_REPLAY",
            "SAVED_SOURCE_REPLY_UNTRUSTED_NO_REPLAY",
        } for x in before)
        # The original 115 "ambiguous" units are lexical ranking hints,
        # not scientific failures. Prioritize the most unresolved ORIGINAL
        # slide first, not an uninteresting title slide, then keep the same
        # deterministic order across process restarts.
        _,draft=load_accepted_checkpoint(
            folder=source_folder,checkpoint=checkpoint)
        burden={
            row["slide_number"]:sum(bool(u["mapping_ambiguous"])
                                   for u in row["proposed_utterances"])
            for row in draft["slides"]
            if type(row.get("proposed_utterances")) is list
        }
        order=sorted(range(1,identity["original_slides"]+1),
                     key=lambda n:(-burden.get(n,0),n))
        if max_new_sends:
            from .rich_element_model_alignment import main as source_model_main
            for n in order:
                prior=before[n-1]
                if sends>=max_new_sends or uncertain>=2:
                    break
                if prior["status"]!="ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET":
                    continue
                f=_files(root,n)
                # This child's own immutable submission_held claim is saved
                # immediately before its one browser Send; even a crash or
                # invalid model reply never permits another Send for this ID.
                try:
                    args=[
                        "--source-folder",str(Path(source_folder).absolute()),
                        "--checkpoint",str(Path(checkpoint).absolute()),
                        "--slide",str(n),"--out",str(f["audit"]),
                        "--raw-response-out",str(f["response"]),
                        "--gemini-web","--browser-port",str(port),
                        "--wait-s",str(wait_s),
                    ]
                    sends+=1
                    source_model_main(args)
                    uncertain=0
                except Exception as exc:
                    diagnosed=_inspect_one(
                        source_folder=source_folder,checkpoint=checkpoint,
                        root=root,n=n)
                    content_rejection=(diagnosed["status"]==
                                       "SOURCE_QUOTE_REJECTED_NO_REPLAY")
                    failures.append({
                        "slide":n,"error_type":type(exc).__name__,
                        "error":str(exc)[:240],
                        "failure_classification":(
                            "SOURCE_QUOTE_REJECTED_NO_REPLAY"
                            if content_rejection else "UNTRUSTED_OR_UNCERTAIN_SEND"),
                    })
                    if not content_rejection:
                        uncertain+=1
                    # Two distinct uncertain original requests block any
                    # further fresh Sends until source/transport requalification.
        after=[
            _inspect_one(source_folder=source_folder,checkpoint=checkpoint,
                         root=root,n=n) for n in range(1,identity["original_slides"]+1)
        ]
        good=[x for x in after
              if x["status"]=="SAVED_BROWSER_REVIEW_REVALIDATED_NO_SEND"]
        pending=[x for x in after
                 if x["status"]=="ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET"]
        source_rejected=[x for x in after
                         if x["status"]=="SOURCE_QUOTE_REJECTED_NO_REPLAY"]
        blocked=[x for x in after
                 if x["status"] not in (
                     "ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET",
                     "SAVED_BROWSER_REVIEW_REVALIDATED_NO_SEND",
                     "SOURCE_QUOTE_REJECTED_NO_REPLAY")]
        return {
            "schema_version":1,
            "status":"G3_SOURCE_PINNED_BROWSER_MAPPING_REVIEW_IN_PROGRESS"
                     if pending or blocked or source_rejected else
                     "G3_ALL_MODEL_REPLIES_SOURCE_AUDITED_NOT_ACADEMICALLY_ACCEPTED",
            "source_inputs_sha256":identity["source_inputs_sha256"],
            "original_slides":identity["original_slides"],
            "original_reviewed_slides_reused":len(good),
            "original_textbook_and_rendered_text_anchors_proven":sum(
                x["source_text_anchors"] for x in good),
            "source_review_gaps_within_reviewed_slides":sum(
                x["review_pending"] for x in good),
            "remaining_unreviewed_slides":len(pending),
            "quarantined_or_uncertain_slides":len(blocked),
            "source_rejected_slides":len(source_rejected),
            "max_new_sends_authorized":max_new_sends,
            "new_browser_dispatch_attempts_this_run":sends,
            "dispatch_failures":failures,
            "slides":after,
            "developer_api_fallback_permitted":False,
            "paid_gemini_api_requests":0,
            "independent_scientific_QA_complete":False,
            "independent_acoustic_QA_complete":False,
            "highlighted_video_accepted":False,
            "student_publication_authorized":False,
        }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ("source-folder","checkpoint","review-root"):
        parser.add_argument("--"+option,required=True,type=Path)
    parser.add_argument("--max-new-sends",type=int,default=0)
    parser.add_argument("--browser-port",type=int,default=9222)
    parser.add_argument("--wait-s",type=int,default=120)
    args=parser.parse_args(argv)
    summary=run(source_folder=args.source_folder,checkpoint=args.checkpoint,
                review_root=args.review_root,max_new_sends=args.max_new_sends,
                port=args.browser_port,wait_s=args.wait_s)
    print(json.dumps({k:v for k,v in summary.items() if k!="slides"},
                     indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
