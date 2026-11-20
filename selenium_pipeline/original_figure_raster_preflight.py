"""Structural + raster QA of actual source-hash-bound lecture figures.

A visible, unclipped raster is NOT evidence of correct axes, labels, triangle
geometry, panel segmentation, original textbook fidelity, or student release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pymupdf

from .ai_academic_web_review import build_review_job
from .figure_source_identity import require, _sha


def inspect_material_image(*, page, image:dict)->dict:
    width,height=image.get("width"),image.get("height")
    coords=image.get("bbox")
    if (type(width) is not int or type(height) is not int
        or width<48 or height<48
        or not isinstance(coords,(tuple,list)) or len(coords)!=4
        or any(not isinstance(v,(int,float)) or not math.isfinite(v)
               for v in coords)):
        raise ValueError("Material image dimensions or geometry invalid")
    bbox=pymupdf.Rect(coords)
    frame=page.rect
    require(bbox.is_valid and not bbox.is_empty
            and bbox.width>=8 and bbox.height>=8
            and bbox.x0>=frame.x0-0.1 and bbox.y0>=frame.y0-0.1
            and bbox.x1<=frame.x1+0.1 and bbox.y1<=frame.y1+0.1,
            "Teaching image clipped outside the original PDF slide")
    raster_ratio=width/height
    displayed_ratio=bbox.width/bbox.height
    aspect_error=abs(raster_ratio-displayed_ratio)/raster_ratio
    require(aspect_error<=0.06,"Original teaching image is geometrically distorted")

    crop=page.get_pixmap(
        matrix=pymupdf.Matrix(2,2),clip=bbox,
        colorspace=pymupdf.csGRAY,alpha=False)
    data=crop.samples
    require(crop.width>20 and crop.height>20 and len(data)>400,
            "Original visual crop unreadable")
    tones=list(data)
    ink_fraction=sum(t<245 for t in tones)/len(tones)
    contrast=max(tones)-min(tones)
    require(ink_fraction>0.005 and contrast>=15,
            "Original mathematical figure is blank or insufficiently visible")
    return {
        "original_image_pixel_width":width,
        "original_image_pixel_height":height,
        "original_image_bbox_pdf_pt":[round(v,3) for v in coords],
        "original_image_ratio":round(raster_ratio,5),
        "displayed_bbox_ratio":round(displayed_ratio,5),
        "relative_aspect_distortion":round(aspect_error,6),
        "decoded_crop_sample_sha256":hashlib.sha256(data).hexdigest(),
        "cropped_visible_ink_fraction":round(ink_fraction,5),
        "decoded_grayscale_contrast":contrast,
        "image_inside_original_slide":True,
        "blank_or_clipped_figure_detected":False,
        "original_textbook_figure_equivalence_approved":False,
        "independent_subpanel_geometry_verified":False,
        "diagram_label_and_mathematical_semantics_verified":False,
    }


def inspect_original_slide_figure(*,folder:Path,slide:int,
                                  minimum_images:int=1)->dict:
    root=Path(folder).absolute()
    require(root.is_dir() and not root.is_symlink()
            and type(slide) is int and 1<=slide<=100
            and type(minimum_images) is int and minimum_images>=1,
            "Original single-slide figure QA input invalid")
    paths=(root/"source.pdf",root/"slides.pdf",root/"script.txt")
    require(all(p.is_file() and not p.is_symlink() for p in paths),
            "Immutable teaching source files unavailable")
    hashes=tuple(_sha(p) for p in paths)
    job=build_review_job(folder=root,slide_numbers=[slide])
    require((job["source_sha256"],job["slides_sha256"],
             job["script_sha256"])==hashes,
            "Original source identity changed before figure inspection")
    with pymupdf.open(paths[1]) as deck:
        require(1<=slide<=len(deck),"Original slide missing")
        page=deck[slide-1]
        all_images=page.get_image_info()
        materials=[p for p in all_images
                   if isinstance(p.get("width"),int)
                   and isinstance(p.get("height"),int)
                   and p["width"]>=48 and p["height"]>=48]
        require(len(materials)>=minimum_images,
                "Expected source teaching figure absent from real slide")
        inspected=[inspect_material_image(page=page,image=p) for p in materials]
        ignored=len(all_images)-len(materials)
    require(tuple(_sha(p) for p in paths)==hashes,
            "Original source files changed during figure inspection")
    return {
        "status":"ORIGINAL_FIGURE_STRUCTURAL_RASTER_QA_PANEL_SEMANTICS_PENDING",
        "original_source_sha256":hashes[0],
        "original_slide_pdf_sha256":hashes[1],
        "original_script_sha256":hashes[2],
        "slide":slide,
        "original_utterances_on_slide":job["utterance_count"],
        "material_figure_count":len(inspected),
        "tiny_or_decorative_rasters_ignored":ignored,
        "material_figures":inspected,
        "technical_figure_bbox_and_contrast_accepted":True,
        "source_textbook_figure_semantics_approved":False,
        "composite_figure_subpanels_independently_mapped":False,
        "independent_academic_consensus_verified":False,
        "new_provider_request_sent":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    p.add_argument("--slide",required=True,type=int)
    args=p.parse_args(argv)
    print(json.dumps(
        inspect_original_slide_figure(folder=args.folder,slide=args.slide),
        indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
