"""Evidence-required original Slide4 audio readiness: no WAV inference or sends.

The historical whole-slide WAV can support technical muxing but never supply
individually verified utterance timing or acoustically proved Kore voice.
Every original utterance remains in the denominator; candidate rectangles are
not approved mathematical targets. No original audio folders are listed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .ai_academic_web_review import build_review_job
from .ai_academic_review_consensus import reconcile_actual_review_queue
from .figure_source_identity import _sha, require
from .original_slide4_figure_highlight_candidates import (
    inspect_original_slide4_highlight_candidates,
)
from .original_slide4_five_visual_candidates import (
    inspect_original_slide4_five_visual_candidates,
)


def summarize_slide4_audio_gate(*,job:dict,candidates:dict,
                                independently_reconciled:dict,
                                per_utterance_deliveries:list|None=None,
                                complete_visual_review:dict|None=None)->dict:
    require(job.get("status")=="SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED"
            and job.get("utterance_count")==5
            and len(job.get("slides",[]))==1
            and job["slides"][0]["slide"]==4
            and candidates.get("status")=="ORIGINAL_SLIDE4_THREE_RASTER_REGION_CANDIDATES_REVIEW_ONLY"
            and candidates.get("original_utterance_count")==5
            and candidates.get("proposed_figure_region_utterance_count")==3
            and candidates.get("unmapped_original_utterance_count")==2
            and candidates.get("original_source_sha256")==job.get("source_sha256")
            and candidates.get("original_slides_sha256")==job.get("slides_sha256")
            and candidates.get("original_script_sha256")==job.get("script_sha256"),
            "Actual original Slide4 candidate/source proof required")
    original=job["slides"][0]["utterances"]
    mapped=candidates.get("utterance_candidates")
    require(type(mapped) is list and len(mapped)==5
            and type(independently_reconciled) is dict
            and independently_reconciled.get("status")
                =="INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE"
            and independently_reconciled.get("student_publication_authorized") is False
            and type(independently_reconciled.get("accepted_ai_evidence")) is list
            and type(independently_reconciled.get("unresolved")) is list,
            "Independent original math queue and five speech candidates required")
    accepted=independently_reconciled["accepted_ai_evidence"]
    unresolved=independently_reconciled["unresolved"]
    total=independently_reconciled.get("original_utterances")
    require(type(total) is int and total>=5
            and independently_reconciled.get("agreed_source_witnessed_segments")==len(accepted)
            and independently_reconciled.get("pending_or_disputed")==len(unresolved)
            and total==len(accepted)+len(unresolved),
            "Source review count or denominator changed")
    present={u["id"] for u in original}
    require(len(present)==5 and all(
            type(u.get("spoken_sha256")) is str
            and re.fullmatch("[0-9a-f]{64}",u["spoken_sha256"])
            for u in original),
            "Exact original utterance ID and SHA coverage required")
    accepted_lookup={}
    for review in accepted:
        ident=review.get("utterance_id")
        require(type(ident) is str and ident not in accepted_lookup
                and type(review.get("original_spoken_sha256")) is str
                and re.fullmatch("[0-9a-f]{64}",review["original_spoken_sha256"])
                and review.get("author_human_attestation") is False,
                "Unverifiable or duplicate academic approval")
        accepted_lookup[ident]=review
    unresolved_ids=[x.get("utterance_id") for x in unresolved]
    require(len(set(unresolved_ids))==len(unresolved_ids)
            and not set(unresolved_ids).intersection(accepted_lookup)
            and present.issubset(set(unresolved_ids).union(accepted_lookup)),
            "Original review queue omitted or duplicated a Slide4 decision")
    # Any submitted receipt is untrusted until independent academic approval,
    # full visual target coverage and real provider WAV-byte checking.
    require(per_utterance_deliveries is None or
            (type(per_utterance_deliveries) is list
             and len(per_utterance_deliveries)<=5),
            "Provider deliveries must be explicitly presented for inspection")
    asserted=[] if per_utterance_deliveries is None else per_utterance_deliveries
    seen=set()
    for receipt in asserted:
        require(type(receipt) is dict
                and type(receipt.get("job_id")) is str
                and receipt["job_id"] in present and receipt["job_id"] not in seen,
                "Duplicate or foreign original element audio receipt")
        seen.add(receipt["job_id"])
    # A second source-bound layer may propose two additional ORIGINAL slide
    # text candidates. Such hints never establish exact speech timing or QA.
    expanded=None
    if complete_visual_review is not None:
        full=complete_visual_review
        require(type(full) is dict
                and full.get("status")
                    =="FIVE_ORIGINAL_SLIDE4_VISUAL_CANDIDATES_NOT_TIMED_OR_APPROVED"
                and all(full.get(f"{n}_sha256")==job.get(f"{n}_sha256")
                        for n in ("source","slides","script"))
                and full.get("utterance_candidate_count")==5
                and full.get("source_matched_figure_region_candidate_count")==3
                and full.get("original_slide_text_region_candidate_count")==2
                and full.get("unmapped_visual_candidate_count")==0
                and full.get("source_mathematical_review_approved") is False
                and full.get("narration_timing_verified") is False
                and full.get("highlighted_video_verified") is False
                and full.get("student_publication_authorized") is False,
                "Expanded visual candidate report cannot confer approvals")
        expanded=full.get("utterance_candidates")
        require(type(expanded) is list and len(expanded)==5,
                "Expanded report must preserve all five original utterances")
        for j,(unit,old,new) in enumerate(zip(original,mapped,expanded)):
            require(new.get("utterance_id")==unit["id"]
                    and new.get("original_spoken_sha256")==unit["spoken_sha256"]
                    and new.get("source_math_independently_agreed") is False
                    and new.get("actual_audio_start_s") is None
                    and new.get("actual_audio_end_s") is None
                    and new.get("speech_to_visual_sync_verified") is False
                    and new.get("actual_highlighted_video_frames_verified") is False
                    and type(new.get("review_target_id")) is str
                    and type(new.get("candidate_highlight_bbox_pdf_pt")) is list,
                    "Expanded original visual target lost identity or invented times")
            if j in (1,2,3):
                require(new["candidate_panel_id"]==old["candidate_panel_id"]
                        and new["candidate_highlight_bbox_pdf_pt"]
                            ==old["candidate_highlight_bbox_pdf_pt"]
                        and new.get("original_source_strip_sha256")
                            ==old.get("original_source_strip_sha256"),
                        "Previously source-matched triangle strip altered")
            else:
                require(new["candidate_panel_id"] is None
                        and new["candidate_kind"] in (
                            "VISIBLE_SLIDE_TEXT_REGION",
                            "MULTILINE_RADICAL_AND_ABSOLUTE_VALUE_TEXT_REGION"),
                        "Introduction/root explanation must target source text")
    rows=[]
    for index,(u,c) in enumerate(zip(original,mapped)):
        uid=u["id"]
        require(c.get("utterance_id")==uid
                and c.get("original_spoken_sha256")==u["spoken_sha256"]
                and c.get("speech_to_visual_sync_verified") is False
                and c.get("speaking_start_s") is None
                and c.get("speaking_end_s") is None,
                "Original utterance candidate has fabricated speech timing")
        approved=accepted_lookup.get(uid)
        if approved:
            require(approved["original_spoken_sha256"]==u["spoken_sha256"],
                    "Accepted academic review refers to other original narration")
        visual=(expanded[index].get("review_target_id") is not None
                if expanded is not None
                else c.get("candidate_panel_id") is not None)
        rows.append({
            "original_utterance_id":uid,
            "original_spoken_sha256":u["spoken_sha256"],
            "original_source_math_double_pass_agreed":bool(approved),
            "source_authenticated_visual_candidate_present":visual,
            "visual_candidate_kind":(expanded[index].get("candidate_kind")
                                     if expanded is not None
                                     else "SOURCE_MATCHED_TRIANGLE_RASTER_STRIP"
                                     if visual else None),
            "original_visual_target_academically_approved":False,
            "specific_provider_receipt_supplied_unverified":uid in seen,
            "real_element_WAV_bytes_validated":False,
            "individual_audio_duration_s":None,
            "claimed_voice_acoustically_verified":False,
            "spoken_content_fidelity_verified":False,
            "actual_speech_to_highlight_sync_verified":False,
            "action_required":(
                "SOURCE_MATH_DOUBLE_PASS_REVIEW" if not approved
                else "AUTHORITATIVE_VISUAL_TARGET_REVIEW" if not visual
                else "VALIDATED_PER_UTTERANCE_VOICE_AND_AUDIO_RECEIPT"
            ),
        })
    return {
        "status":"ORIGINAL_SLIDE4_AUDIO_BLOCKED_PENDING_REAL_ACCEPTANCE",
        "source_sha256":job["source_sha256"],
        "slides_sha256":job["slides_sha256"],
        "script_sha256":job["script_sha256"],
        "original_slide":4,
        "original_slide_utterances":5,
        "original_source_math_accepted_utterances":sum(
            r["original_source_math_double_pass_agreed"] for r in rows),
        "unreviewed_original_slide_utterances":sum(
            not r["original_source_math_double_pass_agreed"] for r in rows),
        "visual_candidate_utterances":sum(
            r["source_authenticated_visual_candidate_present"] for r in rows),
        "unmapped_visual_utterances":sum(
            not r["source_authenticated_visual_candidate_present"] for r in rows),
        "original_source_text_visual_candidates":(2 if expanded is not None else 0),
        "all_visual_candidates_only_not_media_approval":True,
        "provider_deliveries_presented_not_validated":len(asserted),
        "audited_original_element_WAV_count":0,
        "original_slide_level_archived_WAV_existence_here":"NOT_CHECKED",
        "original_utterance_rows":rows,
        "new_provider_calls":0,
        "model_or_voice_provenance_accepted":False,
        "permission_to_synthesize_or_publish":False,
        "real_speech_timing_evidence_accepted":False,
        "encoded_element_highlight_video_accepted":False,
        "student_publication_authorized":False,
    }


def inspect_original_slide4_audio_readiness(*,folder:Path,
                                            queue_root:Path)->dict:
    root=Path(folder).absolute()
    names=("source.pdf","slides.pdf","script.txt")
    hashes=tuple(_sha(root/name) for name in names)
    job=build_review_job(folder=root,slide_numbers=[4])
    candidates=inspect_original_slide4_highlight_candidates(folder=root)
    complete=inspect_original_slide4_five_visual_candidates(folder=root)
    consensus=reconcile_actual_review_queue(
        queue_root=Path(queue_root),folder=root)
    report=summarize_slide4_audio_gate(
        job=job,candidates=candidates,
        independently_reconciled=consensus,
        complete_visual_review=complete)
    require(tuple(_sha(root/name) for name in names)==hashes,
            "Protected original files changed during read-only audio eligibility")
    require((report["source_sha256"],report["slides_sha256"],
             report["script_sha256"])==hashes,
            "Original slide/math source identity drift")
    report["full_original_queue_total"]=consensus["original_utterances"]
    report["full_original_queue_two_pass_agreements"]=consensus[
        "agreed_source_witnessed_segments"]
    report["full_original_queue_pending_or_disputed"]=consensus[
        "pending_or_disputed"]
    return report


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    p.add_argument("--queue-root",required=True,type=Path)
    args=p.parse_args(argv)
    print(json.dumps(inspect_original_slide4_audio_readiness(
        folder=args.folder,queue_root=args.queue_root),indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
