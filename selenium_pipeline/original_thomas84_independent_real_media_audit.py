"""Independently re-audit actual PR333 Thomas 8.4 review media, fail closed.

A source-preserving, Windows-only diagnostic that checks the physically saved
MP4s, H264/AAC stream durations, individual clips, frame PNGs and provenance.
It NEVER upgrades a provisional lexical highlight to semantic acceptance and
NEVER writes student release receipts.  No paid service or network is needed.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .production_video_contract import _hash, _mp4_duration, VideoContractError

REVIEW_STATUS = "TWO_REAL_ORIGINAL_8_4_VIDEOS_FOUR_MORE_ACOUSTIC_PDF_HIGHLIGHTS_REVIEW_ONLY"
REVIEWED_SLIDE_SPANS = ((1, 8), (9, 17))
PROVISIONAL_SLIDES = (5, 6, 15, 17)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise VideoContractError(reason)


def _within_untrusted_bundle(value: object, root: Path) -> Path:
    require(isinstance(value, str) and value.strip(), "Missing real local artifact path")
    target = Path(value)
    require(target.is_absolute() and target.resolve().is_relative_to(root.resolve())
            and target.is_file() and not target.is_symlink(),
            "Video review artifact missing, symlinked or outside saved review directory")
    return target


def _equal_sha(path: Path, digest: object) -> None:
    require(isinstance(digest, str) and len(digest) == 64
            and all(c in "0123456789abcdef" for c in digest),
            "Malformed saved SHA256 receipt")
    require(_hash(path) == digest, f"Saved media hash mismatch: {path.name}")


def inspect_real_thomas84_review(*, receipt: Path, original: Path | None = None,
                                 timing_receipt: Path | None = None,
                                 probe=None) -> dict:
    """Check real files afresh, return diagnostic coverage, never release approval.

    `probe` is ONLY for deterministic unit tests; normal command execution
    independently probes actual container durations using FFmpeg.
    """
    receipt = Path(receipt).absolute()
    require(receipt.is_file() and not receipt.is_symlink(),
            "Missing immutable real-render receipt")
    data = json.loads(receipt.read_text(encoding="utf8"))
    require(type(data) is dict and data.get("schema_version") == 1
            and data.get("status") == REVIEW_STATUS,
            "Unrecognized or forged real-render review receipt")
    for flag in ("student_publication_authorized",
                 "academic_source_mathematics_two_pass_approved",
                 "all_remaining_original_source_elements_speech_synced"):
        require(data.get(flag) is False, f"Review-only report falsely approves {flag}")
    require(data.get("student_accepted_complete_video_parts") == 0
            and data.get("four_measured_asr_word_timed_original_PDF_highlights") == 4
            and data.get("five_corrected_slide4_actual_PCM_source_highlights") == 5
            and data.get("original_PDFs_WAVs_and_MP4s_unchanged") is True
            and data.get("whisper_used") is False,
            "Cannot reclassify historical/partial media as release accepted")
    if original is not None:
        orig = Path(original)
        for name, digest in data["protected_original_hashes"].items():
            _equal_sha(orig / name, digest)
        require(data["protected_original_hashes"]["source.pdf"] ==
                data.get("original_source_sha256"),
                "Original PDF SHA is not the saved PDF identity")
    if timing_receipt is not None:
        _equal_sha(Path(timing_receipt), data.get("timing_receipt_sha256"))
    parts = data.get("real_parts")
    require(type(parts) is list and len(parts) == 2, "Exactly two actual original videos required")
    video_results = []
    visual_targets = set()
    slides_seen = set()
    all_units = 0
    clip_count = 0
    for i, part in enumerate(parts):
        require(type(part) is dict and part.get("part_id") == f"part_{i+1:02d}"
                and part.get("original_slide_span") == list(REVIEWED_SLIDE_SPANS[i]),
                "Unexpected original slide partition")
        require(part.get("student_publication_authorized") is False
                and part.get("complete_element_synchronization_approved") is False,
                "Non-final original media misrepresented as complete")
        movie = _within_untrusted_bundle(part.get("actual_h264_aac_mp4"), receipt.parent)
        require(movie.stat().st_size == part.get("actual_MP4_bytes"), "MP4 byte count changed")
        _equal_sha(movie, part.get("actual_MP4_sha256"))
        seconds = (probe or _mp4_duration)(movie)
        require(type(seconds) in (float, int) and math.isfinite(seconds)
                and 0 < seconds < 600 and
                abs(seconds - part.get("actual_encoded_MP4_duration_s", -1)) <= .08
                and part.get("strictly_less_than_ten_minutes") is True,
                "Independently measured encoded MP4 is stale/overlong/nonfinite")
        units = part.get("all_source_visual_audio_units")
        require(type(units) is list and len(units) >= 8, "Missing real encoded segment inventory")
        slides_in_part = []
        for item in units:
            require(type(item) is dict and item.get("semantic_sync_approved") is False,
                    "Unapproved audio/visual candidate mislabeled as accepted")
            slide = item.get("source_slide")
            require(type(slide) is int and
                    REVIEWED_SLIDE_SPANS[i][0] <= slide <= REVIEWED_SLIDE_SPANS[i][1],
                    "Segment source slide outside original partition")
            slides_in_part.append(slide)
            target = item.get("candidate_target_id")
            if target is not None:
                require(type(target) is str and target, "Empty PDF element target")
                visual_targets.add((slide, target))
            clip = _within_untrusted_bundle(item.get("clip_file"), receipt.parent)
            png = _within_untrusted_bundle(item.get("image_file"), receipt.parent)
            _equal_sha(clip, item.get("actual_encoded_mp4_sha256"))
            _equal_sha(png, item.get("candidate_visual_frame_sha256"))
            clip_count += 1
        require(slides_in_part == sorted(slides_in_part) and
                set(slides_in_part) == set(range(REVIEWED_SLIDE_SPANS[i][0],
                                                REVIEWED_SLIDE_SPANS[i][1]+1)),
                "Not all original slides are represented in sequence")
        slides_seen.update(slides_in_part)
        all_units += len(units)
        video_results.append({"part":part["part_id"], "duration_s":round(seconds, 3),
                              "sha256":part["actual_MP4_sha256"],
                              "actual_segments_checked":len(units)})
    require(slides_seen == set(range(1,18)) and len(visual_targets) == 9,
            "Original 17-slide coverage or nine PDF candidates changed")
    require({s for s, _ in visual_targets} == {4, *PROVISIONAL_SLIDES},
            "Incorrect set of highlighted original PDF slides")
    proofs = data.get("four_lossless_original_PCM_sample_split_proofs")
    require(type(proofs) is list and {p.get("slide") for p in proofs} ==
            set(PROVISIONAL_SLIDES) and all(p.get("all_samples_recombined_losslessly")
                                            is True for p in proofs),
            "Four real PCM split proofs missing or incomplete")
    return {
        "status": "REAL_MEDIA_REVERIFIED_RELEASE_BLOCKED",
        "video_parts": video_results,
        "real_video_and_audio_clips_hashed": clip_count,
        "distinct_pdf_highlight_candidates": 9,
        "original_slides_covered": 17,
        "historic_slides_still_without_full_semantic_element_sync": 16,
        "static_or_only_partially_highlighted_slides": list(range(1,18)),
        "source_semantics_approved": False,
        "student_publication_authorized": False,
        "next_work": "Certify true speech-to-visible-element mapping for sixteen historical WAV slides and independently review source mathematics before regenerating release media",
    }


def main(argv=None) -> None:
    cmd = argparse.ArgumentParser(description=__doc__)
    cmd.add_argument("--receipt", required=True, type=Path)
    cmd.add_argument("--original", type=Path)
    cmd.add_argument("--timing-receipt", type=Path)
    ns = cmd.parse_args(argv)
    print(json.dumps(inspect_real_thomas84_review(
        receipt=ns.receipt, original=ns.original,
        timing_receipt=ns.timing_receipt), indent=2))


if __name__ == "__main__":
    main()
