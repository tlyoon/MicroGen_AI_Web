"""Exhaustive source-bound highlight event QA + evidence-required audio repair worklist.

A whole-slide recorded WAV and acoustic pauses cannot prove which math
element was spoken at each pause. Verify every actual encoded event but keep
speech-to-element acceptance FALSE without independent element-WAV evidence.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import tempfile
from pathlib import Path

from .figure_source_identity import require, _sha, FigureIdentityReviewRequired
from .original_wav_element_cues import propose_wav_pdf_element_highlights
from .original_highlight_pilot_encode import _encoded_sample_pixels
from .original_multipart_review_encode import _original_element_fallback
from .original_highlight_pilot_encode import _reference_frames
from .independent_multipart_recovery_audit import (
    independent_reaudit_multipart, _read_exact_json,
)
from .highlight_video_preview import ffmpeg_path
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .element_plan_autodraft import propose as propose_source_bound_narration

_FILE = re.compile(r"file '([^\r\n']+)'\Z")
_DURATION = re.compile(r"duration (\d+(?:\.\d{1,9})?)\Z")
_FRAME = re.compile(r"slide_(\d{2,3})[/\\]highlight_(\d{3})\.png\Z")


def parse_original_review_timeline(concat:Path, frames_dir:Path) -> list[dict]:
    """Reject absolute file substitution or altered displayed event order."""
    require(concat.is_file() and not concat.is_symlink()
            and frames_dir.is_dir() and not frames_dir.is_symlink()
            and concat.stat().st_size <= 250_000,
            "Missing, linked or oversized encoded video event list")
    rows=concat.read_text(encoding="utf-8-sig").splitlines()
    require(len(rows)>=4 and rows[0]=="ffconcat version 1.0"
            and len(rows)%2==0 and len(rows)<=1502,
            "Invalid original FFconcat event format")
    records=[]
    elapsed=0.0
    for i in range(1,len(rows)-1,2):
        file_match=_FILE.fullmatch(rows[i])
        time_match=_DURATION.fullmatch(rows[i+1])
        require(file_match is not None and time_match is not None,
                "Invalid paired source-image and duration entry")
        original=Path(file_match.group(1))
        require(original.is_absolute() and original.is_file()
                and not original.is_symlink(),
                "Source event image must exist unchanged")
        frame=original.resolve()
        root=frames_dir.resolve()
        require(frame.is_relative_to(root),"Foreign replacement reference frame")
        relative=frame.relative_to(root).as_posix()
        match=_FRAME.fullmatch(relative)
        require(match is not None,"Non-source-bound slide/element filename")
        slide,event=map(int,match.groups())
        duration=float(time_match.group(1))
        require(math.isfinite(duration) and .001<=duration<=540,
                "Invalid recorded original event duration")
        if records:
            previous=records[-1]
            require(slide>=previous["slide_index"] and
                    (slide>previous["slide_index"] or
                     event==previous["element_index"]+1),
                    "Duplicated/misordered original visual target")
            if slide>previous["slide_index"]:
                require(slide==previous["slide_index"]+1 and event==1,
                        "Missing source slide or first element")
        else:
            require(event==1,"First image event does not name element 1")
        records.append({
            "slide_index":slide,"element_index":event,
            "file":str(frame),"start_s":elapsed,
            "end_s":elapsed+duration,"duration_s":duration,
        })
        elapsed+=duration
    require(bool(records), "No source-bound original encoded frame events")
    # concat reuses the final image as a hold frame; it must be exact.
    last=_FILE.fullmatch(rows[-1])
    require(last is not None and
            Path(last.group(1)).resolve()==Path(records[-1]["file"]),
            "Final encoded frame does not repeat last original highlight")
    require(len(records)<=750,"Too many elements to re-audit safely")
    return records


def verify_full_staged_element_coverage(*,original:Path,staged:Path,
                                        check_all_pixels:bool=True) ->dict:
    """Recompute source cues + re-decode every original visual highlight.

    Returns an actionable repair list, not a student's video approval.
    If a narration WAV is only available per slide, source content of each
    smaller audio interval remains unknown and technical speech acceptance
    MUST remain blocked.
    """
    original,staged=Path(original).absolute(),Path(staged).absolute()
    verify=independent_reaudit_multipart(folder=original,staged=staged)
    require(verify["source_pcm_sample_equality_verified"] is True
            and verify["student_publication_authorized"] is False,
            "Independent media/PCM audit required first")
    plan=inspect_original_slide_wav_plan(original)
    exe=ffmpeg_path() if check_all_pixels else None
    data=[]
    pixel_count=0
    all_event_count=0
    for part in plan["proposed_parts"]:
        part_id=part["part_id"]
        part_dir=staged/part_id
        receipt=_read_exact_json(part_dir/"review_receipt.json")
        require(receipt["part_id"]==part_id and
                receipt["encoded_mp4_sha256"]==_sha(part_dir/(part_id+"_review.mp4"))
                and receipt["student_publication_authorized"] is False,
                "Stale or forged per-part encoded element record")
        events=parse_original_review_timeline(
            part_dir/"frames.ffconcat",part_dir/"reference_frames")
        require(len(events)==receipt["highlight_event_count"]
                and events[0]["slide_index"]==part["slide_start"]
                and events[-1]["slide_index"]==part["slide_end"],
                "Incomplete or added original slide/element events")
        all_event_count+=len(events)
        evidence_by_slide={}
        for slide in range(part["slide_start"],part["slide_end"]+1):
            source_wav=original/f"slide{slide}.wav"
            evidence=[entry for entry in plan["wav_evidence"]
                      if entry["slide_index"]==slide]
            require(len(evidence)==1 and _sha(source_wav)==evidence[0]["sha256"],
                    "Original PCM WAV replaced during media audit")
            fallback=False
            try:
                cues=propose_wav_pdf_element_highlights(
                    slides=original/"slides.pdf",wav=source_wav,
                    slide_index=slide)
                expected=cues["events"]
            except FigureIdentityReviewRequired:
                # A missing acoustic pause cannot establish speech alignment.
                fallback=True
                expected=_original_element_fallback(
                    original/"slides.pdf",source_wav,slide,
                    evidence[0]["duration_s"])
            subset=[x for x in events if x["slide_index"]==slide]
            require(len(subset)==len(expected),"Displayed event count contradicts original WAV")
            for i,(record,guide) in enumerate(zip(subset,expected),1):
                require(record["element_index"]==i
                        and abs(record["duration_s"]-(
                            guide["end_s"]-guide["start_s"]))<.03,
                        "Displayed event time is not bound to original WAV sample")
            if check_all_pixels:
                # Independent reconstruction from the original slides.pdf:
                # staged reference PNGs are NOT acceptable proof by themselves.
                with tempfile.TemporaryDirectory(
                        prefix="microgen_source_ref_check_") as temporary:
                    regenerated=_reference_frames(
                        original/"slides.pdf",slide,expected,Path(temporary))
                    require(len(regenerated)==len(subset),
                            "Cannot regenerate all original source geometry")
                    for file,observed in zip(regenerated,subset):
                        require(_sha(file)==_sha(Path(observed["file"])),
                                "Staged highlight reference differs from original PDF")
            evidence_by_slide[slide]={
                "source_wav_sha256":evidence[0]["sha256"],
                "candidate_event_count":len(subset),
                "fallback_highlight_used":fallback,
                "speech_semantic_alignment_verified":False,
                "separately_recorded_element_wav_evidence_found":False,
                "required_next_action":(
                    "SOURCE_BOUND_PER_ELEMENT_NARRATION_REGENERATION_REQUIRED"
                    if len(subset)>1 or fallback
                    else "VERIFY_SINGLE_ELEMENT_NARRATION_SOURCE_CORRESPONDENCE"),
            }
        boundary=events[-1]["end_s"]
        require(abs(boundary-part["original_wav_duration_sum_s"])<.2,
                "Original WAV and displayed full-part timeline disagree")
        for record in events:
            if check_all_pixels:
                at=(record["start_s"]+record["end_s"])/2
                diff=_encoded_sample_pixels(
                    exe,part_dir/(part_id+"_review.mp4"),
                    Path(record["file"]),at)
                require(diff<16,
                        "Original encoded event failed independent decoded pixel check")
                pixel_count+=1
        data.append({
            "part_id":part_id,"slide_start":part["slide_start"],
            "slide_end":part["slide_end"],
            "all_displayed_candidate_events_rebound_to_source_wav_samples":True,
            "all_encoded_event_pixels_rechecked":bool(check_all_pixels),
            "all_reference_images_regenerated_from_original_slides_pdf":
                bool(check_all_pixels),
            "event_count":len(events),
            "slide_repair_worklist":[{"slide_index":slide,**row}
                                     for slide,row in sorted(evidence_by_slide.items())],
            "speech_to_highlight_semantics_verified":False,
        })
    require(all_event_count>=plan["original_wav_count"],
            "Missing original visual coverage")
    return {
        "schema_version":1,
        "status":"ALL_ENCODED_EVENTS_INDEPENDENTLY_VERIFIED_SPOKEN_SEMANTICS_UNPROVEN"
                 if check_all_pixels else "SOURCE_AUDIO_EVENT_TIMING_REVIEW_ONLY",
        "verified_part_count":len(data),"verified_original_slide_count":plan["original_wav_count"],
        "source_sha256":plan["source_sha256"],
        "slides_sha256":plan["slides_sha256"],
        "total_provisional_highlight_events":all_event_count,
        "all_events_encoded_pixel_recheck_count":pixel_count,
        "parts":data,
        "per_element_tts_or_manual_speech_alignment_needed":True,
        "audio_to_element_semantic_correspondence_verified":False,
        "technical_production_approved":False,
        "human_academic_listening_review_verified":False,
        "student_publication_authorized":False,
    }



def summarize_source_bound_tts_repair(*,media:dict,draft:dict)->dict:
    """Immutable repair worklist, never a machine-approved TTS request."""
    require(type(media) is dict and
            media.get("student_publication_authorized") is False and
            type(draft) is dict and
            draft.get("status")=="REVIEW_REQUIRED_NOT_TTS_READY" and
            draft.get("can_stage_or_synthesize_audio") is False and
            draft.get("source_sha256")==media.get("source_sha256") and
            draft.get("slides_sha256")==media.get("slides_sha256") and
            draft.get("slide_count")==media.get("verified_original_slide_count"),
            "Original storyboard draft does not match actual source/media")
    source=media["parts"]
    originals={x["slide_index"]:x for p in source
               for x in p["slide_repair_worklist"]}
    require(len(originals)==draft["slide_count"] and
            set(originals)==set(range(1,draft["slide_count"]+1)),
            "Incomplete original WAV alignment worklist")
    rows=[]
    for slide in draft["slides"]:
        number=slide["slide_number"]
        source_row=originals[number]
        utterances=slide["proposed_utterances"]
        require(len(utterances)>=1 and
                all(x["spoken_word_fidelity_verified"] is False and
                    x["approved_for_tts"] is False for x in utterances),
                "Auto-suggested utterance silently approved")
        ambiguities=sum(x["mapping_ambiguous"] for x in utterances)
        rows.append({
            "slide_index":number,
            "exact_verbatim_narration_utterances":len(utterances),
            "ambiguous_visual_element_utterances":ambiguities,
            "source_pdf_visual_candidate_count":len(slide["auto_candidate_targets"]),
            "figure_panel_source_semantics_review_required":
                slide["figure_panel_review_required"],
            "original_wav_sha256":source_row["source_wav_sha256"],
            "provisional_video_event_count":source_row["candidate_event_count"],
            "independent_per_element_tts_audio_available":False,
            "requires_new_source_bound_segmented_tts":
                source_row["required_next_action"]==
                "SOURCE_BOUND_PER_ELEMENT_NARRATION_REGENERATION_REQUIRED",
            "repair_priority":(
                "P0_SOURCE_MATH_AND_SPEECH_VISUAL_TARGET_REVIEW"
                if ambiguities or slide["figure_panel_review_required"]
                else "P1_VERIFY_TARGET_AND_REGENERATE_PER_ELEMENT_VOICE"),
            "approved_for_tts":False,
            "approved_for_student_publication":False,
        })
    require(sum(x["ambiguous_visual_element_utterances"] for x in rows)
            ==draft["ambiguous_utterance_count"],
            "Narration/visual mapping ambiguity inventory changed")
    return {
        "schema_version":1,
        "status":"ORIGINAL_AUDIO_SEGMENT_REGENERATION_SOURCE_MAPPING_REVIEW_REQUIRED",
        "source_sha256":media["source_sha256"],
        "slides_sha256":media["slides_sha256"],
        "original_script_sha256":draft["script_sha256"],
        "lecture_slide_count":len(rows),
        "total_original_utterances":draft["utterance_count"],
        "source_visual_target_candidates":draft["candidate_target_count"],
        "unresolved_utterance_visual_target_mappings":
            draft["ambiguous_utterance_count"],
        "slides_needing_new_source_bound_element_wavs":
            sum(x["requires_new_source_bound_segmented_tts"] for x in rows),
        "slides":rows,
        "voice_rule":"One consistent voice throughout all regenerated parts",
        "default_primary_tts":"Gemini Flash-Lite TTS/Kore",
        "approved_cloud_tts_fallback_rule":
            "Same voice only after 3 genuine primary TTS failures",
        "unreviewed_auto_tts_execution_authorized":False,
        "original_slide_wav_cutting_authorized":False,
        "same_voice_element_wav_generation_complete":False,
        "independent_audio_word_semantics_verified":False,
        "encoded_spoken_element_highlight_sync_verified":False,
        "academic_figure_review_complete":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--staged",type=Path,required=True)
    p.add_argument("--skip-all-pixel-recheck",action="store_true")
    p.add_argument("--script",type=Path,help="Original read-only narration script for source-bound repair worklist")
    a=p.parse_args(argv)
    report=verify_full_staged_element_coverage(
        original=a.folder,staged=a.staged,
        check_all_pixels=not a.skip_all_pixel_recheck)
    if a.script is not None:
        script=Path(a.script).absolute()
        require(script.is_file() and not script.is_symlink()
                and script.parent==Path(a.folder).absolute(),
                "Use the original source-adjacent narration script")
        draft=propose_source_bound_narration(
            source_pdf=Path(a.folder)/"source.pdf",
            slides_pdf=Path(a.folder)/"slides.pdf",
            script_txt=script)
        report["original_element_tts_repair_worklist"]=summarize_source_bound_tts_repair(
            media=report,draft=draft)
    print(json.dumps(report,indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
