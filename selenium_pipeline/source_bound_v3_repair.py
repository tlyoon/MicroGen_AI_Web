"""Restart-safe v3 figure repair for fully SHA-pinned original textbook figures.

No browser/API calls and no caption inventing. Historic candidate folders remain
untouched. Every output passes the standard source PDF/render/edge/panel validator.
This module does NOT establish scientific, slide or media acceptance.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

STAGE_RECEIPT="source_figures_v3_receipt.json"
SIGNATURE="SOURCE_SHA_BOUND_V3_COMPLETE_FIGURES"
MECHANISM="RECOVER_SHA_PINNED_SOURCE_CROPS_WITH_NO_LEGACY_MAPPING_SEND"

def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for piece in iter(lambda: stream.read(1024*1024),b""):
            h.update(piece)
    return h.hexdigest()

def registered_and_complete(source: Path) -> bool:
    """Only sources with explicit, complete, source-SHA-bound v3 crop entries."""
    from .figure_recovery_registry_v1 import lookup_mechanism
    from . import source_caption_figure_chain_v1 as crop
    source=Path(source)
    if not source.is_file() or source.is_symlink():
        return False
    # First filter by the literal SHA registry, *before* using MuPDF.
    # Legacy tests and user-supplied sources can contain non-PDF placeholder
    # bytes. Those are not v3 candidates and must reach the normal
    # preservation/error guard without opening or locking malformed PDFs.
    sha=_sha(source)
    override=Path(crop.__file__).with_name("source_crop_overrides_v1.json")
    data=json.loads(override.read_text(encoding="utf-8"))
    if data.get("schema_version")!=1 or not isinstance(data.get("overrides"),dict):
        raise crop.FigureChainError("Invalid source-SHA crop registry")
    known=data["overrides"].get(sha)
    if not isinstance(known,dict) or not known:
        return False
    if lookup_mechanism("source_figure_recovery",SIGNATURE)!=MECHANISM:
        raise crop.FigureChainError("V3 source-bound recovery registry missing/disabled")
    with crop.fitz.open(str(source)) as doc:
        captions=crop._caption_rows(doc)
        if not captions:
            return False
        if set(known)!={row["id"] for row in captions}:
            return False
        for row in captions:
            if crop._source_sha_bound_crop_override(sha,row,doc[row["page"]-1]) is None:
                return False
        return True

def _resume_candidate(source:Path, stage:Path):
    from . import source_caption_figure_chain_v1 as crop
    original_sha=_sha(source)
    stage.mkdir(parents=False,exist_ok=True) if not stage.exists() else None
    if stage.is_symlink() or not stage.is_dir():
        raise crop.FigureChainError("Unsafe v3 candidate directory")
    staged_src=stage/"source.pdf"
    if not staged_src.is_file():
        shutil.copy2(source,staged_src)
    if staged_src.is_symlink() or _sha(staged_src)!=original_sha:
        raise crop.FigureChainError("Foreign/stale v3 candidate source")
    if (stage/crop.LEDGER).is_file():
        return crop.verify_figure_crops(stage)
    # Rebuild independently into local disk. Each preexisting source figure in
    # the interrupted Drive candidate MUST match the new source render; never
    # silently replace an old candidate with different bytes.
    with tempfile.TemporaryDirectory(prefix="microgen_v3_restart_") as temp:
        base=Path(temp)
        incoming=base/"input";incoming.mkdir()
        shutil.copy2(source,incoming/"source.pdf")
        produced=base/"candidate";produced.mkdir()
        shutil.copy2(source,produced/"source.pdf")
        output=crop.generate_candidates(incoming/"source.pdf",produced)
        crop.verify_figure_crops(produced)
        for row in output["figures"]:
            filename=row["filename"]
            src=produced/filename;dest=stage/filename
            if dest.exists() or dest.is_symlink():
                if not dest.is_file() or dest.is_symlink() or _sha(dest)!=_sha(src):
                    raise crop.FigureChainError(
                        "Historical v3 source crop differs: "+filename)
            else:
                shutil.copy2(src,dest)
                if _sha(dest)!=_sha(src):
                    raise crop.FigureChainError("V3 crop readback checksum mismatch")
        ledger=stage/crop.LEDGER
        if ledger.exists() or ledger.is_symlink():
            raise crop.FigureChainError("Concurrent/foreign v3 ledger publication")
        shutil.copy2(produced/crop.LEDGER,ledger)
        if _sha(ledger)!=_sha(produced/crop.LEDGER):
            raise crop.FigureChainError("V3 ledger readback checksum mismatch")
    return crop.verify_figure_crops(stage)

def recover_source_figures_v3(folder: Path) -> dict:
    from . import source_caption_figure_chain_v1 as crop
    folder=Path(folder);source=folder/"source.pdf"
    if not registered_and_complete(source):
        raise crop.FigureChainError("V3 original-source SHA profile incomplete")
    source_sha=_sha(source)
    try:
        status=crop.verify_figure_crops(folder)
        return {**status,"v3_source_bound":True,"v3_reused":True}
    except (ValueError,OSError):
        pass
    failures=[]
    for attempt in range(2):
        suffix="_retry1" if attempt else ""
        stage=folder/(".microgen_source_caption_crop_stage_v3_"+source_sha[:12]+suffix)
        try:
            _resume_candidate(source,stage)
            published=crop.promote_candidates(stage,folder)
            if _sha(source)!=source_sha:
                raise crop.FigureChainError("Original source changed during v3 repair")
            return {
                "status":"SOURCE_CAPTION_COMPLETE_CROPS_PROMOTED",
                "v3_source_bound":True,"v3_reused":False,
                "source_sha256":source_sha,"figure_count":published["figure_count"],
                "promoted":published["promoted"],
                "old_failed_candidates_preserved":True,
                "v3_attempt":attempt+1,
                "failed_v3_attempts":failures,
                "scientific_approval":False,
            }
        except (OSError,ValueError) as exc:
            failures.append(f"{type(exc).__name__}: {str(exc)[:180]}")
    raise crop.FigureChainError(
        "V3_SOURCE_BOUND_TWO_ATTEMPTS_EXHAUSTED_NO_MODEL_SEND "+
        json.dumps(failures))

def publish_source_only_receipt(folder: Path) -> dict:
    from . import source_caption_figure_chain_v1 as crop
    folder=Path(folder)
    if not registered_and_complete(folder/"source.pdf"):
        raise crop.FigureChainError("Source-only bypass lacks complete registered v3 PDF profile")
    proof=crop.verify_figure_crops(folder)
    pages=folder/"pages";crops=folder/"crops"
    if not pages.is_dir() or not crops.is_dir() or not any(pages.iterdir()):
        raise crop.FigureChainError("Original source page extraction missing")
    record={
        "schema_version":3,
        "source_sha256":_sha(folder/"source.pdf"),
        "source_figure_chain_sha256":_sha(folder/crop.LEDGER),
        "source_figure_png_sha256":{
            f:_sha(folder/f) for f in proof["figures"]},
        "count":proof["figure_count"],
        "status":"VERIFIED_PRINTED_SOURCE_FIGURES_WITHOUT_LEGACY_LLM_MAPPING",
        "no_figure_mapping_model_send":True,
        "scientific_approval":False,
    }
    dest=folder/STAGE_RECEIPT
    pending=folder/("."+STAGE_RECEIPT+".pending")
    pending.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    pending.replace(dest)
    return record

def valid_source_only_figures(folder: Path) -> bool:
    from . import source_caption_figure_chain_v1 as crop
    folder=Path(folder);p=folder/STAGE_RECEIPT
    if not p.is_file() or p.is_symlink():
        return False
    try:
        if not registered_and_complete(folder/"source.pdf"):
            return False
        data=json.loads(p.read_text(encoding="utf-8-sig"))
        proof=crop.verify_figure_crops(folder)
        pages=folder/"pages";crops=folder/"crops"
        return (data.get("schema_version")==3
            and data.get("status")=="VERIFIED_PRINTED_SOURCE_FIGURES_WITHOUT_LEGACY_LLM_MAPPING"
            and data.get("no_figure_mapping_model_send") is True
            and data.get("scientific_approval") is False
            and data.get("source_sha256")==_sha(folder/"source.pdf")
            and data.get("source_figure_chain_sha256")==_sha(folder/crop.LEDGER)
            and data.get("source_figure_png_sha256")=={
                name:_sha(folder/name) for name in proof["figures"]}
            and data.get("count")==proof["figure_count"]
            and pages.is_dir() and crops.is_dir() and any(pages.iterdir()))
    except (ValueError,OSError,KeyError):
        return False
