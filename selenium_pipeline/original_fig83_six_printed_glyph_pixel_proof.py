"""Actual publisher Figure 8.3 equation-glyph and zero-axis PIXEL acceptance.

PREVIOUS full three-panel art identity & geometric mapping is reused byte-for-
byte from PR452. Never reruns figure search or re-encodes/pays for an image.
Proves 6 source-printed label patches on exactly the frozen original author
bitmap, but NOT graph curve truth, nonzero tick values or spoken-word timing.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .evidence_reuse_contract import file_sha256, EvidenceReuseBlocked
from .recover_pinned_original_thomas_corpus import ORIGINAL_PINS

STATUS="ORIGINAL_THOMAS84_FIG83_SIX_SOURCE_PRINTED_GLYPH_PATCHES_IN_AUTHOR_PIXELS_PASS_NONPRODUCTION"
PRIOR_STATUS="ORIGINAL_FIGURE82_83_ALL_THREE_PANELS_TEXTBOOK_SOURCE_FEATURE_PROVEN_LABELS_PENDING"
FAMILIES=(("tan",1,(52,95,108,132)),("sin",2,(110,164,189,221)),
          ("sec",3,(112,169,330,357)))
ZEROS=((1,(104,115,129,144)),(2,(104,115,245,258)),(3,(104,115,381,393)))

def _require(ok,why):
    if not ok: raise EvidenceReuseBlocked(why)

def _source_word(page,token,x0,x1,y0,y1):
    import pymupdf
    words=[w for w in page.get_text("words") if
           x0<=w[0]<=x1 and y0<=w[1]<=y1 and
           ((token=="tan" and w[4].replace("−","-")=="tan-1") or
            (token=="sin" and w[4].replace("−","-")=="sin-1") or
            (token=="sec" and w[4].replace("−","-")=="sec-1") or
            (token=="zero" and w[4]=="0"))]
    _require(len(words)==1,f"Missing/multiple original source {token} equation glyph")
    return [float(x) for x in words[0][:4]]

def registered_patch(*,author,source_warp,homography,box,
                     min_correlation:float)->dict:
    import cv2,numpy as np
    _require(type(min_correlation) is float and .70<min_correlation<1,
             "Unsafe label alignment acceptance threshold")
    _require(author.ndim==2 and source_warp.shape==author.shape,
             "Source/author pixels lack common grayscale coordinate system")
    h,w=author.shape
    src=np.asarray([[[box[0]*2,box[1]*2]],
                    [[box[2]*2,box[3]*2]]],dtype=np.float32)
    points=cv2.perspectiveTransform(src,np.linalg.inv(homography)).reshape(2,2)
    x0,y0=np.floor(points[0]).astype(int)
    x1,y1=np.ceil(points[1]).astype(int)
    x0=max(0,x0-2);y0=max(0,y0-2)
    x1=min(w,x1+2);y1=min(h,y1+2)
    _require(x1-x0>=9 and y1-y0>=10 and 0<=x0<x1<=w
             and 0<=y0<y1<=h,"Source word patch outside original bitmap")
    a=author[y0:y1,x0:x1].astype(np.float64)
    b=source_warp[y0:y1,x0:x1].astype(np.float64)
    _require(a.std()>12 and b.std()>12 and (a<170).mean()>.025
             and (b<170).mean()>.025,
             "Source/author mathematical label patch has insufficient genuine ink")
    correlation=float(np.corrcoef(a.ravel(),b.ravel())[0,1])
    _require(math.isfinite(correlation) and correlation>=min_correlation,
             "Exact original publisher function/tick glyph pixels changed, cropped or missing")
    return {
        "registered_author_rect_px":[int(x0),int(y0),int(x1),int(y1)],
        "source_original_pdf_glyph_bbox_pt":[round(float(q),3) for q in box],
        "registered_normalized_source_to_author_gray_correlation":round(correlation,5),
        "independent_nonempty_ink_both_sources":True,
        "this_exact_source_printed_glyph_has_original_author_bitmap_pixel_evidence":True,
    }

def audit(*,original:Path,registration_receipt:Path)->dict:
    import cv2,pymupdf,numpy as np
    original=Path(original).absolute()
    registration_receipt=Path(registration_receipt).absolute()
    expected_pub,expected_slides=ORIGINAL_PINS["8.4"]
    prior_paths=[original/n for n in (
        "source.pdf","slides.pdf","Figure 8.3.png")]
    _require(all(p.is_file() and not p.is_symlink() for p in
                 prior_paths+[registration_receipt]),
             "Frozen publisher figure or previous accepted 3-panel proof missing")
    prior_hashes={p.name:file_sha256(p) for p in prior_paths}
    original_prev_sha=file_sha256(registration_receipt)
    _require(prior_hashes["source.pdf"]==expected_pub
             and prior_hashes["slides.pdf"]==expected_slides,
             "Different original publisher/author version: old label proof invalid")
    old=json.loads(registration_receipt.read_text("utf8"))
    _require(old.get("status")==PRIOR_STATUS and
             old.get("publisher_source_sha256")==expected_pub and
             old.get("student_publication_authorized") is False and
             old.get("whole_panels_axis_labels_symbol_meaning_certified") is False,
             "Wrong or falsely upgraded old Figure 8.3 artwork receipt")
    fig=old["two_exact_source_figure_panel_image_matches"]["8.3"]
    _require(fig.get("original_author_png_sha256")==prior_hashes["Figure 8.3.png"]
             and fig.get("publisher_page")==2 and
             fig.get("original_author_slide")==6 and
             fig.get("corridor_2x")==[0,0,600,1000] and
             fig.get("all_three_source_image_panel_artwork_correspondence_proven") is True
             and fig.get("geometric_RANSAC_inliers")>=35
             and fig.get("author_image_thirds_inlier_counts")==[19,15,8],
             "Previously proved original figure layout/SIFT registration invalid")
    hmatrix=np.array(fig["estimated_source_image_similarity_transform"],
                     dtype=np.float64)
    _require(hmatrix.shape==(3,3) and np.isfinite(hmatrix).all()
             and abs(np.linalg.det(hmatrix))>1e-5,
             "Original 3-panel proof has invalid perspective transform")
    author=cv2.imread(str(original/"Figure 8.3.png"),cv2.IMREAD_GRAYSCALE)
    _require(author is not None and author.shape==(480,232),
             "Original author graph bitmap dimensions changed")
    with pymupdf.open(original/"source.pdf") as textbook:
        page=textbook[1]
        pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
        source=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
        source_gray=cv2.cvtColor(source,cv2.COLOR_RGB2GRAY)[:1000,:600]
        # The exact previous homography maps author pixels INTO publisher
        # 2x source coordinates; do not rediscover/re-optimize the transform.
        source_warp=cv2.warpPerspective(source_gray,hmatrix,
              (author.shape[1],author.shape[0]),
              flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,borderValue=255)
        rows={}
        for family,idx,area in FAMILIES:
            box=_source_word(page,family,*area)
            rows[f"{idx}_{family}_inverse_printed_function_label"]={
                **registered_patch(author=author,source_warp=source_warp,
                       homography=hmatrix,box=box,min_correlation=.78),
                "source_function_family":family,
                "source_graph_panel_index":idx,
                "label_is_source_vector_glyph_not_guessed_ocr":True,
            }
        for idx,area in ZEROS:
            box=_source_word(page,"zero",*area)
            rows[f"{idx}_axis_zero_tick"]={
                **registered_patch(author=author,source_warp=source_warp,
                       homography=hmatrix,box=box,min_correlation=.83),
                "source_graph_panel_index":idx,
                "label_is_source_vector_glyph_not_guessed_ocr":True,
            }
    _require(len(rows)==6 and all(v[
                 "this_exact_source_printed_glyph_has_original_author_bitmap_pixel_evidence"
                 ] is True for v in rows.values()),
             "All three actual original graph labels and zero ticks required")
    _require({p.name:file_sha256(p) for p in prior_paths}==prior_hashes
             and file_sha256(registration_receipt)==original_prev_sha,
             "Prior accepted evidence or original publisher/author source changed")
    return {
        "status":STATUS,"publisher_source_pdf_sha256":expected_pub,
        "original_author_slides_pdf_sha256":expected_slides,
        "original_author_figure_png_sha256":prior_hashes["Figure 8.3.png"],
        "reused_previous_three_panel_registration_receipt_sha256":original_prev_sha,
        "registration_reused_without_redoing_similarity":True,
        "original_source_figure_publisher_page":2,
        "original_author_figure_slide":6,
        "three_inverse_function_labels_pixel_matched":3,
        "three_graph_axis_zero_tick_labels_pixel_matched":3,
        "six_independent_source_printed_math_glyph_patch_pixel_receipts":rows,
        "all_nonzero_ticks_axis_shapes_and_curve_mathematics_certified":False,
        "all_spoken_fig83_label_word_times_certified":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--previous-registration",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    _require(a.out.parent.is_dir() and not a.out.exists()
             and not a.out.is_relative_to(a.original.absolute()),
             "Only new immutable QA receipts outside original source allowed")
    result=audit(original=a.original,registration_receipt=a.previous_registration)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":result["status"],
         "matched_printed_original_glyphs":len(
             result["six_independent_source_printed_math_glyph_patch_pixel_receipts"]),
         "student_publication_authorized":False}))
if __name__=="__main__":
    main()
