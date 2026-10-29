"""Map original Figure 8.3 embedded-raster review anchors to real PDF page points.

This is a verified coordinate transform, NOT a mathematical, timing or
publication certificate. Rejects rotated/skewed image placement.
"""
from __future__ import annotations
import math
from pathlib import Path
import pymupdf
from .figure_source_identity import require, _sha

def bitmap_box_to_page(box:list, placement:list, bitmap_size:list)->list[float]:
    require(type(box) is list and len(box)==4
            and all(type(v) is int for v in box)
            and type(bitmap_size) is list and len(bitmap_size)==2
            and all(type(v) is int and 0<v<=10000 for v in bitmap_size)
            and type(placement) is list and len(placement)==4
            and all(type(v) in (int,float) and math.isfinite(v) for v in placement),
            "Invalid embedded slide figure dimensions or coordinates")
    w,h=bitmap_size
    x0,y0,x1,y1=box
    l,t,r,b=placement
    require(0<=x0<x1<=w and 0<=y0<y1<=h and 0<=l<r and 0<=t<b,
            "Figure review rectangle escapes actual raster or slide placement")
    return [round(l+(r-l)*x0/w,4),round(t+(b-t)*y0/h,4),
            round(l+(r-l)*x1/w,4),round(t+(b-t)*y1/h,4)]

def actual_slide_figure_placement(*,slides:Path,slide_page:int=5)->dict:
    slides=Path(slides).absolute()
    initial=_sha(slides)
    with pymupdf.open(slides) as pdf:
        require(type(slide_page) is int and 1<=slide_page<=len(pdf),
                "Invalid actual slide number")
        page=pdf[slide_page-1]
        require(page.rotation==0,"Unreviewed rotated slide page")
        images=[im for im in page.get_image_info(xrefs=True)
                if im.get("xref",0)>0 and int(im["width"])>=48
                and int(im["height"])>=48
                and pymupdf.Rect(im["bbox"]).width>=50
                and pymupdf.Rect(im["bbox"]).height>=25]
        require(len(images)==1,"Require a unique material figure image")
        im=images[0]
        rect=pymupdf.Rect(im["bbox"])
        require(rect in page.rect,"Material bitmap must lie on PDF slide")
        transform=im.get("transform")
        require(transform is not None and len(transform)==6
                and all(math.isfinite(float(v)) for v in transform)
                and abs(float(transform[1]))<1e-6
                and abs(float(transform[2]))<1e-6
                and float(transform[0])>0 and float(transform[3])>0,
                "Image contains skew/rotation/flip; simple page transform unsafe")
        result={"original_slides_sha256":initial,"slide_page":slide_page,
                "bitmap_dimensions_px":[int(im["width"]),int(im["height"])],
                "figure_placement_pdf_pt":[round(v,5) for v in rect],
                "slide_dimensions_pdf_pt":[round(page.rect.width,5),round(page.rect.height,5)],
                "figure_coordinate_transform_verified":True,
                "figure_mathematics_verified":False,"audio_timing_verified":False,
                "publication_authorized":False}
    require(_sha(slides)==initial,"Slide PDF changed during geometry review")
    return result

def transform_review_boxes(*,placement:dict, boxes:list)->dict:
    require(type(placement) is dict and placement.get("figure_coordinate_transform_verified") is True
            and type(boxes) is list and 0<len(boxes)<=50,"Untrusted review anchors")
    converted=[]
    for entry in boxes:
        require(type(entry) is dict and type(entry.get("utterance_id")) is str,
                "Source-bound utterance ID required")
        box=entry.get("candidate_full_expression_bitmap_bbox_for_review")
        if box is None:
            page_box=None
        else:
            page_box=bitmap_box_to_page(box,placement["figure_placement_pdf_pt"],
                                        placement["bitmap_dimensions_px"])
        converted.append({"utterance_id":entry["utterance_id"],
                          "candidate_equation_pdf_points":page_box,
                          "semantic_review_approved":False,
                          "spoken_element_timing_verified":False})
    return {"source_slides_sha256":placement["original_slides_sha256"],
            "page":placement["slide_page"],"review_anchors":converted,
            "publication_authorized":False}
