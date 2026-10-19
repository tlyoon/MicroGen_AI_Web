"""Read-only panel-wise source-vector reconstruction across rearranged slides.

A figure may contain vertically stacked vector panels while a slide uses
independent or composite horizontal raster panels. This checker compares
the *actual* original PDF rendering to each independently declared slide
region after a coordinate-controlled redraw. It NEVER infers panel semantics,
approves cropped panels, or authorizes narration/publication.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha
from .figure_vector_provenance import _checked_pdf


def _rect(page, value, label):
    require(isinstance(value,(list,tuple)) and len(value)==4
            and all(type(v) in (int,float) for v in value),
            f"{label}: four finite coordinates required")
    r=pymupdf.Rect(*value)
    require(not r.is_empty and not r.is_infinite
            and page.rect.contains(r)
            and r.width>=22 and r.height>=22
            and all(abs(float(v))<=100000 for v in r),
            f"{label}: invalid/outside/clipped rectangle")
    return r


def _contains(outer,inner,epsilon=.2):
    return (inner.x0 >= outer.x0-epsilon and
            inner.y0 >= outer.y0-epsilon and
            inner.x1 <= outer.x1+epsilon and
            inner.y1 <= outer.y1+epsilon)


def _intersects_including_lines(a,b):
    return a.x1>=b.x0 and a.x0<=b.x1 and a.y1>=b.y0 and a.y0<=b.y1


def _pixels(page,rect,width,height):
    # Require integer-aligned dimensions; changing page scale is explicit.
    xs=width/rect.width
    ys=height/rect.height
    pix=page.get_pixmap(matrix=pymupdf.Matrix(xs,ys),clip=rect,
                        colorspace=pymupdf.csRGB,alpha=False,annots=True)
    require((pix.width,pix.height,pix.n)==(width,height,3),
            "Source/slide pixel-grid registration failed")
    return bytes(pix.samples)


def inspect_reflowed_vector_panels(
    *, source: Path,slides: Path,source_page:int,slide_page:int,
    figure_id:str,source_figure_bbox:list[float],panels:list[dict],
    render_scale:int=2,
)->dict:
    """Return exact visual panel reconstruction *candidate*, never approval.

    Each panel is explicit {id:'a',source_bbox:[...],slide_bbox:[...]}.
    Source drawing and PDF-text inventory must have exactly one owner panel.
    The same pixels must be present in the chosen slide region regardless of
    panel ordering or layout. Original figure region/caption/labels must all
    be independently represented, otherwise reject without guessing.
    """
    require(type(source_page) is int and type(slide_page) is int
            and type(render_scale) is int and 2<=render_scale<=4,
            "One-based integer pages and bounded render scale required")
    require(isinstance(figure_id,str)
            and re.fullmatch(r"[1-9]\d*\.\d+",figure_id),
            "Explicit chapter.figure source identifier required")
    require(isinstance(panels,list) and 2<=len(panels)<=6,
            "Require two to six explicit labelled panels")
    require([entry.get("id") if isinstance(entry,dict) else None
             for entry in panels]==list("abcdef"[:len(panels)]),
            "Missing, repeated or reordered source panel identifiers")
    require(all(isinstance(e,dict) and
                set(e)=={"id","source_bbox","slide_bbox"}
                for e in panels),
            "Every panel requires exactly source and slide bboxes")
    src,dst=_checked_pdf(source),_checked_pdf(slides)
    require(src!=dst,"Source and slide PDF must differ")
    sh,dh=_sha(src),_sha(dst)
    receipts=[]
    with pymupdf.open(src) as original,pymupdf.open(dst) as deck:
        require(1<=source_page<=len(original)
                and 1<=slide_page<=len(deck),
                "PDF page out of range")
        sp,dp=original[source_page-1],deck[slide_page-1]
        figure=_rect(sp,source_figure_bbox,"Original figure")
        source_boxes=[_rect(sp,e["source_bbox"],"Source panel")
                      for e in panels]
        slide_boxes=[_rect(dp,e["slide_bbox"],"Slide panel")
                     for e in panels]
        require(all(_contains(figure,b) for b in source_boxes),
                "Source panel extends outside original figure")
        for i in range(len(panels)):
            for j in range(i+1,len(panels)):
                require((source_boxes[i]&source_boxes[j]).get_area()<.01
                        and (slide_boxes[i]&slide_boxes[j]).get_area()<.01,
                        "Overlapping original/slide panel extents")
        captions=[pymupdf.Rect(b[:4]) for b in sp.get_text("blocks")
                  if len(b)>4 and isinstance(b[4],str)
                  and re.match(r"(?i)^\s*fig(?:ure)?\s*"
                               +re.escape(figure_id)+r"\b",b[4])]
        require(len(captions)==1 and
                captions[0].y0 >= figure.y1-.5
                and captions[0].y0-figure.y1<180,
                "Exactly one adjacent original figure caption required")
        # Reject all embedded source raster images within vector scope.
        require(not any(_intersects_including_lines(
                  pymupdf.Rect(im["bbox"]),figure)
                  for im in sp.get_image_info(xrefs=True)),
                "Mixed source raster/vector figure requires separate proof")
        drawings=[pymupdf.Rect(x["rect"]) for x in sp.get_drawings()
                  if _intersects_including_lines(pymupdf.Rect(x["rect"]),figure)]
        require(len(drawings)>=len(panels),
                "Original PDF has insufficient figure vector content")
        source_words=[(str(x[4]),pymupdf.Rect(x[:4]))
                      for x in sp.get_text("words")
                      if _intersects_including_lines(
                           pymupdf.Rect(x[:4]),figure)]
        source_labels=[(word[1:-1].lower(),rect)
                       for word,rect in source_words
                       if re.fullmatch(r"\([a-f]\)",word,re.I)]
        require(len(source_labels)==len(panels)
                and sorted(x[0] for x in source_labels)
                    ==[e["id"] for e in panels],
                "Original figure lacks unique extractable (a)/(b)/... labels")
        for kind,objects in (("vector path",drawings),
                             ("figure text",[box for _,box in source_words])):
            for obj in objects:
                require(len([i for i,box in enumerate(source_boxes)
                             if _contains(box,obj)])==1,
                        f"Original {kind} omitted, clipped or crosses panels")
        for label,rect in source_labels:
            idx=[e["id"] for e in panels].index(label)
            require(_contains(source_boxes[idx],rect),
                    "Source panel label does not belong to declared panel")
        for entry,sbox,dbox in zip(panels,source_boxes,slide_boxes):
            scale_ratio_src=sbox.width/sbox.height
            scale_ratio_slide=dbox.width/dbox.height
            require(abs(scale_ratio_src-scale_ratio_slide)
                    <= .002*scale_ratio_src,
                    "Source-to-slide panel aspect ratio distortion")
            # Ensure slide region is covered by one and only one actual
            # referenced image, no ungrounded vector/text replacements.
            touching=[im for im in dp.get_image_info(xrefs=True)
                      if _intersects_including_lines(
                          pymupdf.Rect(im["bbox"]),dbox)]
            require(len(touching)==1 and touching[0].get("xref",0)>0
                    and _contains(pymupdf.Rect(touching[0]["bbox"]),dbox),
                    "Slide region is not uniquely covered by a real raster")
            require(not any(_intersects_including_lines(
                        pymupdf.Rect(x["rect"]),dbox)
                        for x in dp.get_drawings()),
                    "Slide vector drawing overlaps panel")
            width=round(sbox.width*render_scale)
            height=round(sbox.height*render_scale)
            require(60<=width<=1800 and 60<=height<=1800
                    and width*height<=1500000
                    and abs(width/render_scale-sbox.width)<.001
                    and abs(height/render_scale-sbox.height)<.001,
                    "Panel render grid not exact or exceeds safety limits")
            a=_pixels(sp,sbox,width,height)
            b=_pixels(dp,dbox,width,height)
            require(a==b,
                    f"Panel {entry['id']}: source-vector and slide-raster pixels differ")
            receipts.append({
                "id":entry["id"],
                "source_bbox":list(sbox),"slide_bbox":list(dbox),
                "render_size":[width,height],
                "matching_rgb_sha256":hashlib.sha256(a).hexdigest(),
                "source_original_label_in_panel":True,
                "source_slide_pixel_identity_verified":True,
                "semantic_label_meaning_certified":False,
            })
    require(_sha(src)==sh and _sha(dst)==dh,
            "Original textbook or slide PDF mutated during QA")
    return {
        "schema_version":1,
        "status":"DECLARED_REFLOWED_VECTOR_PANELS_VISUALLY_MATCHED_REVIEW_REQUIRED",
        "source_sha256":sh,"slides_sha256":dh,
        "figure_id":figure_id,
        "source_page":source_page,"slide_page":slide_page,
        "source_figure_bbox":list(figure),"source_caption_unique":True,
        "declared_panel_count":len(receipts),"panels":receipts,
        "all_original_panel_paths_and_words_accounted_for":True,
        "panel_reflow_render_identity_verified":True,
        "author_intended_complete_panel_boundaries_certified":False,
        "figure_semantics_certified":False,
        "tts_or_video_authorized":False,
        "human_review_claimed":False,
    }
