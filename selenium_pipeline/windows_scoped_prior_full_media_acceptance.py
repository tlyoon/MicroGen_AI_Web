"""Reuse one previously ACCEPTED original-source full lesson by exact SHA.

No retesting mathematics, listening, decoding old MP4s, regenerating slides,
repeating paid Gemini TTS or making source-dependent false approvals.
Only exact trusted receipt/physical SHA is accepted; old proof is not a
substitute for a SECOND independent original-source end-to-end acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .evidence_reuse_contract import file_sha256


class HistoricalScopeMismatch(ValueError):
    pass


# Owner's exact historical 2026-10-29 PR362 three-check source/media receipt.
# Trust is PINNED here, not self-declared by arbitrary input JSON.
_PR362 = {
    "qa_sha256": "c092169bf945f5aba10c62e55ebea7c02994b33081d0a5cdca983d48756643df",
    "source_sha256": "b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068",
    "slides_sha256": "6f9842512c2b12441eff58725b190f34db9fbea29d6eb302080ed78d3ad508da",
    "movie_sha256": [
        "f91cebc44a84767864e5f52a46ae2fb5ebbf4e536434a25a6a79d4ca0a37b5af",
        "0a5221f85f235afa5bc911fa0d63ca57e10f04c3351de5a6ec22fb422fce62e9",
    ],
}
_STATUS = "THOMAS84_ALL_THREE_QA_CHECKS_COMPLETED_SOURCE_MATH_PHONETIC_MEDIA_PASS_REVIEW_ONLY"


def _must(cond: bool, message: str) -> None:
    if not cond:
        raise HistoricalScopeMismatch(message)


def sources_at_checkpoint(checkpoint_root: Path) -> dict[str, Path | list[Path]]:
    root = Path(checkpoint_root).absolute()
    accepted = root / "20261029_PR361D_SLIDE8_SLIDE17_BOTH_SOURCE_MATH_CORRECTED_FULL_REAL_MP4S"
    return {
        "qa": root / "20261029_PR362_COMPLETE_66_SOURCE_MATH_TTS_VIDEO_COMBINED_QA.json",
        "source": root / "20261029_WINDOWS_E2E_RELEASE_TEST" / "Thomas_calculus_13ed" / "8" / "8.4" / "source.pdf",
        "slides": root / "20261029_PR361_SIGNED_TRIANGLE_SOURCE_PDF_SCRIPT_CORRECTED_NO_AUDIO" / "slides.pdf",
        "movies": [
            accepted / "part_01" / "Thomas_8_4_part01_SIGNED_TRIANGLE_SOURCE_KORE_CORRECTED_REVIEW_ONLY.mp4",
            accepted / "part_02_OriginalSource_Slide17_MATH_CORRECTED_REVIEW_ONLY.mp4",
        ],
    }


def verify_scoped(*, qa: Path, source: Path, slides: Path, movies: list[Path],
                  anchor: dict | None = None) -> dict:
    if os.name != "nt":
        raise HistoricalScopeMismatch("Only authorized Windows evidence re-use")
    anchor = dict(_PR362) if anchor is None else anchor
    paths = [Path(x).absolute() for x in (qa, source, slides, *movies)]
    _must(len(movies) == 2 and len({str(p) for p in paths}) == 5,
          "Exact one publisher source, corrected PDF, QA, two distinct MP4s required")
    _must(all(p.is_file() and not p.is_symlink() and p.stat().st_size > 100
              for p in paths), "Missing or symlinked original accepted evidence")
    hashes = [file_sha256(p) for p in paths]
    _must(hashes[0] == anchor["qa_sha256"]
          and hashes[1] == anchor["source_sha256"]
          and hashes[2] == anchor["slides_sha256"]
          and hashes[3:] == anchor["movie_sha256"],
          "Existing acceptance does not match exact historical frozen source/video SHA")
    try:
        record = json.loads(Path(qa).read_text(encoding="utf8"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise HistoricalScopeMismatch("Unreadable original accepted QA receipt") from exc
    _must(type(record) is dict and record.get("schema_version") == 1
          and record.get("status") == _STATUS,
          "Wrong historical original-source acceptance receipt")
    _must(record.get("original_textbook_sha256") == hashes[1]
          and record.get("corrected_actual_source_pdf_sha256") == hashes[2]
          and record.get("independently_audited_actual_final_movie_SHA256") == hashes[3:],
          "Historical source and final media receipts refer to different artifacts")
    required_true = (
        "all_actual_final_movies_under_600_s",
        "math_source_automated_review_criteria_satisfied",
        "owner_flexible_soundalike_TTS_criteria_satisfied",
        "source_visual_element_relevance_criteria_satisfied",
        "actual_H264_AAC_media_integrity_criteria_satisfied",
        "three_requested_QA_checks_completed",
        "release_candidate_QA_gate_pass",
        "strict_no_original_source_or_prior_movie_overwrite",
    )
    _must(record.get("all_66_original_narration_meanings_referenced_to_actual_PDF") == 66
          and all(record.get(k) is True for k in required_true)
          and record.get("publication_was_performed") is False
          and record.get("student_publication_authorized") is False,
          "Full historically accepted QA contract changed or publication claimed")
    durations = record.get("real_complete_movies_seconds")
    _must(isinstance(durations, list) and len(durations) == 2
          and all(type(x) in (float, int) and 0 < x < 600 for x in durations),
          "Accepted two-part original media durations invalid")
    return {
        "schema_version": 1,
        "status": "ONE_SCOPED_HISTORICAL_ORIGINAL_FULL_MEDIA_ACCEPTANCE_REUSED",
        "accepted_scoped_original_source_count": 1,
        "source_scope": "Thomas calculus chapter 8 section 8.4, PR362 QA 2026-10-29",
        "source_sha256": hashes[1],
        "corrected_slides_sha256": hashes[2],
        "two_full_mp4_sha256": hashes[3:],
        "historical_mp4_seconds": durations,
        "historical_accepted_narration_source_elements": 66,
        "historical_frame_checks_reused_no_new_frames_processed": 104,
        "new_synthesis_or_media_generation": False,
        "new_independent_second_source_accepted": False,
        "independent_human_aural_voice_identity_certified":
            record.get("independent_human_aural_voice_identity_certified") is True,
        "student_publication_authorized": False,
        "not_a_new_automated_pipeline_generation": True,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint-root", type=Path,
                   default=Path(os.getenv("LOCALAPPDATA", "")) /
                           "MicroGen_AI_Web_Checkpoints")
    a = p.parse_args(argv)
    try:
        result = verify_scoped(**sources_at_checkpoint(a.checkpoint_root))
    except (HistoricalScopeMismatch, KeyError, OSError) as exc:
        print(json.dumps({"status": "ORIGINAL_HISTORICAL_QA_SCOPE_REJECTED",
                          "reason": str(exc),
                          "student_publication_authorized": False}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
