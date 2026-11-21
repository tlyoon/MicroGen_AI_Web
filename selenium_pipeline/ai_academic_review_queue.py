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
    review_instructions,validate_source_demoted_review)
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


def _sourcebound_neon_high_continuation(*,queue_root:Path,folder:Path):
    """Reuse source-specific Neon/High qualification after an accepted pass.

    The immediate two-uncertain-request streak can legitimately reset when
    later slides pass. That does NOT make an originally absent Pro family
    available in a new Gemini tab. Bind the previous old claims and immutable
    NEW Neon two-PDF success to this exact original source before choosing
    the qualified model on a further untouched source review.
    """
    from .academic_neon_high_two_pdf_requalification import qualifying_proof
    from .figure_source_identity import FigureIdentityReviewRequired
    try:
        proof=qualifying_proof(
            queue_root=queue_root,checkpoint_parent=queue_root.parent,
            source_sha=_sha(folder/"source.pdf"),prior_slides=[10,11])
    except (FigureIdentityReviewRequired,ValueError,OSError):
        return None
    if (type(proof) is dict
            and proof.get("status")==
                "NEON_HIGH_TWO_PDF_SOURCE_FREE_RESPONSE_VERIFIED"
            and proof.get("source_free_neon_pdf_capability_verified") is True
            and proof.get("verified_model_family")=="neon"
            and proof.get("verified_thinking_level")=="high"
            and proof.get("new_source_review_send_allowed") is False
            and proof.get("student_publication_authorized") is False):
        return proof
    return None


def execute_one_review(*,queue_root:Path,folder:Path,
                       slide:int,mode:str,
                       attempt:int=1,transport=None,
                       wrapped_recovery_only:bool=False,
                       certified_presend_only:bool=False,
                       expected_failed_attempt_sha256:str|None=None,
                       health_family:str="pro")->dict:
    queue_root=Path(queue_root).absolute();folder=Path(folder).absolute()
    require(type(attempt) is int and 1<=attempt<=3,"No unbounded AI retry loop")
    row=_check_queue(queue_root=queue_root,folder=folder,slide=slide,mode=mode)
    success=queue_root/_receipt_name(slide,mode)
    require(not success.exists(),"Do not resubmit an already verified source review")
    evidence_file=queue_root/f"slide_{slide:03d}_{mode.lower()}_attempt_{attempt:02d}.json"
    live_checkpoint=queue_root/(
        f"slide_{slide:03d}_{mode.lower()}_attempt_{attempt:02d}_request")
    require(type(wrapped_recovery_only) is bool,
            "Invalid saved-review recovery mode")
    if wrapped_recovery_only:
        require(transport is None and attempt==1,
                "Envelope recovery MUST NOT issue any Gemini Send")
        prior_reconciliation=queue_root/(
            f"slide_{slide:03d}_{mode.lower()}_reconciled_after_attempt_01.json")
        require(prior_reconciliation.is_file()
                and not prior_reconciliation.is_symlink(),
                "Original failed reconciliation evidence is required")
        old=json.loads(prior_reconciliation.read_text(encoding="utf8"))
        require(old.get("status")=="FAILED_SAVED_RESPONSE_RECONCILIATION_NO_SEND"
                and old.get("slide")==slide and old.get("mode")==mode
                and old.get("provider_submission_state")=="PRIOR_SAVED_RESPONSE_ONLY"
                and old.get("new_provider_requests") is False
                and old.get("academically_approved") is False
                and old.get("student_publication_authorized") is False,
                "Cannot reinterpret a previously approved or unclaimed source review")
        from .academic_review_envelope_recovery import (
            inspect_owned_nested_envelope)
        candidate=inspect_owned_nested_envelope(
            checkpoint=live_checkpoint, mode=mode,
            job=build_review_job(folder=folder,slide_numbers=[slide]))
        require(candidate is not None
                and candidate["status"]=="VERIFIED_WRAPPED_SOURCE_REVIEW_NO_SEND",
                "Not an exact source-bound model-owned wrapped reply")
    if transport is not None and (live_checkpoint/"dispatch_attempted.claim").exists():
        require(False,"Previously claimed Gemini review cannot use an injected "
                      "transport; only verify same saved reply without Send")
    saved_reply_candidate=False
    if transport is None and (live_checkpoint.exists() or live_checkpoint.is_symlink()):
        from .academic_review_checkpoint import _load
        require(live_checkpoint.is_dir() and not live_checkpoint.is_symlink(),
                "Previous model request window untrusted")
        saved_state=_load(live_checkpoint)
        saved_path=live_checkpoint/"model_response_untrusted.txt"
        saved_reply_candidate=(
            (saved_state["status"] in {
                "MODEL_REPLY_OBSERVED_UNVALIDATED",
                "REJECTED_RESPONSE_UNTRUSTED",
                "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED",
            } or (saved_state["status"] in {
                "SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED"}
                and (live_checkpoint/"model_response_identity.json").is_file()
                and not (live_checkpoint/"model_response_identity.json").is_symlink()))
            and saved_path.is_file() and not saved_path.is_symlink())
    reconciliation_only=evidence_file.exists() and saved_reply_candidate
    if reconciliation_only:
        # Historical failure is permanent evidence; successor receipt
        # cannot overwrite its previous scientific validation decision.
        evidence_file=queue_root/(
            f"slide_{slide:03d}_{mode.lower()}_reconciled_after_attempt_{attempt:02d}.json")
    if wrapped_recovery_only:
        require(reconciliation_only,
                "Envelope recovery needs existing invalid saved reply")
        evidence_file=queue_root/(
            f"slide_{slide:03d}_{mode.lower()}_envelope_recovered_after_attempt_{attempt:02d}.json")
    require(type(certified_presend_only) is bool
            and not (certified_presend_only and wrapped_recovery_only),
            "Only one exact historical review recovery mode may run")
    certified_prior_digest=None
    if certified_presend_only:
        from .academic_review_checkpoint import (
            _load, _verify_certified_unsent, fingerprint,
            MAX_CERTIFIED_PRESEND_RECOVERIES)
        require(transport is None and attempt == 1
                and type(expected_failed_attempt_sha256) is str
                and re.fullmatch(r"[a-f0-9]{64}", expected_failed_attempt_sha256)
                and evidence_file.is_file() and not evidence_file.is_symlink()
                and _sha(evidence_file) == expected_failed_attempt_sha256,
                "Certified pre-Send resume needs exact original failed receipt")
        old=json.loads(evidence_file.read_text(encoding="utf8"))
        require(old.get("slide")==slide and old.get("mode")==mode
                and old.get("attempt")==1
                and old.get("status")=="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
                and old.get("provider_submission_state")==
                    "UNKNOWN_AFTER_POSSIBLE_SUBMISSION"
                and old.get("manual_retry_eligible") is False
                and old.get("student_publication_authorized") is False,
                "Only the original ambiguous failure may gain a stronger typed no-Send witness")
        original_claim=_load(live_checkpoint)
        proof_count=_verify_certified_unsent(live_checkpoint,original_claim)
        job_before=build_review_job(folder=folder,slide_numbers=[slide])
        prompt_fingerprint=fingerprint(
            request_text=review_instructions(job_before,mode=mode),
            source_hashes={
                "source.pdf":job_before["source_sha256"],
                "slides.pdf":job_before["slides_sha256"],
                "script.txt":job_before["script_sha256"],
            },
            review_mode=mode)
        original_index=queue_root/".microgen_academic_review_once"/(
            prompt_fingerprint+".claim")
        require(original_claim["status"]=="CERTIFIED_PRESEND_UNSENT"
                and 1<=proof_count<MAX_CERTIFIED_PRESEND_RECOVERIES
                and original_claim["request_fingerprint"]==prompt_fingerprint
                and all(original_claim[k]==job_before[k] for k in
                        ("source_sha256","slides_sha256","script_sha256"))
                and job_before["utterance_count"]==row["utterance_count"]
                and original_index.is_file() and not original_index.is_symlink(),
                "No source-bound certified original academic reviewer Send window")
        certified_prior_digest=expected_failed_attempt_sha256
        # The old immutable JSON remains a historical failure; this
        # write-once successor records the exact bounded SAME-claim resume.
        evidence_file=queue_root/(
            f"slide_{slide:03d}_{mode.lower()}_certified_presend_resumed_after_attempt_01.json")
    require(not evidence_file.exists() and not evidence_file.is_symlink(),
            "Observed attempt/reconciliation receipt must never be overwritten")
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
    prior=_prior_unattributed_streak(
        queue_root=queue_root,
        slide_jobs=json.loads((queue_root/"queue.json").read_text(encoding="utf8"))["slide_jobs"],
        before_slide=slide)
    required_model_family=None
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
        if not saved_reply:
            # The same-model short text-only canary proved insufficient:
            # two real full-source reviews lost all model attribution.
            # Require a *newer*, exact synthetic two-PDF/readback proof.
            # The original failed source requests remain unrepeatable.
            from .academic_dual_pdf_capability import qualifying_proof
            from .figure_source_identity import FigureIdentityReviewRequired
            try:
                capability = qualifying_proof(
                    queue_root=queue_root,checkpoint_parent=queue_root.parent,
                    source_sha=_sha(folder/"source.pdf"),prior_slides=prior,
                    family=health_family)
            except (FigureIdentityReviewRequired, ValueError, OSError):
                # Some historical QUEUE receipts predate the strict claim
                # schema. They can NEVER support a new Send; remain blocked.
                capability = None
            if capability is None:
                from .academic_neon_high_two_pdf_requalification import (
                    qualifying_proof as neon_high_proof)
                try:
                    capability=neon_high_proof(
                        queue_root=queue_root,checkpoint_parent=queue_root.parent,
                        source_sha=_sha(folder/"source.pdf"),prior_slides=prior)
                except (FigureIdentityReviewRequired, ValueError, OSError):
                    capability=None
                if capability is not None and capability.get(
                        "source_free_neon_pdf_capability_verified") is True:
                    required_model_family="neon"
            require(capability is not None,
                    "DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND: a fresh "
                    "owned dual-synthetic-PDF capability result is required "
                    "before any new full-source scientific submission")
    if required_model_family is None and transport is None:
        # The immediate uncertain-send streak resets after a successful Neon
        # pass; the source-specific qualified runtime model must NOT revert
        # to a stale Pro default for a later original source Send.
        if _sourcebound_neon_high_continuation(
                queue_root=queue_root,folder=folder) is not None:
            required_model_family="neon"
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
                _load, fingerprint, validate_saved, recover_claimed_observation)
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
            if (checkpoint_state["status"] in {
                    "SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED"}
                and (live_checkpoint/"model_response_identity.json").is_file()):
                checkpoint_state=recover_claimed_observation(
                    checkpoint=live_checkpoint,expected_fingerprint=expected)
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
                    validator=lambda raw: validate_source_demoted_review(
                        folder=folder, job=job,
                        response=decode_storyboard_response(raw),
                        mode=mode),
                    required_model_family=required_model_family,
                )
            elif checkpoint_state["status"] == "CERTIFIED_PRESEND_UNSENT":
                # This status is NOT ordinarily safe to retry. Admission
                # above must have source-fingerprint-validated typed no-click
                # witnesses and the original immutable failed receipt.
                require(certified_presend_only,
                        "Certified review recovery requires exact prior-claim evidence")
            elif checkpoint_state["status"] not in {"PREPARED_NOT_SENT"}:
                raise RuntimeError(
                    "Academic browser Send may already have occurred; "
                    "only response reconciliation is allowed, never resend")
        if response is None:
            response=run_web_review(
                folder=folder,job=job,mode=mode,
                transport=transport,
                response_observer=witness_model_return,
                checkpoint_dir=live_checkpoint if transport is None else None,
                required_model_family=required_model_family)
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
        fail={"status":("FAILED_SAVED_RESPONSE_RECONCILIATION_NO_SEND"
                        if saved_reply_candidate else
                        "FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"),
              "slide":slide,"mode":mode,"attempt":attempt,
              "error_type":type(exc).__name__,"reason":str(exc)[:450],
              "requires_explicit_next_attempt":not saved_reply_candidate,
              "provider_submission_state":(
                  "PRIOR_SAVED_RESPONSE_ONLY" if saved_reply_candidate else
                  "RETURNED_RESPONSE_INVALID" if returned_response else
                  "CONFIRMED_PRE_SUBMISSION_MODEL_SELECTION_FAILURE"
                  if model_failure_before_send else
                  "UNKNOWN_AFTER_POSSIBLE_SUBMISSION"),
              "manual_retry_eligible":False if saved_reply_candidate else manual_retry_eligible,
              "requires_owner_reconciliation":(
                  not saved_reply_candidate and not manual_retry_eligible
                  and not returned_response),
              "requires_new_independent_source_evidence":bool(returned_response),
              "can_advance_other_unattempted_slides":not saved_reply_candidate,
              "new_provider_requests":False if saved_reply_candidate else None,
              "academically_approved":False,"student_publication_authorized":False}
        with evidence_file.open("x",encoding="utf8") as f:
            json.dump(fail,f,indent=2);f.write("\n")
        return fail
    with success.open("x",encoding="utf8") as f:
        json.dump(response,f,indent=2);f.write("\n")
    audit=response.get("source_only_downgrade_audit") or {}
    genuinely_returned=audit.get(
        "model_returned_utterance_count",response["review_count"])
    require(type(genuinely_returned) is int
            and 1<=genuinely_returned<=response["review_count"],
            "Missing source-bound original model-row count")
    done={"status":"GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED",
          "slide":slide,"mode":mode,"attempt":attempt,
          "verified_original_utterances":genuinely_returned,
          "machine_unreviewed_placeholders":
              response["review_count"]-genuinely_returned,
          "full_original_model_review_coverage":
              genuinely_returned==response["review_count"],
          "receipt_sha256":_sha(success),
          "academic_independent_challenge_complete":False,
          "student_publication_authorized":False}
    if certified_presend_only:
        done["certified_presend_original_claim_provenance"]={
            "schema_version":1,
            "status":"EXACT_ORIGINAL_NO_CLICK_CLAIM_RESUMED_FOR_ONE_SOURCE_REVIEW",
            "original_failed_attempt_sha256":certified_prior_digest,
            "original_source_sha256":_sha(folder/"source.pdf"),
            "certified_presend_count_before_resume":proof_count,
            "old_historical_receipt_preserved":True,
            "independent_math_accepted":False,
            "student_publication_authorized":False,
        }
    if wrapped_recovery_only:
        # Audit the write-once successor. Original request and prior failed
        # reconciliation receipts stay immutable, and the next academic
        # reviewer must still pass separate independent source consensus.
        done["saved_envelope_recovery_provenance"]={
            "schema_version":1,
            "status":"OWNED_REPLY_SOURCE_ONLY_ENVELOPE_RECOVERY_V1",
            "original_model_response_sha256":candidate["response_sha256"],
            "prior_failed_reconciliation_sha256":_sha(prior_reconciliation),
            "new_provider_requests":False,
            "scientific_verdicts_added":0,
            "source_citations_invented":0,
            "student_publication_authorized":False,
        }
    with evidence_file.open("x",encoding="utf8") as f:
        json.dump(done,f,indent=2);f.write("\n")
    return done


def select_next_safe_review(*,queue_root:Path,folder:Path,
                            health_family:str="pro")->dict:
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
        if scope.get("certified_presend_same_claim_recovery_ready") is True:
            from .recovery_registry import lookup_mechanism
            require(lookup_mechanism(
                "source_review_claim",
                "G2_TYPED_PRESEND_UNSENT_REUSE_EXACT_ORIGINAL_WINDOW") ==
                "RESUME_ONLY_ORIGINAL_CERTIFIED_UNSENT_CLAIM_ONCE",
                "No executable registry admission for certified academic pre-Send")
            # A proven no-click request does not cure repeated unattributed
            # Sends from other slides. Preserve the provider-health circuit.
            prior = _prior_unattributed_streak(
                queue_root=queue_root, slide_jobs=plan["slide_jobs"],
                before_slide=slide)
            if len(prior)>=2:
                blocked.append({"slide":slide,"mode":mode,
                                "reason":"CERTIFIED_UNSENT_HELD_BY_PROVIDER_HEALTH"})
                continue
            old_receipt = queue_root/(
                f"slide_{slide:03d}_{mode.lower()}_attempt_01.json")
            require(old_receipt.is_file() and not old_receipt.is_symlink(),
                    "Missing original failed attempt for typed pre-Send recovery")
            return {
                "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
                "next_slide":slide,"next_mode":mode,"attempt":1,
                "action":"RESUME_CERTIFIED_UNSENT_ORIGINAL_CLAIM",
                "original_failed_attempt_sha256":_sha(old_receipt),
                "original_source_sha256":scope["original_source_sha256"],
                "certified_presend_count":
                    scope["review_stages"][mode]["certified_presend_count"],
                "previously_completed_slides":completed,
                "blocked_other_slides":blocked,
                "new_model_requests":False,
                "original_request_replay_authorized":False,
                "same_original_claim_pre_click_recovery_only":True,
                "per_slide_approval_required":False,
                "student_publication_authorized":False,
            }
        # A previous failed attempt does not invalidate bytes already saved
        # by the SAME claimed review request. Reconcile the immutable saved
        # response before considering another browser Send; never erase its
        # historical failure receipt or reset its provider claim.
        saved_claim=queue_root/(
            f"slide_{slide:03d}_{mode.lower()}_attempt_01_request")
        if saved_claim.exists() or saved_claim.is_symlink():
            require(saved_claim.is_dir() and not saved_claim.is_symlink(),
                    "Previous academic review request window untrusted")
            prior_state=_load(saved_claim)
            saved_path=saved_claim/"model_response_untrusted.txt"
            reconciled=queue_root/(
                f"slide_{slide:03d}_{mode.lower()}_reconciled_after_attempt_01.json")
            if reconciled.exists() or reconciled.is_symlink():
                require(reconciled.is_file() and not reconciled.is_symlink(),
                        "Saved-response reconciliation record untrusted")
                reconcile_result=json.loads(reconciled.read_text(encoding="utf8"))
                # An invalid saved reply is permanently unavailable for
                # this mode. Do NOT replay, approve, or silently repair it.
                # Its outstanding scientific gap remains in the queue, but
                # independently unattempted slides may advance under the
                # ordinary provider health and source-validation gates.
                require(reconcile_result.get("status") in {
                    "FAILED_SAVED_RESPONSE_RECONCILIATION_NO_SEND",
                    "GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED"},
                    "Unexpected prior saved-response reconciliation")
                if reconcile_result["status"]=="FAILED_SAVED_RESPONSE_RECONCILIATION_NO_SEND":
                    require(
                        reconcile_result.get("slide")==slide
                        and reconcile_result.get("mode")==mode
                        and reconcile_result.get("attempt")==1
                        and reconcile_result.get("provider_submission_state")
                            =="PRIOR_SAVED_RESPONSE_ONLY"
                        and reconcile_result.get("new_provider_requests") is False
                        and reconcile_result.get("academically_approved") is False
                        and reconcile_result.get("student_publication_authorized") is False,
                        "Failed saved reply cannot be quarantined without exact identity")
                    # Historical salvage route: the same owned model bytes
                    # may contain a single known {"job":...} envelope. It is
                    # NOT another reviewer response; source/quote/math checks
                    # remain independently mandatory and no Send is possible.
                    successor=queue_root/(
                        f"slide_{slide:03d}_{mode.lower()}_envelope_recovered_after_attempt_01.json")
                    if successor.exists() or successor.is_symlink():
                        require(successor.is_file() and not successor.is_symlink(),
                                "Unsafe historical envelope successor")
                        previous=json.loads(successor.read_text(encoding="utf8"))
                        require(previous.get("slide")==slide
                                and previous.get("mode")==mode
                                and previous.get("attempt")==1
                                and previous.get("student_publication_authorized") is False
                                and previous.get("status") in {
                                    "GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED",
                                    "FAILED_SAVED_RESPONSE_RECONCILIATION_NO_SEND"},
                                "Untrusted envelope recovery successor")
                        require(previous.get("status")!=
                                "GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED",
                                "Accepted envelope reply has no original source pass")
                    else:
                        from .academic_review_envelope_recovery import (
                            inspect_owned_nested_envelope)
                        from .figure_source_identity import FigureIdentityReviewRequired
                        try:
                            proof=inspect_owned_nested_envelope(
                                checkpoint=saved_claim,mode=mode,
                                job=build_review_job(folder=folder,slide_numbers=[slide]))
                        except (FigureIdentityReviewRequired, ValueError,
                                KeyError, TypeError):
                            # A tampered, unbound or malformed saved reply is
                            # NOT evidence of recovery. Keep it quarantined,
                            # without claiming any source-supported verdict.
                            proof=None
                        if proof is not None:
                            return {
                                "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
                                "next_slide":slide,"next_mode":mode,"attempt":1,
                                "action":"RECOVER_WRAPPED_SAVED_REPLY_NO_SEND",
                                "historical_reconciliation_sha256":_sha(reconciled),
                                "original_model_response_sha256":proof["response_sha256"],
                                "original_model_rows":proof["model_rows"],
                                "previously_completed_slides":completed,
                                "blocked_other_slides":blocked,
                                "new_model_requests":False,
                                "per_slide_approval_required":False,
                                "automatic_retry_authorized":False,
                                "student_publication_authorized":False,
                            }
                    blocked.append({
                        "slide":slide,"mode":mode,
                        "reason":"SOURCE_REVIEW_QUARANTINED_INVALID_SAVED_REPLY",
                        "reconciliation_receipt_sha256":_sha(reconciled),
                        "original_request_replay_authorized":False,
                        "needs_new_independent_source_evidence":True,
                    })
                    continue
                blocked.append({"slide":slide,"mode":mode,
                                "reason":"PRIOR_SAVED_REPLY_RECONCILIATION_ALREADY_ATTEMPTED"})
                continue
            if (prior_state["status"] in {
                "MODEL_REPLY_OBSERVED_UNVALIDATED",
                "REJECTED_RESPONSE_UNTRUSTED",
                "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED",
            } or (prior_state["status"] in {
                "SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED"}
                and (saved_claim/"model_response_identity.json").is_file()
                and not (saved_claim/"model_response_identity.json").is_symlink())
            ) and saved_path.is_file() and not saved_path.is_symlink():
                return {
                    "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
                    "next_slide":slide,"next_mode":mode,"attempt":1,
                    "action":"RECONCILE_PRIOR_RESPONSE_NO_SEND",
                    "previously_completed_slides":completed,
                    "blocked_other_slides":blocked,
                    "new_model_requests":False,
                    "per_slide_approval_required":False,
                    "automatic_retry_authorized":False,
                    "student_publication_authorized":False,
                }
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
                from .academic_dual_pdf_capability import qualifying_proof
                from .figure_source_identity import FigureIdentityReviewRequired
                try:
                    capability=qualifying_proof(
                        queue_root=queue_root,checkpoint_parent=queue_root.parent,
                        source_sha=_sha(folder/"source.pdf"),prior_slides=prior,
                        family=health_family)
                except (FigureIdentityReviewRequired, ValueError, OSError):
                    # A historical unsupported claim or tampered receipt
                    # cannot prove a healthy two-PDF response. Fail closed
                    # to the existing two-original-Send circuit breaker.
                    capability=None
                if capability is not None:
                    return {
                        "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
                        "next_slide":slide,"next_mode":mode,"attempt":1,
                        "action":action,
                        "original_source_pdf_health_proven":True,
                        "synthetic_pdf_capability_incident":
                            capability["incident_sha256"],
                        "blocked_other_slides":blocked,
                        "new_model_requests":False,
                        "student_publication_authorized":False,
                    }
                from .academic_neon_high_two_pdf_requalification import (
                    qualifying_proof as neon_high_proof)
                try:
                    neon=neon_high_proof(
                        queue_root=queue_root,checkpoint_parent=queue_root.parent,
                        source_sha=_sha(folder/"source.pdf"),prior_slides=prior)
                except (FigureIdentityReviewRequired, ValueError, OSError):
                    neon=None
                if (neon is not None
                        and neon.get("source_free_neon_pdf_capability_verified") is True
                        and neon.get("verified_model_family")=="neon"
                        and neon.get("verified_thinking_level")=="high"):
                    from .recovery_registry import lookup_mechanism
                    require(lookup_mechanism(
                        "selection_action",
                        "G2_NEW_SOURCE_REVIEW_AFTER_VERIFIED_NEON_HIGH_TWO_PDF") ==
                        "SELECT_ONE_UNATTEMPTED_SOURCE_SLIDE_WITH_NEON_HIGH_WITNESS",
                        "No registered Neon academic review source handoff")
                    return {
                        "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
                        "next_slide":slide,"next_mode":mode,"attempt":1,
                        "action":action,"required_runtime_family":"neon",
                        "required_thinking_level":"high",
                        "original_source_pdf_health_proven":True,
                        "synthetic_pdf_capability_incident":neon["original_incident_sha256"],
                        "new_model_requests":False,
                        "original_request_replay_authorized":False,
                        "student_publication_authorized":False,
                    }
                # A consumed, unsuccessful synthetic probe is NOT a reason
                # to create another "recovery" stage in every future run.
                # Preserve its exclusive request claim; only a *new* incident
                # with newer original source evidence could qualify again.
                try:
                    from .academic_dual_pdf_capability import existing_outcome
                    consumed=existing_outcome(
                        queue_root=queue_root,checkpoint_parent=queue_root.parent,
                        source_sha=_sha(folder/"source.pdf"),prior_slides=prior,
                        family=health_family)
                except (FigureIdentityReviewRequired, ValueError, OSError):
                    consumed=None
                if consumed is not None and (
                        consumed.get("new_source_review_send_allowed") is not True):
                    # Only one genuinely NEW modality test after the observed
                    # primary-profile repair is permitted. It is never v1
                    # re-submission: same original claim identities, new
                    # two-PDF secrets and exclusive versioned v2 receipt.
                    if (health_family == "pro" and
                        consumed.get("status") == "DUAL_SYNTHETIC_PDF_RESPONSE_UNVERIFIED"):
                        from .academic_dual_pdf_profile_repair_v2 import newly_eligible
                        try:
                            v2_allowed = newly_eligible(
                                queue_root=queue_root,
                                checkpoint_parent=queue_root.parent,
                                source_sha=_sha(folder/"source.pdf"),
                                prior_slides=prior, family=health_family)
                        except (FigureIdentityReviewRequired, ValueError, OSError):
                            v2_allowed = False
                        if v2_allowed:
                            return {
                                "status":"DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND",
                                "required_recovery_action":
                                    "SYNTHETIC_DUAL_PDF_AFTER_VERIFIED_PRIMARY_PROFILE_REPAIR",
                                "next_slide":None,"next_mode":None,
                                "unattempted_candidate_slide":slide,
                                "unattributed_prior_slides":prior,
                                "new_model_requests":False,
                                "original_request_replay_authorized":False,
                                "student_publication_authorized":False,
                            }
                    return {
                        "status":"DEFERRED_SYNTHETIC_PDF_CAPABILITY_EXHAUSTED_NO_RESEND",
                        "next_slide":None,"next_mode":None,
                        "unattempted_candidate_slide":slide,
                        "unattributed_prior_slides":prior,
                        "last_capability_status":consumed["status"],
                        "original_request_replay_authorized":False,
                        "new_model_requests":False,
                        "student_publication_authorized":False,
                    }
                return {
                    "status":"DEFERRED_REPEATED_UNATTRIBUTED_BROWSER_SEND",
                    "required_recovery_action":"SYNTHETIC_DUAL_PDF_CAPABILITY_PROBE",
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
        if action=="FRESH_FIRST_ATTEMPT":
            # The two ambiguous original requests remain protected even after
            # a later source-valid Neon pass resets the immediate failure
            # *streak*. Continue using the same exact source-bound Neon/High
            # qualification for NEW slide or challenge requests only.
            neon=_sourcebound_neon_high_continuation(
                queue_root=queue_root,folder=folder)
            if neon is not None:
                from .recovery_registry import lookup_mechanism
                require(lookup_mechanism(
                    "selection_action",
                    "G2_NEW_SOURCE_REVIEW_AFTER_VERIFIED_NEON_HIGH_TWO_PDF") ==
                    "SELECT_ONE_UNATTEMPTED_SOURCE_SLIDE_WITH_NEON_HIGH_WITNESS",
                    "No registered Neon source continuation after accepted pass")
                return {
                    "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
                    "next_slide":slide,"next_mode":mode,"attempt":1,
                    "action":action,"required_runtime_family":"neon",
                    "required_thinking_level":"high",
                    "original_source_pdf_health_proven":True,
                    "synthetic_pdf_capability_incident":
                        neon["original_incident_sha256"],
                    "new_model_requests":False,
                    "original_request_replay_authorized":False,
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
                            execute:bool=False,transport=None,
                            health_family:str="pro")->dict:
    """At most one standing-authorized browser review; no source loops."""
    selection=select_next_safe_review(
        queue_root=queue_root,folder=folder,health_family=health_family)
    if not execute or selection["status"]!="ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY":
        return selection
    saved_envelope=selection.get("action")=="RECOVER_WRAPPED_SAVED_REPLY_NO_SEND"
    certified_presend=selection.get("action")=="RESUME_CERTIFIED_UNSENT_ORIGINAL_CLAIM"
    require((not saved_envelope and not certified_presend) or transport is None,
            "Historical academic recoveries require original owned browser transport")
    result=execute_one_review(
        queue_root=queue_root,folder=folder,
        slide=selection["next_slide"],mode=selection["next_mode"],
        attempt=1,transport=transport,
        wrapped_recovery_only=saved_envelope,
        certified_presend_only=certified_presend,
        expected_failed_attempt_sha256=selection.get(
            "original_failed_attempt_sha256") if certified_presend else None,
        health_family=health_family)
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
                                 transport=None,health_family:str="pro")->dict:
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
        selection=select_next_safe_review(
            queue_root=queue_root,folder=folder,health_family=health_family)
        return {"status":"READONLY_BOUNDED_REVIEW_PLAN",
                "max_units":max_units,"next_selection":selection,
                "new_provider_requests":False,"student_publication_authorized":False}
    completed=[]
    for _ in range(max_units):
        # advance_one_safe_review itself independently revalidates the source,
        # queue, model-claim state and anti-stall budget before every action.
        outcome=advance_one_safe_review(
            queue_root=queue_root,folder=folder,execute=True,
            transport=transport,health_family=health_family)
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
    next_safe=select_next_safe_review(
        queue_root=queue_root,folder=folder,health_family=health_family)
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
