"""Fail-closed, evidence-locked handoff from REVIEW_ONLY media to an isolated candidate.

This is a *candidate handoff*, not the production receipt generator. It never
creates lecture_completion.json, academic approval, Moodle publication or
automatic student permission. No cloud calls or TTS synthesis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from .element_highlight_workflow import read, verify_rendered


class CandidateHandoffError(ValueError):
    """Source, encoded media, or independent human acceptance is incomplete."""


REVIEW_FLAGS = (
    "mathematics_and_source_approved",
    "complete_figures_and_panels_approved",
    "all_original_element_wavs_listened_and_approved",
    "semantic_spoken_highlight_mapping_approved",
    "uniform_tts_voice_listening_approved",
)


def required(ok: bool, reason: str) -> None:
    if not ok:
        raise CandidateHandoffError(reason)


def sha(path: Path) -> str:
    required(path.is_file() and not path.is_symlink(),
             f"Required immutable candidate asset missing: {path}")
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"),
                   allow_nan=False, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _paths(*, source: Path, slides: Path, authored: Path,
           audio: Path, review_root: Path) -> tuple[Path, ...]:
    original = tuple(Path(x).absolute()
                     for x in (source, slides, authored, audio, review_root))
    required(all(not x.is_symlink() for x in original),
             "No symlinked source/slide/audio/review roots allowed")
    source, slides, authored, audio, review = (x.resolve() for x in original)
    required(all(x.is_file() for x in (source, slides, authored)),
             "Original source, slides and authored element plan required")
    required(audio.is_dir() and review.is_dir(),
             "Original WAVs and technical review directory required")
    required(not review.is_relative_to(source.parent)
             and not review.is_relative_to(audio)
             and not audio.is_relative_to(review),
             "Original and review trees must remain independent")
    return source, slides, authored, audio, review


def inspect_candidate(*, source: Path, slides: Path, authored: Path,
                      audio: Path, review_root: Path) -> dict:
    """Fresh independent decoded-pixel check and immutable content fingerprint.

    Fingerprints are based on file contents, never source machine absolute
    paths. This function neither produces an approval nor writes any files.
    """
    source, slides, authored, audio, root = _paths(
        source=source, slides=slides, authored=authored,
        audio=audio, review_root=review_root)
    technical = verify_rendered(
        source=source, slides=slides, authored=authored, audio=audio,
        staged=root/"staged", rendered=root/"rendered",
        output=None, recheck_pixels=True)
    required(technical.get("status")
             == "COMPLETE_ELEMENT_HIGHLIGHT_TECHNICAL_REVIEW_ONLY"
             and technical.get("production_approved") is False
             and technical.get("student_published") is False
             and technical.get("human_listening_approved") is False,
             "Only unapproved, freshly verified technical review video may be staged")
    plan = read(authored)
    staged = root/"staged"
    rendered = root/"rendered"
    receipt = root/"highlight_technical_review.json"
    required(receipt.is_file() and not receipt.is_symlink(),
             "Original, unapproved technical review receipt missing")
    saved = read(receipt)
    required(saved == technical, "Saved review report is stale or differs from fresh verification")
    parts = plan["parts"]
    files = {
        "source.pdf": sha(source),
        "slides.pdf": sha(slides),
        "authored_element_plan.json": sha(authored),
        "highlight_technical_review.json": sha(receipt),
        "staged/element_stage_receipt.json": sha(staged/"element_stage_receipt.json"),
        "staged/series_inputs.json": sha(staged/"series_inputs.json"),
        "rendered/series_review_receipt.json": sha(rendered/"series_review_receipt.json"),
    }
    seen_original_names = set()
    declared_voices = set()
    media = []
    for i, part in enumerate(parts, 1):
        part_id = f"part_{i:02d}"
        required(part.get("part_id") == part_id,
                 "Non-contiguous or reordered element audio parts")
        stage = staged/part_id
        target = rendered/part_id
        tts = read(stage/"tts_chunks.json")
        board = read(stage/"storyboard.json")
        required(len(tts.get("segments", []))
                 == len(board.get("narration_segments", [])),
                 "TTS and narrated element counts do not match")
        for chunk in tts["segments"]:
            declared_voices.add(chunk.get("voice_id"))
        media.append({
            "part_id": part_id,
            "review_mp4_sha256": sha(target/f"{part_id}_review.mp4"),
            "combined_wav_sha256": sha(target/"narration.wav"),
            "encoded_pixel_qa_sha256": sha(target/"encoded_pixel_qa.json"),
            "review_receipt_sha256": sha(target/"review_receipt.json"),
        })
        # Freeze every byte required to re-run source/geometry/timing and
        # decoded-pixel checks INSIDE the isolated handoff, not merely a
        # summary whose scratch reference frames are missing.
        for relative in ("storyboard.json", "tts_chunks.json", "instrumented.pdf"):
            files[f"staged/{part_id}/{relative}"] = sha(stage/relative)
        for index, chunk in enumerate(tts["segments"], 1):
            required(chunk.get("filename") == f"n{index}.wav",
                     "Noncontiguous staged element WAV identity")
            files[f"staged/{part_id}/wav/n{index}.wav"] = sha(stage/"wav"/f"n{index}.wav")
        for relative in ("element_geometry.json", "narration_timeline.json",
                         "encoded_pixel_qa.json", "review_receipt.json",
                         "clean_slides.pdf", "clean_pdf_receipt.json",
                         "wave_timing_receipt.json"):
            files[f"rendered/{part_id}/{relative}"] = sha(target/relative)
        for index in range(1, len(board["slides"])+1):
            filename=f"base_{index:04d}.png"
            files[f"rendered/{part_id}/scratch_frames/{filename}"] = sha(
                target/"scratch_frames"/filename)
        for index in range(1, len(board["narration_segments"])+1):
            filename=f"event_{index:04d}.png"
            files[f"rendered/{part_id}/scratch_frames/{filename}"] = sha(
                target/"scratch_frames"/filename)
        files[f"rendered/{part_id}/{part_id}_review.mp4"] = media[-1]["review_mp4_sha256"]
        files[f"rendered/{part_id}/narration.wav"] = media[-1]["combined_wav_sha256"]
        for slide in part["slides"]:
            for element in slide["elements"]:
                name = element["wav"]
                required(name not in seen_original_names
                         and name == Path(name).name and name.endswith(".wav"),
                         "Repeated or unsafe original element WAV")
                seen_original_names.add(name)
                files[f"frozen_audio/{name}"] = sha(audio/name)
    required(len(declared_voices) == 1
             and next(iter(declared_voices)) == plan.get("voice_id"),
             "Mixed or stale declared TTS voice across multipart recordings")
    # A declaration is not independent provider authentication or actual
    # listening. The human must review real audio; release gate stays closed.
    evidence = {
        "schema_version": 1,
        "status": "review_only_frozen_candidate_evidence",
        "source_sha256": files["source.pdf"],
        "slides_sha256": files["slides.pdf"],
        "authored_plan_sha256": files["authored_element_plan.json"],
        "declared_voice_id": plan["voice_id"],
        "voice_origin_independently_verified": False,
        "covered_slides": technical["covered_slides"],
        "covered_elements": technical["covered_elements"],
        "parts": media,
        "files": files,
        "production_approved": False,
        "student_published": False,
    }
    return {
        "status": "TECHNICALLY_VERIFIED_CANDIDATE_AWAITING_HUMAN_REVIEW",
        "candidate_sha256": canonical(evidence),
        "evidence": evidence,
        "human_approval_verified": False,
        "production_approved": False,
        "student_published": False,
    }


def check_human_review(candidate: dict, approval_path: Path, *,
                       source: Path, audio: Path, review_root: Path) -> dict:
    """Validate *independently authored* human evidence, never create it."""
    raw = Path(approval_path).absolute()
    required(not raw.is_symlink(), "No symlinked academic approvals")
    approval_file = raw.resolve()
    roots = (Path(source).resolve().parent,
             Path(audio).resolve(), Path(review_root).resolve())
    required(all(not approval_file.is_relative_to(folder) for folder in roots),
             "Approval must be independently authored outside source, WAV and review folders")
    row = read(approval_file)
    required(row.get("schema_version") == 1
             and row.get("status") == "human_candidate_review_approved"
             and row.get("human_authored_explicit_approval") is True,
             "Missing explicit, separate human candidate approval")
    reviewer = row.get("reviewed_by")
    required(isinstance(reviewer, str) and len(reviewer.strip()) >= 3,
             "Actual human reviewer must be identified")
    moment = row.get("approved_at_utc")
    required(isinstance(moment, str) and moment.endswith("Z"),
             "Explicit UTC review time required")
    try:
        instant = datetime.fromisoformat(moment.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CandidateHandoffError("Invalid human approval timestamp") from exc
    required(instant.utcoffset().total_seconds() == 0,
             "Review timestamp is not UTC")
    required(row.get("candidate_sha256") == candidate["candidate_sha256"]
             and row.get("source_sha256") == candidate["evidence"]["source_sha256"]
             and row.get("slides_sha256") == candidate["evidence"]["slides_sha256"],
             "Human approval does not bind the exact source-bound media fingerprint")
    for name in REVIEW_FLAGS:
        required(row.get(name) is True, f"Human approval missing: {name}")
    required(row.get("student_publication_permitted") is False,
             "Candidate review cannot itself authorize student publication")
    return {
        "status": "EXPLICIT_HUMAN_REVIEW_RECORDED_CANDIDATE_ONLY",
        "candidate_sha256": candidate["candidate_sha256"],
        "approval_sha256": sha(approval_file),
        "human_review_record_verified": True,
        "production_approved": False,
        "student_published": False,
    }


def stage_human_reviewed_candidate(*, source: Path, slides: Path,
                                  authored: Path, audio: Path, review_root: Path,
                                  approval: Path, destination: Path) -> dict:
    """Package reviewed media into a NEW isolated folder, never publish it.

    Every source and review byte is checked AGAINST the preflight fingerprint
    before and after a fresh exclusive copy. No student/production receipt.
    """
    source, slides, authored, audio, review = _paths(
        source=source, slides=slides, authored=authored,
        audio=audio, review_root=review_root)
    approval = Path(approval).absolute()
    dest = Path(destination).absolute()
    required(not dest.exists() and not dest.is_symlink()
             and dest.parent.is_dir() and not dest.parent.is_symlink(),
             "Candidate destination must be new, existing-parent, non-symlink directory")
    dest = dest.resolve()
    required(all(not dest.is_relative_to(p) and not p.is_relative_to(dest)
                 for p in (source.parent, audio, review, approval.parent)),
             "Candidate destination must be isolated from source, media and approval")
    expected = inspect_candidate(
        source=source, slides=slides, authored=authored,
        audio=audio, review_root=review)
    accepted = check_human_review(
        expected, approval, source=source, audio=audio, review_root=review)
    files = expected["evidence"]["files"]
    originals = {
        "source.pdf": source,
        "slides.pdf": slides,
        "authored_element_plan.json": authored,
    }
    origins = {}
    for relative in files:
        parts = Path(relative).parts
        required(".." not in parts and len(parts)>=1,
                 "Unsafe handoff manifest relative path")
        if relative in originals:
            origin = originals[relative]
        elif relative == "highlight_technical_review.json":
            origin = review/relative
        elif parts[0] in ("staged", "rendered"):
            origin = review/relative
        elif parts[0] == "frozen_audio" and len(parts) == 2:
            origin = audio/parts[1]
        else:
            raise CandidateHandoffError(f"Unexpected immutable source: {relative}")
        required(origin.resolve().is_relative_to(
            audio if parts[0] == "frozen_audio" else
            review if parts[0] in ("staged", "rendered") or relative == "highlight_technical_review.json"
            else origin.parent),
            "Candidate origin escapes its trusted evidence root")
        origins[relative] = origin
    # A change between the independent decoded-pixel QA and initial copy is
    # a hard stop. Atomic exclusive files prevent overwriting another packet.
    dest.mkdir()
    try:
        for relative, origin in sorted(origins.items()):
            required(sha(origin) == files[relative],
                     f"Candidate source changed before copy: {relative}")
            target = dest/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with origin.open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)
            required(sha(target) == files[relative],
                     f"Candidate copy hash differs: {relative}")
        with approval.open("rb") as src, (dest/"independent_human_review.json").open("xb") as dst:
            shutil.copyfileobj(src, dst)
        required(sha(dest/"independent_human_review.json") == accepted["approval_sha256"],
                 "Copied human review was changed")
        required(all(sha(origin) == files[name] for name, origin in origins.items()),
                 "Original media changed while creating candidate")
        # Prove the transferred, self-contained package can independently
        # repeat all source/audio/encoded-pixel checks, not just hash-match
        # copies of historic QA report files.
        imported=verify_rendered(
            source=dest/"source.pdf", slides=dest/"slides.pdf",
            authored=dest/"authored_element_plan.json",
            audio=dest/"frozen_audio",
            staged=dest/"staged", rendered=dest/"rendered",output=None,
            recheck_pixels=True)
        required(imported == read(dest/"highlight_technical_review.json"),
                 "Repacked candidate cannot reproduce fresh technical evidence")
        packet = {
            "schema_version": 1,
            "status": "HUMAN_REVIEWED_TECHNICAL_CANDIDATE_NOT_PUBLISHED",
            "candidate_sha256": expected["candidate_sha256"],
            "evidence": expected["evidence"],
            "independent_review_sha256": accepted["approval_sha256"],
            "technical_source_identity_verified": True,
            "human_review_record_verified": True,
            "voice_origin_independently_verified": False,
            "production_completion_receipt_created": False,
            "production_approved": False,
            "student_published": False,
        }
        with (dest/"candidate_handoff.json").open("x",encoding="utf-8") as out:
            json.dump(packet,out,sort_keys=True,indent=2,ensure_ascii=False)
        return packet
    except BaseException:
        # This directory was exclusively created by our invocation; no
        # pre-existing files or original lecture materials are affected.
        shutil.rmtree(dest,ignore_errors=True)
        raise


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Review-only candidate fingerprint or isolated handoff")
    for name in ("source","slides","authored","audio","review-root"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--approval",type=Path)
    p.add_argument("--destination",type=Path)
    a=p.parse_args(argv)
    args=dict(source=a.source,slides=a.slides,authored=a.authored,
              audio=a.audio,review_root=a.review_root)
    if bool(a.approval) != bool(a.destination):
        p.error("Independent --approval and fresh --destination must be supplied together")
    result=(stage_human_reviewed_candidate(**args,approval=a.approval,
                                         destination=a.destination)
            if a.approval else inspect_candidate(**args))
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
