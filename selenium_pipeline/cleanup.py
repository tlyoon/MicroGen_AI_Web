"""Conservative, idempotent cleanup after a verified completed lecture.

Do not remove a workspace, intermediate output, or old history until the
final user-facing artifacts have been published beside the original source.pdf.
Keep a small completion receipt for safe, inexpensive subsequent reruns.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

RECEIPT = ".microgen_completion.json"
FINAL_FILES = ("slides.tex", "slides.pdf", "script.txt", "slides.mp4")
# These are known *intermediate* files, not teaching deliverables.
TRANSIENT_FILES = {
    "script_tts.json",
    ".selenium_pipeline_state.json",
    ".microgen_checkpoint.json",
    "microgen_batch.log",
    "gen_video.log",
    "slice_pdf.log",
    "run_clean_leftover.log",
    "rem_mp4.log",
    "png_dimensions.json",
}
TRANSIENT_DIRS = {
    ".microgen_work",
    ".microgen_batch_work",
    ".history",
    "__pycache__",
    "pages",
    "crops",
}
SLIDE_INTERMEDIATE = re.compile(r"slide[1-9][0-9]*\.(?:pdf|wav)$", re.I)
BUILD_INTERMEDIATE = re.compile(
    r"[^/\\]+\.(?:aux|log|nav|out|snm|toc|vrb|fls|fdb_latexmk|synctex\.gz)$", re.I
)
PIPELINE_LOG = re.compile(r"microgen_[a-z_]+\.log$", re.I)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _final_hashes(folder: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in FINAL_FILES:
        file = folder / name
        if not file.is_file() or file.is_symlink() or file.stat().st_size == 0:
            raise ValueError(f"Cannot clean incomplete lecture: missing/empty {file}")
        result[name] = _sha256(file)
    return result


def completed_lecture(source_pdf: Path) -> bool:
    """True only for a fully published lecture with a matching receipt.

    A changed source.pdf or changed/deleted published media must never be
    considered an already-complete lecture.
    """
    receipt = source_pdf.parent / RECEIPT
    if source_pdf.name.lower() != "source.pdf" or not source_pdf.is_file() or not receipt.is_file():
        return False
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
        if (data.get("source_sha256") != _sha256(source_pdf)
                or data.get("final_sha256") != _final_hashes(source_pdf.parent)):
            return False
        _ensure_latex_graphics(source_pdf.parent, None)
        return True
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return False


def _write_receipt(source_pdf: Path, data: dict) -> None:
    path = source_pdf.parent / RECEIPT
    pending = source_pdf.parent / (RECEIPT + ".tmp")
    try:
        pending.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def _safe_remove(path: Path) -> None:
    """Never follow or delete symlinks/reparse points or an unexpected path."""
    if path.is_symlink():
        raise ValueError(f"Refusing to delete symlink: {path}")
    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()


GRAPHIC = re.compile(r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}", re.I)
GRAPHICSPATH = re.compile(r"\\graphicspath\s*\{((?:\{[^{}]*\}\s*)+)\}", re.I)
GRAPHICS_DIR = re.compile(r"\{([^{}]+)\}")


def _ensure_latex_graphics(folder: Path, workspace: Path | None) -> None:
    r"""Keep every directly referenced LaTeX graphic before pruning staging.

    Common root-level figures/logos are already published by the slides stage.
    This also handles relative subfolders and \graphicspath on the rare deck
    where figures have not been copied beside the TeX yet.
    """
    for tex in folder.glob("*.tex"):
        if not tex.is_file():
            continue
        lines = tex.read_text(encoding="utf-8", errors="replace").splitlines()
        text = "\n".join(line for line in lines if not line.lstrip().startswith("%"))
        dirs = [Path(".")]
        for directive in GRAPHICSPATH.finditer(text):
            for raw in GRAPHICS_DIR.findall(directive.group(1)):
                dirs.append(Path(raw.strip().replace("\\", "/")))
        for match in GRAPHIC.finditer(text):
            raw = match.group(1).strip()
            if "\\" in raw or not raw:
                raise ValueError(f"Unresolved LaTeX graphic reference in {tex}: {raw}")
            graphic = Path(raw)
            if graphic.is_absolute() or ".." in graphic.parts:
                raise ValueError(f"Unsafe LaTeX graphic reference in {tex}: {raw}")
            suffixes = ("",) if graphic.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg"} else (".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg")
            found = False
            for prefix in dirs:
                if prefix.is_absolute() or ".." in prefix.parts:
                    raise ValueError(f"Unsafe LaTeX graphic path in {tex}: {prefix}")
                for suffix in suffixes:
                    relative = prefix / (raw + suffix)
                    published = folder / relative
                    if published.is_file() and published.stat().st_size > 0:
                        found = True
                        break
                    if workspace is not None:
                        staged = workspace / relative
                        if staged.is_file() and not staged.is_symlink() and staged.stat().st_size > 0:
                            published.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(staged, published)
                            found = True
                            break
                if found:
                    break
            if not found:
                raise ValueError(
                    f"Refusing cleanup: required LaTeX graphic {raw!r} is not published "
                    f"beside {tex} or present in the workspace"
                )


def _tex_needs_directory(folder: Path, directory_name: str) -> bool:
    """Preserve assets in subfolders referenced by LaTeX.

    In addition to includegraphics, this conservatively catches graphicspath,
    input, and any literal TeX reference to a folder, including nested paths.
    """
    term = re.compile(r"(?<![\w])" + re.escape(directory_name) + r"\s*[/\\]", re.I)
    for tex in folder.glob("*.tex"):
        if tex.is_file() and term.search(tex.read_text(encoding="utf-8", errors="replace")):
            return True
    return False


def cleanup_completed_lecture(
    source_pdf: Path,
    *,
    workspace: Path | None = None,
    pipeline: str,
) -> list[str]:
    """Prune only recognized generated intermediates after final outputs exist.

    Never delete original source.pdf, final TeX/PDF/script/MP4, PNG/JPG/JPEG
    or unrelated user-supplied files. Preserve an external workspace unless
    it demonstrably belongs to the same source.pdf (matching staging copy).
    Completion is stamped before cleanup to support crash-safe retry.
    """
    if pipeline not in {"selenium", "batch"}:
        raise ValueError(f"Unknown pipeline: {pipeline}")
    if source_pdf.name.lower() != "source.pdf" or not source_pdf.is_file() or source_pdf.is_symlink():
        raise FileNotFoundError(f"Invalid source PDF: {source_pdf}")
    folder = source_pdf.parent
    hashes = _final_hashes(folder)  # No mutation before checking all deliverables.
    signature = _sha256(source_pdf)

    # Check external workspace ownership *before* writing the completion stamp.
    owned_work: Path | None = None
    if workspace is not None and workspace.exists():
        if workspace.is_symlink():
            raise ValueError(f"Refusing symlink workspace: {workspace}")
        work = workspace.resolve()
        if work == folder.resolve() or source_pdf.resolve().is_relative_to(work):
            raise ValueError(f"Refusing unsafe workspace: {workspace}")
        staged_source = workspace / "source.pdf"
        if not staged_source.is_file() or staged_source.is_symlink() or _sha256(staged_source) != signature:
            raise ValueError(f"Refusing workspace not owned by source.pdf: {workspace}")
        # Require known pipeline-specific workspace identity as well as source copy.
        expected_name = ".microgen_work" if pipeline == "selenium" else ".microgen_batch_work"
        marker = ".selenium_pipeline_state.json" if pipeline == "selenium" else ".microgen_checkpoint.json"
        if workspace.name != expected_name and not (workspace / marker).is_file():
            raise ValueError(f"Refusing unrecognized external workspace: {workspace}")
        owned_work = workspace

    # Check/copy the images referenced by LaTeX *before* deleting any staging.
    # This matters for figures outside Figure*.png and for nested image paths.
    _ensure_latex_graphics(folder, owned_work)

    receipt = {
        "pipeline": pipeline,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": signature,
        "final_sha256": hashes,
        "cleanup": "pending",
    }
    _write_receipt(source_pdf, receipt)
    removed: list[str] = []
    try:
        # A default hidden workspace is an owned workspace, removed below.
        if owned_work is not None:
            _safe_remove(owned_work)
            removed.append(str(owned_work))
        for entry in folder.iterdir():
            if entry.name == RECEIPT or entry.name == "source.pdf" or entry.is_symlink():
                continue
            if entry.is_file():
                name = entry.name
                if (name in TRANSIENT_FILES or SLIDE_INTERMEDIATE.fullmatch(name)
                        or BUILD_INTERMEDIATE.fullmatch(name) or PIPELINE_LOG.fullmatch(name)
                        or name.endswith(".microgen.tmp")):
                    _safe_remove(entry)
                    removed.append(name)
            elif entry.is_dir() and entry.name in TRANSIENT_DIRS:
                # Images nested under these directories could be required to
                # recompile LaTeX; only prune the directory when unreferenced.
                if _tex_needs_directory(folder, entry.name):
                    continue
                _safe_remove(entry)
                removed.append(entry.name)
        receipt["cleanup"] = "complete"
        receipt["removed_count"] = len(removed)
        _write_receipt(source_pdf, receipt)
    except Exception:
        # The receipt remains marked pending; a future run can retry safely.
        raise
    return removed
