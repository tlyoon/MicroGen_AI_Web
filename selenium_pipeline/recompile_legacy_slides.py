"""Recompile *unfinished* legacy Beamer decks safely, without regenerating slides.

Default is a read-only dry run against the source tree. Both pdflatex passes
run in an isolated LOCAL workspace. Only with --apply, and only when no
downstream script/WAV/MP4/receipt exists, may the corrected PDF replace the old
one. The old PDF is archived first and can be restored.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .cleanup import _ensure_latex_graphics
from .latex_footer import enforce_correct_page_totals, incorrect_page_totals

ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".sty", ".eps", ".pdf"}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as inp:
        for chunk in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _nonfooter_text(page) -> str:
    # Compare every text block, excluding only counters at the page edge.
    words = []
    for block in page.get_text("blocks"):
        x0, y0, _x1, _y1, text = block[:5]
        if (x0 > page.rect.width * .70 and y0 < page.rect.height * .12
                and re.fullmatch(r"\s*\d+\s*/\s*\d+\s*", str(text).strip())):
            continue
        words.append(str(text).strip())
    return "\n".join(words)


def compare_slide_content(previous: Path, candidate: Path) -> int:
    """Reject recompiled PDFs changing any non-footer text or raster counts."""
    import pymupdf
    with pymupdf.open(previous) as old, pymupdf.open(candidate) as new:
        if len(old) != len(new):
            raise ValueError(f"Slide count drift after recompilation: {len(old)} to {len(new)}")
        for i in range(len(old)):
            if _nonfooter_text(old[i]) != _nonfooter_text(new[i]):
                raise ValueError(f"Slide {i+1}: non-footer PDF text changed after recompilation")
            if len(old[i].get_images()) != len(new[i].get_images()):
                raise ValueError(f"Slide {i+1}: image count changed after recompilation")
        return len(new)


def _copy_graphic_assets(folder: Path, staging: Path) -> None:
    """Copy only TeX compilation resources, never credentials or final media."""
    shutil.copy2(folder / "slides.tex", staging / "slides.tex")
    for f in folder.rglob("*"):
        if not f.is_file() or f.is_symlink():
            continue
        if ".microgen_work" in f.parts or ".history" in f.parts:
            continue
        if f.name.lower() in {"source.pdf", "slides.pdf"} or f.suffix.lower() not in ASSET_EXTENSIONS:
            continue
        relative = f.relative_to(folder)
        out = staging / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
    # Older decks may depend on local custom Beamer themes/assets shipped by
    # the package rather than already published in the source directory.
    root = Path(__file__).resolve().parents[1]
    for glob in ("*.sty", "usmlg.jpg", "usmemb.jpg", "logotype.jpg"):
        for f in root.glob(glob):
            dest = staging / f.name
            if not dest.exists() and f.is_file():
                shutil.copy2(f, dest)


def _two_pass_compile(staging: Path) -> Path:
    cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "slides.tex"]
    for n in (1, 2):
        done = subprocess.run(
            cmd, cwd=staging, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=180,
        )
        (staging / f"latex_pass_{n}.log").write_text(done.stdout or "", encoding="utf-8")
        if done.returncode:
            raise RuntimeError(f"Isolated pdflatex pass {n}/2 failed: exit {done.returncode}")
    candidate = staging / "slides.pdf"
    if not candidate.is_file() or not candidate.stat().st_size:
        raise ValueError("No compiled slide PDF produced")
    enforce_correct_page_totals(candidate)
    return candidate


def repair(folder: Path, *, apply: bool = False, cache_root: Path | None = None) -> dict:
    folder = Path(folder).expanduser().resolve()
    source, original, tex = (folder / x for x in ("source.pdf", "slides.pdf", "slides.tex"))
    for required in (source, original, tex):
        if not required.is_file() or required.is_symlink() or not required.stat().st_size:
            raise ValueError(f"Missing or untrusted input {required}")
    _ensure_latex_graphics(folder, None)
    wrong = incorrect_page_totals(original)
    if not wrong:
        return {"status": "already_correct", "folder": str(folder), "changed": False}
    artifacts = ["script.txt", "slides.mp4", ".microgen_completion.json", "slide_narration_sync.json"]
    forbidden = [name for name in artifacts if (folder / name).exists()]
    forbidden.extend(p.name for p in folder.glob("slide[0-9]*.wav"))
    if forbidden:
        raise ValueError(
            "Do not modify a deck with downstream narration, audio, MP4 or receipt: "
            + ", ".join(sorted(forbidden)[:12])
        )

    snapshot = {"source": _sha(source), "slides": _sha(original), "tex": _sha(tex)}
    if cache_root is None:
        cache_root = Path(os.getenv("LOCALAPPDATA") or tempfile.gettempdir()) / "MicroGenStage7FooterRepair"
    cache_root = Path(cache_root).expanduser().resolve()
    if folder == cache_root or folder in cache_root.parents or cache_root in folder.parents:
        raise ValueError("Footer-repair cache must be outside the published source tree")
    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="beamer_repair_", dir=cache_root) as temporary:
        scratch = Path(temporary)
        _copy_graphic_assets(folder, scratch)
        candidate = _two_pass_compile(scratch)
        pages = compare_slide_content(original, candidate)
        if any(_sha(p) != snapshot[n] for n, p in
               (("source", source), ("slides", original), ("tex", tex))):
            raise ValueError("Source, slides or LaTeX changed during recompile")
        result = {"status": "eligible" if not apply else "repaired",
                  "folder": str(folder), "slide_count": pages,
                  "old_slides_sha256": snapshot["slides"],
                  "candidate_sha256": _sha(candidate),
                  "source_unchanged": True, "nonfooter_content_unchanged": True}
        if not apply:
            return result
        # Refuse races: recheck downstream protection immediately before write.
        if any((folder / name).exists() for name in artifacts) or list(folder.glob("slide[0-9]*.wav")):
            raise ValueError("A downstream asset appeared while recompiling; refusing overwrite")
        if _sha(source) != snapshot["source"] or _sha(original) != snapshot["slides"] or _sha(tex) != snapshot["tex"]:
            raise ValueError("Lecture source/output changed before applying repair")
        history = folder / ".history" / ("stage7_footer_" +
                   datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
        history.mkdir(parents=True, exist_ok=False)
        backup = history / "slides.previous.pdf"
        shutil.copy2(original, backup)
        pending = folder / (".slides.stage7_pending_" + str(os.getpid()) + ".pdf")
        try:
            shutil.copy2(candidate, pending)
            pending.replace(original)
            enforce_correct_page_totals(original)
            if compare_slide_content(backup, original) != pages:
                raise RuntimeError("Unexpected slide-page drift after publication")
        except Exception:
            if backup.is_file():
                shutil.copy2(backup, original)
            raise
        finally:
            pending.unlink(missing_ok=True)
        (history / "repair.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        result["backup"] = str(backup)
        result["published_sha256"] = _sha(original)
        return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--apply", action="store_true", help="Explicitly allow the validated footer-only PDF correction")
    p.add_argument("--cache-root", type=Path, help="Local scratch directory outside source root")
    args = p.parse_args(argv)
    print(json.dumps(repair(args.folder, apply=args.apply, cache_root=args.cache_root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
