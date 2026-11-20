"""Original Figure 8.2 to Slide 4 *pixel* registration, not mathematical QA.

Source PDF pixels are independently rendered and compared to the original
embedded slide bitmap. Strictly read-only; alignment never approves triangle
semantics, narration highlighting, audio or student publication.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

import pymupdf
from PIL import Image

from .figure_source_identity import require, _sha
from .original_figure82_source_label_order import inspect_original_figure82_label_order
from .original_composite_gutter_proposals import inspect_original_composite_gutters


def score_registered_pixels(*, original_page_gray, slide_gray,
                             scan_box_px:tuple[int,int,int,int],
                             strip_boundaries_px:tuple[int,...]) -> dict:
    """Reject blank/changed/misregistered imagery and each displaced strip."""
    import numpy as np
    import cv2

    source=np.asarray(original_page_gray)
    target=np.asarray(slide_gray)
    require(source.ndim==2 and target.ndim==2 and source.dtype==np.uint8
            and target.dtype==np.uint8 and 60<=target.shape[0]<=800
            and 150<=target.shape[1]<=1600
            and target.size<=500_000 and source.size<=7_000_000,
            "Invalid bounded source or slide image for pixel registration")
    require(type(scan_box_px) is tuple and len(scan_box_px)==4,
            "Bounded source figure search box required")
    x0,y0,x1,y1=scan_box_px
    require(all(type(x) is int for x in scan_box_px)
            and 0<=x0<x1<=source.shape[1]
            and 0<=y0<y1<=source.shape[0]
            and x1-x0>=target.shape[1] and y1-y0>=target.shape[0],
            "Source image figure scan window missing or too small")
    require(type(strip_boundaries_px) is tuple
            and len(strip_boundaries_px)==4
            and strip_boundaries_px[0]==0
            and strip_boundaries_px[-1]==target.shape[1]
            and all(type(x) is int for x in strip_boundaries_px)
            and all(b-a>=60 for a,b in zip(strip_boundaries_px,strip_boundaries_px[1:])),
            "Unverified or overlapping native slide strip boundaries")
    require(float(target.std())>=15,
            "Original slide raster lacks informative source texture")
    roi=source[y0:y1,x0:x1]
    correlations=cv2.matchTemplate(roi,target,cv2.TM_CCOEFF_NORMED)
    _,peak,_,loc=cv2.minMaxLoc(correlations)
    require(peak>=0.90,
            "Original slide figure not reliably registered to source pixels")
    sx=x0+loc[0];sy=y0+loc[1]
    matched=source[sy:sy+target.shape[0],sx:sx+target.shape[1]]
    mae=float(np.abs(matched.astype(np.int16)-target.astype(np.int16)).mean())
    require(mae<=8.0, "Original source and slide raster differ beyond tolerance")
    metrics=[]
    for idx,(a,b) in enumerate(zip(strip_boundaries_px,strip_boundaries_px[1:]),1):
        ref=matched[:,a:b];candidate=target[:,a:b]
        require(float(candidate.std())>=10 and float(ref.std())>=10,
                "Blank or low-information figure strip")
        cc=float(cv2.matchTemplate(ref,candidate,cv2.TM_CCOEFF_NORMED)[0,0])
        difference=float(np.abs(ref.astype(np.int16)-candidate.astype(np.int16)).mean())
        require(cc>=0.88 and difference<=10,
                "Individual figure panel source-to-slide pixel identity failed")
        metrics.append({
            "candidate_ordinal":idx,
            "normalized_source_pixel_correlation":round(cc,6),
            "grayscale_mean_absolute_difference":round(difference,6),
            "registered_source_strip_sha256":hashlib.sha256(ref.tobytes()).hexdigest(),
            "source_triangle_semantics_verified":False,
        })
    return {
        "full_figure_normalized_pixel_correlation":round(float(peak),6),
        "full_figure_grayscale_mean_absolute_difference":round(mae,6),
        "matching_source_pixel_box_at_render_scale":
            [sx,sy,sx+target.shape[1],sy+target.shape[0]],
        "strip_pixel_registration_metrics":metrics,
        "individual_strip_count":len(metrics),
        "pixel_similarity_verified":True,
        "triangle_meanings_or_side_labels_verified":False,
    }


def inspect_original_figure82_pixel_registration(*,folder:Path) -> dict:
    """Pilot is explicitly anchored to ORIGINAL Thomas 8.4 Figure 8.2."""
    root=Path(folder).absolute()
    require(root.is_dir() and not root.is_symlink(),"Immutable source folder required")
    source,slides,script=(root/p for p in ("source.pdf","slides.pdf","script.txt"))
    hashes=tuple(_sha(p) for p in (source,slides,script))
    label_report=inspect_original_figure82_label_order(folder=root)
    strips=inspect_original_composite_gutters(folder=root,slide=4)
    require((label_report["source_sha256"],label_report["slides_sha256"],
             label_report["script_sha256"])==hashes
            and (strips["original_source_sha256"],strips["original_slides_sha256"],
                 strips["original_script_sha256"])==hashes,
            "Independent original source and slide checks disagree")
    require(len(label_report["ordered_review_candidates"])==3
            and len(strips["candidate_strips"])==3
            and strips["native_composite_width"]==409
            and strips["native_composite_height"]==134,
            "Original review-specific Figure 8.2 geometry has changed")

    # Cross-check proposals and raster crop SHA BEFORE any pixel registration.
    cut=[0]
    for i,(proposal,item) in enumerate(zip(strips["candidate_strips"],
                                           label_report["ordered_review_candidates"]),1):
        require(proposal["candidate_index"]==i
                and item["candidate_ordinal"]==i
                and proposal["panel_native_pixel_sha256"]
                    ==item["slide_image_candidate_native_sha256"],
                "Gutter or physical label mapping changed between checks")
        cut.append(proposal["native_bbox_px"][2])
    require(cut[-1]==409 and tuple(cut)==(0,120,246,409),
            "Original composite pixel boundaries changed from inspected pilot")

    try:
        import numpy as np
        import cv2
    except ImportError:
        return {
            "status":"CV2_NUMPY_UNAVAILABLE_PIXEL_REGISTRATION_REVIEW_REQUIRED",
            "source_sha256":hashes[0],
            "slides_sha256":hashes[1],
            "source_to_slide_pixel_fidelity_verified":False,
            "independent_math_approval":False,
            "student_publication_authorized":False,
        }

    with pymupdf.open(source) as book,pymupdf.open(slides) as deck:
        require(len(book)>=1 and len(deck)>=4,
                "Expected physical original textbook/slide pages unavailable")
        target_images=[x for x in deck[3].get_image_info(xrefs=True)
                       if x["width"]>=48 and x["height"]>=48]
        require(len(target_images)==1
                and type(target_images[0].get("xref")) is int
                and target_images[0]["xref"]>0,
                "Exactly one source Slide4 embedded composite required")
        with Image.open(BytesIO(deck.extract_image(target_images[0]["xref"])["image"])) as im:
            target=np.asarray(im.convert("L"),dtype=np.uint8)
        caption=label_report["source_caption_geometry"]
        results=[]
        for zoom in (1.45,1.5,1.55):
            pix=book[0].get_pixmap(
                matrix=pymupdf.Matrix(zoom,zoom),
                colorspace=pymupdf.csGRAY,alpha=False)
            arr=np.frombuffer(pix.samples,dtype=np.uint8).reshape(
                pix.height,pix.width)
            roi=(int((caption[0]-24)*zoom),
                 int((caption[1]-125)*zoom),
                 int((caption[0]+289)*zoom),
                 int((caption[1]+29)*zoom))
            try:
                result=score_registered_pixels(
                    original_page_gray=arr,slide_gray=target,
                    scan_box_px=roi,strip_boundaries_px=tuple(cut))
            except ValueError:
                continue
            results.append((zoom,result))
        require(len(results)==1 and results[0][0]==1.5,
                "Multiple or zero unique original textbook pixel registrations")
        zoom,match=results[0]
    require(tuple(_sha(p) for p in (source,slides,script))==hashes,
            "Protected original source assets changed during registration")
    box=match.pop("matching_source_pixel_box_at_render_scale")
    return {
        "status":"ORIGINAL_FIGURE82_SLIDE4_PIXEL_FIDELITY_VERIFIED_MATH_QA_PENDING",
        "source_sha256":hashes[0],
        "slides_sha256":hashes[1],
        "script_sha256":hashes[2],
        "original_textbook_physical_page":1,
        "original_lecture_slide":4,
        "matched_source_render_zoom":zoom,
        "matched_source_pdf_bbox_pt":[round(v/zoom,5) for v in box],
        "source_figure_printed_label_order_consistent":True,
        **match,
        "original_source_to_slide_pixel_similarity_accepted":True,
        "source_figure_triangle_side_geometry_verified":False,
        "narration_highlight_alignment_verified":False,
        "independent_AI_mathematical_consensus_verified":False,
        "human_academic_listening_approval":False,
        "genuine_Kore_TTS_authorized":False,
        "student_publication_authorized":False,
        "new_Gemini_request_sent":False,
    }


def main(argv=None)->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--folder",required=True,type=Path)
    args=ap.parse_args(argv)
    print(json.dumps(inspect_original_figure82_pixel_registration(folder=args.folder),
                     indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
