"""Recover a COMPLETE, isolated highlighted review from preserved source-bound inputs.

This rebuilds NEW review MP4s; it never claims that older flattened MP4
exports were freshly re-decoded or that audio/maths were human approved.
No TTS/network/cloud API is invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from .element_highlight_workflow import (
    HighlightReviewGateError, source_bound_plan,
)
from .series_review_preview import render_review_series
from .read_only_video_review_audit import audit_existing


class PreservedReviewRecoveryError(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise PreservedReviewRecoveryError(why)


def file_sha(path: Path) -> str:
    need(path.is_file() and not path.is_symlink(),
         f"Missing or unsafe preserved file: {path.name}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_file(path: Path) -> dict:
    file_sha(path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise PreservedReviewRecoveryError("Invalid original JSON evidence") from exc
    need(isinstance(doc, dict), "Preserved evidence must be a JSON object")
    return doc


def _within(child: Path, parent: Path) -> bool:
    return child == parent or child.is_relative_to(parent)


def preflight(*, source: Path, slides: Path, authored: Path,
              frozen: Path, synthesis_receipt: Path) -> dict:
    """Verify source, slide, exact 48-or-N WAV mappings and original receipts.

    No source or output file is modified; filename mappings are indexed by
    frozen per-part storyboard and the authored original element plan.
    """
    paths = [Path(x) for x in (source, slides, authored, frozen, synthesis_receipt)]
    need(not any(x.is_symlink() for x in paths),
         "Symlinked preserved source/review files forbidden")
    source, slides, authored, frozen, synthesis_receipt = [
        x.resolve(strict=True) for x in paths]
    need(frozen.is_dir() and not frozen.is_symlink(),
         "Preserved frozen stage is not a directory")
    plan = json_file(authored)
    manifest = json_file(frozen / "series_inputs.json")
    stage_receipt = json_file(frozen / "element_stage_receipt.json")
    tts = json_file(synthesis_receipt)
    need(plan.get("schema_version") == 1
         and plan.get("status") == "author_specified_unapproved_element_narration"
         and plan.get("source_sha256") == file_sha(source)
         and plan.get("slides_sha256") == file_sha(slides),
         "Source or slides differ from preserved authored plan")
    from .element_narration_stage import canonical
    plan_hash = canonical(plan)
    need(manifest.get("schema_version") == 1
         and manifest.get("status") == "review_only_source_bound_inputs"
         and manifest.get("source_sha256") == plan["source_sha256"]
         and manifest.get("plan_sha256") == plan_hash
         and stage_receipt.get("source_sha256") == plan["source_sha256"]
         and stage_receipt.get("slides_sha256") == plan["slides_sha256"]
         and stage_receipt.get("plan_sha256") == plan_hash
         and stage_receipt.get("complete_lecture_coverage") is True
         and stage_receipt.get("audio_text_fidelity_verified") is False
         and stage_receipt.get("mathematical_approval") is False,
         "Frozen review-stage evidence is stale, unsourced or already claimed approved")
    need(tts.get("status") ==
             "real_gemini_tts_generated_review_only_word_fidelity_unverified"
         and tts.get("original_plan_sha256") == plan_hash
         and tts.get("provider") == "gemini"
         and tts.get("model") == "gemini-3.8-flash-lite-tts"
         and tts.get("voice") == "Kore"
         and tts.get("same_declared_voice_all_segments") is True
         and tts.get("audible_word_fidelity_verified") is False,
         "No source-bound, genuine, still-unreviewed Gemini/Kore TTS receipt")
    parts = plan.get("parts")
    need(isinstance(parts, list) and 1 <= len(parts) <= 40,
         "No bounded authored lecture parts")
    expected = [f"part_{i:02d}" for i in range(1, len(parts)+1)]
    need([p.get("part_id") for p in parts] == expected
         and manifest.get("parts") == expected,
         "Frozen stage does not contain all contiguous authored parts")
    claims = tts.get("segments")
    need(isinstance(claims, list), "No original recorded WAV receipts")
    by_name = {}
    for claim in claims:
        need(isinstance(claim, dict)
             and isinstance(claim.get("filename"), str)
             and claim["filename"] == Path(claim["filename"]).name
             and claim["filename"] not in by_name,
             "Duplicate or unsafe original narration WAV receipt")
        by_name[claim["filename"]] = claim
    mapping = []
    all_names = set()
    for part in parts:
        part_id = part["part_id"]
        root = frozen / part_id
        need(root.is_dir() and not root.is_symlink(),
             f"Missing preserved {part_id} directory")
        file_sha(root / "instrumented.pdf")
        board = json_file(root / "storyboard.json")
        chunks = json_file(root / "tts_chunks.json")
        elements = [e for sl in part["slides"] for e in sl["elements"]]
        speech = board.get("narration_segments")
        wavs = chunks.get("segments")
        need(isinstance(speech, list) and isinstance(wavs, list)
             and len(elements) == len(speech) == len(wavs) > 0,
             "Frozen per-element coverage is incomplete")
        for i, (element, segment, wav) in enumerate(zip(elements,speech,wavs),1):
            name = element.get("wav")
            need(isinstance(name, str) and name == Path(name).name
                 and name.endswith(".wav") and name not in all_names
                 and name in by_name,
                 "Original recorded element WAV missing from provider receipt")
            all_names.add(name)
            need(wav.get("filename") == f"n{i}.wav"
                 and wav.get("segment_id") == segment.get("segment_id")
                 and wav.get("voice_id") == plan.get("voice_id")
                 and segment.get("spoken_text") == element.get("spoken_text")
                 and isinstance(element.get("spoken_text"), str)
                 and hashlib.sha256(element["spoken_text"].encode("utf-8")
                                    ).hexdigest() == wav.get("speech_sha256")
                 and by_name[name].get("spoken_text_sha256") ==
                     wav["speech_sha256"]
                 and by_name[name].get("model") == tts["model"]
                 and by_name[name].get("voice") == tts["voice"],
                 f"Recorded source text or voice changed for {name}")
            frozen_wav = root / "wav" / wav["filename"]
            need(file_sha(frozen_wav) == by_name[name].get("wav_sha256"),
                 f"Original {name} WAV differs from attested provider hash")
            mapping.append((name, frozen_wav, by_name[name]["wav_sha256"]))
    need(len(mapping) == len(claims) == len(all_names)
         and len(mapping) >= len(stage_receipt.get("staged_source_slides", [])),
         "Original WAV coverage/receipts incomplete")
    return {
        "source_sha256": plan["source_sha256"],
        "slides_sha256": plan["slides_sha256"],
        "plan_sha256": plan_hash,
        "part_count": len(parts),
        "audio_elements": len(mapping),
        "voice_id": plan["voice_id"],
        "bindings": mapping,
    }


def recover(*, source: Path, slides: Path, authored: Path,
            frozen: Path, synthesis_receipt: Path,
            destination: Path) -> dict:
    """Create a new full review bundle; originals are never written/replaced."""
    originals = [Path(x) for x in
                 (source,slides,authored,frozen,synthesis_receipt)]
    destination = Path(destination).absolute()
    need(not destination.exists() and not destination.is_symlink()
         and destination.parent.is_dir() and not destination.parent.is_symlink(),
         "Recovery destination must be a new isolated folder")
    dest_resolved = destination.resolve(strict=False)
    for path in originals:
        original = path.resolve(strict=True)
        boundary = original if original.is_dir() else original.parent
        need(not _within(dest_resolved, boundary)
             and not _within(boundary, dest_resolved),
             "Recovered review must not contain or overwrite preserved sources")
    state = preflight(source=source, slides=slides, authored=authored,
                      frozen=frozen, synthesis_receipt=synthesis_receipt)
    # Important: create NO output until source/review WAV hashes all pass.
    destination.mkdir()
    staged = destination / "staged"
    rendered = destination / "rendered"
    audio = destination / "frozen_original_element_audio"
    shutil.copytree(frozen, staged)
    audio.mkdir()
    for name, preserved, expected in state["bindings"]:
        with (audio / name).open("xb") as out, preserved.open("rb") as source_wav:
            shutil.copyfileobj(source_wav, out)
        need(file_sha(audio/name) == expected,
             f"Recovered element WAV corrupted during copy: {name}")
    # The copied stages, original slides/source and newly recovered WAVs
    # must pass existing independent authored-plan preflight.
    checked = source_bound_plan(source=source, slides=slides,
                                plan=authored, audio=audio)
    need(checked["elements"] == state["audio_elements"],
         "Recovered audio no longer covers the authored elements")
    render_review_series(source_pdf=source, inputs_root=staged,
                         output_root=rendered)
    result = audit_existing(source=source,slides=slides,authored=authored,
                            audio=audio,review_root=destination)
    need(result["covered_elements"] == state["audio_elements"]
         and len(result["parts"]) == state["part_count"],
         "Recovery did not verify all original narrated elements")
    result["status"] = "ISOLATED_REBUILT_MEDIA_TECHNICALLY_CHECKED_ONLY"
    result["origin_is_freshly_rebuilt_not_archived_mp4"] = True
    result["archive_mp4s_independently_redecoded"] = False
    result["real_tts_audio_transcription_verified"] = False
    result["academic_figure_review_approved"] = False
    result["student_published"] = False
    result["production_approved"] = False
    receipt = destination / "recovered_review_technical_result.json"
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("source","slides","authored","frozen",
                "synthesis-receipt","destination"):
        parser.add_argument("--"+key,required=True,type=Path)
    args=parser.parse_args(argv)
    result=recover(source=args.source,slides=args.slides,
                   authored=args.authored,frozen=args.frozen,
                   synthesis_receipt=args.synthesis_receipt,
                   destination=args.destination)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
