"""A genuinely narrower source-grounded academic task after an uncertain G2 Send.

This is NOT a retry/replay of the original multi-utterance slide request.
It creates a *single original utterance versus one physically witnessed
textbook quotation/one slide target* question. An old submitted claim is
preserved and checked, never reset. A new task can be sent only through the
existing academic one-Send checkpoint and after fresh, source-free provider
health attestation. Its own first/challenge passes remain unapproved; neither
is automatically imported into the original G2 consensus or published.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import time

from .academic_review_checkpoint import (
    _load, fingerprint, validate_saved, recover_claimed_observation)
from .academic_provider_requalification import verify_result as verify_health
from .ai_academic_review_queue import _check_queue, _receipt_name
from .ai_academic_web_review import (
    build_review_job, review_instructions, run_web_review,
    validate_source_demoted_review)
from .series_gemini import decode_storyboard_response
from .figure_source_identity import _sha, require
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .recovery_registry import lookup_mechanism

KIND = "g2_distinct_focused_source_review"
SIGNATURE = "HISTORIC_FULL_SLIDE_SEND_UNCERTAIN_NEEDS_NEW_SOURCE_MATH_TASK"
MECHANISM = "ADMIT_ONE_QUOTE_ONE_UTTERANCE_REVIEW_WITH_OWN_CLAIM_AND_QA"
FOCUS_KIND = "SINGLE_UTTERANCE_SOURCE_MATH_CHALLENGE_V1"
REVIEW_ROOT_NAME = "G2_DISTINCT_FOCUSED_SOURCE_REVIEW_V1"


def _digest(data: object) -> str:
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, ensure_ascii=False,
        separators=(",", ":")).encode("utf8")).hexdigest()


def _files(folder: Path) -> dict:
    return {name: _sha(folder/name) for name in
            ("source.pdf", "slides.pdf", "script.txt")}


def plan(*, folder: Path, queue_root: Path, slide: int,
         utterance_id: str) -> dict:
    """Read-only, no-Send admission; no old source or review receipt mutated."""
    require(lookup_mechanism(KIND, SIGNATURE) == MECHANISM,
            "Source-focused review recovery not registered")
    folder, queue_root = Path(folder).absolute(), Path(queue_root).absolute()
    require(folder.is_dir() and not folder.is_symlink()
            and queue_root.is_dir() and not queue_root.is_symlink()
            and queue_root != folder and not queue_root.is_relative_to(folder)
            and type(slide) is int and 1 <= slide <= 200
            and type(utterance_id) is str,
            "Isolated genuine original academic review required")
    original_hashes = _files(folder)
    row = _check_queue(queue_root=queue_root, folder=folder,
                       slide=slide, mode="INITIAL_REVIEW")
    require(all(row["original_"+k+"_sha256"] == original_hashes[name]
                for name,k in (("source.pdf","source"),("slides.pdf","slides"),
                               ("script.txt","script"))),
            "Original source queue changed")
    old = queue_root/f"slide_{slide:03d}_initial_review_attempt_01_request"
    require(old.is_dir() and not old.is_symlink(),
            "No genuine original multi-utterance uncertain claim")
    historical = _load(old)
    original_claim = old/"dispatch_attempted.claim"
    require(original_claim.is_file() and not original_claim.is_symlink()
            and original_claim.read_text(encoding="utf8").strip() ==
                historical["request_fingerprint"]
            and historical["status"] in {
                "SUBMITTED_OR_UNCERTAIN", "NO_RESPONSE_UNRESOLVED",
                "LEGACY_SENT_NO_RESPONSE"}
            and historical.get("submission_may_have_occurred") is True
            and historical.get("can_auto_retry") is False
            and historical.get("review_mode") == "INITIAL_REVIEW"
            and all(historical.get(k+"_sha256") == original_hashes[name]
                    for k,name in (("source","source.pdf"),
                                   ("slides","slides.pdf"),
                                   ("script","script.txt")))
            and not (old/"model_response_untrusted.txt").is_file()
            and not (queue_root/_receipt_name(slide,"INITIAL_REVIEW")).exists(),
            "Previously submitted original claim is not eligible for new-task planning")
    full = build_review_job(folder=folder, slide_numbers=[slide])
    original = full["slides"][0]
    require(full["utterance_count"] == len(original["utterances"]) > 1
            and full["source_sha256"] == original_hashes["source.pdf"]
            and full["slides_sha256"] == original_hashes["slides.pdf"]
            and full["script_sha256"] == original_hashes["script.txt"]
            and type(full.get("verified_source_quote_candidates_v1")) is dict,
            "A material single-claim scope change requires a real larger original job")
    units = [u for u in original["utterances"] if u["id"] == utterance_id]
    require(len(units) == 1, "Unknown original narration unit")
    unit = units[0]
    candidates = full["verified_source_quote_candidates_v1"]
    require(candidates.get("status") == "PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1"
            and all(candidates.get(name+"_sha256") == full[name+"_sha256"]
                    for name in ("source", "slides", "script"))
            and candidates.get("citations_are_scientific_proof") is False,
            "No authentic original publisher quotation whitelist")
    rows = [r for r in candidates.get("utterances",[])
            if r.get("utterance_id") == utterance_id
            and r.get("spoken_sha256") == unit["spoken_sha256"]]
    require(len(rows) == 1 and type(rows[0].get("allowed_citations")) is list
            and bool(rows[0]["allowed_citations"]),
            "No original utterance-specific source witness")
    quote = copy.deepcopy(rows[0]["allowed_citations"][0])
    witness = prove_source_quote_occurrence(
        source_pdf=folder/"source.pdf",
        expected_sha256=full["source_sha256"],
        page_number=quote["source_page"],
        verbatim_quote=quote["verbatim_source_quote"])
    require(witness["status"] == "EXACT_ORIGINAL_PDF_PAGE_QUOTE_PRESENT"
            and witness["math_semantics_author_verified"] is False,
            "Not a physical textbook quote or falsely claimed mathematics proof")
    ranks = unit.get("ranked_candidates",[])
    visuals = [t for t in original["visual_targets"]
               if t.get("id") in ranks and t.get("bbox_pdf_pt") is not None]
    require(bool(visuals), "No physically rendered target for focused source task")
    chosen = visuals[0]
    focus = copy.deepcopy(full)
    focus["slides"][0]["utterances"] = [copy.deepcopy(unit)]
    focus["slides"][0]["visual_targets"] = [copy.deepcopy(chosen)]
    focus["utterance_count"] = 1
    packet = copy.deepcopy(candidates)
    packet["utterances"] = [copy.deepcopy(rows[0])]
    packet["utterances"][0]["allowed_citations"] = [quote]
    focus["verified_source_quote_candidates_v1"] = packet
    # Unique by original SOURCE and utterance, NOT user-entered nonce,
    # quote index, prompt wording or a caller-selected checkpoint directory.
    scope = _digest({
        "kind":FOCUS_KIND,"source_sha256":full["source_sha256"],
        "slides_sha256":full["slides_sha256"],
        "script_sha256":full["script_sha256"],
        "slide":slide,"utterance_id":utterance_id,
        "historic_original_claim_sha256":_sha(original_claim)})
    focus["focused_source_review_v1"] = {
        "kind":FOCUS_KIND,"scope_sha256":scope,
        "full_original_slide_utterances":full["utterance_count"],
        "selected_original_utterance_id":utterance_id,
        "single_source_page":quote["source_page"],
        "single_physically_witnessed_quote_sha256":quote["quote_sha256"],
        "single_original_slide_target":chosen["id"],
        "historic_original_claim_sha256":_sha(original_claim),
        "task_distinct_from_original_whole_slide_review":True,
        "quote_is_not_semantic_approval":True,
        "initial_and_independent_challenge_still_required":True,
        "original_g2_consensus_approved":False,
        "student_publication_authorized":False}
    original_text = review_instructions(full, mode="INITIAL_REVIEW")
    new_text = review_instructions(focus, mode="INITIAL_REVIEW")
    require(hashlib.sha256(new_text.encode("utf8")).hexdigest()
            != historical["prompt_sha256"]
            and len(new_text) < len(original_text)
            and _files(folder) == original_hashes,
            "New task would be the old full-slide Send in disguise")
    return {
        "status":"DISTINCT_SINGLE_UTTERANCE_SOURCE_TASK_PREPARED_NO_SEND",
        "scope_sha256":scope,"original_claim_sha256":_sha(original_claim),
        "original_prompt_sha256":historical["prompt_sha256"],
        "new_prompt_sha256":hashlib.sha256(new_text.encode()).hexdigest(),
        "source_sha256":full["source_sha256"],
        "physical_source_quote_sha256":quote["quote_sha256"],
        "original_utterance_count":full["utterance_count"],
        "focused_utterance_count":1,"slide":slide,"utterance_id":utterance_id,
        "job":focus,"provider_health_verified":False,
        "new_provider_requests":0,"old_send_replay_authorized":False,
        "original_g2_consensus_approved":False,
        "student_publication_authorized":False}


def _last_original_gemini_quarantine_mtime() -> float:
    """Conservative cross-stage Gemini failure circuit-breaker witness.

    A response health probe before a newer G3 failure cannot justify new G2
    scientific sends. This uses only local original metadata timestamps,
    never another user's browser response or source contents.
    """
    root=Path(os.getenv("LOCALAPPDATA") or
              (Path.home()/".cache"))/"Microvid"/"gemini_quarantine"
    if not root.exists():
        return 0.0
    require(root.is_dir() and not root.is_symlink(),
            "Quarantine evidence owner changed")
    markers=list(root.glob("gemini_*.meta.json"))
    require(len(markers)<=4096
            and all(p.is_file() and not p.is_symlink() for p in markers),
            "Unbounded or redirected provider uncertainty history")
    return max((p.stat().st_mtime for p in markers),default=0.0)


def _health_ok(*, health_result: Path, queue_root: Path,
               source_sha: str, old_claim: Path,
               family: str) -> dict:
    receipt = verify_health(
        result_path=health_result, checkpoint_parent=queue_root.parent,
        source_sha=source_sha, family=family)
    stamp = receipt.get("observed_unix")
    require(receipt["status"]=="SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"
            and receipt.get("verified_model_family")==family
            and receipt.get("verified_thinking_level") in ("medium","high")
            and (family!="neon" or receipt["verified_thinking_level"]=="high")
            and type(stamp) in (int,float)
            and stamp > max(old_claim.stat().st_mtime,
                            _last_original_gemini_quarantine_mtime())
            and 0 <= time.time()-stamp <= 21600
            and receipt["G2_approved"] is False
            and receipt["student_publication_authorized"] is False,
            "No fresh source-free Gemini response health after original uncertain Send")
    return receipt


def run_one(*, folder: Path, queue_root: Path, slide: int,
            utterance_id: str, health_result: Path,
            family: str = "flash") -> dict:
    """Execute ONE new source-focused Selenium claim, never the original Send."""
    folder, queue_root = Path(folder).absolute(),Path(queue_root).absolute()
    item = plan(folder=folder,queue_root=queue_root,
                slide=slide,utterance_id=utterance_id)
    old = queue_root/f"slide_{slide:03d}_initial_review_attempt_01_request"
    require(family in ("flash","pro","neon"),"Unverified browser family")
    root = queue_root.parent/REVIEW_ROOT_NAME
    require(not root.is_symlink() and not root.is_relative_to(folder),
            "Untrusted focused-work owner")
    scope_root = root/item["scope_sha256"]
    require(not scope_root.is_symlink(),"Redirected new review scope")
    manifest = scope_root/"admission.json"
    request = scope_root/"initial_request"
    if request.exists():
        # Restart the SAME independently claimed new task without another
        # Send. Recover only authenticated, immutable saved response bytes.
        require(manifest.is_file() and not manifest.is_symlink(),
                "No original distinct-task admission for recovery")
        prior = json.loads(manifest.read_text("utf8"))
        require(prior.get("status")==
                    "NEW_SUBSTANTIVE_SOURCE_QUOTE_CHECK_NOT_ORIGINAL_RETRY"
                and prior.get("scope_sha256")==item["scope_sha256"]
                and prior.get("old_claim_sha256")==item["original_claim_sha256"]
                and prior.get("prompt_sha256")==item["new_prompt_sha256"]
                and prior.get("source_sha256")==item["source_sha256"]
                and prior.get("source_quote_sha256")==
                    item["physical_source_quote_sha256"]
                and prior.get("old_request_resubmitted") is False
                and prior.get("health_model_family")==family
                and prior.get("student_publication_authorized") is False,
                "Existing distinct scientific task not provenance verified")
        state = _load(request)
        digest = fingerprint(
            request_text=review_instructions(item["job"],mode="INITIAL_REVIEW"),
            source_hashes={
                "source.pdf":item["job"]["source_sha256"],
                "slides.pdf":item["job"]["slides_sha256"],
                "script.txt":item["job"]["script_sha256"]},
            review_mode="INITIAL_REVIEW")
        require(state.get("request_fingerprint")==digest,
                "Existing focused request has unrelated prompt or source")
        if (state["status"] in {
                "SUBMITTED_OR_UNCERTAIN", "NO_RESPONSE_UNRESOLVED"}
                and (request/"model_response_identity.json").is_file()):
            recover_claimed_observation(
                checkpoint=request,expected_fingerprint=digest)
            state=_load(request)
        require(state["status"] in {
            "MODEL_REPLY_OBSERVED_UNVALIDATED",
            "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"},
            "Uncertain source-focused Send has no saved model text: NO REPLAY")
        result=validate_saved(
            checkpoint=request,expected_fingerprint=digest,
            validator=lambda raw:validate_source_demoted_review(
                folder=folder,job=item["job"],
                response=decode_storyboard_response(raw),
                mode="INITIAL_REVIEW"),
            required_model_family=("neon" if family=="neon" else None))
        return {
            "status":"FOCUSED_NEW_REVIEW_ONE_PASS_UNAPPROVED",
            "scope_sha256":item["scope_sha256"],
            "model_result":result,
            "new_original_slide_consensus_count":0,
            "original_request_resubmitted":False,
            "independent_challenge_pending":True,
            "student_publication_authorized":False}
    proof = _health_ok(health_result=health_result,queue_root=queue_root,
                       source_sha=item["source_sha256"],
                       old_claim=old/"dispatch_attempted.claim",family=family)
    root.mkdir(exist_ok=True)
    scope_root.mkdir(exist_ok=True)
    admission = {
        "schema_version":1,
        "status":"NEW_SUBSTANTIVE_SOURCE_QUOTE_CHECK_NOT_ORIGINAL_RETRY",
        "scope_sha256":item["scope_sha256"],
        "old_claim_sha256":item["original_claim_sha256"],
        "source_sha256":item["source_sha256"],
        "prompt_sha256":item["new_prompt_sha256"],
        "source_quote_sha256":item["physical_source_quote_sha256"],
        "health_receipt_sha256":_sha(Path(health_result)),
        "health_model_family":family,
        "old_request_resubmitted":False,
        "g2_scientific_acceptance":False,
        "student_publication_authorized":False}
    if manifest.exists():
        require(manifest.is_file() and not manifest.is_symlink()
                and json.loads(manifest.read_text("utf8"))==admission,
                "Changed prior focused task admission; NO REPLAY")
    else:
        with manifest.open("x",encoding="utf8") as file:
            json.dump(admission,file,sort_keys=True,indent=2)
            file.write("\n");file.flush();os.fsync(file.fileno())
    # The shared academic checkpoint writes a durable Send claim BEFORE
    # transport and never submits an uncertain source request twice.
    prior_mode=os.environ.get("MICROGEN_GEMINI_UI_MODE")
    prior_thinking=os.environ.get("MICROGEN_GEMINI_THINKING_LEVEL")
    try:
        # Neon is a distinct exact UI contract, not a silent Flash fallback.
        # The shared browser code independently verifies Neon/High again.
        os.environ["MICROGEN_GEMINI_UI_MODE"]=(
            "pro" if family=="neon" else family)
        if family=="neon":
            os.environ["MICROGEN_GEMINI_THINKING_LEVEL"]="high"
        result = run_web_review(
            folder=folder, job=item["job"], mode="INITIAL_REVIEW",
            checkpoint_dir=scope_root/"initial_request",
            chrome_port=9222,wait_cap_s=240,
            required_model_family=("neon" if family=="neon" else None))
    finally:
        for key,value in (
            ("MICROGEN_GEMINI_UI_MODE",prior_mode),
            ("MICROGEN_GEMINI_THINKING_LEVEL",prior_thinking)):
            if value is None:
                os.environ.pop(key,None)
            else:
                os.environ[key]=value
    require(result["status"] == "SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
            and result["review_count"] == 1
            and result["student_publication_authorized"] is False
            and result["academic_mathematics_independently_verified"] is False,
            "New focused reply is not independently source validated")
    return {
        "status":"FOCUSED_NEW_REVIEW_ONE_PASS_UNAPPROVED",
        "scope_sha256":item["scope_sha256"],
        "model_result":result,
        "new_original_slide_consensus_count":0,
        "original_request_resubmitted":False,
        "independent_challenge_pending":True,
        "student_publication_authorized":False}
