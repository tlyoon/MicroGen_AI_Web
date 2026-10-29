"""Compare ORIGINAL PDF inverse-function glyph ink to EXISTING slide bitmap.

No OCR, source alterations or approximate word-level speech alignment.
Corroborates three individual printed operator glyphs by a scale-sweep
template, not entire mathematical/axis/curve correctness.
"""
from __future__ import annotations

import argparse
import io
import math
from pathlib import Path

import pymupdf
from PIL import Image

from .figure_source_identity import require,_sha
from .figure_original_math_labels import audit_original_graph_labels
from .figure83_original_inverse_label_identity import (
    audit_original_inverse_labels, INVERSE_LABEL, _normalized_word)
from .figure_three_graph_color_reflow import (
    _dependencies, audit_real_three_graph_reflow)

def _black(rgb,np):
    require(isinstance(rgb,np.ndarray) and rgb.ndim==3
            and rgb.shape[2]==3 and rgb.dtype==np.uint8
            and 0<rgb.size<20_000_000,
            "Require bounded real RGB image to extract glyph ink")
    return ((rgb[:,:,0]<170)&(rgb[:,:,1]<170)&
            (rgb[:,:,2]<170)).astype("uint8")*255

def _best_template(original_black,target_black,cv2,np)->dict:
    require(original_black.ndim==target_black.ndim==2
            and original_black.shape[0]>=8 and original_black.shape[1]>=8
            and target_black.shape[0]>=12 and target_black.shape[1]>=12
            and int((original_black>0).sum())>=15
            and int((target_black>0).sum())>=15,
            "Missing/malformed original or displayed label black ink")
    best=(-1.,0.,[0,0],[0,0])
    for scale in range(27,90,3):
        factor=scale/100.
        template=cv2.resize(original_black,None,fx=factor,fy=factor,
                            interpolation=cv2.INTER_AREA)
        if template.shape[0]<4 or template.shape[1]<4 or (
                template.shape[0]>=target_black.shape[0] or
                template.shape[1]>=target_black.shape[1]):
            continue
        metric=cv2.matchTemplate(target_black,template,cv2.TM_CCOEFF_NORMED)
        _,peak,_,position=cv2.minMaxLoc(metric)
        if math.isfinite(peak) and peak>best[0]:
            best=(float(peak),factor,[int(position[0]),int(position[1])],
                  [int(template.shape[1]),int(template.shape[0])])
    require(best[0]>=0,"No reliable bounded original glyph search")
    return {"normalized_correlation":round(best[0],5),
            "relative_pixel_scale":best[1],
            "panel_local_top_left_px":best[2],
            "template_size_px":best[3],
            "panel_size_px":[int(target_black.shape[1]),int(target_black.shape[0])]}

def validate_glyph_matrix(matrix:list,*,min_score:float=.75,
                          min_margin:float=.075)->dict:
    """Fail closed if another panel/label competes or a glyph disappears."""
    require(type(min_score) in (float,int) and type(min_margin) in (float,int)
            and math.isfinite(min_score) and math.isfinite(min_margin)
            and 0 < min_score <= 1 and 0 < min_margin <= 1,
            "Invalid finite strict glyph acceptance thresholds")
    require(type(matrix) is list and len(matrix)==3
            and all(type(row) is list and len(row)==3 for row in matrix)
            and all(type(x) in (float,int) and math.isfinite(x)
                    and -1<=x<=1 for row in matrix for x in row),
            "Invalid 3x3 independent operator-pixel evidence")
    panels=[]
    for i in range(3):
        own=float(matrix[i][i])
        best_other_row=max(float(matrix[i][j]) for j in range(3) if j!=i)
        best_other_col=max(float(matrix[j][i]) for j in range(3) if j!=i)
        margin=min(own-best_other_row,own-best_other_col)
        accepted=(own>=min_score and margin>=min_margin)
        panels.append({"source_panel_index":i+1,
            "existing_slide_panel_index":i+1,
            "original_operator_label_correlation":round(own,5),
            "closest_competing_label_or_panel":round(
                max(best_other_row,best_other_col),5),
            "uniqueness_margin":round(margin,5),
            "original_to_existing_bitmap_operator_glyph_correspondence_verified":
                bool(accepted)})
    return {"operator_glyph_matches":panels,
        "all_three_source_inverse_operator_glyphs_in_slide_verified":
            all(x["original_to_existing_bitmap_operator_glyph_correspondence_verified"]
                for x in panels)}

def validate_scale_coherence(details:list,*,max_ratio:float=2.0)->dict:
    """Check that the three matching original glyphs have plausible common scale.

    This is supplemental image-registration consistency, not math correctness.
    """
    require(type(max_ratio) in (int,float) and math.isfinite(max_ratio)
            and 1 <= max_ratio <= 3,
            "Invalid bounded scale coherence threshold")
    require(type(details) is list and len(details)==3
            and all(type(row) is list and len(row)==3 for row in details),
            "Expected all nine independent original-to-slide image searches")
    values=[]
    for i,row in enumerate(details):
        match=row[i]
        require(type(match) is dict
                and type(match.get("relative_pixel_scale")) in (float,int)
                and math.isfinite(match["relative_pixel_scale"])
                and .25 <= match["relative_pixel_scale"] <= .9,
                "Missing bounded diagonal source-to-slide glyph pixel scale")
        values.append(float(match["relative_pixel_scale"]))
    ratio=max(values)/min(values)
    return {"diagonal_original_operator_pixel_scales":values,
            "max_operator_scale_ratio":round(ratio,5),
            "matched_operator_label_scales_consistent":ratio<=max_ratio}

def derive_slide_operator_boxes(details:list, bands:list, *,width:int,height:int)->list[dict]:
    """Map matched ORIGINAL glyph pixels into actual EXISTING slide-bitmap pixels.

    Bounding boxes are review anchors, never spoken-word timing evidence.
    """
    require(type(width) is int and type(height) is int
            and 0<width<=3000 and 0<height<=3000
            and type(details) is list and len(details)==3
            and type(bands) is list and len(bands)==3,
            "Untrusted slide figure pixel canvas")
    boxes=[]
    for i in range(3):
        require(type(details[i]) is list and len(details[i])==3,
                "Missing glyph comparison row")
        point=details[i][i]
        require(type(point) is dict
                and type(point.get("panel_local_top_left_px")) is list
                and type(point.get("template_size_px")) is list
                and type(point.get("panel_size_px")) is list
                and type(bands[i]) in (list,tuple) and len(bands[i])==2,
                "Incomplete matched original glyph location")
        x,y=point["panel_local_top_left_px"]
        tw,th=point["template_size_px"]
        pw,ph=point["panel_size_px"]
        start,end=bands[i]
        require(all(type(n) is int for n in (x,y,tw,th,pw,ph,start,end))
                and 0<=start<end<=width and pw==end-start and ph==height
                and tw>0 and th>0 and 0<=x<x+tw<=pw
                and 0<=y<y+th<=height,
                "Original operator glyph template escaped its actual slide panel")
        boxes.append({"panel_index":i+1,
            "matched_original_glyph_bbox_on_existing_slide_bitmap_px":
              [start+x,y,start+x+tw,y+th],
            "mathematical_complete_equation_verified":False,
            "narrated_spoken_word_timing_verified":False})
    return boxes

def audit_source_to_slide_inverse_glyphs(*,source:Path,slides:Path,
                                        source_page:int=2,slide_page:int=5,
                                        figure_id:str="8.3")->dict:
    source,slides=Path(source).absolute(),Path(slides).absolute()
    before=(_sha(source),_sha(slides))
    label_identity=audit_original_inverse_labels(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    originals=audit_original_graph_labels(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    geometry=audit_real_three_graph_reflow(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    require([label_identity["source_sha256"],label_identity["slides_sha256"]]
            ==list(before)
            and [geometry["original_pdf_sha256"],geometry["existing_slides_pdf_sha256"]]
            ==list(before)
            and geometry["detected_graph_count"]==3
            and geometry["three_graph_black_ink_geometry_plausible"] is True,
            "Existing source figure must be independently reflow corroborated")
    cv2,np=_dependencies()
    with pymupdf.open(source) as textbook,pymupdf.open(slides) as deck:
        pix=textbook[source_page-1].get_pixmap(
            matrix=pymupdf.Matrix(3,3),colorspace=pymupdf.csRGB,alpha=False)
        rendered=np.asarray(Image.frombytes(
            "RGB",(pix.width,pix.height),pix.samples))
        shown=[x for x in deck[slide_page-1].get_image_info(xrefs=True)
               if int(x["width"])>=48 and int(x["height"])>=48
               and int(x.get("xref",0))>0
               and pymupdf.Rect(x["bbox"]).width>=50
               and pymupdf.Rect(x["bbox"]).height>=25]
        require(len(shown)==1,"Actual original slide figure bitmap must be unique")
        with Image.open(io.BytesIO(
                deck.extract_image(shown[0]["xref"])["image"])) as im:
            require(im.width*im.height<=2_000_000,
                    "Oversized original slide figure bitmap")
            displayed=np.asarray(im.convert("RGB"))
    templates=[]
    for source_panel in originals["panels"]:
        tokens=[x for x in source_panel["original_printed_tokens"]
                if INVERSE_LABEL.fullmatch(_normalized_word(x["text"]))]
        require(len(tokens)==1,"Source panel missing unique original math glyph")
        x0,y0,x1,y1=tokens[0]["original_bbox_pt"]
        # Actual 3x source PDF pixels, preserving original glyphs.
        coordinates=(int(x0*3),int(y0*3),int(x1*3+1),int(y1*3+1))
        left,top,right,bottom=coordinates
        require(0<=left<right<=rendered.shape[1]
                and 0<=top<bottom<=rendered.shape[0],
                "Original inverse-function glyph extends outside PDF")
        templates.append(_black(rendered[top:bottom,left:right],np))
    regions=[]
    for match in geometry["graph_correspondence_evidence"]:
        start,end=match["slide_bitmap_scan_band_px"]
        require(0<=start<end<=displayed.shape[1],
                "Untrusted source-to-slide bitmap graph band")
        regions.append(_black(displayed[:,start:end],np))
    details=[[_best_template(a,b,cv2,np) for b in regions] for a in templates]
    scores=[[e["normalized_correlation"] for e in row] for row in details]
    compared=validate_glyph_matrix(scores)
    actual_bands=[x["slide_bitmap_scan_band_px"]
                  for x in geometry["graph_correspondence_evidence"]]
    operator_boxes=derive_slide_operator_boxes(
        details,actual_bands,width=int(displayed.shape[1]),
        height=int(displayed.shape[0]))
    scale_evidence=validate_scale_coherence(details)
    require([_sha(source),_sha(slides)]==list(before),
            "Original Figure 8.3 sources changed during glyph matching")
    require(scale_evidence["matched_operator_label_scales_consistent"],
            "Three original-to-slide operator glyph scales disagree")
    return {"schema_version":1,
        "status":("SOURCE_AND_SLIDE_INVERSE_OPERATOR_GLYPHS_CORROBORATED_REVIEW_REQUIRED"
                  if compared["all_three_source_inverse_operator_glyphs_in_slide_verified"]
                  else "ORIGINAL_SLIDE_INVERSE_LABEL_PIXEL_MATCH_INCOMPLETE_REVIEW_REQUIRED"),
        "original_source_sha256":before[0],
        "existing_slides_sha256":before[1],
        "figure_id":figure_id,
        "original_source_function_labels":label_identity["panels"],
        "original_to_slide_operator_match_score_matrix":scores,
        "original_to_slide_operator_match_locations":details,
        **compared,
        **scale_evidence,
        "source_operator_target_pixel_boxes_for_review":operator_boxes,
        "complete_equation_x_over_a_and_theta_glyphs_verified":False,
        "all_axes_and_ticks_mathematically_correct_verified":False,
        "source_plot_mathematical_curve_equivalence_verified":False,
        "spoken_element_narration_timing_verified":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False}

def main(argv=None):
    import json
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("source","slides"):
        p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args(argv)
    r=audit_source_to_slide_inverse_glyphs(source=a.source,slides=a.slides)
    print(json.dumps(r,indent=2,sort_keys=True))
    return 2
if __name__=="__main__":
    raise SystemExit(main())
