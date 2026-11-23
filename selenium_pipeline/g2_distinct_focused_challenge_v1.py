"""Independent second review of a genuinely new, narrowly source-bound G2 task.

One initial source-verified model response is NOT an original G2 acceptance.
Run an independently challenged same one-utterance task, using its separate
immutable Send claim and fresh Gemini chat. Reconcile only source-witnessed
actual model reasoning; never write the historical original full-slide queue.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .academic_review_checkpoint import (
    _load, fingerprint, validate_saved, recover_claimed_observation)
from .ai_academic_web_review import (
    review_instructions, run_web_review, validate_source_demoted_review)
from .ai_academic_review_consensus import (
    _independently_check_saved_pass, _actual_model_rows,
    _canonical_academic_rationale)
from .figure_source_identity import _sha, require
from .g2_distinct_focused_source_review_v1 import (
    plan, run_one, _health_ok, REVIEW_ROOT_NAME)
from .series_gemini import decode_storyboard_response


def challenge_once(*, folder: Path, queue_root: Path, slide: int,
                   utterance_id: str, health_result: Path,
                   family: str = "neon") -> dict:
    """Separate exact model-scoped challenge; never replay initial or old Send."""
    require(family=="neon",
            "Only independently qualified Neon/High source reviewer supported")
    folder, queue_root = Path(folder).absolute(),Path(queue_root).absolute()
    item=plan(folder=folder,queue_root=queue_root,
              slide=slide,utterance_id=utterance_id)
    scope=queue_root.parent/REVIEW_ROOT_NAME/item["scope_sha256"]
    initial=scope/"initial_request"
    challenge=scope/"challenge_request"
    require(initial.is_dir() and not initial.is_symlink()
            and (initial/"model_response_untrusted.txt").is_file()
            and not (initial/"model_response_untrusted.txt").is_symlink(),
            "Source-verified independent first reviewer required")
    first=run_one(folder=folder,queue_root=queue_root,slide=slide,
                  utterance_id=utterance_id,health_result=health_result,
                  family=family)["model_result"]
    unit=item["job"]["slides"][0]["utterances"][0]
    require(first.get("mode")=="INITIAL_REVIEW"
            and _actual_model_rows(
                first,_independently_check_saved_pass(
                    folder=folder,job=item["job"],
                    record=first,mode="INITIAL_REVIEW"))==1,
            "One actual initial AI reviewer verdict missing")

    text=review_instructions(item["job"],mode="INDEPENDENT_CHALLENGE")
    initial_text=review_instructions(item["job"],mode="INITIAL_REVIEW")
    require(text!=initial_text and hashlib.sha256(text.encode()).hexdigest()
            !=item["new_prompt_sha256"],
            "The second reviewer cannot reuse the first prompt")
    source_hashes={
        "source.pdf":item["job"]["source_sha256"],
        "slides.pdf":item["job"]["slides_sha256"],
        "script.txt":item["job"]["script_sha256"]}
    digest=fingerprint(request_text=text,source_hashes=source_hashes,
                       review_mode="INDEPENDENT_CHALLENGE")
    if challenge.exists():
        require(challenge.is_dir() and not challenge.is_symlink(),
                "Unexpected second-pass claim type")
        state=_load(challenge)
        require(state.get("request_fingerprint")==digest,
                "Second reviewer request differs from original claim")
        if (state["status"] in ("SUBMITTED_OR_UNCERTAIN",
                                "NO_RESPONSE_UNRESOLVED")
                and (challenge/"model_response_identity.json").is_file()):
            recover_claimed_observation(
                checkpoint=challenge,expected_fingerprint=digest)
            state=_load(challenge)
        require(state["status"] in (
            "MODEL_REPLY_OBSERVED_UNVALIDATED",
            "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"),
            "Uncertain independent challenge has no saved model reply; NO REPLAY")
        second=validate_saved(
            checkpoint=challenge,expected_fingerprint=digest,
            validator=lambda raw:validate_source_demoted_review(
                folder=folder,job=item["job"],
                response=decode_storyboard_response(raw),
                mode="INDEPENDENT_CHALLENGE"),
            required_model_family="neon")
    else:
        old=queue_root/f"slide_{slide:03d}_initial_review_attempt_01_request"
        _health_ok(health_result=health_result,queue_root=queue_root,
                   source_sha=item["source_sha256"],
                   old_claim=old/"dispatch_attempted.claim",family=family)
        old_mode=os.environ.get("MICROGEN_GEMINI_UI_MODE")
        old_thinking=os.environ.get("MICROGEN_GEMINI_THINKING_LEVEL")
        try:
            os.environ["MICROGEN_GEMINI_UI_MODE"]="pro"
            os.environ["MICROGEN_GEMINI_THINKING_LEVEL"]="high"
            second=run_web_review(
                folder=folder,job=item["job"],mode="INDEPENDENT_CHALLENGE",
                checkpoint_dir=challenge,chrome_port=9222,wait_cap_s=240,
                required_model_family="neon")
        finally:
            for name,value in (("MICROGEN_GEMINI_UI_MODE",old_mode),
                               ("MICROGEN_GEMINI_THINKING_LEVEL",old_thinking)):
                if value is None:os.environ.pop(name,None)
                else:os.environ[name]=value

    a=_independently_check_saved_pass(
        folder=folder,job=item["job"],record=first,mode="INITIAL_REVIEW")
    b=_independently_check_saved_pass(
        folder=folder,job=item["job"],record=second,mode="INDEPENDENT_CHALLENGE")
    require(_actual_model_rows(first,a)==_actual_model_rows(second,b)==1,
            "Only actually reviewed original source units count")
    x,y=a[0],b[0]
    require(x["utterance_id"]==y["utterance_id"]==unit["id"]
            and x["spoken_sha256"]==y["spoken_sha256"]==unit["spoken_sha256"],
            "Second reviewer changed original narration identity")
    agreeing=bool(
        x["verdict"]==y["verdict"]=="SUPPORTED"
        and x["target_id"]==y["target_id"] is not None
        and x["source_page"]==y["source_page"]
        and x["exact_textbook_quote_verified"] is True
        and y["exact_textbook_quote_verified"] is True
        and _canonical_academic_rationale(x["math_explanation"])
            !=_canonical_academic_rationale(y["math_explanation"]))
    # Hash exact original raw responses. These exist only for truly submitted
    # and source-validated separate owned Gemini browser conversations.
    first_raw=initial/"model_response_untrusted.txt"
    second_raw=challenge/"model_response_untrusted.txt"
    require(first_raw.is_file() and second_raw.is_file()
            and not first_raw.is_symlink() and not second_raw.is_symlink(),
            "Missing independent original model reply bytes")
    first_sha,second_sha=_sha(first_raw),_sha(second_raw)
    require(first_sha!=second_sha,
            "Identical raw model texts cannot prove independent reasoning")
    report={
        "schema_version":1,
        "status":(
            "FOCUSED_TWO_PASS_SOURCE_AI_AGREEMENT_UNAPPROVED" if agreeing else
            "FOCUSED_TWO_PASS_DISPUTED_NO_PROMOTION"),
        "source_sha256":item["source_sha256"],
        "scope_sha256":item["scope_sha256"],
        "original_historical_claim_sha256":item["original_claim_sha256"],
        "utterance_id":unit["id"],
        "spoken_sha256":unit["spoken_sha256"],
        "first_response_sha256":first_sha,
        "challenge_response_sha256":second_sha,
        "two_distinct_review_modes":True,
        "two_actual_model_review_passes":True,
        "source_quote_physically_witnessed_in_both":bool(
            x["exact_textbook_quote_verified"]
            and y["exact_textbook_quote_verified"]),
        "source_math_AI_agreed":agreeing,
        "original_g2_segments_promoted":0,
        "independent_acoustic_QA_complete":False,
        "human_academic_approval":False,
        "student_publication_authorized":False,
        "new_model_requests_during_reconciliation":0,
    }
    saved=scope/"two_pass_evidence.json"
    if saved.exists():
        require(saved.is_file() and not saved.is_symlink()
                and json.loads(saved.read_text("utf8"))==report,
                "Changed previous source-verified two-pass evidence")
    else:
        with saved.open("x",encoding="utf8") as writer:
            json.dump(report,writer,sort_keys=True,indent=2)
            writer.write("\n");writer.flush();os.fsync(writer.fileno())
    return report
