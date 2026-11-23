"""Publish completed slide-PDF/narration/TTS/MP4 chains without highlight QA.

Explicitly scoped VIDEO-ONLY operation. Never treats whole-slide static MP4s
as time-synchronized source-grounded figure/equation highlights. No LLM, API,
synthesis, student-release, scientific QA, or full G3 acceptance is performed.

Existing source-bound video previews may be promoted *without transcoding* only
when immutable original PDF, script, WAV, independent QA and preview hashes all
match. A conflicting canonical MP4 is never overwritten or falsely accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime, timezone

from .slide_narration_sync import verify as verify_slide_sync
from .video_ffmpeg import ffmpeg_executable, validate_video

NEW_SECTIONS = ("11.1", "11.3", "11.5")
OLD_SECTIONS = ("11.2", "11.4")
ALL_SECTIONS = ("11.1", "11.2", "11.3", "11.4", "11.5")
STATUS = "TECHNICAL_NARRATED_MP4_CHAIN_COMPLETE_HIGHLIGHTS_EXPLICITLY_NOT_REQUESTED"
LEGACY_STATUS = "EXISTING_MP4_CHAIN_TECHNICALLY_REVALIDATED_HIGHLIGHTS_NOT_EVALUATED"


def sha(file: Path) -> str:
    d = hashlib.sha256()
    with Path(file).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            d.update(chunk)
    return d.hexdigest()


def _require(condition: bool, problem: str) -> None:
    if not condition:
        raise RuntimeError(problem)


def _json(file: Path) -> dict:
    obj = json.loads(file.read_text(encoding="utf8"))
    _require(isinstance(obj, dict), f"Invalid JSON object: {file}")
    return obj


def _atomic_json(path: Path, document: dict) -> None:
    # Leave existing receipt untouched until new verified JSON is ready.
    _require(not path.is_symlink(), f"Linked receipt is forbidden: {path}")
    temp = path.with_name(f".{path.name}.pending.{os.getpid()}")
    try:
        temp.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _audio_qa(folder: Path, slides: int | None = None) -> dict:
    report = _json(folder / "tts_fidelity_report.json")
    summary = report["summary"]
    _require(summary["slides"] > 0 and summary["slides"] == summary["passed"]
             and summary.get("review", 0) == 0
             and summary.get("blocking_failures", 0) == 0,
             f"Acoustic QA is not passing: {folder}")
    if slides is not None:
        _require(summary["slides"] == slides, f"Slide and acoustic counts differ: {folder}")
    return report


def _duration_and_decode(file: Path, expected: float, ffmpeg: str) -> float:
    _require(0 < expected < 600, f"Part expected duration violates 600s cap: {file}")
    validate_video(ffmpeg, file, expected)
    probe = subprocess.run([ffmpeg, "-hide_banner", "-i", str(file)],
                           capture_output=True, text=True, errors="replace", timeout=60)
    text = probe.stdout + probe.stderr
    match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", text)
    _require(match is not None, f"No measured media duration: {file}")
    duration = int(match[1])*3600 + int(match[2])*60 + float(match[3])
    _require(0 < duration < 600 and abs(duration-expected) < max(2.0, expected*.05),
             f"Unexpected MP4 duration {duration}s vs {expected}s: {file}")
    decoded = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-i", str(file),
         "-f", "null", os.devnull],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        text=True, errors="replace", timeout=900)
    _require(decoded.returncode == 0 and not decoded.stderr.strip(),
             f"Independent media decoding failed: {file}: {decoded.stderr[-600:]}")
    return round(duration, 3)


def _guarded_copy(source: Path, dest: Path, expected_sha: str) -> None:
    _require(source.is_file() and not source.is_symlink(), f"Invalid preview input: {source}")
    _require(sha(source) == expected_sha, f"Input changed while preparing: {source}")
    _require(not dest.is_symlink(), f"Output linked to an unexpected target: {dest}")
    if dest.exists():
        _require(sha(dest) == expected_sha,
                 f"Existing original video conflicts; do not overwrite: {dest}")
        return
    pending = dest.with_name(f".{dest.name}.pending.{os.getpid()}")
    try:
        shutil.copy2(source, pending)
        _require(sha(source) == expected_sha and sha(pending) == expected_sha,
                 f"Source changed during publication: {source}")
        # A single-owner caller is required; never overwrite a concurrently
        # created different final video.
        _require(not dest.exists(), f"Another worker created: {dest}")
        os.replace(pending, dest)
        _require(sha(dest) == expected_sha, f"Publication checksum mismatch: {dest}")
    finally:
        pending.unlink(missing_ok=True)


def _technical_input_proof(folder: Path, preview: Path) -> tuple[dict, dict, list]:
    for name in ("source.pdf", "slides.pdf", "slides.tex", "script.txt"):
        _require((folder / name).is_file(), f"Missing required source input: {folder / name}")
    try:
        synced = verify_slide_sync(folder)
    except ValueError:
        # The generic published-lecture source validator remains strict.
        # This explicit VIDEO-ONLY stage has no completion/release receipt,
        # and may revalidate original bytes against its independent preview
        # after a PyMuPDF derived page-text ABI change. Never regenerate or
        # re-Send provider requests to work around a parser version change.
        from .ch11_stage_only_pdf_text_parity_v1 import (
            verify_stage_only_parser_drift)
        proof = verify_stage_only_parser_drift(folder=folder, preview=preview)
        _require(proof["student_publication_authorized"] is False
                 and proof["paid_model_sends"]==0
                 and proof["independent_visual_highlight_accepted"] is False,
                 "Stage-only parser source evidence attempted release")
        synced=proof["technical_sync_original"]
    qa = _audio_qa(folder, synced["pages"])
    previous = _json(preview / "preview_manifest.json")
    _require(previous["status"] ==
             "TECHNICAL_PREVIEW_SLIDE_AUDIO_SYNC_NO_ELEMENT_HIGHLIGHTS_NOT_RELEASED",
             "Preview was not independently rendered to the known safe profile")
    _require(previous["preview_has_element_highlights"] is False
             and previous["student_published"] is False
             and previous["independent_encoded_highlight_qa_passed"] is False,
             "Never promote an unqualified highlight or publication claim")
    expected_inputs = {
        name: sha(folder / name)
        for name in ("source.pdf", "slides.pdf", "script.txt", "slide_narration_sync.json",
                     "tts_fidelity_report.json")
    }
    _require(previous["original_sha256"] == expected_inputs,
             f"Source PDF/narration/QA changed after rendering: {folder}")
    expected_wavs = {
        f"slide{i}.wav": sha(folder / f"slide{i}.wav")
        for i in range(1, synced["pages"]+1)}
    _require(previous["original_wav_sha256"] == expected_wavs,
             "WAV changed after video rendering")
    parts = previous["parts"]
    _require(isinstance(parts, list) and parts and len(parts) <= 100,
             "Missing bounded preview parts")
    covered = []
    filenames = set()
    for index, part in enumerate(parts, start=1):
        _require(part["index"] == index, "Preview part order changed")
        _require(isinstance(part["slides"], list) and part["slides"],
                 "Preview part contains no mapped slides")
        _require(part["video_audio_streams_verified"] is True
                 and part["decode_all_frames_passed"] is True,
                 "Preview has not passed technical media checks")
        _require(0 < part["wav_seconds"] < 600,
                 "Preview segment exceeds MP4 duration cap")
        name = part["filename"]
        _require(re.fullmatch(r"preview_slide_sync_no_highlights_part_\d{2}\.mp4", name)
                 and name not in filenames,
                 "Unsafe or duplicate preview filename")
        filenames.add(name)
        covered.extend(part["slides"])
    _require(covered == list(range(1, synced["pages"]+1)),
             "Preview is missing or repeating slides")
    return synced, qa, parts


def _completed_technical_section(folder: Path, preview: Path, ffmpeg: str) -> dict:
    synced, qa, parts = _technical_input_proof(folder, preview)
    results = []
    for index, part in enumerate(parts, start=1):
        original = preview / part["filename"]
        target = folder / ("slides.mp4" if index == 1 else f"slides_part{index:02d}.mp4")
        digest = part["sha256"]
        _require(original.is_file() and sha(original) == digest,
                 f"Video bytes do not match render receipt: {original}")
        print(f"[narrated-chain] verified-preview {folder.name} {index}/{len(parts)}", flush=True)
        actual = _duration_and_decode(original, part["wav_seconds"], ffmpeg)
        _guarded_copy(original, target, digest)
        measured = _duration_and_decode(target, part["wav_seconds"], ffmpeg)
        _require(abs(measured - actual) < .05, "Published duration changed unexpectedly")
        results.append({
            "filename": target.name, "sha256": digest,
            "duration_seconds": measured, "slides": part["slides"],
            "audio_video_streams": True, "decoded_all_frames": True})
        print(f"[narrated-chain] published {folder.name}/{target.name} {measured:.2f}s", flush=True)
    receipt = {
        "schema_version": 1, "status": STATUS,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "original_source_pdf_sha256": sha(folder / "source.pdf"),
        "slides_pdf_sha256": sha(folder / "slides.pdf"),
        "slides_tex_sha256": sha(folder / "slides.tex"),
        "script_txt_sha256": sha(folder / "script.txt"),
        "tts_qa_report_sha256": sha(folder / "tts_fidelity_report.json"),
        "narration_wav_count": synced["pages"],
        "acoustic_qa_passed_count": qa["summary"]["passed"],
        "narration_synced_structurally": True,
        "video_parts": results,
        "total_parts": len(results),
        "all_videos_below_600s": True,
        "highlight_verification_scope": "explicitly_skipped_by_user",
        "independent_visual_highlight_acceptance": "not_performed",
        "full_g3_release_accepted": False,
        "student_publication_authorized_by_this_receipt": False,
        "no_paid_model_calls": True,
        "reused_verified_preview_bytes_without_tts_or_slide_regeneration": True,
    }
    _atomic_json(folder / ".microgen_narrated_video_chain.json", receipt)
    # Exact filenames in existing Chapter 11 length-control convention, so
    # external MP4 enumerators can locate every part. Not a final G3 receipt.
    _atomic_json(folder / "lecture_parts_manifest.json", {
        "schema_version":1,"status":"technical_length_control_passed",
        "source_sha256":receipt["original_source_pdf_sha256"],
        "parts": [
            {k:item[k] for k in ("filename","sha256","duration_seconds")}
            for item in results],
        "total_parts":len(results),
        "independent_acoustic_acceptance":"passed",
        "independent_visual_highlight_acceptance":"not_performed_user_skipped",
        "full_g3_release_accepted":False,
        "technical_only":True,
        "checked_utc":receipt["completed_at_utc"],
    })
    return receipt


def _validate_existing_legacy(folder: Path, ffmpeg: str) -> dict:
    receipt = _json(folder / ".microgen_completion.json")
    manifest = _json(folder / "lecture_parts_manifest.json")
    _require(receipt.get("source_sha256") == sha(folder / "source.pdf") ==
             manifest.get("source_sha256"), "Legacy source hashes disagree")
    qa = _audio_qa(folder)
    for name in ("source.pdf","slides.pdf","slides.tex","script.txt"):
        _require((folder/name).is_file(), f"Missing legacy input {name}")
    _require(manifest.get("status") == "technical_length_control_passed"
             and manifest.get("total_parts") == len(manifest["parts"]),
             "Legacy video parts manifest invalid")
    _require([p["filename"] for p in manifest["parts"]] ==
             ["slides.mp4"]+[f"slides_part{i:02d}.mp4" for i in range(2,len(manifest["parts"])+1)],
             "Legacy MP4 parts are not sequential")
    result = []
    for part in manifest["parts"]:
        file = folder / part["filename"]
        _require(sha(file) == part["sha256"], f"Historical MP4 changed: {file}")
        observed = _duration_and_decode(file, part["duration_seconds"], ffmpeg)
        result.append({"filename":file.name,"sha256":part["sha256"],
                       "duration_seconds":observed})
        print(f"[narrated-chain] existing-verified {folder.name}/{file.name}", flush=True)
    return {
        "schema_version":1,"status":LEGACY_STATUS,"section":folder.name,
        "original_source_pdf_sha256":receipt["source_sha256"],
        "slides_pdf_sha256":sha(folder / "slides.pdf"),
        "script_txt_sha256":sha(folder / "script.txt"),
        "tts_qa_report_sha256":sha(folder / "tts_fidelity_report.json"),
        "qa_reported_passed":qa["summary"]["passed"],
        "qa_reported_total":qa["summary"]["slides"],
        "parts":result,"total_parts":len(result),
        "highlight_verification_scope":"explicitly_skipped_by_user",
        "full_g3_release_revalidated":False,
        "legacy_independent_acoustic_proof":"not_reestablished",
        "source_assets_and_videos_unchanged":True,
    }


def run(chapter: Path, sections: tuple[str, ...] = ALL_SECTIONS) -> dict:
    from .recovery_registry import lookup_mechanism
    _require(lookup_mechanism(
        "narrated_mp4_stage_only",
        "EXPLICIT_USER_SCOPED_NARRATED_MP4_WITHOUT_HIGHLIGHT_QA"
    ) == "SOURCE_QA_SYNC_HASH_VERIFIED_VIDEO_PROMOTION_NO_G3_RELEASE",
        "Narrated-only MP4 recovery not registered; do not publish")
    chapter = Path(chapter)
    _require(chapter.name=="11", "This bounded completion run is Chapter 11 only")
    _require(set(sections) <= set(ALL_SECTIONS) and len(set(sections))==len(sections),
             "Unknown/duplicated Chapter 11 sections")
    ffmpeg = ffmpeg_executable()
    summary = {}
    for section in sections:
        folder = chapter / section
        _require(folder.is_dir(), f"Missing subtopic: {folder}")
        if section in NEW_SECTIONS:
            receipt = _completed_technical_section(
                folder, chapter / "_review_only_video_previews" / section, ffmpeg)
            summary[section] = {
                "status":STATUS,"parts":receipt["video_parts"],
                "acoustic_qa_passed_count":receipt["acoustic_qa_passed_count"],
                "technical_receipt":str(folder / ".microgen_narrated_video_chain.json")}
        else:
            receipt = _validate_existing_legacy(folder, ffmpeg)
            summary[section] = {
                "status":LEGACY_STATUS,"parts":receipt["parts"],
                "acoustic_qa_reported_passed":receipt["qa_reported_passed"],
                "existing_legacy_completion_receipt":str(folder / ".microgen_completion.json")}
    complete = len(summary)==5 and set(summary)==set(ALL_SECTIONS)
    result = {
        "schema_version":1,"status":(
            "CHAPTER_11_NARRATED_MP4_CHAIN_COMPLETE_EXCLUDING_HIGHLIGHTS"
            if complete else "CHAPTER_11_NARRATED_MP4_CHAIN_PARTIAL"),
        "updated_at_utc":datetime.now(timezone.utc).isoformat(),
        "user_scope":"slide -> narration -> tts -> mp4; skip highlight verification",
        "technical_video_chain_completed":complete,
        "all_source_grounded_visual_highlights_accepted":False,
        "highlight_verification_skipped_not_passed":True,
        "full_g3_release_accepted":False,
        "paid_gemini_api_requests_in_this_operation":0,
        "chapter":11,"sections":summary,
        "total_mp4_parts":sum(len(q["parts"]) for q in summary.values())
    }
    _atomic_json(chapter / ".microgen_ch11_narrated_mp4_chain_status.json",result)
    print("[narrated-chain] SUMMARY",result["status"],
          "mp4_parts=",result["total_mp4_parts"],flush=True)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter-folder",type=Path,required=True)
    parser.add_argument("--scope",choices=("narrated-video-only",),required=True,
                        help="Explicitly excludes visual-highlight/G3 release certification")
    parser.add_argument("--sections",nargs="*",choices=ALL_SECTIONS,
                        default=list(ALL_SECTIONS))
    args=parser.parse_args(argv)
    run(args.chapter_folder,tuple(args.sections))


if __name__=="__main__":
    main()
