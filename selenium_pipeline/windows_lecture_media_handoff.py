"""Windows reviewed-audio → real MP4 handoff for a SHA-complete original source.

One explicit source-bound media encode from ALREADY reviewed per-element WAVs.
No Gemini/ChatGPT request, no TTS generation, no publication, and never any
resend of a previously ambiguous PDF model request. A second invocation can
only inspect and reuse fully SHA-verified output; partial outputs quarantine.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _new_atomic, _verified_json, require,
)
from .windows_lecture_progression_coordinator import inspect_progress

_RECEIPT = "sourcebound_media_handoff_receipt.json"
_CORE_RECEIPT = "review_only_receipt.json"
_PASS = "SOURCEBOUND_ELEMENT_REVIEW_MP4_ENCODED_AND_DECODED"


def _part_files(outdir: Path) -> list[Path]:
    root = outdir / "encoded_review" / "rendered"
    return sorted(root.glob("part_*/part_*_review.mp4"))


def _input_hashes(*, draft: Path, selection: Path, tts_request: Path,
                  audio: Path) -> dict[str, str]:
    required = (draft, selection, tts_request)
    require(all(p.is_file() and not p.is_symlink() and p.stat().st_size > 0
                for p in required), "Missing original reviewed author inputs")
    require(audio.is_dir() and not audio.is_symlink(),
            "Missing distinct existing recorded PCM audio directory")
    wavs = sorted(audio.glob("*.wav"))
    proofs = sorted(audio.glob("*.verified.json"))
    require(wavs and proofs and len(wavs) == len(proofs)
            and {p.name for p in proofs}
                == {p.name + ".verified.json" for p in wavs}
            and all(p.is_file() and not p.is_symlink() and p.stat().st_size > 100
                    for p in wavs)
            and all(p.is_file() and not p.is_symlink() and p.stat().st_size > 0
                    for p in proofs),
            "Each existing recorded PCM WAV requires an unmodified proof")
    return {str(p): file_sha256(p) for p in (*required, *wavs, *proofs)}


def _exact_review(*, media_dir: Path, original: dict,
                  inputs: dict[str, str]) -> dict:
    manifest = _verified_json(media_dir / _RECEIPT)
    source, slides, script = (
        Path(original[k]) for k in ("source", "slides_pdf", "script"))
    base = media_dir / _CORE_RECEIPT
    require(base.is_file() and not base.is_symlink(),
            "No accepted source-bound FFmpeg technical media receipt")
    try:
        reviewed = json.loads(base.read_text(encoding="utf8"))
    except (OSError, ValueError) as exc:
        raise CampaignRecoveryBlocked("Malformed exact decoded MP4 review") from exc
    require(type(reviewed) is dict and reviewed.get("schema_version") == 1
            and reviewed.get("status") == _PASS
            and reviewed.get("source_sha256") == original["source_sha256"]
            and reviewed.get("slides_sha256") == original["slides_pdf_sha256"]
            and reviewed.get("script_sha256") == original["script_sha256"]
            and reviewed.get("new_tts_or_model_calls") is False
            and reviewed.get("decoded_pixel_checks_passed") is True
            and reviewed.get("production_media_approved") is False
            and reviewed.get("student_publication_authorized") is False,
            "Prior media has no source-bound technical-only decoded acceptance")
    require(manifest.get("schema_version") == 1
            and manifest.get("source_sha256") == original["source_sha256"]
            and manifest.get("slides_pdf_sha256") == original["slides_pdf_sha256"]
            and manifest.get("script_sha256") == original["script_sha256"]
            and manifest.get("review_input_sha256") == inputs
            and manifest.get("base_review_receipt_sha256") == file_sha256(base)
            and manifest.get("student_publication_authorized") is False
            and manifest.get("new_model_or_tts_calls") is False
            and manifest.get("formal_academic_release_approved") is False,
            "Immutable media handoff identity, reviewed WAV evidence or consent changed")
    outputs = manifest.get("encoded_video_sha256")
    files = _part_files(media_dir)
    require(type(outputs) is dict and files
            and len(files) == len(outputs)
            and len({p.name for p in files}) == len(files)
            and all(p.is_file() and not p.is_symlink() and p.stat().st_size > 1000
                    and outputs.get(p.name) == file_sha256(p) for p in files)
            and outputs == reviewed.get("part_sha256"),
            "Prior actual encoded video bytes changed; do not rerender")
    require(file_sha256(source) == original["source_sha256"]
            and file_sha256(slides) == original["slides_pdf_sha256"]
            and file_sha256(script) == original["script_sha256"],
            "Original text/slides/script changed after video encode")
    return {
        "schema_version": 1,
        "status": "SOURCEBOUND_REVIEWED_MEDIA_REUSED_SHA_VERIFIED",
        "source_sha256": original["source_sha256"],
        "decoded_mp4_parts_verified": len(files),
        "new_model_or_tts_calls": False,
        "new_video_rendered": False,
        "formal_academic_release_approved": False,
        "student_publication_authorized": False,
    }


def handoff_media(*, source_root: Path, section: str, trial_dir: Path,
                  draft: Path, selection: Path, tts_request: Path,
                  audio: Path, outdir: Path, execute_encode: bool = False,
                  technical_check=None, media_renderer=None) -> dict:
    """One safe reviewed-media action, never starts another model/TTS task."""
    require(os.name == "nt", "Windows-only source-bound media completion")
    state = inspect_progress(
        source_root=source_root, section=section, trial_dir=trial_dir,
        technical_check=technical_check)
    if state["status"] != "REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS":
        return {
            "schema_version": 1,
            "status": "MEDIA_PREREQUISITES_NOT_ACCEPTED_NO_ENCODING",
            "source_stage_status": state["status"],
            "new_model_or_tts_calls": False,
            "new_video_rendered": False,
            "student_publication_authorized": False,
        }
    original = state
    source_root, trial_dir = Path(source_root).absolute(), Path(trial_dir).absolute()
    draft, selection, tts_request, audio, outdir = (
        Path(p).absolute() for p in (draft, selection, tts_request, audio, outdir))
    source = Path(original["source"])
    slides = Path(original["slides_pdf"])
    script = Path(original["script"])
    require(source.parent == slides.parent == script.parent
            and source.is_relative_to(trial_dir)
            and not source.is_relative_to(source_root),
            "Reviewed media must use local original-source staged slide/script triad")
    require(outdir.parent.is_dir() and not outdir.parent.is_symlink()
            and not outdir.is_symlink()
            and not outdir.is_relative_to(source_root)
            and not outdir.is_relative_to(source.parent)
            and not source.parent.is_relative_to(outdir)
            and not outdir.is_relative_to(audio)
            and not audio.is_relative_to(outdir),
            "Outdir must be new, external, and non-overlapping")
    inputs = _input_hashes(
        draft=draft, selection=selection, tts_request=tts_request, audio=audio)
    if outdir.exists():
        if not (outdir / _RECEIPT).is_file():
            return {
                "schema_version": 1,
                "status": "HALTED_PARTIAL_MEDIA_OUTPUT_NO_REENCODE",
                "source_sha256": original["source_sha256"],
                "new_model_or_tts_calls": False,
                "new_video_rendered": False,
                "student_publication_authorized": False,
            }
        return _exact_review(media_dir=outdir, original=original, inputs=inputs)
    if not execute_encode:
        return {
            "schema_version": 1,
            "status": "REVIEWED_MEDIA_INPUTS_READY_EXPLICIT_FFMPEG_ONLY",
            "source_sha256": original["source_sha256"],
            "reviewed_input_files": len(inputs),
            "reviewed_audio_wavs": len(list(audio.glob("*.wav"))),
            "no_new_gemini_or_tts_calls": True,
            "new_model_or_tts_calls": False,
            "new_video_rendered": False,
            "student_publication_authorized": False,
        }
    from .windows_reviewed_element_media_bridge import render_review
    renderer = render_review if media_renderer is None else media_renderer
    receipt = renderer(source=source, slides=slides, script=script,
                       draft=draft, selection=selection, tts_request=tts_request,
                       audio=audio, outdir=outdir)
    require(type(receipt) is dict and receipt.get("schema_version") == 1
            and receipt.get("status") == _PASS
            and receipt.get("source_sha256") == original["source_sha256"]
            and receipt.get("slides_sha256") == original["slides_pdf_sha256"]
            and receipt.get("script_sha256") == original["script_sha256"]
            and receipt.get("decoded_pixel_checks_passed") is True
            and receipt.get("new_tts_or_model_calls") is False
            and receipt.get("production_media_approved") is False
            and receipt.get("student_publication_authorized") is False,
            "Reviewed media renderer did not prove decoded H264/AAC integrity")
    base = outdir / _CORE_RECEIPT
    require(base.is_file() and not base.is_symlink()
            and json.loads(base.read_text(encoding="utf8")) == receipt,
            "Actual reviewed media receipt missing or altered")
    files = _part_files(outdir)
    require(files and len({p.name for p in files}) == len(files)
            and receipt.get("part_sha256") ==
                {p.name: file_sha256(p) for p in files}
            and all(p.is_file() and not p.is_symlink() and p.stat().st_size > 1000
                    for p in files),
            "Actual H264/AAC final bytes missing or changed")
    require(inputs == _input_hashes(
        draft=draft, selection=selection, tts_request=tts_request, audio=audio),
        "Reviewed per-element author/audio evidence changed during encode")
    immutable = {
        "schema_version": 1,
        "source_sha256": original["source_sha256"],
        "slides_pdf_sha256": original["slides_pdf_sha256"],
        "script_sha256": original["script_sha256"],
        "review_input_sha256": inputs,
        "base_review_receipt_sha256": file_sha256(base),
        "encoded_video_sha256": receipt["part_sha256"],
        "new_model_or_tts_calls": False,
        "formal_academic_release_approved": False,
        "student_publication_authorized": False,
    }
    _new_atomic(outdir / _RECEIPT, immutable)
    prior = _exact_review(media_dir=outdir, original=original, inputs=inputs)
    return {
        **prior,
        "status": "SOURCEBOUND_REVIEWED_MEDIA_NEW_MP4_TECHNICAL_PASS_ONLY",
        "new_video_rendered": True,
        "no_student_publication": True,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("source-root", "section", "trial-dir", "draft", "selection",
                 "tts-request", "audio", "outdir"):
        ap.add_argument("--" + name, required=True,
                        type=Path if name != "section" else str)
    ap.add_argument("--render-reviewed-media-once", action="store_true",
                    help="Real local FFmpeg, never any model or TTS generation")
    args = ap.parse_args(argv)
    try:
        report = handoff_media(
            source_root=args.source_root, section=args.section,
            trial_dir=args.trial_dir, draft=args.draft, selection=args.selection,
            tts_request=args.tts_request, audio=args.audio, outdir=args.outdir,
            execute_encode=args.render_reviewed_media_once)
    except (CampaignRecoveryBlocked, OSError, ValueError) as exc:
        report = {"schema_version": 1,
                  "status": "REVIEWED_MEDIA_HANDOFF_REJECTED",
                  "reason": str(exc), "new_model_or_tts_calls": False,
                  "new_video_rendered": False,
                  "student_publication_authorized": False}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in (
        "REVIEWED_MEDIA_INPUTS_READY_EXPLICIT_FFMPEG_ONLY",
        "SOURCEBOUND_REVIEWED_MEDIA_REUSED_SHA_VERIFIED",
        "SOURCEBOUND_REVIEWED_MEDIA_NEW_MP4_TECHNICAL_PASS_ONLY",
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
