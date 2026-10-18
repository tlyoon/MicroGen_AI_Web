"""Generic, fail-closed element-highlighted multipart REVIEW video integration.

The standard runner may call this only with an explicit, source-bound author
plan and frozen separate WAVs. Never publishes over the original lecture or
creates a student/academic/production acceptance receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path

from .element_narration_stage import prepare, canonical, digest
from .series_review_preview import render_review_series
from .highlight_video_preview import ffmpeg_path, probe_mp4
from .encoded_highlight_pixels import verify_encoded_highlight_pixels

class HighlightReviewGateError(ValueError):
    """Required source-bound audio/visual proof is absent or invalid."""


def need(condition: bool, message: str) -> None:
    if not condition:
        raise HighlightReviewGateError(message)


def read(path: Path) -> dict:
    need(path.is_file() and not path.is_symlink(), "Missing review evidence: " + str(path))
    data = json.loads(path.read_text(encoding="utf8"))
    need(isinstance(data, dict), "Review evidence must be a JSON object")
    return data


def source_bound_plan(*, source: Path, slides: Path, plan: Path,
                      audio: Path) -> dict:
    """Validate ALL rendered slides and WAV identities before any rendering."""
    import pymupdf
    source, slides, plan, audio = (Path(p).resolve()
                                  for p in (source, slides, plan, audio))
    need(all(p.is_file() and not p.is_symlink()
             for p in (source, slides, plan)), "Missing source, slides or authored plan")
    need(audio.is_dir() and not audio.is_symlink(),
         "Frozen recorded audio folder missing")
    data = read(plan)
    need(data.get("schema_version") == 1
         and data.get("status") == "author_specified_unapproved_element_narration"
         and data.get("source_sha256") == digest(source)
         and data.get("slides_sha256") == digest(slides),
         "Stale, unapproved or unsourced element scene plan")
    voice = data.get("voice_id")
    need(isinstance(voice, str) and len(voice) >= 6 and
         "unknown" not in voice.casefold(), "Explicit narration voice required")
    parts = data.get("parts")
    need(isinstance(parts, list) and 1 <= len(parts) <= 40
         and [x.get("part_id") for x in parts] ==
             [f"part_{i:02d}" for i in range(1, len(parts)+1)],
         "No contiguous authored multipart plan")
    with pymupdf.open(slides) as deck:
        total = len(deck)
    need(1 <= total <= 500, "Empty or oversized slide deck")
    ordered, wav_names = [], []
    timings = []
    for part in parts:
        slides_in_part = part.get("slides")
        need(isinstance(slides_in_part, list) and bool(slides_in_part),
             "A video part has no slides")
        part_seconds = 0.0
        for slide in slides_in_part:
            number = slide.get("slide")
            need(type(number) is int, "Missing explicit slide number")
            ordered.append(number)
            elements = slide.get("elements")
            need(isinstance(elements, list) and elements,
                 "Every slide must declare specific narrated highlight elements")
            for item in elements:
                need(isinstance(item, dict) and isinstance(item.get("anchor"), dict),
                     "Narration has no source-linked element rectangle")
                name = item.get("wav")
                need(isinstance(name, str) and bool(name)
                     and name == Path(name).name and name.endswith(".wav")
                     and name not in wav_names, "Unsafe or repeated narration WAV")
                wav_names.append(name)
                wav = audio/name
                need(wav.is_file() and not wav.is_symlink(),
                     "Narration audio missing: " + name)
                with wave.open(str(wav), "rb") as file:
                    need(file.getcomptype() == "NONE" and
                         file.getnchannels() == 1 and
                         file.getsampwidth() == 2, "Invalid source PCM WAV")
                    part_seconds += file.getnframes()/file.getframerate()
        need(0 < part_seconds < 590,
             "Video part audio must provide safety margin below 600 seconds")
        timings.append(part_seconds)
    need(ordered == list(range(1, total+1)),
         "Element highlight plan must cover every slide once in order")
    need(len(wav_names) >= total,
         "Each original slide must have at least one synchronized spoken element")
    return {"plan_sha256":canonical(data), "source_sha256":digest(source),
            "slides_sha256":digest(slides), "slides":total,
            "elements":len(wav_names), "parts":len(parts),
            "part_audio_s":[round(n, 3) for n in timings],
            "voice_id":voice, "status":"review_only_preflight_complete"}


def verify_rendered(*, source: Path, slides: Path, authored: Path,
                    audio: Path, staged: Path, rendered: Path,
                    output: Path | None, recheck_pixels: bool = True) -> dict:
    """Recheck the real encoded MP4. If output=None, NEVER write a report.

    This read-only mode is for existing review bundles and does not give
    academic, narrator, semantics, video production or student approval.
    """
    original_paths = (source, slides, authored, audio, staged, rendered)
    need(all(not Path(x).is_symlink() for x in original_paths),
         "Symlinked source or evidence paths are not accepted")
    source,slides,authored,audio,staged,rendered=(
        Path(x).resolve() for x in original_paths)
    need(recheck_pixels is True,
         "Fresh decoded MP4 pixel verification is mandatory; no count-only acceptance")
    if output is not None:
        output=Path(output).absolute()
        need(not output.exists() and not output.is_symlink()
             and output.parent.is_dir(),
             "Review report must be a fresh file outside published originals")
        need(not output.is_relative_to(source.parent)
             and not output.is_relative_to(audio),
             "Never publish a technical review to the source/audio tree")
    before=source_bound_plan(source=source,slides=slides,plan=authored,audio=audio)
    plan=read(authored)
    staged_receipt=read(staged/"element_stage_receipt.json")
    main=read(rendered/"series_review_receipt.json")
    input_manifest=read(staged/"series_inputs.json")
    expected=[p["part_id"] for p in plan["parts"]]
    need(staged_receipt.get("source_sha256")==before["source_sha256"]
         and staged_receipt.get("slides_sha256")==before["slides_sha256"]
         and staged_receipt.get("complete_lecture_coverage") is True
         and staged_receipt.get("audio_text_fidelity_verified") is False
         and staged_receipt.get("mathematical_approval") is False
         and input_manifest.get("status")=="review_only_source_bound_inputs"
         and input_manifest.get("source_sha256")==before["source_sha256"]
         and input_manifest.get("plan_sha256")==before["plan_sha256"]
         and input_manifest.get("parts")==expected,
         "Incomplete source-grounded staged review evidence")
    need(main.get("status")=="review_only_not_approved"
         and main.get("source_sha256")==before["source_sha256"]
         and main.get("plan_sha256")==before["plan_sha256"]
         and main.get("student_published") is False
         and main.get("accepted_lecture_completion_created") is False
         and len(main.get("parts", []))==len(expected),
         "Missing or incorrectly approved encoded highlight review")
    checks=[]
    for index,(part, row) in enumerate(zip(plan["parts"], main["parts"]),1):
        part_id=expected[index-1]
        need(row.get("part_id")==part_id, "Video part reordered")
        stage=staged/part_id; target=rendered/part_id
        rec=read(target/"review_receipt.json")
        geometry=read(target/"element_geometry.json")
        timeline=read(target/"narration_timeline.json")
        board=read(stage/"storyboard.json")
        tts=read(stage/"tts_chunks.json")
        qa=read(target/"encoded_pixel_qa.json")
        mp4=target/f"{part_id}_review.mp4"
        combined=target/"narration.wav"
        need(mp4.is_file() and combined.is_file(),
             "Missing actual rendered video or narration waveform")
        event_count=sum(len(x["elements"]) for x in part["slides"])
        need(len(board.get("narration_segments",[]))==event_count
             and len(tts.get("segments",[]))==event_count
             and len(timeline.get("events",[]))==event_count
             and qa.get("count_events")==event_count
             and len(qa.get("checks",[]))==event_count
             and rec.get("highlight_segments")==event_count
             and rec.get("decoded_pixel_verified_events")==event_count,
             "Not every narrated element received a decoded-pixel check")
        events=timeline["events"]
        expected_window_count=2*sum(len(x["element_ids"]) for x in events)
        gaps=[(0,events[0]["start_ms"])]
        gaps.extend((a["end_ms"],b["start_ms"]) for a,b in zip(events,events[1:]))
        gaps.append((events[-1]["end_ms"],timeline["duration_ms"]))
        expected_idle_count=sum(b-a>=80 for a,b in gaps)
        need(qa.get("time_window_samples_checked")==expected_window_count
             and len(qa.get("time_window_checks",[]))==expected_window_count
             and qa.get("pause_samples_checked")==expected_idle_count
             and len(qa.get("pause_checks",[]))==expected_idle_count,
             "Incomplete speech-window or unhighlighted-pause encoded pixel checks")
        need(rec.get("mp4_sha256")==digest(mp4)
             and rec.get("wav_sha256")==digest(combined)
             and rec.get("decoded_pixel_qa_sha256")==digest(target/"encoded_pixel_qa.json")
             and rec.get("plan_sha256")==before["plan_sha256"]
             and rec.get("original_source_sha256")==before["source_sha256"],
             "Encoded video, PDF source, or recorded pixel QA changed")
        times=timeline["events"]
        running=0
        for num,(event,seg,chunk,check) in enumerate(zip(
                times,board["narration_segments"],tts["segments"],qa["checks"]),1):
            wav=stage/"wav"/chunk["filename"]
            need(wav.is_file() and not wav.is_symlink(), "Missing staged speech WAV")
            need(seg["segment_id"]==event.get("segment_id")==chunk["segment_id"]
                 and event.get("element_ids")==seg.get("element_ids")
                 and len(event["element_ids"])==1
                 and check.get("event")==num
                 and check.get("slide_id")==event.get("slide_id"),
                 "Highlight event is not the narrated element")
            original_element=[e for slide in part["slides"] for e in slide["elements"]][num-1]
            need(chunk["speech_sha256"]==
                 hashlib.sha256(original_element["spoken_text"].encode("utf8")).hexdigest()
                 and digest(audio/original_element["wav"])==digest(wav),
                 "Stage speech text or recorded waveform changed")
            with wave.open(str(wav),"rb") as waveform:
                duration_ms=round(1000*waveform.getnframes()/waveform.getframerate())
            need(type(event.get("start_ms")) is int
                 and type(event.get("end_ms")) is int
                 and abs(event["start_ms"]-running)<=3
                 and abs(event["end_ms"]-running-duration_ms)<=3,
                 "Narration and visible highlight timing drift")
            running=event["end_ms"]
            need(check.get("target_checks") and
                 {x["element_id"] for x in check["target_checks"]}==
                 set(event["element_ids"]) and
                 all(isinstance(x.get("highlight_evidence_gain"),(int,float))
                     and x["highlight_evidence_gain"]>0
                     for x in check["target_checks"]),
                 "Actual active highlighted pixels missing for spoken element")
        need(abs(timeline.get("duration_ms",-9999)-running)<=3,
             "Final audio and element timeline disagree")
        encoded=probe_mp4(mp4,exe=ffmpeg_path())
        need(0 < encoded["duration_s"] < 600
             and abs(encoded["duration_s"]-rec["encoded_mp4_seconds"])<=.11
             and abs(encoded["duration_s"]-running/1000)<=.4,
             "Actual MP4 violates strict ten-minute/timing contract")
        drift=rec.get("encoded_transition_qa",{})
        need(drift.get("verified_transition_count")==event_count
             and isinstance(drift.get("max_encoded_frame_drift_s"),(int,float))
             and 0<=drift["max_encoded_frame_drift_s"]<=.15,
             "Encoded transition verification missing or drifting")
        if recheck_pixels:
            independent=verify_encoded_highlight_pixels(
                mp4=mp4,frames_dir=target/"scratch_frames",
                geometry=geometry,timeline=timeline)
            need(independent.get("count_events")==event_count
                 and len(independent.get("checks",[]))==event_count
                 and all(c.get("target_checks") for c in independent["checks"])
                 and independent.get("time_window_samples_checked")==expected_window_count
                 and independent.get("pause_samples_checked")==expected_idle_count,
                 "Fresh decoded speech-window and pause MP4 pixel audit failed")
        checks.append({"part_id":part_id,"encoded_duration_s":encoded["duration_s"],
                       "narrated_highlight_events":event_count,
                       "encoded_pixels_rechecked":bool(recheck_pixels),
                       "mp4_sha256":digest(mp4)})
    report={"schema_version":1,
            "status":"COMPLETE_ELEMENT_HIGHLIGHT_TECHNICAL_REVIEW_ONLY",
            "source_sha256":before["source_sha256"],
            "slides_sha256":before["slides_sha256"],
            "source_plan_sha256":before["plan_sha256"],
            "covered_slides":before["slides"],
            "covered_elements":before["elements"],
            "parts":checks,
            "scientific_semantic_mapping_approved":False,
            "human_listening_approved":False,
            "student_published":False,
            "production_approved":False}
    if output is not None:
        with output.open("x",encoding="utf8") as handle:
            json.dump(report,handle,indent=2,ensure_ascii=False)
            handle.write("\n")
    return report


def review(*,source:Path,slides:Path,authored:Path,audio:Path,
           output_root:Path)->dict:
    """Stage, render and independently audit in a NEW, isolated review folder."""
    output_root=Path(output_root).resolve()
    source=Path(source).resolve();slides=Path(slides).resolve()
    authored=Path(authored).resolve();audio=Path(audio).resolve()
    need(not output_root.exists() and output_root.parent.is_dir()
         and not output_root.is_relative_to(source.parent)
         and not output_root.is_relative_to(audio),
         "Never overwrite original sources or earlier video review")
    source_bound_plan(source=source,slides=slides,plan=authored,audio=audio)
    # Only create output after preflight; failed render keeps diagnostic work.
    output_root.mkdir()
    stage=output_root/"staged"
    rendered=output_root/"rendered"
    prepare(source_pdf=source,slides_pdf=slides,authored_json=authored,
            recorded_audio=audio,destination=stage)
    render_review_series(source_pdf=source,inputs_root=stage,output_root=rendered)
    return verify_rendered(source=source,slides=slides,authored=authored,
        audio=audio,staged=stage,rendered=rendered,
        output=output_root/"highlight_technical_review.json")


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("source","slides","authored","audio","output-root"):
        p.add_argument("--"+name,required=True,type=Path)
    args=p.parse_args(argv)
    value=review(source=args.source,slides=args.slides,authored=args.authored,
                 audio=args.audio,output_root=args.output_root)
    print(json.dumps({k:v for k,v in value.items() if k!="parts"},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
