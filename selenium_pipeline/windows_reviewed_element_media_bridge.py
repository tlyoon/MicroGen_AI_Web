"""Existing reviewed-element source + recorded TTS -> real encoded MP4 REVIEW.

No new Gemini/ChatGPT call, no automatic TTS, no fabricated narration,
no student publication, and no PR140 figure semantic approval bypass.

This is the missing operator integration between the already-implemented
strict element_plan_review_bridge, per-WAV proof, and actual FFmpeg source-
synchronized highlight review + independent decoded video pixel QA.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .evidence_reuse_contract import file_sha256


class ReviewedMediaBridgeBlocked(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ReviewedMediaBridgeBlocked(reason)


def render_review(*, source: Path, slides: Path, script: Path,
                  draft: Path, selection: Path, tts_request: Path,
                  audio: Path, outdir: Path, review_renderer=None) -> dict:
    require(os.name == "nt", "Only native Windows source-bound review supported")
    source, slides, script, draft, selection, tts_request, audio, outdir = (
        Path(v).absolute() for v in (
            source, slides, script, draft, selection, tts_request, audio, outdir))
    require(source.name == "source.pdf" and slides == source.parent / "slides.pdf"
            and script == source.parent / "script.txt",
            "Exact original source/slide/narration triad required")
    inputs = (source, slides, script, draft, selection, tts_request)
    require(all(p.is_file() and not p.is_symlink() for p in inputs)
            and audio.is_dir() and not audio.is_symlink(),
            "Original files, explicit reviewed selection and recorded PCM required")
    require(not outdir.exists() and not outdir.is_symlink()
            and outdir.parent.is_dir() and not outdir.parent.is_symlink(),
            "New external no-overwrite review directory required")
    require(not outdir.is_relative_to(source.parent)
            and not source.parent.is_relative_to(outdir)
            and not outdir.is_relative_to(audio)
            and not audio.is_relative_to(outdir),
            "Review must be outside publisher/author and immutable audio trees")
    from .element_plan_review_bridge import promoted
    # Recomputes original physical publisher/author/math/figure selection and
    # checks WAV bytes, spoken script fragments, exact model/voice and TTS
    # pre-synthesis request SHA/identity against immutable evidence.
    plan = promoted(source=source, slides=slides, script=script,
                    draft_path=draft, selection=selection, audio=audio,
                    tts_request=tts_request)
    require(plan.get("status") ==
            "author_specified_unapproved_element_narration"
            and isinstance(plan.get("parts"), list) and plan["parts"],
            "Reviewed element source or recorded PCM evidence incomplete")
    from .element_highlight_workflow import source_bound_plan, review
    hashes = {str(p): file_sha256(p) for p in inputs}
    audio_wav = sorted({e["wav"] for part in plan["parts"]
                        for slide in part["slides"] for e in slide["elements"]})
    hashes.update({str(audio / name): file_sha256(audio / name)
                   for name in audio_wav})
    # Strict no-change source and recorded WAV preflight BEFORE outputs.
    require(not outdir.exists(), "Concurrent review output already exists")
    outdir.mkdir()
    authored = outdir / "reviewed_element_plan.json"
    with authored.open("x", encoding="utf8") as output:
        json.dump(plan, output, indent=2, ensure_ascii=False)
        output.write("\n")
    from .element_highlight_workflow import source_bound_plan
    source_bound_plan(source=source, slides=slides, plan=authored, audio=audio)
    render = review if review_renderer is None else review_renderer
    report = render(source=source, slides=slides, authored=authored,
                    audio=audio, output_root=outdir / "encoded_review")
    require(report.get("status") ==
            "COMPLETE_ELEMENT_HIGHLIGHT_TECHNICAL_REVIEW_ONLY"
            and report.get("production_approved") is False
            and report.get("student_published") is False
            and report.get("covered_slides", 0) > 0
            and report.get("covered_elements", 0) > 0
            and all(part.get("encoded_pixels_rechecked") is True
                    for part in report.get("parts", []))
            and len(report.get("parts", [])) == len(plan["parts"]),
            "Actual decoded source-aligned H264/AAC review not accepted")
    require(all(file_sha256(Path(name)) == digest
                for name, digest in hashes.items()),
            "Publisher/author/model/audio evidence changed during encoding")
    videos = sorted((outdir / "encoded_review" / "rendered")
                    .glob("part_*/part_*_review.mp4"))
    require(len(videos) == len(plan["parts"]) and all(
        p.is_file() and not p.is_symlink() and p.stat().st_size > 1000
        for p in videos), "Missing actual final decoded H264/AAC part")
    receipt = {
        "schema_version": 1,
        "status": "SOURCEBOUND_ELEMENT_REVIEW_MP4_ENCODED_AND_DECODED",
        "source_sha256": hashes[str(source)],
        "slides_sha256": hashes[str(slides)],
        "script_sha256": hashes[str(script)],
        "reviewed_selection_sha256": hashes[str(selection)],
        "source_review_plan_sha256": file_sha256(authored),
        "tts_request_sha256": hashes[str(tts_request)],
        "input_sha256": hashes,
        "part_sha256": {p.name: file_sha256(p) for p in videos},
        "covered_slides": report["covered_slides"],
        "covered_elements": report["covered_elements"],
        "decoded_pixel_checks_passed": True,
        "new_tts_or_model_calls": False,
        "perceptual_accurate_narration_human_certified": False,
        "production_media_approved": False,
        "student_publication_authorized": False,
    }
    with (outdir / "review_only_receipt.json").open(
            "x", encoding="utf8") as output:
        json.dump(receipt, output, indent=2, sort_keys=True)
        output.write("\n")
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "slides", "script", "draft", "selection",
                 "tts-request", "audio", "outdir"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args(argv)
    value = render_review(source=a.source, slides=a.slides, script=a.script,
                          draft=a.draft, selection=a.selection,
                          tts_request=a.tts_request, audio=a.audio,
                          outdir=a.outdir)
    print(json.dumps(value, indent=2))
    return 0 if value["status"] == (
        "SOURCEBOUND_ELEMENT_REVIEW_MP4_ENCODED_AND_DECODED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
