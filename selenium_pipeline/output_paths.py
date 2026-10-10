"""Safe, source-adjacent publication of generated MicroGen teaching media.

The validated template_v2 scripts must continue to run in an isolated workspace.
Only explicitly enumerated output artifacts (never copied scripts or credentials)
are published into the subchapter directory containing source.pdf.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE_ROOT_ENV = "MICROGEN_SOURCE_ROOT"


def resolve_source_root(value: str | Path | None, *, code_root: Path) -> Path:
    """Resolve separately configured textbook tree; never default to Git clone.

    Explicit --source-root wins; otherwise a per-PC environment setting applies.
    Browser URLs (including Drive links) are not local filesystem paths.
    """
    choice = str(value).strip() if value is not None else ""
    if not choice:
        choice = os.environ.get(SOURCE_ROOT_ENV, "").strip()
    if not choice:
        raise ValueError(
            "SOURCE_ROOT is required: pass --source-root <LOCAL_PDF_TREE> "
            f"or set {SOURCE_ROOT_ENV} to a local directory. "
            r"Illustrative SOURCE_ROOT only: G:\My Drive\Serway\Serway_8_14 "
            r"(containing 8\8.1\source.pdf); replace with your own PDF tree. "
            "The cloned MicroGen repository is only the code root."
        )
    if "://" in choice:
        raise ValueError("SOURCE_ROOT must be a local/mounted directory, not a URL")
    source_root = Path(choice).expanduser().resolve()
    repo_root = code_root.resolve()
    if source_root == repo_root or source_root.is_relative_to(repo_root) or repo_root.is_relative_to(source_root):
        raise ValueError("SOURCE_ROOT and the MicroGen code root must be separate, non-nested directories")
    if not source_root.is_dir():
        raise NotADirectoryError(f"SOURCE_ROOT is unavailable: {source_root}")
    return source_root


OUTPUT_NAMES = {
    "figures": (),
    "slides": ("slides.tex", "slides.pdf"),
    "narration": ("script.txt", "script_tts.json"),
    "script_qa": ("script_risk_report.json", "script_risk_report.md"),
    "tts": ("script_tts.json",),
    "tts_qa": ("tts_fidelity_report.json", "tts_fidelity_report.md"),
    "video": ("slides.mp4",),
}
OUTPUT_GLOBS = {
    "figures": ("Figure*.png", "FIGURE*.png"),
    # Compile-ready LaTeX may reference logos, additional image formats or a
    # local Beamer theme. Publish these alongside slides.tex before cleanup.
    "slides": ("*.png", "*.jpg", "*.jpeg", "*.sty", "*.cls", "*.bib", "*.eps", "*.svg"),
    "tts": ("slide*.wav",),
    "video": ("slide*.pdf",),
}
NUMBERED_MEDIA = re.compile(r"slide[1-9][0-9]*\.(?:wav|pdf)$", re.IGNORECASE)


def assert_writable_directory(directory: Path) -> None:
    """Fail fast without leaving a file behind, including on synced drives."""
    if not directory.is_dir():
        raise NotADirectoryError(f"Source directory is unavailable: {directory}")
    probe: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".microgen_write_probe_", dir=directory,
            delete=False,
        ) as handle:
            handle.write(b"MicroGen write-permission test")
            probe = Path(handle.name)
    except OSError as exc:
        raise PermissionError(
            f"MicroGen requires write permission to {directory}: {exc}"
        ) from exc
    finally:
        if probe is not None:
            try:
                probe.unlink(missing_ok=True)
            except OSError as exc:
                raise PermissionError(
                    f"MicroGen could not remove its permission-test file in {directory}"
                ) from exc


def verify_source_tree(source_root: Path, source_pdf: Path) -> None:
    """Check the user-selected root and the target subchapter before generation."""
    root = source_root.resolve()
    source = source_pdf.resolve()
    if not source.is_file() or source.name.lower() != "source.pdf":
        raise FileNotFoundError(f"Missing source.pdf: {source}")
    if not source.is_relative_to(root):
        raise ValueError(f"source.pdf must be under the source root: {root}")
    assert_writable_directory(root)
    assert_writable_directory(source.parent)


def _sha256(path: Path) -> str:
    """Streaming SHA-256 compatible with Python 3.10 on Dell-115."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_atomically(src: Path, dest: Path) -> None:
    """Publish each artifact using an in-directory temporary copy and rename."""
    if not src.is_file() or src.is_symlink():
        return
    if src.resolve() == dest.resolve():
        return
    temp = dest.with_name(f".{dest.name}.{os.getpid()}.microgen.tmp")
    try:
        shutil.copy2(src, temp)
        temp.replace(dest)
    finally:
        temp.unlink(missing_ok=True)


def publish_stage_outputs(
    work_dir: Path, source_pdf: Path, stage: str, *, diagnostics_only: bool = False
) -> list[Path]:
    """Publish user-facing output after successful validation, not code/secrets.

    Diagnostic logs and QA reports are still published on a failed stage.
    """
    if stage not in OUTPUT_NAMES:
        raise ValueError(f"Unsupported MicroGen stage: {stage}")
    destination = source_pdf.parent
    if not destination.is_dir():
        raise NotADirectoryError(destination)
    names = set()
    if not diagnostics_only:
        names.update(OUTPUT_NAMES[stage])
        for pattern in OUTPUT_GLOBS.get(stage, ()):
            for artifact in work_dir.glob(pattern):
                if pattern.startswith("slide") and not NUMBERED_MEDIA.fullmatch(artifact.name):
                    continue
                names.add(artifact.name)
        names.add(".selenium_pipeline_state.json")
    else:
        if stage in {"script_qa", "tts_qa"}:
            names.update(OUTPUT_NAMES[stage])
    names.add(f"microgen_{stage}.log")
    published: list[Path] = []
    for name in sorted(names):
        src = work_dir / name
        if src.is_file() and not src.is_symlink() and src.stat().st_size > 0:
            target = destination / name
            if stage == "video" and name == "slides.mp4" and target.is_file():
                # Keep a previously published lecture when a validated
                # replacement is different. Reusing an identical MP4 does not
                # create redundant history snapshots.
                if _sha256(src) != _sha256(target):
                    archive = destination / ".history" / (
                        "video_publish_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                    )
                    archive.mkdir(parents=True, exist_ok=False)
                    shutil.copy2(target, archive / target.name)
            _copy_atomically(src, target)
            published.append(target)
    return published
