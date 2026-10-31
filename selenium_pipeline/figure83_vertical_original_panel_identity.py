"""Verify real Figure 8.3 *vertical* slide reflow using original textbook.

The older horizontal-slide assumption merged all three source graphs into one
slide band. This is a separate bounded, reproducible investigation of the
actual 232x480 bitmap on ORIGINAL §8.4 slide 6.

Checks independent original PDF vector geometry, three colored curve shapes,
black axes/label ink, printed original inverse mathematical operator names,
and a full cross-panel 3x3 original glyph similarity/uniqueness matrix.

Does NOT assert numerical axis tick equality, full scientific equation truth,
sentence-to-figure PCM timing or student release. Those need further evidence.
Run only on authorized Dell-115 Windows Python with OpenCV.
"""
from __future__ import annotations
import argparse
import io
import json
import math
from pathlib import Path

import pymupdf
from PIL import Image
from .figure_source_identity import require,_sha
from .figure_pre_caption_vector_inventory import inventory_pre_caption_vectors
from .figure_slide_raster_visibility import audit_vector_source_slide_raster
from .figure_original_math_labels import classify_original_panel_words
from .figure83_original_inverse_label_identity import (
    identify_original_panel_labels,INVERSE_LABEL,_normalized_word)
from .figure83_slide_inverse_glyph_correspondence import (
    _black,_best_template,validate_glyph_matrix)
from .figure_three_graph_color_reflow import (
    _dependencies,_runs,_blue_red_masks,_shape_difference,_flat_red_line_score)

PINNED_ORIGINAL_SOURCE="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
SOURCE_PAGE=2
ORIGINAL_SLIDE_PAGE=6
FIGURE_ID="8.3"

def choose_original_slide_axis(*,image_width:int,image_height:int)->str:
    require(type(image_width) is int and type(image_height) is int
            and 40<=image_width<=2000 and 40<=image_height<=2000,
            "Missing bounded genuine source-slide bitmap dimensions")
    # Orientation is measured from actual embedded bitmap—not hard-coded
    # graph panel order or historical slide number.
    if image_height >= image_width*1.4:
        return "vertical"
    if image_width >= image_height*1.4:
        return "horizontal"
    return "undetermined"

def audit(*,source:Path,slides:Path)->dict:
    source,slides=Path(source).absolute(),Path(slides).absolute()
    require(source.is_file() and slides.is_file()
            and not source.is_symlink() and not slides.is_symlink(),
            "Original publisher PDF and original slides.pdf required")
    originals=(_sha(source),_sha(slides))
    require(originals[0]==PINNED_ORIGINAL_SOURCE,
            "Do not infer label identity from another unrecognized publisher source")
    inventory=inventory_pre_caption_vectors(source=source,
                                             page_number=SOURCE_PAGE,figure_id=FIGURE_ID)
    visible=audit_vector_source_slide_raster(
        source=source,slides=slides,source_page=SOURCE_PAGE,
        slide_page=ORIGINAL_SLIDE_PAGE,figure_id=FIGURE_ID)
    require(inventory["source_sha256"]==originals[0]
            and visible["source_sha256"]==originals[0]
            and visible["slides_sha256"]==originals[1]
            and visible["slide_reference_render_pixels_equal"] is True,
            "Original vector/source and actual slide bitmap provenance not corroborated")
    cv2,np=_dependencies()  # no unapproved fallback to guessed figure descriptions
    with pymupdf.open(source) as pdf,pymupdf.open(slides) as deck:
        require(len(deck)==17 and len(pdf)>=4,
                "Wrong Thomas 8.4 lecture source or changed slide count")
        page=pdf[SOURCE_PAGE-1]
        source_page_height=float(page.rect.height)
        sourcepix=page.get_pixmap(matrix=pymupdf.Matrix(3,3),
                                 colorspace=pymupdf.csRGB,alpha=False)
        original=np.asarray(Image.frombytes(
            "RGB",(sourcepix.width,sourcepix.height),sourcepix.samples))
        images=[i for i in deck[ORIGINAL_SLIDE_PAGE-1].get_image_info(xrefs=True)
                if int(i["width"])>=48 and int(i["height"])>=48
                and int(i.get("xref",0))>0
                and pymupdf.Rect(i["bbox"]).width>=50
                and pymupdf.Rect(i["bbox"]).height>=25]
        require(len(images)==1,"Expected exactly one true Figure 8.3 original bitmap")
        blob=deck.extract_image(images[0]["xref"])["image"]
        with Image.open(io.BytesIO(blob)) as img:
            shown=np.asarray(img.convert("RGB"))
        require(shown.shape==(480,232,3)
                and choose_original_slide_axis(image_width=232,image_height=480)=="vertical",
                "Source figure reflow changed; do NOT scan original vertical image horizontally")
        page_words=page.get_text("words")
    heading=inventory["heading_bbox"]
    begin=int(round(max(source_page_height*.07,float(heading[1])*.155)*3))
    end=int(math.floor((float(heading[1])-4)*3))
    x0=max(0,int((float(heading[0])-9)*3))
    x1=min(original.shape[1],int(min(
        float(inventory["candidate_scan_corridor"][2])-15,
        float(heading[0])+160)*3))
    require(0<=begin<end<=original.shape[0] and 0<=x0<x1<=original.shape[1],
            "Original publisher Figure 8.3 source scan corridor invalid")
    segment=original[begin:end,x0:x1]
    source_rows=_runs((np.min(segment,axis=2)<205).sum(axis=1),
                      max_blank=18,min_width=55)
    slide_rows=_runs((np.min(shown,axis=2)<205).sum(axis=1),
                     max_blank=18,min_width=55)
    require(len(source_rows)==len(slide_rows)==3,
            f"Real source/slide vertical panel count changed: {source_rows}, {slide_rows}")
    original_global_rows=[[begin+a,begin+b] for a,b in source_rows]
    labels=identify_original_panel_labels(classify_original_panel_words(
        words=page_words,bands=original_global_rows,
        source_x=[x0,x1])["panels"])
    require([l["original_printed_inverse_function_family"] for l in labels]
            ==["tangent","sine","secant"],
            "Original source 3-panel mathematical function order is not proven")
    panels=[]
    for i,(s,t) in enumerate(zip(source_rows,slide_rows),1):
        original_panel=segment[s[0]:s[1],:]
        displayed_panel=shown[t[0]:t[1],:]
        blue_source,red_source=_blue_red_masks(original_panel,cv2,np)
        blue_slide,red_slide=_blue_red_masks(displayed_panel,cv2,np)
        black_source=np.max(original_panel,axis=2)<165
        black_slide=np.max(displayed_panel,axis=2)<165
        blue=_shape_difference(blue_source,blue_slide,cv2,np)
        black=_shape_difference(black_source,black_slide,cv2,np)
        both_red_absent=not red_source.any() and not red_slide.any()
        red=(None if both_red_absent else
             _shape_difference(red_source,red_slide,cv2,np))
        if red is None and red_source.any() and red_slide.any():
            red=_flat_red_line_score(blue_source,blue_slide,
                                      red_source,red_slide,np)
        matched=(blue is not None and blue<=.04
                 and black is not None and black<=.045
                 and (both_red_absent or red is not None and red<=.035))
        require(matched,f"Original Figure 8.3 panel {i} curve/axes shape mismatch")
        panels.append({
            "panel_index":i,
            "verified_source_function_name":labels[i-1]["original_printed_inverse_function_family"],
            "original_book_source_pdf_page":SOURCE_PAGE,
            "source_book_vertical_panel_y_pixels":original_global_rows[i-1],
            "original_slide_bitmap_vertical_panel_y_pixels":t,
            "original_blue_curve_chamfer":blue,
            "original_red_curve_chamfer":red,
            "red_absent_in_both":bool(both_red_absent),
            "black_axis_label_ink_chamfer":black,
            "source_to_slide_color_and_ink_shapes_correspond":True,
            "complete_axis_tick_values_verified":False,
            "all_slide_math_expression_tokens_verified":False})
    # Now independently match EACH printed source inverse glyph against ALL
    # three slide panels. Disallow an operator that matches the wrong panel.
    all_source_labels=classify_original_panel_words(
        words=page_words,bands=original_global_rows,source_x=[x0,x1])["panels"]
    source_templates=[]
    for original_panel in all_source_labels:
        operator=[word for word in original_panel["original_printed_tokens"]
                  if INVERSE_LABEL.fullmatch(_normalized_word(word["text"]))]
        require(len(operator)==1,"Original PDF source inverse label missing/duplicated")
        l,t,r,b=operator[0]["original_bbox_pt"]
        ink=original[int(t*3):int(b*3+1),int(l*3):int(r*3+1)]
        source_templates.append(_black(ink,np))
    displayed_ink=[_black(shown[a:b,:],np) for a,b in slide_rows]
    match_details=[[ _best_template(template,canvas,cv2,np)
                     for canvas in displayed_ink]
                   for template in source_templates]
    matrix=[[detail["normalized_correlation"] for detail in row]
            for row in match_details]
    matches=validate_glyph_matrix(matrix,min_score=.75,min_margin=.075)
    require(matches["all_three_source_inverse_operator_glyphs_in_slide_verified"] is True,
            "Original source inverse labels not uniquely mapped to all three slide panels")
    require((_sha(source),_sha(slides))==originals,
            "Original textbook/slides PDF changed during Figure 8.3 audit")
    return {"schema_version":1,
            "status":"ORIGINAL_FIGURE83_THREE_VERTICAL_PANEL_CURVES_AND_INVERSE_GLYPHS_CORROBORATED",
            "source_pdf_sha256":originals[0],
            "original_slides_pdf_sha256":originals[1],
            "original_book_page":SOURCE_PAGE,
            "original_slide_number":ORIGINAL_SLIDE_PAGE,
            "original_figure_id":FIGURE_ID,
            "original_slide_bitmap_wh_px":[232,480],
            "original_slide_panel_layout_measured":"vertical",
            "three_source_panels_located_and_curve_shapes_verified":True,
            "three_source_printed_inverse_glyphs_uniquely_matched_to_slide":True,
            "curve_and_inverse_operator_evidence":panels,
            "original_to_slide_operator_score_matrix":matrix,
            "independent_operator_panel_uniqueness":matches,
            "complete_figure_axis_labels_and_tick_values_verified":False,
            "complete_source_figure_semantic_equivalence_approved":False,
            "per_element_spoken_acoustic_timing_verified":False,
            "full_lecture_video_accepted":False,
            "student_publication_authorized":False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ("source","slides","out"):
        parser.add_argument("--"+field,type=Path,required=True)
    a=parser.parse_args(argv)
    dest=a.out.absolute()
    require(dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(a.source.absolute().parent),
            "Immutable source-independent exclusive review receipt needed")
    result=audit(source=a.source,slides=a.slides)
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=True)
        f.write("\n")
    print(json.dumps({"status":result["status"],
                      "panels":[(p["verified_source_function_name"],
                                  p["original_blue_curve_chamfer"],
                                  p["black_axis_label_ink_chamfer"])
                                 for p in result["curve_and_inverse_operator_evidence"]],
                      "three_labels_verified":result[
                          "three_source_printed_inverse_glyphs_uniquely_matched_to_slide"]}))
if __name__=="__main__":
    main()
