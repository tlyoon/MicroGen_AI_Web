"""Recover the exact prior original Thomas QA corpus, without touching live lectures.

Only a full 41-slide pinned publisher/source/author version may be selected.
A valid sample/video QA witness does NOT establish full academic acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

from .figure_source_identity import require
from .original_three_section_academic_remaining_inventory import audit, EXPECTED
from .original_thomas85_86_first_math_highlights import SOURCE

ORIGINAL_PINS = {
    "8.4": ("b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068",
            "a25f48be4ad532bf21663dc55cdf4caac99c4b1d1e2fb235d439b0bd269dc03d"),
    "8.5": (SOURCE["8.5"]["publisher_sha"], SOURCE["8.5"]["slides_pdf_sha"]),
    "8.6": (SOURCE["8.6"]["publisher_sha"], SOURCE["8.6"]["slides_pdf_sha"]),
}
CANDIDATE_SUBDIRS = (Path("Thomas_calculus_13ed/8"), Path("WORK/8"), Path("."))


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_candidate(root: Path, *, pins=ORIGINAL_PINS,
                      counts=EXPECTED) -> tuple[dict | None, str]:
    """Inspect only; never repair a rejected candidate in place."""
    records = {}
    for section, count in counts.items():
        folder = root / section
        required = [folder / name for name in ("source.pdf", "slides.pdf",
                                               "slides.tex", "script.txt")]
        required += [folder / f"slide{i}.wav" for i in range(1, count + 1)]
        if (not folder.is_dir() or folder.is_symlink()
                or any(not p.is_file() or p.is_symlink() for p in required)):
            return None, f"{section}: missing or linked original input"
        source_sha, slides_sha = (hash_file(folder / "source.pdf"),
                                  hash_file(folder / "slides.pdf"))
        if (source_sha, slides_sha) != pins[section]:
            return None, f"{section}: publisher/author hash mismatch"
        source = (folder / "slides.tex").read_text(encoding="utf-8")
        actual = len(re.findall(r"\\begin\{frame\}", source))
        if actual != count:
            return None, f"{section}: original frames {actual}, expected {count}"
        # Full filenames are checked. File size 44 is only a minimal WAV sanity
        # check, not a guarantee of correct speech, timing or academic content.
        if any(p.stat().st_size <= 44 for p in required[4:]):
            return None, f"{section}: missing/nonphysical original WAV bytes"
        records[section] = {
            "source_pdf_sha256": source_sha,
            "slides_pdf_sha256": slides_sha,
            "authored_tex_sha256": hash_file(folder / "slides.tex"),
            "script_sha256": hash_file(folder / "script.txt"),
            "original_slide_count": count,
            "original_wav_sha256": {
                f"slide{i}.wav": hash_file(folder / f"slide{i}.wav")
                for i in range(1, count + 1)
            },
        }
    return records, "pinned source hashes, frames and files verified"


def resolve_original(search_roots: list[Path], *, pins=ORIGINAL_PINS,
                     counts=EXPECTED):
    attempted = []
    for search in search_roots:
        for rel in CANDIDATE_SUBDIRS:
            root = (Path(search) / rel).absolute()
            if not root.is_dir() or root.is_symlink():
                continue
            found, reason = inspect_candidate(root, pins=pins, counts=counts)
            attempted.append({"root": str(root), "result": reason})
            if found is not None:
                return root, found, attempted
    raise RuntimeError("PINNED_ORIGINAL_41_SOURCE_NOT_FOUND; all candidates "
                       "rejected, do not substitute regenerated live slides. "
                       + json.dumps(attempted, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-root", required=True, type=Path, action="append")
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--out-manifest", required=True, type=Path)
    parser.add_argument("--out-audit", required=True, type=Path)
    args = parser.parse_args(argv)
    manifest_path, audit_path = (args.out_manifest.absolute(),
                                 args.out_audit.absolute())
    require(manifest_path != audit_path and manifest_path.parent.is_dir()
            and audit_path.parent.is_dir() and not manifest_path.exists()
            and not audit_path.exists(), "Versioned output paths must be new")
    root, records, attempted = resolve_original(args.search_root)
    # Audit actual preserved corpus before writing any accepted inventory.
    result = audit(root=root, checkpoint=args.checkpoint)
    require(result["original_source_slides"] == 41
            and result["full_original_production_gate_passed"] is False
            and result["student_publication_authorized"] is False,
            "Recovered original source QA unexpectedly claims production")
    verified_again, reason = inspect_candidate(root)
    require(records == verified_again, "Recovered original corpus mutated during audit")
    manifest = {
        "status": "PINNED_ORIGINAL_41_SLIDE_SOURCE_RECOVERED_READ_ONLY_NONPRODUCTION",
        "original_source_root": str(root), "pinned_source_records": records,
        "candidate_search": attempted, "source_immutability_rechecked": True,
        "sampled_focus_witness_count": result["original_source_pixel_and_audio_math_focus_slides"],
        "slides_without_accepted_focus": result["original_slides_without_any_verified_focus"],
        "full_original_production_gate_passed": False,
        "student_publication_authorized": False,
        "live_regenerated_lectures_modified": False,
    }
    # Create-only output: never replace previously accepted QA or source files.
    with audit_path.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with manifest_path.open("x", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"status": manifest["status"], "root": str(root),
                      "slides": 41, "focus_samples": manifest["sampled_focus_witness_count"],
                      "production": False}))


if __name__ == "__main__":
    main()
