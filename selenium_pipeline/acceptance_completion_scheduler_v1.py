"""Completion-driven, source-pinned G2/G3 forward scheduler.

Each *independent* workstream advances safely despite a blocked neighbor:
  G2: independently reconcile real AI-source evidence, stage missing original
      one-unit source inputs with existing ZERO-Send campaign only;
  G3 science: inspect original immutable finite campaign with ZERO new Sends,
      preserving all previously reserved/uncertain requests;
  G3 technical: reverify real pinned PCM/encoded slide pages offline.
Never create a new campaign ID or perform browser, TTS, paid API or publication
work. Only the existing autonomous science controllers may make model Sends,
after their own fresh-owned-health and fixed-budget authorization gates.
This scheduler reports *acceptance gates*, not superficial test totals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from .figure_source_identity import _sha,require
from .recovery_registry import lookup_mechanism

KIND="completion_driven_acceptance_scheduler"
SIGNATURE="G2_G3_INDEPENDENT_WORK_STRANDED_WHEN_ONE_ACCEPTANCE_GATE_BLOCKED"
MECHANISM="CONTINUE_ALL_ZERO_SEND_WORKSTREAMS_PIN_GATES_AND_HOLD_MODEL_BUDGET"
ROOT="ACCEPTANCE_COMPLETION_SCHEDULER_V1"
STATUS="COMPLETION_GATES_OPEN_SAFE_WORKSTREAMS_ADVANCED"
CAMPAIGN_NAME=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")
MAX_GATE_ACTIONS=3


def _canonical(data:dict)->bytes:
    return (json.dumps(data,sort_keys=True,ensure_ascii=False,
                       separators=(",",":"),allow_nan=False)+"\n").encode("utf8")


def _read(path:Path,limit:int=500_000)->dict:
    require(path.is_file() and not path.is_symlink()
            and 0<path.stat().st_size<=limit,
            "Original source-bound checkpoint unavailable")
    val=json.loads(path.read_text("utf8"))
    require(type(val) is dict,"Original checkpoint is not a JSON object")
    return val


def _journal_hashes(home:Path)->dict:
    """Pin original non-replayable journal. Never create a new campaign."""
    require(home.is_dir() and not home.is_symlink()
            and (home/"campaign.json").is_file()
            and not (home/"campaign.json").is_symlink(),
            "Only an EXISTING finite model-Send campaign may be inspected")
    files=[home/"campaign.json",*sorted(home.glob("event_*.json"))]
    require(len(files)<=100 and all(
        f.is_file() and not f.is_symlink() for f in files),
        "Original immutable Send event journal is unsafe")
    return {f.name:_sha(f) for f in files}


def _g2_zero_send(*,source:Path,queue:Path,campaign:str)->dict:
    from .autonomous_recovery_continuation_v1 import run_campaign
    result=run_campaign(
        folder=source,queue_root=queue,work_root=queue,
        campaign_id=campaign,max_possible_sends=0,
        execute=False,auto_health=False,
        stage_source_only=True,max_actions=24)
    require(result["max_possible_provider_sends"]==0
            and result["possible_provider_sends_reserved"]==0
            and result["new_paid_gemini_api_calls"]==0
            and result["original_historical_requests_replayed"] is False
            and result["student_publication_authorized"] is False
            and result["reconciled_source_AI_agreements"]<=85,
            "G2 source-only review may not claim a new model Send or release")
    # The source-only G2 controller has ALREADY revalidated the original
    # V1 saved independent model evidence under its exclusive owner lock.
    # A new ranked V3 scope counts only if BOTH independently attributable
    # model replies pass the same original source/math validators. Reuse the
    # verified V1 baseline rather than doing a duplicate 85-page review.
    source_agreed=result["reconciled_source_AI_agreements"]
    source_pending=result["pending_source_AI_review"]
    v3_new=0
    v3_receipt=None
    v1_receipt=result.get("V1_actual_two_pass_source_AI_receipt")
    if v1_receipt is not None:
        from .g2_ranked_v3_two_pass_consensus_bridge_v1 import (
            reconcile as reconcile_v3)
        v1_proven={
            "receipt":v1_receipt,
            "combined_source_AI_agreements":source_agreed,
            "new_focused_utterance_ids":result[
                "V1_actual_source_AI_utterance_ids"]}
        v3=reconcile_v3(
            folder=source,queue_root=queue,base_v1_receipt=Path(v1_receipt),
            v1_validator=lambda **_kw:v1_proven)
        require(v3["original_V1_two_pass_source_AI_agreements"]==source_agreed
                and v3["new_provider_requests"]==0
                and v3["paid_gemini_API_calls"]==0
                and v3["student_publication_authorized"] is False
                and v3["combined_source_AI_agreements"]>=source_agreed,
                "V3 model-source evidence must not alter old G2 acceptance")
        source_agreed=v3["combined_source_AI_agreements"]
        source_pending=v3["pending_or_disputed_source_AI"]
        v3_new=v3["new_V3_independent_source_AI_agreements"]
        v3_receipt=v3["receipt"]
    stages=result["stages"]
    return {
        "status":"G2_REAL_SOURCE_AGREEMENT_RECONCILED_NO_SEND",
        "original_total":(source_agreed+source_pending),
        "original_two_pass_AI_agreements":result["original_source_AI_agreements"],
        "total_two_pass_AI_agreements":source_agreed,
        "pending_or_disputed":source_pending,
        "new_V3_actual_independent_two_pass_agreements":v3_new,
        "V3_independent_two_pass_receipt":v3_receipt,
        "source_only_focused_tasks_rechecked":len(stages),
        "separate_ranked_v3_review_inputs_rechecked":sum(
            x.get("ranked_source_review_candidate",{}).get("new_browser_sends")==0
            for x in stages if x.get("ranked_source_review_candidate")),
        "existing_campaign_checkpoint":result["campaign_checkpoint"],
        "source_pdf_sha256":result["source_sha256"],
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "independent_academic_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "student_publication_authorized":False,
    }


def _g3_science_zero_send(*,manifest:Path,state:Path,campaign:str)->dict:
    from .g3_continuous_advance_v1 import advance
    value=advance(
        manifest=manifest,state_root=state,campaign_id=campaign,
        max_science_sends=0,max_tasks=4,max_health_probes=0,
        execute=False)
    require(value["max_science_browser_sends"]==0
            and value["health_probes_attempted_this_run"]==0
            and value["stages_advanced_this_run"]==0
            and value["paid_gemini_API_requests"]==0
            and value["original_historical_model_claims_replayed"] is False
            and value["source_scientific_approval_automatically_granted"] is False
            and value["student_publication_authorized"] is False,
            "G3 science inventory must never launch old or new model Sends")
    return {
        "status":value["status"],
        "original_immutable_campaign_send_cap":
            value["original_immutable_campaign_send_cap"],
        "original_possible_model_sends_reserved":
            value["science_browser_sends_reserved"],
        "remaining_source_science_tasks":value["remaining_eligible_tasks"],
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "independent_scientific_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "student_publication_authorized":False,
    }


def _g3_media_zero_send(*,manifest:Path,state:Path,media:Path)->dict:
    from .g3_original_video_page_parity_v1 import materialize
    result=materialize(manifest=manifest,media_root=media,state_root=state)
    require(result["original_slides_pixel_witnessed"]>0
            and result["all_original_visual_page_order_matched"] is True
            and result["source_scientific_QA_complete"] is False
            and result["independent_acoustic_QA_complete"] is False
            and result["independent_video_highlight_QA_complete"] is False
            and result["new_browser_sends"]==0
            and result["new_paid_gemini_API_calls"]==0
            and result["student_publication_authorized"] is False,
            "Video page match must not be called academic/video acceptance")
    # Use the ALREADY REGISTERED historical G3 pixel-based static-video
    # recovery rather than reimplementing a superficial visual detector.
    # Its actual encoded frame/wav/part/source probes distinguish original
    # static legacy exports from a usable element-highlight video. A found
    # defect automatically receives an isolated, immutable source-bound
    # rebuild worklist, without overwriting any legacy MP4 or granting QA.
    from .g3_multisection_autoforward_v71 import _verified_specs
    from .g3_source_media_technical_preflight_v1 import SECTION
    from .g3_legacy_visual_recovery_v71 import (
        inspect_legacy,stage_recovery)
    _,specs=_verified_specs(manifest)
    state=Path(state).absolute()
    media=Path(media).absolute()
    staging=state/"g3_legacy_static_auto_rebuild_worklists_v1"
    require(not staging.is_symlink() and not staging.is_relative_to(media),
            "G3 original source/encoding and repair worklists must be isolated")
    staging.mkdir(exist_ok=True)
    sections=[]
    for spec in specs:
        section=spec["section"]
        require(section in SECTION,
                "No original source-bound G3 media mapping for visual repair")
        try:
            diagnosis=inspect_legacy(folder=media/SECTION[section])
            require(all(diagnosis["original_sha256"][name]==
                        spec["identity"]["source_inputs_sha256"][name]
                        for name in ("source.pdf","slides.pdf","script.txt"))
                    and diagnosis["student_publication_authorized"] is False
                    and diagnosis["model_requests"]==0
                    and diagnosis["paid_api_requests"]==0,
                    "Static-video pixel diagnosis is not original source pinned")
            row={
                "section":section,"status":diagnosis["status"],
                "original_slide_count":diagnosis["original_slide_count"],
                "moving_slides":diagnosis["moving_slides"],
                "encoded_frames_sampled":diagnosis["sampled_encoded_frames"],
                "original_MP4_SHA":diagnosis["original_full_video_sha256"],
                "isolation_rebuild_worklist":None,
                "independent_within_slide_highlight_QA":False,
                "student_publication_authorized":False}
            if diagnosis["status"]=="G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED":
                path=stage_recovery(report=diagnosis,staging_root=staging)
                row["isolation_rebuild_worklist"]=str(path)
                row["isolation_rebuild_worklist_sha256"]=_sha(path)
                # Continue automatically to the NEXT eligible source-only
                # repair: publisher/narration PDF element draft plus mandatory
                # ambiguity review, never new TTS or encoded media. A partial
                # failure in one subsection does not strand the other one.
                try:
                    from .g3_source_element_review_draft_v1 import (
                        materialize as source_elements)
                    row["element_mapping_source_review"]=source_elements(
                        source_folder=media/SECTION[section],
                        state_root=state,section=section,
                        original_source_hashes=spec["identity"][
                            "source_inputs_sha256"])
                    # Do not stop at an unapproved worklist: reuse the
                    # historical physically witnessed publisher context
                    # retriever for up to two *new* ambiguous original units.
                    # No new model Send, no guessed figure semantics, no TTS.
                    try:
                        from .g3_element_publisher_quote_autoforward_v1 import (
                            advance as source_quotes)
                        packet=row["element_mapping_source_review"]
                        row["publisher_quote_mapping_recovery"]=source_quotes(
                            source_folder=media/SECTION[section],
                            state_root=state,section=section,
                            draft_receipt=Path(packet["draft_receipt"]),
                            source_hashes=spec["identity"][
                                "source_inputs_sha256"])
                        initial=row["publisher_quote_mapping_recovery"]
                        remaining=initial.get("remaining_unprocessed_ambiguous_tasks")
                        if (type(remaining) is int and remaining>0
                                and initial.get("new_source_quote_tasks_staged",0)>0):
                            from .g3_source_quote_bounded_continuation_v1 import (
                                continue_quotes)
                            row["publisher_quote_batch_continuation"]=continue_quotes(
                                source_folder=media/SECTION[section],
                                state_root=state,section=section,
                                draft_receipt=Path(packet["draft_receipt"]),
                                source_hashes=spec["identity"]["source_inputs_sha256"],
                                expected_remaining=remaining)

                    except Exception as error:
                        row["publisher_quote_mapping_recovery"]={
                            "status":"G3_PUBLISHER_QUOTE_SOURCE_REVIEW_HELD",
                            "error_class":type(error).__name__,
                            "error_detail":str(error)[:200],
                            "source_scientific_QA_complete":False,
                            "per_element_TTS_ready":False,
                            "student_publication_authorized":False,
                            "new_browser_sends":0,
                            "new_paid_gemini_API_calls":0}
                except Exception as error:
                    row["element_mapping_source_review"]={
                        "status":"G3_SOURCE_ELEMENT_MAPPING_DRAFT_HELD",
                        "error_class":type(error).__name__,
                        "error_detail":str(error)[:200],
                        "per_element_TTS_ready":False,
                        "independent_within_slide_highlight_QA_complete":False,
                        "student_publication_authorized":False}
            else:
                require(diagnosis["status"]==
                        "G3_MOTION_OBSERVED_HIGHLIGHT_STILL_UNATTESTED",
                        "Unknown encoded video visual state")
            sections.append(row)
        except Exception as exc:
            # A source-specific missing legacy manifest is NOT permission
            # to suppress QA, nor to strand the other original subsection.
            sections.append({
                "section":section,"status":"G3_STATIC_REBUILD_SOURCE_HELD",
                "error_class":type(exc).__name__,
                "error_detail":str(exc)[:200],
                "independent_within_slide_highlight_QA":False,
                "student_publication_authorized":False})
    require(len(sections)==len(specs),
            "Every original G3 section needs its own visual disposition")
    return {
        "status":"G3_SOURCE_PINNED_TECHNICAL_MEDIA_REVERIFIED_NO_RELEASE",
        "original_subsections_checked":len(result["sections"]),
        "source_bound_actual_highlight_recovery":sections,
        "original_static_video_rebuilds_staged":sum(
            row["status"]=="G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED"
            for row in sections),
        "source_only_element_mapping_drafts_staged":sum(
            row.get("element_mapping_source_review",{}).get("status")==
                "G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS"
            for row in sections),
        "new_physically_source_witnessed_mapping_tasks_staged":sum(
            row.get("publisher_quote_mapping_recovery",{}).get(
                "new_source_quote_tasks_staged",0)
            + row.get("publisher_quote_batch_continuation",{}).get(
                "new_source_quote_tasks_staged",0) for row in sections),
        "source_only_physical_quote_candidates_staged":sum(
            row.get("publisher_quote_mapping_recovery",{}).get(
                "new_physically_witnessed_publisher_quotes",0)
            + row.get("publisher_quote_batch_continuation",{}).get(
                "new_physically_witnessed_publisher_quotes",0)
            for row in sections),
        "independent_video_highlight_QA_complete":False,
        "source_video_pages_pixel_witnessed":
            result["original_slides_pixel_witnessed"],
        "source_video_page_receipt_sha256":[
            _sha(Path(x["receipt"])) for x in result["sections"]],
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "independent_scientific_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "student_publication_authorized":False,
    }


def _gate_matrix(results:dict)->list[dict]:
    g2=results.get("G2_SOURCE")
    g3=results.get("G3_SCIENCE")
    media=results.get("G3_MEDIA")
    static_rebuild_count=(media or {}).get(
        "original_static_video_rebuilds_staged",0)
    agreed=g2.get("total_two_pass_AI_agreements",0) if g2 else 0
    total=g2.get("original_total") if g2 else None
    source_ai_done=bool(g2 is not None and type(total) is int
                        and total>0 and agreed==total)
    cap=(g3 or {}).get("original_immutable_campaign_send_cap")
    spent=(g3 or {}).get("original_possible_model_sends_reserved")
    exhausted=(type(cap) is int and type(spent) is int and spent>=cap)
    rows=[
        {"gate_id":"G2_INDEPENDENT_SOURCE_AI",
         "accepted_units":agreed if g2 else None,
         "required_units":total,"accepted":source_ai_done,
         "status":"TWO_PASS_SOURCE_AI_EVIDENCE_COMPLETE"
             if source_ai_done else "PENDING_INDEPENDENT_MODEL_REVIEW"
             if g2 else "BLOCKED_G2_EVIDENCE_READ",
         "next_action":"Recover genuine owned Selenium Neon/High health and "+
             "review ONLY distinct source-locked eligible scopes within an "+
             "independently authorized original immutable Send budget"},
        {"gate_id":"G2_INDEPENDENT_ACOUSTIC_QA","accepted":False,
         "status":"PENDING_INDEPENDENT_ACOUSTIC_EVIDENCE",
         "next_action":"Independently compare genuine WAV narration with "+
             "accepted original textbook-based scripts; do not promote PCM QA"},
        {"gate_id":"G3_INDEPENDENT_SCIENCE",
         "remaining_source_science_tasks":(
             g3.get("remaining_source_science_tasks") if g3 else None),
         "accepted":False,
         "status":("BLOCKED_EXHAUSTED_ORIGINAL_MODEL_SEND_CAP"
                   if exhausted else "PENDING_G3_INDEPENDENT_MODEL_SCIENCE"
                   if g3 else "BLOCKED_G3_SCIENCE_EVIDENCE_READ"),
         "next_action":"Honor original possible-Send claims; require "+
             "fresh owned post-incident health and genuinely authorized "+
             "eligible distinct science-review inputs; never reset caps"},
        {"gate_id":"G3_INDEPENDENT_ACOUSTIC_QA","accepted":False,
         "status":"PENDING_INDEPENDENT_SPOKEN_CONTENT_EVIDENCE",
         "next_action":"Independently verify real WAV spoken content and "+
             "substantive pronunciation, not energy/clipping alone"},
        {"gate_id":"G3_ORIGINAL_VIDEO_PAGE_TECHNICAL",
         "accepted":bool(media),
         "status":"TECHNICAL_PASS_NOT_VIDEO_QA" if media else
             "BLOCKED_OR_UNVERIFIED_TECHNICAL_EVIDENCE",
         "source_video_pages_pixel_witnessed":(
             media.get("source_video_pages_pixel_witnessed") if media else None),
         "next_action":"Retain original encoded-frame SHA and PDF page proof"},
        {"gate_id":"G3_WITHIN_SLIDE_VISUAL_HIGHLIGHT_QA","accepted":False,
         "status":("BLOCKED_SOURCE_PINNED_STATIC_VIDEO_REBUILD_REQUIRED"
                   if static_rebuild_count else
                   "PENDING_ACTUAL_HIGHLIGHT_AND_SPEECH_TIMING"),
         "source_pinned_rebuild_worklists":static_rebuild_count,
         "source_only_element_review_worklists":(media or {}).get(
             "source_only_element_mapping_drafts_staged",0),
         "new_publisher_quote_mapping_tasks":(media or {}).get(
             "new_physically_source_witnessed_mapping_tasks_staged",0),
         "next_action":(
             "Rebuild source-verified element-synchronized MP4 in isolated "+
             "staging, requiring genuine per-element source anchors and "+
             "narration timing; then obtain independent encoded video QA"
             if static_rebuild_count else
             "Independently witness physics element highlights in actual "+
             "encoded MP4 at genuine spoken timings")},
        {"gate_id":"G3_SECOND_SUBSECTION_ACCEPTANCE","accepted":False,
         "status":"BLOCKED_PENDING_SCIENCE_ACOUSTIC_HIGHLIGHT_ACCEPTANCE",
         "next_action":"Close source science, authentic acoustic and "+
             "encoded synchronized highlights for Serway 8.2 AND 8.3"},
        {"gate_id":"END_TO_END_PRODUCTION_RELEASE","accepted":False,
         "status":"BLOCKED_PENDING_G2_G3_MILESTONES",
         "next_action":"Regression and restart on additional original "+
             "chapter only after all independent G2/G3 acceptances"},
    ]
    return rows


def run(*,g2_source:Path,g2_queue:Path,g2_campaign:str,
        g3_manifest:Path,g3_state:Path,g3_campaign:str,
        g3_media:Path,report_root:Path,
        g2_runner=None,g3_science_runner=None,g3_media_runner=None)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Missing executable completion scheduler recovery")
    require(all(type(x) is str and CAMPAIGN_NAME.fullmatch(x)
                for x in (g2_campaign,g3_campaign)),
            "Use ONLY existing, exact named historical finite campaigns")
    g2_source,g2_queue,g3_manifest,g3_state,g3_media,report_root=[
        Path(v).absolute() for v in (
            g2_source,g2_queue,g3_manifest,g3_state,g3_media,report_root)]
    require(all(x.exists() and not x.is_symlink()
                for x in (g2_source,g2_queue,g3_manifest,g3_state,g3_media))
            and g2_source.is_dir() and g2_queue.is_dir()
            and g3_manifest.is_file() and g3_state.is_dir()
            and g3_media.is_dir()
            and not report_root.is_relative_to(g2_source)
            and not report_root.is_relative_to(g2_queue)
            and not report_root.is_relative_to(g3_state),
            "Separate original-source, journal and output roots required")
    original=_read(g2_queue/"queue.json")
    require(original["original_source_folder"]==str(g2_source)
            and original["expected_utterances"]>0,
            "Original G2 publisher source was not authoritative")
    original_g2_journal=g2_queue/"autonomous_recovery_continuation_v1"/g2_campaign
    original_g3_journal=g3_state/"g3_continuous_advance_v1"/g3_campaign
    before={
        "G2_original_queue_sha256":_sha(g2_queue/"queue.json"),
        "G2_original_campaign_journal":_journal_hashes(original_g2_journal),
        "G3_original_manifest_sha256":_sha(g3_manifest),
        "G3_original_campaign_journal":_journal_hashes(original_g3_journal),
    }
    # Existing preserved campaign identity is mandatory, including the old
    # 4/4 possibly-sent G3 journal. Never create a new journal to dodge limits.
    results={}
    errors={}
    actions=(
        ("G2_SOURCE",g2_runner or _g2_zero_send,dict(
            source=g2_source,queue=g2_queue,campaign=g2_campaign)),
        ("G3_SCIENCE",g3_science_runner or _g3_science_zero_send,dict(
            manifest=g3_manifest,state=g3_state,campaign=g3_campaign)),
        ("G3_MEDIA",g3_media_runner or _g3_media_zero_send,dict(
            manifest=g3_manifest,state=g3_state,media=g3_media)),
    )
    require(len(actions)==MAX_GATE_ACTIONS,
            "Unbounded completion actions are not permitted")
    for name,worker,arguments in actions:
        try:
            value=worker(**arguments)
            require(type(value) is dict
                    and value.get("new_browser_sends")==0
                    and value.get("new_paid_gemini_API_calls")==0
                    and value.get("student_publication_authorized") is False
                    and value.get("independent_academic_QA_complete",False) is False
                    and value.get("independent_scientific_QA_complete",False) is False,
                    "Source-only scheduler attempted paid/model Send or approval")
            if name=="G2_SOURCE":
                require(type(value.get("original_total")) is int
                        and value["original_total"]>0
                        and 0<=value["total_two_pass_AI_agreements"]<=
                            value["original_total"],
                        "Invalid original G2 independent review count")
            if name=="G3_SCIENCE":
                require(value.get("original_possible_model_sends_reserved",0)>=0,
                        "Invalid immutable G3 possible Send count")
            if name=="G3_MEDIA":
                require(value.get("independent_video_highlight_QA_complete") is False,
                        "Encoded page parity is not academic video QA")
            results[name]=value
        except Exception as exc:
            # Scope the failure to the affected workstream, never continue
            # inside a failed action or claim fake acceptance.
            errors[name]={"status":"BLOCKED_SPECIFIC_WORKSTREAM",
                          "error_class":type(exc).__name__,
                          "error_message":str(exc)[:200]}
            continue
    after={
        "G2_original_queue_sha256":_sha(g2_queue/"queue.json"),
        "G2_original_campaign_journal":_journal_hashes(original_g2_journal),
        "G3_original_manifest_sha256":_sha(g3_manifest),
        "G3_original_campaign_journal":_journal_hashes(original_g3_journal),
    }
    require(before==after,
            "Completion controller attempted to mutate original Send journals")
    matrix=_gate_matrix(results)
    require(not all(x["accepted"] for x in matrix),
            "Source-only readiness may not complete scientific milestones")
    summary={
        "status":STATUS,"schema_version":1,
        "source_identifiers_sha256":before,
        "original_G2_source_pdf_sha256":_sha(g2_source/"source.pdf"),
        "G2_original_campaign_id":g2_campaign,
        "G3_original_campaign_id":g3_campaign,
        "source_only_workstreams_completed":sorted(results),
        "independent_workstreams_held":errors,
        "actions":results,
        "acceptance_gates":matrix,
        "required_acceptance_gates":len(matrix),
        "academically_accepted_gates":sum(
            bool(row["accepted"]) and
            row["gate_id"]!="G3_ORIGINAL_VIDEO_PAGE_TECHNICAL"
            for row in matrix),
        "technical_only_gates_passed":sum(
            row["gate_id"]=="G3_ORIGINAL_VIDEO_PAGE_TECHNICAL"
            and row["accepted"] for row in matrix),
        "next_eligible_development_priority":
            "Restore authorized source-specific Selenium review health "+
            "and a genuine finite non-replay science budget, then close "+
            "G2/85 and G3 independent acceptance; other source-only "+
            "workstreams continue even when one source is blocked",
        "new_browser_sends":0,"paid_gemini_API_calls":0,
        "original_historical_requests_replayed":False,
        "all_G2_G3_requirements_accepted":False,
        "student_publication_authorized":False}
    require(not report_root.is_symlink(),
            "Completion report checkpoint cannot be a redirected link")
    report_root.mkdir(parents=True,exist_ok=True)
    scope=hashlib.sha256(_canonical(summary)).hexdigest()
    report={"scope_sha256":scope,**summary}
    file=report_root/(scope+".json")
    require(not file.is_symlink(),
            "Completion report cannot overwrite a linked checkpoint")
    content=_canonical(report)
    if file.exists():
        require(file.is_file() and file.read_bytes()==content,
                "Completion checkpoint altered since last certified run")
    else:
        with file.open("xb") as stream:
            stream.write(content);stream.flush();os.fsync(stream.fileno())
    return {"status":STATUS,"receipt":str(file),
            "scope_sha256":scope,
            "G2_source_AI_agreed":(results.get("G2_SOURCE") or {}).get(
                "total_two_pass_AI_agreements"),
            "G2_source_AI_required":(results.get("G2_SOURCE") or {}).get(
                "original_total"),
            "G3_historical_sends_reserved":(results.get("G3_SCIENCE") or {}).get(
                "original_possible_model_sends_reserved"),
            "G3_historical_send_cap":(results.get("G3_SCIENCE") or {}).get(
                "original_immutable_campaign_send_cap"),
            "G3_science_tasks_eligible":(results.get("G3_SCIENCE") or {}).get(
                "remaining_source_science_tasks"),
            "G3_original_video_pages_technical":(results.get("G3_MEDIA") or {}).get(
                "source_video_pages_pixel_witnessed"),
            "independent_workstreams_held":errors,
            "source_only_workstreams_completed":sorted(results),
            "academically_accepted_gates":summary[
                "academically_accepted_gates"],
            "new_browser_sends":0,"paid_gemini_API_calls":0,
            "all_G2_G3_requirements_accepted":False,
            "student_publication_authorized":False}


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--g2-source",required=True,type=Path)
    p.add_argument("--g2-queue",required=True,type=Path)
    p.add_argument("--g2-campaign",required=True)
    p.add_argument("--g3-manifest",required=True,type=Path)
    p.add_argument("--g3-state",required=True,type=Path)
    p.add_argument("--g3-campaign",required=True)
    p.add_argument("--g3-media",required=True,type=Path)
    p.add_argument("--report-root",required=True,type=Path)
    args=p.parse_args(argv)
    print(json.dumps(run(
        g2_source=args.g2_source,g2_queue=args.g2_queue,
        g2_campaign=args.g2_campaign,g3_manifest=args.g3_manifest,
        g3_state=args.g3_state,g3_campaign=args.g3_campaign,
        g3_media=args.g3_media,report_root=args.report_root),
        indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
