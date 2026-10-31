"""Read-only combined acceptance of source correspondence, timing and encoded video.

Never infer synchronization from whole-slide WAV QA or preview frames.
Every section must independently pass all three original-media checks.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .visual_element_mapping_readiness import inspect_all
from .true_sync_video_acceptance_audit import inspect as inspect_sync
from .figure_source_identity import require, _sha

SECTIONS = ("8.4", "8.5", "8.6")

def inspect_three_sections(*, root: Path) -> dict:
    root = Path(root).absolute()
    rows = []
    for section in SECTIONS:
        folder = root / section
        files = [folder / name for name in ("source.pdf", "slides.pdf", "script.txt")]
        require(all(p.is_file() and not p.is_symlink() for p in files),
                f"Missing immutable original inputs: {section}")
        original = [_sha(p) for p in files]
        source_report = inspect_all(source=files[0], slides=files[1], script=files[2])
        sync = inspect_sync(folder=folder)
        require(
            [source_report[k] for k in ("source_sha256", "slides_sha256", "script_sha256")] == original
            and [sync[k] for k in ("source_sha256", "slides_sha256", "script_sha256")] == original,
            f"Original source and independent acceptance reports differ: {section}",
        )
        # All three are independently required. A slide WAV is not a word or
        # per-element sample, and a rendered review MP4 is not a timed proof.
        correspondence = bool(source_report.get("automatic_video_approved", False))
        timing = bool(sync.get("complete_verified_source_element_wav_receipts_found", False)
                      and sync.get("real_spoken_element_audio_semantics_verified", False))
        video = bool(sync.get("all_visual_elements_highlighted_as_spoken_verified", False)
                     and sync.get("final_true_sync_production_encoded", False)
                     and sync.get("all_staged_preview_parts_strictly_under_600", False))
        require([_sha(p) for p in files] == original, "Original media mutated during inspection")
        rows.append({
            "section": section, "original_sha256": dict(zip(
                ("source_pdf", "slides_pdf", "script"), original)),
            "slide_count": source_report["slide_count"],
            "whole_slide_wav_count": sync["original_slide_wav_count"],
            "source_correspondence_accepted": correspondence,
            "per_element_narration_timing_accepted": timing,
            "final_encoded_video_accepted": video,
            "blockers": [
                label for label, passed in (
                    ("ORIGINAL_ELEMENT_SEMANTIC_CORRESPONDENCE_UNVERIFIED", correspondence),
                    ("PER_ELEMENT_AUDIO_TIMING_UNVERIFIED", timing),
                    ("ENCODED_SYNCHRONIZED_VIDEO_UNVERIFIED", video),
                ) if not passed
            ],
            "section_pass": all((correspondence, timing, video)),
        })
    return {
        "schema_version": 1,
        "status": "FULL_PRODUCTION_ACCEPTED" if all(r["section_pass"] for r in rows)
                  else "FAIL_CLOSED_INCOMPLETE_SOURCE_AUDIO_VIDEO_ACCEPTANCE",
        "slides_checked": sum(r["slide_count"] for r in rows),
        "section_count": len(rows), "sections": rows,
        "all_three_stages_pass": all(r["section_pass"] for r in rows),
        "student_publication_authorized": False,
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    a = parser.parse_args(argv)
    out = a.out.absolute()
    require(out.parent.is_dir() and not out.exists() and not out.is_symlink()
            and not out.is_relative_to(a.root.absolute()),
            "New external output sidecar mandatory; never overwrite original media")
    report = inspect_three_sections(root=a.root)
    with out.open("x", encoding="utf8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"status": report["status"], "slides_checked": report["slides_checked"],
                      "all_three_stages_pass": report["all_three_stages_pass"]}))
    return 0 if report["all_three_stages_pass"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
