"""Source-hash-bound per-page Gemini figure mapping checkpoints.

No Gemini/API/Chrome calls. Existing page mappings can only be adopted after
all original crop bytes match targets, transport receipts show success,
and the unchanged source/page PNGs are available. This is a structural gate,
not independent proof of figure caption correctness.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from .figure_composites import (
    FigureCompositeReviewRequired, validate_and_prepare_mappings,
)

CHECKPOINT_VERSION=1
_SOURCE_CROP=re.compile(r"(?i)^fig_[0-9]+[.]png$")
_MAPPING_LINE=re.compile(r'^([^:\r\n]+?)\s+:\s+"([^"\r\n]+)"\s+:\s+([^:\r\n]+[.]png)\s*$')
_MAX_MAPPING_BYTES=100_000


def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda:stream.read(1024*1024),b""):
            h.update(data)
    return h.hexdigest()


def _regular(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _inputs(root: Path,page: int) -> tuple[Path,Path,Path,Path,Path]:
    root=Path(root).resolve()
    if type(page) is not int or not (1<=page<=100000):
        raise ValueError("Invalid source page")
    folder=root/"crops"/f"page_{page}"
    source=root/"source.pdf"
    page_png=root/"pages"/f"page_{page}"/f"page_{page}.png"
    mapping=root/"pages"/f"page_{page}"/f"page_{page}_mapping.txt"
    receipt=folder/"gemini_transport_attempts.json"
    return folder,source,page_png,mapping,receipt


def _candidate(root: Path,page: int,*,copy_to_root: bool) -> dict:
    folder,source,page_png,mapping,transport=_inputs(root,page)
    if not all(_regular(p) for p in (source,page_png,mapping,transport)):
        raise ValueError("Required source or verified page-mapping files missing")
    if mapping.stat().st_size>_MAX_MAPPING_BYTES:
        raise ValueError("Mapping content exceeds size limit")
    trace=json.loads(transport.read_text(encoding="utf-8"))
    if not (trace.get("completed") is True and trace.get("page")==page
            and isinstance(trace.get("attempts"),list)
            and any(a.get("status")=="validated" for a in trace["attempts"])):
        raise ValueError("Gemini transport did not validate this page")

    crops=sorted(
        (p for p in folder.iterdir() if p.is_file() and _SOURCE_CROP.fullmatch(p.name)),
        key=lambda p:int(p.stem.split("_")[1]),
    )
    if not crops:
        raise ValueError("This page has no original figure crops to checkpoint")

    triples=[]
    for line in mapping.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        match=_MAPPING_LINE.fullmatch(line.strip())
        if not match:
            raise ValueError("Mapping line is malformed or ambiguous")
        triples.append(tuple(x.strip() for x in match.groups()))
    if len(triples)!=len(crops):
        raise ValueError("Mapping count not equal to original crop count")
    try:
        triples=validate_and_prepare_mappings(triples)
    except FigureCompositeReviewRequired as exc:
        raise ValueError("Unsafe multipart target mapping") from exc
    if [t[0] for t in triples]!=[p.name for p in crops]:
        raise ValueError("Mapping order does not match original numbered crops")

    mapped=[]
    for name,label,target in triples:
        source_crop=folder/name
        target_crop=folder/target
        if not _regular(source_crop) or not _regular(target_crop):
            raise ValueError("Original/mapped crop is missing or symlinked")
        digest=_sha(source_crop)
        if _sha(target_crop)!=digest:
            raise ValueError(f"Mapped target {target} differs from the original crop")
        if copy_to_root:
            published=Path(root)/target
            if not _regular(published) or _sha(published)!=digest:
                raise ValueError(f"Root publication copy not present/identical: {target}")
        mapped.append({
            "crop":name,"caption":label,"target":target,
            "sha256":digest,
        })
    return {
        "schema_version":CHECKPOINT_VERSION,
        "status":"validated_source_mapping_not_visual_approval",
        "page":page,"source_pdf_sha256":_sha(source),
        "page_png_sha256":_sha(page_png),
        "mapping_sha256":_sha(mapping),
        "transport_sha256":_sha(transport),
        "copy_to_root":bool(copy_to_root),
        "mapped":mapped,
    }


def _path(root:Path,page:int)->Path:
    return _inputs(root,page)[0]/"source_bound_mapping_checkpoint.json"


def checkpoint_can_resume(root:Path,page:int,*,copy_to_root:bool=True)->bool:
    """Fail closed unless ALL current source/page/mapping/crop hashes agree."""
    try:
        path=_path(root,page)
        if not _regular(path):
            return False
        record=json.loads(path.read_text(encoding="utf-8"))
        return record==_candidate(root,page,copy_to_root=copy_to_root)
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
        return False


def save_checkpoint(root:Path,page:int,*,copy_to_root:bool=True)->Path:
    """Adopt only an already-successful, fully byte-verified mapping page.

    This also allows one-time adoption of pre-fix mapping results AFTER
    reviewers have verified their captions, without repeating Gemini calls.
    """
    new=_candidate(root,page,copy_to_root=copy_to_root)
    dest=_path(root,page)
    if dest.exists():
        if not checkpoint_can_resume(root,page,copy_to_root=copy_to_root):
            raise ValueError("Existing page checkpoint conflicts with source/mapping")
        return dest
    partial=dest.with_suffix(".json.pending")
    with partial.open("x",encoding="utf-8") as file:
        json.dump(new,file,ensure_ascii=False,indent=2)
        file.write("\n")
    partial.replace(dest)
    if not checkpoint_can_resume(root,page,copy_to_root=copy_to_root):
        raise ValueError("New page checkpoint failed re-verification")
    return dest
