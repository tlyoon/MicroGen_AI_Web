"""Production seven-stage -> existing source-bound multipart video handoff.

The legacy static-slide encoder is NEVER used. The handoff accepts only
published source-adjacent math/slides/script/PCM and a passing source-bound
pronunciation QA for the full seven-stage route. It preserves existing files
and uses the already implemented automatic element-TTS + sourcebound renderer.
This is a technical internal stage, not academic/student release approval.
"""
from __future__ import annotations

import os
from pathlib import Path


class VideoHandoffBlocked(ValueError):
    """The existing source-bound production prerequisites are incomplete."""


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise VideoHandoffBlocked(msg)


def complete_from_published(*, source: Path, require_slide_tts_qa: bool = False) -> dict:
    """Finish the same approved multipart video flow used by video-only mode.

    No new paid element synthesis occurs before the existing complete slide
    audio/text coverage has been verified. A partial element batch is NEVER
    silently replaced, and prior published part files are NEVER overwritten.
    """
    from .runner import check_valid
    source = Path(source).absolute()
    lecture = source.parent
    require(source.is_file() and not source.is_symlink()
            and source.name == "source.pdf", "Original source.pdf unavailable")
    # Re-use a complete previously accepted multipart series without opening
    # Gemini, synthesizing WAVs, rendering new video, or replacing any MP4.
    if check_valid("video", lecture):
        return {"status": "REUSED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
                "new_generation_performed": False,
                "student_publication_authorized": False}
    require(not (lecture / "lecture_completion.json").exists()
            and not any(lecture.glob("part_[0-9][0-9]")),
            "Partial or conflicting multipart publication requires targeted recovery")
    require(not (lecture / "slides.mp4").exists(),
            "Old slide MP4 is protected; no silent video replacement")
    # Legacy but independently source-proven video-only jobs may already
    # contain a complete authored element plan and per-element PCM manifest.
    # Those inputs are sufficient to verify/render without a separate
    # slide-level script.txt, which may never have existed in that version.
    # For a NEW element TTS batch, however, the original script is mandatory.
    slides = lecture / "slides.pdf"
    require(slides.is_file() and not slides.is_symlink()
            and slides.stat().st_size > 0,
            "Missing real published slides.pdf prior to synchronized video")
    if require_slide_tts_qa:
        require(check_valid("tts_qa", lecture),
                "Complete passing original slide-WAV pronunciation QA is required "
                "before the full seven-stage video handoff")
        from .slide_narration_sync import verify
        verify(lecture)
    from .source_numbered_example_coverage import require_coverage
    tex = lecture / "slides.tex"
    if tex.is_file() and not tex.is_symlink():
        require_coverage(source_pdf=source, latex_path=tex)
    from .sourcebound_production_video import render_and_install_prepared
    targets = (lecture / "element_narration_plan.json",
               lecture / "element_wav",
               lecture / "element_tts_manifest.json")
    # Refuse incomplete element output before a paid/repeated TTS operation.
    require(all(not p.is_symlink() for p in targets),
            "Element source/PCM provenance cannot be a symlink")
    present = [p.exists() for p in targets]
    require(not any(present) or all(present),
            "Partial original per-element TTS batch: preserve it for recovery")
    if require_slide_tts_qa or not any(present):
        script = lecture / "script.txt"
        require(script.is_file() and not script.is_symlink()
                and script.stat().st_size > 0,
                "Missing real published script.txt; cannot initiate new "
                "source-bound element narration/TTS generation")
    root = Path(os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache"))
    staging = root / "MicroGen_AI_Web_VideoStaging"
    require(not staging.is_relative_to(lecture)
            and not lecture.is_relative_to(staging),
            "Local video staging must be separate from textbook source")
    staging.mkdir(parents=True, exist_ok=True)
    # Video-only resumes can bypass runner.script_qa, including when a
    # completed source-bound element-WAV batch already exists. Apply the
    # same versioned independent math remedy to both NEW and PREVIOUS
    # element audio before any render; legacy video-only manifests without
    # a script keep their older explicit source-anchor constraints.
    if (lecture/"script.txt").is_file():
        from .independent_math_checkpoint import ensure as ensure_math
        ensure_math(source=source,script=lecture/"script.txt")
    if not any(present):
        # The old exact-text-only element selector failed at the first Beamer
        # image/icon on every original Thomas section. Produce an immutable
        # entire-lecture mapping worklist ONCE before any paid audio attempt,
        # and reuse the same SHA-bound gap report on subsequent resumes.
        from .rich_element_mapping_checkpoint import (
            require_automatic_mapping_or_checkpoint)
        require_automatic_mapping_or_checkpoint(
            source=source, slides=lecture / "slides.pdf",
            script=lecture / "script.txt", checkpoint_root=staging)
        from .automatic_element_audio_stage import produce_element_audio
        produce_element_audio(source=source, slides=lecture / "slides.pdf",
                              script=lecture / "script.txt", local_work_root=staging)
    require(all(p.exists() and not p.is_symlink() for p in targets),
            "Incomplete source-anchored element PCM or narration plan")
    result = render_and_install_prepared(
        source=source, slides=lecture / "slides.pdf",
        authored=targets[0], audio=targets[1], local_work_root=staging)
    require(result.get("status") ==
            "INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
            "Rendering did not install technically accepted multipart video")
    require(check_valid("video", lecture),
            "Installed highlighted multipart video failed production technical QA")
    return {
        "status": "INSTALLED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO",
        "new_generation_performed": True,
        "part_count": result["part_count"],
        "student_publication_authorized": False,
    }
