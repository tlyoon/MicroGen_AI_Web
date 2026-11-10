"""Resumable original-source AI review queue; no phantom approvals or blind retries.

One source-bound slide and reviewer pass per bounded attempt. Failed model
output is never promoted, and an observed failed response requires an explicit
new attempt; already completed work is immutable and never re-submitted.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from .figure_source_identity import require,_sha
from .ai_academic_web_review import (build_review_job,run_web_review,
    review_instructions,validate_model_review)
from .series_gemini import decode_storyboard_response
from .gemini_model import GeminiModelError

def _receipt_name(slide:int,mode:str)->str:
    require(type(slide) is int and 1<=slide<=200
            and mode in ("INITIAL_REVIEW","INDEPENDENT_CHALLENGE"),
            "Invalid bounded reviewer unit")
    return f"slide_{slide:03d}_{mode.lower()}.json"

def prepare_resumable_review(*,folder:Path,output_root:Path,
                             slide_numbers:list[int])->dict:
    folder=Path(folder).absolute()
    output_root=Path(output_root).absolute()
    require(type(slide_numbers) is list and bool(slide_numbers)
            and len(slide_numbers)<=200 and
            all(type(n) is int for n in slide_numbers)
            and slide_numbers==sorted(set(slide_numbers))
            and output_root.parent.is_dir() and not output_root.exists()
            and not output_root.is_relative_to(folder),
            "New isolated queue cannot modify original teaching data")
    work=[]
    for n in slide_numbers:
        j=build_review_job(folder=folder,slide_numbers=[n])
        work.append({"slide":n,"utterance_count":j["utterance_count"],
                     "original_source_sha256":j["source_sha256"],
                     "original_slides_sha256":j["slides_sha256"],
                     "original_script_sha256":j["script_sha256"]})
    output_root.mkdir()
    plan={"status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
          "original_source_folder":str(folder),
          "slide_jobs":work,"expected_utterances":sum(x["utterance_count"] for x in work),
          "provider_requests_performed":0,"approved_math_utterances":0,
          "student_publication_authorized":False}
    with (output_root/"queue.json").open("x",encoding="utf8") as f:
        json.dump(plan,f,indent=2);f.write("\n")
    return plan

def _check_queue(*,queue_root:Path,folder:Path,slide:int,mode:str)->dict:
    queue_root=Path(queue_root).absolute();folder=Path(folder).absolute()
    plan=json.loads((queue_root/"queue.json").read_text(encoding="utf8"))
    require(plan.get("status")=="IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE"
            and plan.get("original_source_folder")==str(folder)
            and plan.get("student_publication_authorized") is False
            and type(plan.get("slide_jobs")) is list
            and sum(x["utterance_count"] for x in plan["slide_jobs"])==plan["expected_utterances"],
            "Original immutable review queue corrupt")
    row=next((x for x in plan["slide_jobs"] if x["slide"]==slide),None)
    require(row is not None,"Original requested slide absent from queued review")
    for name,key in (("source.pdf","original_source_sha256"),("slides.pdf","original_slides_sha256"),
                     ("script.txt","original_script_sha256")):
        require(_sha(folder/name)==row[key],"Original source assets drifted")
    if mode=="INDEPENDENT_CHALLENGE":
        first=queue_root/_receipt_name(slide,"INITIAL_REVIEW")
        require(first.is_file() and not first.is_symlink(),
                "Independent challenge requires a successfully validated first-pass review")
        check=json.loads(first.read_text(encoding="utf8"))
        require(check.get("mode")=="INITIAL_REVIEW"
                and check.get("status")=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
                and check.get("review_count")==row["utterance_count"],
                "Initial source review failed or was incomplete")
    return row

def _prior_unattributed_streak(*, queue_root:Path, slide_jobs:list[dict],
                               before_slide:int) -> list[int]:
    """Read-only guard against indefinitely shifting an uncertain Send to new slides.

    A complete reply or a known source-invalid result breaks the streak;
    two distinct immediately preceding original slide review units whose
    browser request might have been sent but returned no attributable reply
    make another *fresh* Send unsafe until the transport has independent
    new evidence.  No previous receipt is edited and no budget is reset.
    """
    from .academic_review_checkpoint import _load
    streak=[]
    for row in slide_jobs:
        previous=row["slide"]
        if previous>=before_slide:
            break
        completed=queue_root/_receipt_name(previous,"INITIAL_REVIEW")
        if completed.exists():
            require(completed.is_file() and not completed.is_symlink(),
                    "Source review completion receipt untrusted")
            streak=[]
            continue
        receipt=queue_root/f"slide_{previous:03d}_initial_review_attempt_01.json"
        claim=queue_root/f"slide_{previous:03d}_initial_review_attempt_01_request"
        uncertain=False
        if receipt.exists() or receipt.is_symlink():
            require(receipt.is_file() and not receipt.is_symlink(),
                    "Prior source review receipt untrusted")
            outcome=json.loads(receipt.read_text(encoding="utf8"))
            uncertain=(outcome.get("status")
                       =="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
                       and outcome.get("provider_submission_state")
                       =="UNKNOWN_AFTER_POSSIBLE_SUBMISSION")
        elif claim.exists() or claim.is_symlink():
            require(claim.is_dir() and not claim.is_symlink(),
                    "Prior review claim directory untrusted")
            uncertain=_load(claim)["status"] in {
                "SUBMITTED_OR_UNCERTAIN", "NO_RESPONSE_UNRESOLVED",
                "LEGACY_SENT_NO_RESPONSE"}
        if uncertain:
            streak.append(previous)
        else:
            streak=[]
    return streak


def execute_one_review(*,queue_root:Path,folder:Path,
                       slide:int,mode:str,
                       attempt:int=1,transport=None)->dict:
    queue_root=Path(queue_root).absolute();folder=Path(folder).absolute()
    require(type(attempt) is int and 1<=attempt<=3,"No unbounded AI retry loop")
    row=_check_queue(queue_root=queue_root,folder=folder,slide=slide,mode=mode)
    success=queue_root/_receipt_name(slide,mode)
    require(not success.exists(),"Do not resubmit an already verified source review")
    evidence_file=queue_root/f"slide_{slide:03d}_{mode.lower()}_attempt_{attempt:02d}.json"
    require(not evidence_file.exists(),"Observed attempt receipt must never be overwritten")
    # Fail immediately after previous failures unless caller explicitly elects next attempt.
    for i in range(1,attempt):
        previous=queue_root/f"slide_{slide:03d}_{mode.lower()}_attempt_{i:02d}.json"
        require(previous.is_file(),"Cannot skip missing observed failure")
        prior=json.loads(previous.read_text(encoding="utf8"))
        require(prior.get("status")=="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
                and prior.get("attempt")==i
                and prior.get("provider_submission_state") in (
                    "RETURNED_RESPONSE_INVALID",
                    "CONFIRMED_PRE_SUBMISSION_MODEL_SELECTION_FAILURE",
                )
                and prior.get("manual_retry_eligible") is True,
                "Ambiguous or unaccounted provider attempt requires reconciliation")
    job=build_review_job(folder=folder,slide_numbers=[slide])
    require(job["utterance_count"]==row["utterance_count"],"Narration coverage changed")
    # The original reviewer requires a pre-send durable claim. The old queue
    # omitted checkpoint_dir, preventing every live browser review even when
    # source, queue and permission were otherwise correct. Reuse this
    # per-attempt window and its recorded response; never resend an ambiguous
    # previous browser request, including across process crashes.
    live_checkpoint = queue_root / (
        f"slide_{slide:03d}_{mode.lower()}_attempt_{attempt:02d}_request")
    prior=_prior_unattributed_streak(
        queue_root=queue_root,
        slide_jobs=json.loads((queue_root/"queue.json").read_text(encoding="utf8"))["slide_jobs"],
        before_slide=slide)
    if len(prior)>=2:
        # Keep legitimate *already captured* response reconciliation
        # available even when the same browser route is not healthy enough
        # to authorize another new Send.
        from .academic_review_checkpoint import _load
        saved_reply=False
        if live_checkpoint.exists() or live_checkpoint.is_symlink():
            require(live_checkpoint.is_dir() and not live_checkpoint.is_symlink(),
                    "Old academic browser claim untrusted")
            saved_reply=_load(live_checkpoint)["status"] in {
                "MODEL_REPLY_OBSERVED_UNVALIDATED",
                "REJECTED_RESPONSE_UNTRUSTED",
                "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"}
        require(saved_reply,
                "DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND: two prior "
                "slide requests may have been submitted without an "
                "attributable response; require new independent transport "
                "evidence, not another model Send")
    returned_response=False
    def witness_model_return(raw):
        nonlocal returned_response
        # Selenium returns an evidence-bearing str subclass for verified
        # owned Send replies. Exact-type matching falsely treated a returned
        # but invalid answer as no response. Keep the no-resend claim intact.
        returned_response=isinstance(raw,str) and bool(raw.strip())
    try:
        response = None
        if transport is None and live_checkpoint.exists():
            from .academic_review_checkpoint import (
                _load, fingerprint, validate_saved)
            checkpoint_state = _load(live_checkpoint)
            prompt = review_instructions(job,mode=mode)
            expected = fingerprint(
                request_text=prompt,
                source_hashes={name:job[key] for name,key in
                    (("source.pdf","source_sha256"),
                     ("slides.pdf","slides_sha256"),
                     ("script.txt","script_sha256"))},
                review_mode=mode)
            require(checkpoint_state["request_fingerprint"]==expected,
                    "Old academic review request fingerprint changed; no resend")
            if checkpoint_state["status"] in {
                "MODEL_REPLY_OBSERVED_UNVALIDATED",
                "REJECTED_RESPONSE_UNTRUSTED",
                "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED",
            }:
                # The exact response was saved before the crash. Independently
                # validate those SAME bytes against current source and slide
                # geometry, then finish the original queue receipt without
                # issuing any model request.
                returned_response = True
                response = validate_saved(
                    checkpoint=live_checkpoint,
                    expected_fingerprint=expected,
                    validator=lambda raw: validate_model_review(
                        folder=folder, job=job,
                        response=decode_storyboard_response(raw),
                        mode=mode),
                )
            elif checkpoint_state["status"] not in {"PREPARED_NOT_SENT"}:
                raise RuntimeError(
                    "Academic browser Send may already have occurred; "
                    "only response reconciliation is allowed, never resend")
        if response is None:
            response=run_web_review(
                folder=folder,job=job,mode=mode,
                transport=transport,
                response_observer=witness_model_return,
                checkpoint_dir=live_checkpoint if transport is None else None)
    except (RuntimeError,ValueError,OSError) as exc:
        # Model-family errors from the built-in browser transport are raised
        # BEFORE upload, typing and click-send. Injected transports are NOT
        # trusted as evidence that a request remained unsent.
        web_send_claimed = (
            transport is None and
            (live_checkpoint/"dispatch_attempted.claim").exists())
        model_failure_before_send=(transport is None and
                                   isinstance(exc,GeminiModelError)
                                   and not returned_response and
                                   not web_send_claimed)
        # A received but invalid browser reply is NOT a free resubmit:
        # the exact prompt/source identity is consumed by a durable global
        # one-Send claim. An explicit materially different reviewer scope
        # requires a separate, independently authorized new job.
        manual_retry_eligible = (
            (returned_response or model_failure_before_send)
            and not web_send_claimed)
        # Preserve only a concise bounded type/error description, never private tab text.
        fail={"status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
              "slide":slide,"mode":mode,"attempt":attempt,
              "error_type":type(exc).__name__,"reason":str(exc)[:450],
              "requires_explicit_next_attempt":True,
              "provider_submission_state":(
                  "RETURNED_RESPONSE_INVALID" if returned_response else
                  "CONFIRMED_PRE_SUBMISSION_MODEL_SELECTION_FAILURE"
                  if model_failure_before_send else
                  "UNKNOWN_AFTER_POSSIBLE_SUBMISSION"),
              "manual_retry_eligible":manual_retry_eligible,
              "requires_owner_reconciliation":(
                  not manual_retry_eligible and not returned_response),
              "requires_new_independent_source_evidence":bool(returned_response),
              "can_advance_other_unattempted_slides":True,
              "academically_approved":False,"student_publication_authorized":False}
        with evidence_file.open("x",encoding="utf8") as f:
            json.dump(fail,f,indent=2);f.write("\n")
        return fail
    with success.open("x",encoding="utf8") as f:
        json.dump(response,f,indent=2);f.write("\n")
    done={"status":"GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED",
          "slide":slide,"mode":mode,"attempt":attempt,
          "verified_original_utterances":response["review_count"],
          "receipt_sha256":_sha(success),
          "academic_independent_challenge_complete":False,
          "student_publication_authorized":False}
    with evidence_file.open("x",encoding="utf8") as f:
        json.dump(done,f,indent=2);f.write("\n")
    return done


def select_next_safe_review(*,queue_root:Path,folder:Path)->dict:
    """Source-independent, read-only choice of ONE next review operation.

    This is selection, not provider authorization or a retry. Completed modes
    are never replayed; a checkpoint with a possible Send is never re-sent.
    A source-specific defect cannot trap unrelated, unattempted slide reviews.
    """
    from .review_queue_source_audit import inspect_source_bound_queue
    from .source_review_eligibility_preflight import inspect_original_review_eligibility
    from .academic_review_checkpoint import _load
    queue_root, folder = Path(queue_root).absolute(), Path(folder).absolute()
    inspect_source_bound_queue(queue_root)
    plan = json.loads((queue_root/"queue.json").read_text(encoding="utf8"))
    require(plan["original_source_folder"]==str(folder),
            "Academic queue does not belong to supplied original source")
    blocked=[]
    completed=0
    for row in plan["slide_jobs"]:
        slide=row["slide"]
        scope=inspect_original_review_eligibility(
            folder=folder,queue_root=queue_root,slide=slide)
        mode=scope["suggested_next_stage"]
        if scope["planning_result"]=="EXISTING_PASS_MUST_NOT_BE_REPEATED":
            completed+=1
            continue
        if not scope["fresh_claimed_internal_selenium_review_ready"]:
            blocked.append({"slide":slide,"mode":mode,
                            "reason":scope["planning_result"]})
            continue
        # Reuse the exact old one-Send path; do not pick a different attempt
        # number or alter the source/prompt to bypass an uncertain Send.
        claim=queue_root/(
            f"slide_{slide:03d}_{mode.lower()}_attempt_01_request")
        if claim.exists() or claim.is_symlink():
            require(claim.is_dir() and not claim.is_symlink(),
                    "Academic model claim is linked or corrupted")
            state=_load(claim)
            if state["status"] in {
                "SUBMITTED_OR_UNCERTAIN", "NO_RESPONSE_UNRESOLVED",
                "LEGACY_SENT_NO_RESPONSE"
            }:
                blocked.append({"slide":slide,"mode":mode,
                                "reason":"AMBIGUOUS_OLD_SEND_NO_RESUBMISSION"})
                continue
            if state["status"] not in {
                "PREPARED_NOT_SENT", "MODEL_REPLY_OBSERVED_UNVALIDATED",
                "REJECTED_RESPONSE_UNTRUSTED",
                "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED",
            }:
                blocked.append({"slide":slide,"mode":mode,
                                "reason":"INVALID_PREVIOUS_CHECKPOINT_STATE"})
                continue
            # If the prior validation rejected a reply, the same saved bytes
            # may be reconciled but never sent again. Executor verifies exact
            # prompt fingerprint and original source hashes.
            action=("RECONCILE_PRIOR_RESPONSE_NO_SEND"
                    if state["status"]!="PREPARED_NOT_SENT"
                    else "PREPARED_UNSENT_NO_DUPLICATE")
        else:
            action="FRESH_FIRST_ATTEMPT"
        if action!="RECONCILE_PRIOR_RESPONSE_NO_SEND":
            prior=_prior_unattributed_streak(
                queue_root=queue_root,slide_jobs=plan["slide_jobs"],
                before_slide=slide)
            if len(prior)>=2:
                return {
                    "status":"DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND",
                    "next_slide":None,"next_mode":None,
                    "unattempted_candidate_slide":slide,
                    "unattributed_prior_slides":prior,
                    "blocked_other_slides":blocked,
                    "evidence_type":"TWO_OWNED_SENDS_WITH_NO_ATTRIBUTABLE_REPLY",
                    "cause":"PROVIDER_OR_DOM_ATTRIBUTION_UNVERIFIED",
                    "resume_condition":"NEW_INDEPENDENT_TRANSPORT_EVIDENCE_OR_SAVED_REPLY",
                    "new_model_requests":False,
                    "per_slide_approval_required":False,
                    "automatic_retry_authorized":False,
                    "student_publication_authorized":False,
                }
        return {
            "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
            "next_slide":slide,"next_mode":mode,"attempt":1,
            "action":action,
            "previously_completed_slides":completed,
            "blocked_other_slides":blocked,
            "new_model_requests":False,
            "per_slide_approval_required":False,
            "automatic_retry_authorized":False,
            "student_publication_authorized":False,
        }
    return {
        "status":("ALL_ACADEMIC_REVIEW_PASSES_RECORDED"
                  if not blocked else "NO_SAFE_REVIEW_UNIT_REMAINING"),
        "next_slide":None,"next_mode":None,
        "previously_completed_slides":completed,
        "blocked_other_slides":blocked,
        "new_model_requests":False,
        "automatic_retry_authorized":False,
        "student_publication_authorized":False,
    }


def advance_one_safe_review(*,queue_root:Path,folder:Path,
                            execute:bool=False,transport=None)->dict:
    """At most one standing-authorized browser review; no source loops."""
    selection=select_next_safe_review(queue_root=queue_root,folder=folder)
    if not execute or selection["status"]!="ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY":
        return selection
    result=execute_one_review(
        queue_root=queue_root,folder=folder,
        slide=selection["next_slide"],mode=selection["next_mode"],
        attempt=1,transport=transport)
    return {
        "status":"ONE_AUTONOMOUS_ACADEMIC_REVIEW_ATTEMPT_FINISHED",
        "selection":selection,"review":result,
        # The same call may only reconcile a saved response (zero Sends);
        # never report it as a new provider submission without live proof.
        "new_provider_sends_this_invocation_upper_bound":1,
        "new_provider_send_proved_by_this_summary":False,
        "no_auto_chain":True,
        "academic_consensus_or_TTS_approved":False,
        "student_publication_authorized":False,
    }

def advance_bounded_safe_reviews(*,queue_root:Path,folder:Path,
                                 max_units:int=3,execute:bool=False,
                                 transport=None)->dict:
    """Advance independently eligible review units without per-slide prompts.

    Re-enter the existing select/claim/validate gateway after EACH verified
    immutable acceptance. Never bypass its anti-stall gate, make a second Send
    for an uncertain claim, or interpret review as TTS/release authorization.
    One user invocation permits at most three units; no background scheduler.
    """
    require(type(max_units) is int and 1 <= max_units <= 3,
            "Autonomous academic review batch is bounded to 1-3 units")
    queue_root,folder=Path(queue_root).absolute(),Path(folder).absolute()
    if not execute:
        selection=select_next_safe_review(queue_root=queue_root,folder=folder)
        return {"status":"READONLY_BOUNDED_REVIEW_PLAN",
                "max_units":max_units,"next_selection":selection,
                "new_provider_requests":False,"student_publication_authorized":False}
    completed=[]
    for _ in range(max_units):
        # advance_one_safe_review itself independently revalidates the source,
        # queue, model-claim state and anti-stall budget before every action.
        outcome=advance_one_safe_review(
            queue_root=queue_root,folder=folder,execute=True,
            transport=transport)
        if outcome.get("status")!="ONE_AUTONOMOUS_ACADEMIC_REVIEW_ATTEMPT_FINISHED":
            return {"status":"BOUNDED_REVIEW_STOPPED_NOT_READY",
                    "completed":completed,"stop_evidence":outcome,
                    "no_auto_retry":True,"student_publication_authorized":False}
        selected=outcome["selection"]
        receipt=outcome["review"]
        if receipt.get("status")!="GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED":
            # No more units even if an unrelated slide is technically fresh:
            # investigate the first unknown provider failure, not a send loop.
            return {"status":"BOUNDED_REVIEW_STOPPED_AFTER_UNACCEPTED_UNIT",
                    "completed":completed,"stop_evidence":outcome,
                    "no_auto_retry":True,"student_publication_authorized":False}
        slide,mode=selected["next_slide"],selected["next_mode"]
        accepted=queue_root/_receipt_name(slide,mode)
        require(accepted.is_file() and not accepted.is_symlink()
                and _sha(accepted)==receipt.get("receipt_sha256"),
                "Accepted review claim/receipt changed; stop before next Send")
        # Direct source hash/queue checks, not a bare success label. The same
        # verification happens again on the next selector's normal path.
        _check_queue(queue_root=queue_root,folder=folder,
                     slide=slide,mode=mode)
        completed.append({"slide":slide,"mode":mode,
                          "receipt_sha256":receipt["receipt_sha256"]})
    next_safe=select_next_safe_review(queue_root=queue_root,folder=folder)
    return {"status":"BOUNDED_REVIEW_LIMIT_REACHED",
            "completed":completed,"next_selection":next_safe,
            "max_units":max_units,"no_auto_retry":True,
            "academic_consensus_or_TTS_approved":False,
            "student_publication_authorized":False}


def summarize_queue(*,queue_root:Path,folder:Path)->dict:
    plan=json.loads((Path(queue_root)/"queue.json").read_text(encoding="utf8"))
    complete=[];awaited=[];errors=[]
    for x in plan["slide_jobs"]:
        n=x["slide"]
        for mode in ("INITIAL_REVIEW","INDEPENDENT_CHALLENGE"):
            result=Path(queue_root)/_receipt_name(n,mode)
            if result.is_file():
                _check_queue(queue_root=queue_root,folder=folder,slide=n,mode=mode)
                complete.append({"slide":n,"mode":mode,"count":x["utterance_count"]})
            else:
                awaited.append({"slide":n,"mode":mode})
        errors.extend(str(f.name) for f in Path(queue_root).glob(f"slide_{n:03d}_*_attempt_*.json")
                      if json.loads(f.read_text(encoding="utf8")).get("status")
                      =="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED")
    return {"status":"BOUNDED_AI_REVIEW_QUEUE_CURRENT",
            "expected_utterances":plan["expected_utterances"],
            "completed_passes":complete,"awaited_passes":awaited,
            "quarantined_failed_attempt_receipts":errors,
            "student_publication_authorized":False}
