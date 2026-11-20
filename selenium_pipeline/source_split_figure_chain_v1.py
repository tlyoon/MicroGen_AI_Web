"""Fail-closed legacy source figure coverage across separately rendered slides.

An existing lecture may depict an originally captioned six-panel figure as
verified upper/lower PNGs on two distinct slides. Neither the presence of
those files, nor a legacy receipt, proves that all original source content
survived. This module checks original source pixels, panel labels, all source
raster objects, significant vector paths and source annotation words.

This ledger is evidence ONLY, not scientific or media publication approval.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageChops

from .source_caption_figure_chain_v1 import (
    FigureChainError, _require, _sha, _rect_list, _source,
    printed_source_captions, verify_figure_crops, fitz, RENDER_ZOOM,
)

SPLIT_LEDGER = "source_split_figure_chain_v1.json"
LEGACY_PROVENANCE = "figure_repair_provenance.json"


def _real_rect(seq, page):
    _require(isinstance(seq, list) and len(seq) == 4
             and all(type(x) in (float, int) and math.isfinite(x) for x in seq),
             "Unsafe split-panel source coordinates")
    rect = fitz.Rect(seq)
    _require(rect.is_valid and rect.width >= 20 and rect.height >= 20
             and page.rect.contains(rect), "Split panel outside source PDF")
    return rect


def _part_matches_source(page, rect, png: Path):
    _require(png.is_file() and not png.is_symlink() and png.suffix.lower() == ".png",
             "Missing/unsafe split source panel")
    pix = page.get_pixmap(
        matrix=fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM), clip=rect, alpha=False)
    reconstructed = Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    with Image.open(png) as f:
        old = f.convert("RGB")
    _require(reconstructed.size == old.size,
             "Legacy split PNG dimensions are not source-derived")
    # Strict 8-bit renderer-version tolerance: at most ONE grey level
    # in any channel. Never accept a substitute image, missing label or
    # later white cover-up. The number of differing pixels is also bounded.
    diff = ImageChops.difference(reconstructed, old)
    histogram = diff.histogram()
    worst = max(max(i for i,n in enumerate(histogram[c*256:(c+1)*256]) if n)
                for c in range(3))
    different = sum(diff.convert("L").histogram()[1:])
    _require(worst <= 1 and different <= max(2,old.width*old.height//1000),
             "Split PNG does not match original source crop pixels")
    return {"pixel_max_channel_difference":worst,
            "differing_pixels":different,"pixel_verified":True}


def _prove_coverage(page, full_rect, part_rects):
    rasters = [fitz.Rect(im["bbox"]) for im in page.get_image_info(xrefs=True)
               if fitz.Rect(im["bbox"]).width >= 12
               and fitz.Rect(im["bbox"]).height >= 12
               and full_rect.intersects(fitz.Rect(im["bbox"]))]
    drawings = [fitz.Rect(item["rect"]) for item in page.get_drawings()
                if fitz.Rect(item["rect"]).is_valid
                and (fitz.Rect(item["rect"]).width > 6
                     or fitz.Rect(item["rect"]).height > 6)
                and full_rect.intersects(fitz.Rect(item["rect"]))]
    annotation_words = [
        (str(w[4]).strip().lower(), fitz.Rect(w[:4]))
        for w in page.get_text("words")
        if fitz.Rect(w[:4]).width >= 2
        and fitz.Rect(w[:4]).height >= 2
        and full_rect.contains(fitz.Rect(w[:4]))]
    def covered(rect):
        return any(p.contains(rect) for p in part_rects)
    _require(len(rasters) >= 2, "Split figure requires at least two physical raster panels")
    missing_rasters = [x for x in rasters if not covered(x)]
    missing_vectors = [x for x in drawings if not covered(x)]
    missing_words = [x for x in annotation_words if not covered(x[1])]
    _require(not missing_rasters and not missing_vectors and not missing_words,
             "Split figure dropped source raster, vector or annotation content")
    letter_witnesses={}
    for i, raster in enumerate(rasters):
        matching=[
            (word,rect) for word,rect in annotation_words
            if len(word)==1 and word in "abcdefghijkl"
            and (raster.x0 - 8 <= rect.x0 <= raster.x0 + 30)
            and (raster.y1 - 4 <= rect.y0 <= raster.y1 + 24)
        ]
        if matching:
            letter_witnesses[str(i)] = [
                {"label":word,"bbox":_rect_list(rect)}
                for word,rect in matching]
    # If the original actually uses lettered raster panels, every raster
    # must retain one. Never accept a cropped away (a)/(b)/... label.
    if letter_witnesses:
        _require(len(letter_witnesses) == len(rasters),
                 "Split figure missing source panel letter witnesses")
        labels=[entry[0]["label"] for entry in letter_witnesses.values()]
        _require(len(set(labels)) == len(labels),
                 "Split figure duplicate panel letter witness")
    return {"source_rasters_covered":len(rasters),
            "source_vectors_covered":len(drawings),
            "source_annotation_words_covered":len(annotation_words),
            "source_panel_letter_witnesses":letter_witnesses}


def _candidate_mapping(folder, provenance):
    crop = verify_figure_crops(folder)
    if crop["status"] == "NO_PRINTED_FIGURES":
        return {}
    with fitz.open(str(_source(folder))) as doc:
        mapping={}
        for cap in printed_source_captions(folder/"source.pdf"):
            name=cap["filename"]
            key=cap["id"].replace(".","_")
            expr=re.compile(r"^Figure[_ ]"+re.escape(key)
                            +r"[_ ](?:upper|lower|left|right|panel[a-z0-9_-]+)\.png$",re.I)
            proposals=[
                (n,b) for n,b in provenance["regions_pdf_points"].items()
                if expr.fullmatch(n)]
            if len(proposals)<2:
                continue
            page=doc[cap["page"]-1]
            canonical=json.loads((folder/"source_figure_chain_v1.json").read_text())
            fig=next((x for x in canonical["figures"] if x["id"]==cap["id"]),None)
            _require(fig is not None,"Missing canonical source caption figure")
            full=_real_rect(fig["crop_bbox"],page)
            parts=[]
            rects=[]
            for filename,bbox in sorted(proposals,key=lambda x:(x[1][1],x[1][0])):
                rect=_real_rect(bbox,page)
                _require(full.contains(rect),
                         "Split crop must stay inside canonical source-figure boundary")
                evidence=_part_matches_source(page,rect,folder/filename)
                rects.append(rect)
                parts.append({"filename":filename,"crop_bbox":_rect_list(rect),
                              "sha256":_sha(folder/filename),**evidence})
            proof=_prove_coverage(page,full,rects)
            mapping[name] = {"caption_id":cap["id"],"page":cap["page"],
                             "source_figure_filename":name,
                             "source_figure_sha256":fig["crop_png_sha256"],
                             "parts":parts, **proof}
        return mapping


def prepare_split_figure_chain(folder: Path) -> dict:
    """Bootstrap only in an isolated staging directory, never published input."""
    folder=Path(folder)
    provenance_file=folder/LEGACY_PROVENANCE
    _require(provenance_file.is_file() and not provenance_file.is_symlink(),
             "Missing legacy original-source split provenance")
    provenance=json.loads(provenance_file.read_text(encoding="utf8"))
    _require(provenance.get("source_pdf_sha256")==_sha(_source(folder))
             and provenance.get("source_pdf_page_index") is not None
             and provenance.get("technique")=="pymupdf_page_render_3x_source_anchored"
             and isinstance(provenance.get("regions_pdf_points"),dict),
             "Legacy split provenance not tied to original PDF")
    mapping=_candidate_mapping(folder,provenance)
    _require(mapping,"No complete, source-bound legacy split figure mapping")
    _require(not (folder/SPLIT_LEDGER).exists(),
             "Do not overwrite existing split evidence")
    receipt={
        "schema_version":1,
        "source_sha256":_sha(_source(folder)),
        "provenance_sha256":_sha(provenance_file),
        "status":"SOURCE_SPLIT_PANELS_VERIFIED_CANDIDATE",
        "no_external_model_send":True,
        "scientific_approval":False,
        "student_publication_authorized":False,
        "figures":mapping,
    }
    target=folder/SPLIT_LEDGER
    pending=folder/(SPLIT_LEDGER+".tmp")
    pending.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    pending.replace(target)
    try:
        return verify_split_figure_chain(folder)
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def verify_split_figure_chain(folder: Path) -> dict:
    folder=Path(folder)
    path=folder/SPLIT_LEDGER
    _require(path.is_file() and not path.is_symlink(),
             "Missing source split panel evidence ledger")
    data=json.loads(path.read_text(encoding="utf-8"))
    _require(data.get("schema_version")==1
             and data.get("status")=="SOURCE_SPLIT_PANELS_VERIFIED_CANDIDATE"
             and data.get("source_sha256")==_sha(_source(folder))
             and data.get("provenance_sha256")==_sha(folder/LEGACY_PROVENANCE)
             and data.get("no_external_model_send") is True
             and data.get("scientific_approval") is False
             and data.get("student_publication_authorized") is False,
             "Split source ledger stale, altered or claims false release")
    p=json.loads((folder/LEGACY_PROVENANCE).read_text(encoding="utf-8"))
    _require(p.get("source_pdf_sha256")==data["source_sha256"],
             "Source split provenance mismatched")
    verified=_candidate_mapping(folder,p)
    _require(verified==data.get("figures"),
             "Split ledger no longer matches original source pixels, coverage or panel mapping")
    return {"status":"SOURCE_SPLIT_FIGURE_COMPLETE",
            "source_sha256":data["source_sha256"],
            "figures":{name:[part["filename"] for part in record["parts"]]
                       for name,record in verified.items()},
            "panel_count":sum(x["source_rasters_covered"] for x in verified.values()),
            "scientific_approval":False,
            "student_publication_authorized":False}
