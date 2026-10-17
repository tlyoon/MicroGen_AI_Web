"""No-network compatibility audit: slide-level reviewed audio vs element-highlight plan.

This is a READ-ONLY CHECK, never a converter, audio approval or MP4 publisher.
A single slide WAV cannot be silently split into multiple spoken elements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .element_highlight_workflow import source_bound_plan
from .runner import blocks
from .tts_pcm_contract import verify_pcm, TTSPCMContractError
from .tts_effective_identity import (
    verify_effective_identity, TTSEffectiveIdentityError,
)
from .tts_attempt_evidence import AttemptEvidence, TTSAttemptEvidenceError


class ElementAudioIncompatible(ValueError):
    pass


def required(ok: bool, why: str) -> None:
    if not ok:
        raise ElementAudioIncompatible(why)


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check(*, source_pdf: Path, slides_pdf: Path,
          authored_plan: Path, reviewed_audio: Path) -> dict:
    raw_paths = tuple(Path(p) for p in (source_pdf, slides_pdf, authored_plan, reviewed_audio))
    required(not any(p.is_symlink() for p in raw_paths),
             "No symlinked source, slides, plan or reviewed-audio root permitted")
    source, slides, plan, audio = (p.resolve() for p in raw_paths)
    required(all(p.is_file() and not p.is_symlink() for p in (source, slides, plan))
             and audio.is_dir() and not audio.is_symlink(), "Missing source/slides/plan/audio")
    names = ("tts_reviewed_handoff.json", "script.txt", "tts_input_manifest.json")
    required(all((audio/n).is_file() and not (audio/n).is_symlink() for n in names),
             "Only an independently reviewed isolated audio handoff is permitted")
    try:
        handoff = json.loads((audio/names[0]).read_text(encoding="utf-8"))
        manifest = json.loads((audio/names[2]).read_text(encoding="utf-8"))
        scene = json.loads(plan.read_text(encoding="utf-8"))
        items = blocks((audio/names[1]).read_text(encoding="utf-8"))
        rows = manifest["slides"]
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        raise ElementAudioIncompatible("Invalid handoff, narration or scene JSON") from exc
    required(isinstance(handoff, dict) and isinstance(manifest, dict)
             and isinstance(scene, dict),
             "Handoff, manifest and plan must be JSON objects")
    required(handoff.get("status") == "AUDIO_REVIEWED_ISOLATED_COPY"
             and handoff.get("human_review_approved") is True
             and handoff.get("video_publication_approved") is False
             and handoff.get("destination") == str(audio)
             and handoff.get("source") == str(source.parent),
             "Audio review approval/provenance is not source-bound")
    try:
        actual = verify_effective_identity(manifest, items)
    except TTSEffectiveIdentityError as exc:
        raise ElementAudioIncompatible(str(exc)) from exc
    if actual["fallback_used"]:
        try:
            AttemptEvidence.verify_saved(
                audio, items, manifest.get("attempt_evidence"))
        except TTSAttemptEvidenceError as exc:
            raise ElementAudioIncompatible(
                f"Unverified original Gemini retry-attempt evidence: {exc}") from exc
        required(
            handoff.get("attempt_evidence_sha256") ==
                manifest["attempt_evidence"]["sha256"],
            "Reviewed handoff lacks bound observed retry-attempt digest")
    required(
        handoff.get("provider") == actual["provider"]
        and handoff.get("tts_model") == actual["model"]
        and handoff.get("voice") == actual["voice"]
        and (not actual["fallback_used"] or (
            handoff.get("fallback_chain") == actual["fallback_chain"]
            and handoff.get("requested_primary") == actual["requested_primary"]
            and handoff.get("fallback_used") is True
        )),
        "Audio review approval/provenance is not source-bound (effective model/voice mismatch)")
    required(handoff.get("source_script_sha256") == digest(audio/"script.txt")
             and handoff.get("source_manifest_sha256") == digest(audio/"tts_input_manifest.json"),
             "Reviewed audio script/manifest changed")
    expected_hashes = handoff.get("candidate_wav_sha256")
    required(isinstance(expected_hashes, dict) and len(items) == len(expected_hashes)
             and len({n for n, _ in items}) == len(items)
             and {f"slide{n}.wav" for n, _ in items} == set(expected_hashes),
             "Reviewed audio slide/WAV coverage mismatch")
    required(isinstance(rows, list) and len(rows) == len(items),
             "Manifest is missing or repeating slide audio")
    row_by_number = {}
    for row in rows:
        required(isinstance(row, dict) and type(row.get("slide")) is int,
                 "Malformed manifest slide")
        required(row["slide"] not in row_by_number, "Duplicate manifest slide")
        row_by_number[row["slide"]] = row
    for n, spoken in items:
        entry = row_by_number.get(n)
        required(isinstance(entry, dict)
                 and entry.get("source_text") == spoken
                 and entry.get("tts_text") == spoken
                 and entry.get("provider") == actual["provider"]
                 and entry.get("model") == actual["model"]
                 and entry.get("voice") == actual["voice"]
                 and entry.get("fallback_used") is actual["fallback_used"],
                 f"Manifest narration is not bound to slide {n}")
        wav = audio/f"slide{n}.wav"
        required(wav.is_file() and not wav.is_symlink()
                 and digest(wav) == expected_hashes[f"slide{n}.wav"],
                 f"Audio SHA mismatch for slide {n}")
        try:
            verify_pcm(wav.read_bytes(), label=f"slide{n}.wav")
        except TTSPCMContractError as exc:
            raise ElementAudioIncompatible(str(exc)) from exc
    required(scene.get("schema_version") == 1
             and scene.get("status") == "author_specified_unapproved_element_narration"
             and scene.get("source_sha256") == digest(source)
             and scene.get("slides_sha256") == digest(slides)
             and isinstance(scene.get("voice_id"), str)
             and actual["model"] in scene["voice_id"]
             and actual["voice"] in scene["voice_id"],
             "Element plan does not refer to the same source/model/voice")
    parts = scene.get("parts")
    required(isinstance(parts, list) and bool(parts), "No scene parts")
    by_slide = dict(items)
    covered = []
    for part in parts:
        required(isinstance(part, dict) and isinstance(part.get("slides"), list),
                 "Malformed scene part")
        for entry in part["slides"]:
            required(isinstance(entry, dict) and type(entry.get("slide")) is int,
                     "Malformed scene slide")
            n = entry["slide"]
            covered.append(n)
            elements = entry.get("elements")
            required(isinstance(elements, list) and len(elements) == 1,
                     "A slide-level WAV is NOT sufficient for multiple narrated "
                     "highlight elements; separate source-bound per-element "
                     "recordings and listening review are required")
            el = elements[0]
            required(n in by_slide and isinstance(el, dict)
                     and el.get("wav") == f"slide{n}.wav"
                     and el.get("spoken_text") == by_slide[n],
                     "Slide-level narration cannot be equated to authored element speech")
    required(covered == [n for n, _ in items],
             "Element plan does not cover every reviewed slide in order")
    # Preserve the existing physical timing and source-hash contract in the
    # normal renderer preflight; this is *not* scientific element approval.
    plan_check = source_bound_plan(
        source=source, slides=slides, plan=plan, audio=audio)
    return {
        "status": "REVIEW_ONLY_AUDIO_ELEMENT_COMPATIBILITY",
        "source_sha256": digest(source),
        "slides_sha256": digest(slides),
        "audio_handoff_sha256": digest(audio/names[0]),
        "matched_slide_elements": len(covered),
        "parts": plan_check["parts"],
        "human_audio_review_claimed": True,
        "effective_provider": actual["provider"],
        "effective_model": actual["model"],
        "effective_voice": actual["voice"],
        "fallback_chain": actual["fallback_chain"],
        "scientific_element_mapping_approved": False,
        "student_published": False,
        "production_approved": False,
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="Read-only compatibility of reviewed slide WAVs and element highlights")
    for key in ("source-pdf","slides-pdf","authored-plan","reviewed-audio"):
        p.add_argument("--"+key, type=Path, required=True)
    a=p.parse_args(argv)
    print(json.dumps(check(source_pdf=a.source_pdf,slides_pdf=a.slides_pdf,
                           authored_plan=a.authored_plan,
                           reviewed_audio=a.reviewed_audio),indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
