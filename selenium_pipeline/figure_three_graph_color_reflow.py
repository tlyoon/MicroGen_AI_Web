"""Alternative Figure 8.3 QA: vertical-to-horizontal source graph reflow.

Color-curve shape and sequence can independently corroborate visible graphs
without assuming original source panel labels or blindly comparing one crop.
Passing blue/red curves alone never certifies black axis labels or video.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pymupdf

from .figure_pre_caption_vector_inventory import inventory_pre_caption_vectors
from .figure_slide_raster_visibility import audit_vector_source_slide_raster
from .figure_source_identity import _sha, require


def _dependencies():
    try:
        import cv2
        import numpy as np
        return cv2, np
    except ImportError as exc:
        require(False, f"OpenCV/numpy unavailable: {exc}")


def _runs(signal, *, max_blank=12, min_width=45):
    """Find dense ink regions separated by genuine blank gutters."""
    # A genuine one-pixel-thin graph axis can be the only row ink;
    # require nonzero ink, not two pixels, or synthetic vector art vanishes.
    pos = [int(i) for i, v in enumerate(signal) if v > 0]
    if not pos:
        return []
    runs = []
    start = prev = pos[0]
    for value in pos[1:]:
        if value - prev - 1 >= max_blank:
            if prev - start + 1 >= min_width:
                runs.append([start, prev + 1])
            start = value
        prev = value
    if prev - start + 1 >= min_width:
        runs.append([start, prev + 1])
    return runs


def _blue_red_masks(rgb, cv2, np):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    blue = cv2.inRange(hsv, np.array([88, 75, 75]),
                        np.array([135, 255, 255])) > 0
    # Textbook asymptotes are magenta-red (approximately RGB 236,24,70),
    # while the resampled slide uses pale pink anti-aliasing. Threshold RGB
    # channel dominance rather than treating both as HSV "pure red".
    color = rgb.astype(np.int16)
    red = ((color[:, :, 0] - color[:, :, 1] >= 35) &
           (color[:, :, 0] - color[:, :, 2] >= 20) &
           (color[:, :, 0] >= 140))
    return blue, red


def _shape_difference(source_mask, slide_mask, cv2, np):
    """Compare standardized colored ink contours with symmetric Chamfer error."""
    def norm(mask):
        yy, xx = np.nonzero(mask)
        if len(xx) < 16 or len(yy) < 16:
            return None
        bb = mask[min(yy):max(yy)+1, min(xx):max(xx)+1].astype("uint8")
        if bb.shape[0] < 8 or bb.shape[1] < 8:
            return None
        resized = cv2.resize(bb, (192, 192), interpolation=cv2.INTER_NEAREST)
        return resized != 0
    a, b = norm(source_mask), norm(slide_mask)
    if a is None or b is None:
        return None
    # Pixel-equivalent shape does not mean all original mathematical labels.
    d_to_b = cv2.distanceTransform((~b).astype("uint8"), cv2.DIST_L2, 3)
    d_to_a = cv2.distanceTransform((~a).astype("uint8"), cv2.DIST_L2, 3)
    require(a.any() and b.any(), "Empty colored figure curves")
    error = (float(d_to_b[a].mean()) + float(d_to_a[b].mean())) / (2 * 192)
    return round(error, 6)


def _flat_red_line_score(original_blue, target_blue,
                         original_red, target_red, np):
    """Check thin horizontal asymptote geometry relative to blue ink extent."""
    def describe(red, blue):
        ry, rx = np.nonzero(red)
        by, bx = np.nonzero(blue)
        if len(rx) < 20 or len(bx) < 20:
            return None
        if (ry.max() - ry.min()) > 7 or (rx.max() - rx.min()) < 30:
            return None
        bheight = max(1, by.max() - by.min())
        bwidth = max(1, bx.max() - bx.min())
        return ((float(ry.mean()) - float(by.min())) / bheight,
                (float(rx.max() - rx.min())) / bwidth,
                (float(rx.mean()) - float(bx.min())) / bwidth)
    first, second = describe(original_red, original_blue), describe(target_red, target_blue)
    if first is None or second is None:
        return None
    return round(max(abs(a-b) for a,b in zip(first,second)),6)


def compare_reflowed_graph_color_shapes(source_rgb, slide_rgb, *,
                                        source_bounds, slide_bounds) -> dict:
    """Bounded pure image comparison: requires THREE separated graph regions."""
    cv2, np = _dependencies()
    require(isinstance(source_rgb, np.ndarray) and
            isinstance(slide_rgb, np.ndarray)
            and source_rgb.dtype == slide_rgb.dtype == np.uint8
            and source_rgb.ndim == slide_rgb.ndim == 3
            and source_rgb.shape[2] == slide_rgb.shape[2] == 3
            and source_rgb.size < 20_000_000
            and slide_rgb.size < 8_000_000,
            "Bounded RGB uint8 source and slide arrays required")
    sy0,sy1,sx0,sx1 = source_bounds
    tx0,tx1 = slide_bounds
    require(all(type(x) is int for x in [sy0,sy1,sx0,sx1,tx0,tx1])
            and 0 <= sy0 < sy1 <= source_rgb.shape[0]
            and 0 <= sx0 < sx1 <= source_rgb.shape[1]
            and 0 <= tx0 < tx1 <= slide_rgb.shape[1],
            "Source/slide search window invalid")
    original=source_rgb[sy0:sy1, sx0:sx1]
    target=slide_rgb[:,tx0:tx1]
    ink_orig=(np.min(original,axis=2)<205).sum(axis=1)
    ink_target=(np.min(target,axis=2)<205).sum(axis=0)
    src_runs=_runs(ink_orig,max_blank=18,min_width=55)
    dst_runs=_runs(ink_target,max_blank=18,min_width=48)
    panels=[]
    for i in range(min(len(src_runs),len(dst_runs))):
        sr=src_runs[i]
        tr=dst_runs[i]
        first=original[sr[0]:sr[1],:]
        second=target[:,tr[0]:tr[1]]
        sb,sr_red=_blue_red_masks(first,cv2,np)
        tb,tr_red=_blue_red_masks(second,cv2,np)
        # Independent black-ink geometry: axis lines + mathematical labels
        # are measured, but character recognition or semantic identity is NOT.
        black_source=(np.max(first,axis=2)<165)
        black_slide=(np.max(second,axis=2)<165)
        black=_shape_difference(black_source,black_slide,cv2,np)
        black_shape_plausible=(black is not None and math.isfinite(black)
                               and black <= .045)
        blue=_shape_difference(sb,tb,cv2,np)
        red=_shape_difference(sr_red,tr_red,cv2,np) if sr_red.any() or tr_red.any() else None
        if red is None and sr_red.any() and tr_red.any():
            # A thin horizontal asymptote has zero ink-mask height; compare
            # its normalized position and length relative to BLUE curve.
            red=_flat_red_line_score(sb,tb,sr_red,tr_red,np)
        # Red can legitimately be absent from both *some* panels.
        red_equal_absence=not sr_red.any() and not tr_red.any()
        score_ok=(blue is not None and blue <= .04 and
                  (red_equal_absence or red is not None and red<=.035))
        panels.append({
            "order_index":i,
            "source_scan_band_px":[sr[0]+sy0,sr[1]+sy0],
            "slide_bitmap_scan_band_px":[tr[0]+tx0,tr[1]+tx0],
            "original_blue_curve_pixel_count":int(sb.sum()),
            "slide_blue_curve_pixel_count":int(tb.sum()),
            "source_red_pixel_count":int(sr_red.sum()),
            "slide_red_pixel_count":int(tr_red.sum()),
            "blue_shape_symmetric_chamfer":blue,
            "black_axes_and_label_ink_shape_diagnostic":black,
            "black_ink_geometry_plausible":bool(black_shape_plausible),
            "red_shape_symmetric_chamfer":red,
            "red_absent_in_both":red_equal_absence,
            "blue_red_curve_shapes_coherent":bool(score_ok),
            "original_math_axis_and_labels_verified":False,
        })
    count = len(src_runs)
    all_curves = (2 <= count <= 6 and count == len(dst_runs) == len(panels)
                  and all(row["blue_red_curve_shapes_coherent"]
                          for row in panels))
    all_black = (all_curves and all(row["black_ink_geometry_plausible"]
                                    for row in panels))
    prefix = "THREE_GRAPH" if count == 3 else "MULTI_GRAPH"
    return {
        "schema_version":1,
        "status":(f"{prefix}_COLOR_AND_BLACK_INK_REFLOW_CORROBORATED_REVIEW_REQUIRED"
                  if all_black else f"{prefix}_BLACK_INK_INCOMPLETE_REVIEW_REQUIRED"
                  if all_curves else f"{prefix}_CURVE_REFLOW_INCOMPLETE_REVIEW_REQUIRED"),
        "detected_graph_count":count,
        "original_vertical_graph_run_count":len(src_runs),
        "slide_horizontal_graph_run_count":len(dst_runs),
        "three_graph_curve_shape_sequence_coherent":bool(all_curves),
        "three_graph_black_ink_geometry_plausible":bool(all_black),
        "graph_correspondence_evidence":panels,
        "original_complete_axes_labels_legend_certified":False,
        "full_source_figure_equivalence_certified":False,
        "scientific_math_review_certified":False,
        "narrated_element_highlights_verified":False,
        "video_or_publication_authorized":False,
    }


def audit_real_three_graph_reflow(*, source:Path, slides:Path,
                                 source_page:int, slide_page:int,
                                 figure_id:str)->dict:
    cv2,np=_dependencies()
    source=Path(source).absolute()
    slides=Path(slides).absolute()
    inv=inventory_pre_caption_vectors(
        source=source,page_number=source_page,figure_id=figure_id)
    vis=audit_vector_source_slide_raster(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    require(vis["source_sha256"]==inv["source_sha256"]
            and vis["slide_reference_render_pixels_equal"],
            "Independent original figure or actual slide bitmap not verified")
    with pymupdf.open(source) as doc,pymupdf.open(slides) as deck:
        page=doc[source_page-1]
        pix=page.get_pixmap(matrix=pymupdf.Matrix(3,3),
                            colorspace=pymupdf.csRGB,alpha=False)
        src=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
        images=[x for x in deck[slide_page-1].get_image_info(xrefs=True)
                if int(x["width"])>=48 and int(x["height"])>=48
                and pymupdf.Rect(x["bbox"]).width>=50
                and pymupdf.Rect(x["bbox"]).height>=25]
        require(len(images)==1 and type(images[0].get("xref")) is int
                and images[0]["xref"]>0,"No single material embedded slide image")
        encoded=deck.extract_image(images[0]["xref"])["image"]
        bgr=cv2.imdecode(np.frombuffer(encoded,np.uint8),cv2.IMREAD_COLOR)
        require(bgr is not None and bgr.size <= 8_000_000,
                "Invalid bounded real slide bitmap")
        slide=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
        heading=inv["heading_bbox"]
        stop=int(math.floor((float(heading[1])-4)*3))
        start=int(round(max(page.rect.height*.07,float(heading[1])*.155)*3))
        start=max(0,start)
        x_start=max(0,int((float(heading[0])-9)*3))
        x_end=min(src.shape[1],int(min(float(inv["candidate_scan_corridor"][2])-15,
                   float(heading[0])+160)*3))
        require(0<=start<stop<=src.shape[0]
                and 0<=x_start<x_end<=src.shape[1],
                "Invalid textbook left-column figure scan")
        report=compare_reflowed_graph_color_shapes(
            src,slide,
            source_bounds=(start,stop,x_start,x_end),
            slide_bounds=(0,slide.shape[1]))
    require(_sha(source)==inv["source_sha256"]
            and _sha(slides)==vis["slides_sha256"],
            "Original textbook or slide changed")
    return {**report,
            "figure_id":figure_id,"source_page":source_page,
            "slide_page":slide_page,
            "original_pdf_sha256":inv["source_sha256"],
            "existing_slides_pdf_sha256":vis["slides_sha256"]}


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--source-page",type=int,required=True)
    p.add_argument("--slide-page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    a=p.parse_args(argv)
    print(json.dumps(audit_real_three_graph_reflow(
        source=a.source,slides=a.slides,source_page=a.source_page,
        slide_page=a.slide_page,figure_id=a.figure_id),
        indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
