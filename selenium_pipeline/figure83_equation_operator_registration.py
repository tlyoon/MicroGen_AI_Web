"""Crosscheck full expression candidate placement with independently located operator ink.

A whole-expression normalized correlation peak must NOT be considered correct
merely because its score is relatively high. The independently matched
original mathematical operator must land at that template's predicted offset.
"""
from __future__ import annotations
import math
from pathlib import Path
from .figure_source_identity import require,_sha
from .figure83_full_expression_pixel_candidates import extract_real_equation_pixel_matrix
from .figure83_slide_inverse_glyph_correspondence import audit_source_to_slide_inverse_glyphs

def compare_equation_operator_anchors(equations:dict,operators:dict,
                                      *,max_offset_px:int=8)->dict:
    require(type(max_offset_px) is int and not isinstance(max_offset_px,bool)
            and 0<max_offset_px<=25, "Invalid tight pixel position tolerance")
    require(type(equations) is dict and type(operators) is dict
            and equations.get("source_sha256")==operators.get("original_source_sha256")
            and equations.get("slides_sha256")==operators.get("existing_slides_sha256"),
            "Independent evidence not from identical original assets")
    bounds=operators.get("source_operator_target_pixel_boxes_for_review")
    printed=equations.get("printed_source_equations")
    match=equations.get("image_match_details")
    bands=equations.get("existing_slide_bitmap_bounds")
    require(type(bounds) is list and len(bounds)==3 and
            type(printed) is list and len(printed)==3 and
            type(match) is list and len(match)==3 and
            type(bands) is list and len(bands)==3,
            "Incomplete independent three-panel source-to-slide alignment")
    outcomes=[]
    for i in range(3):
        e=printed[i]
        require(type(e) is dict, "Invalid original equation evidence record")
        local=match[i][i]
        independent_box=bounds[i]["matched_original_glyph_bbox_on_existing_slide_bitmap_px"]
        x0,y0,_,_=e["source_equation_bbox_pt"]
        opx,opy,_,_=e["source_inverse_operator_bbox_pt"]
        s=local["relative_pixel_scale"]
        x,y=local["panel_local_top_left_px"]
        start,end=bands[i]
        require(all(type(v) in (int,float) and math.isfinite(v)
                    for v in (x0,y0,opx,opy,s,x,y,start,end))
                and type(independent_box) is list and len(independent_box)==4
                and 0<s<=1 and 0<=start<end
                and 0<=x<end-start and 0<=y,
                "Equation operator predicted image location corrupted")
        # Full source crop is integer-floor origin at 3x PDF DPI.
        predicted_x=start+x+(opx*3-math.floor(x0*3))*s
        predicted_y=y+(opy*3-math.floor(y0*3))*s
        dx=predicted_x-independent_box[0]
        dy=predicted_y-independent_box[1]
        err=math.hypot(dx,dy)
        outcomes.append({"panel_index":i+1,
                         "predicted_from_full_expression_operator_top_left_px":
                           [round(predicted_x,2),round(predicted_y,2)],
                         "independent_original_operator_top_left_px":independent_box[:2],
                         "operator_registration_distance_px":round(err,2),
                         "independent_operator_anchor_agrees_with_expression_crop":
                           err<=max_offset_px})
    return {"status":"EQUATION_OPERATOR_REGISTRATION_REVIEW_ONLY",
        "panels":outcomes,
        "every_full_expression_template_registration_agrees_with_operator":
            all(x["independent_operator_anchor_agrees_with_expression_crop"] for x in outcomes),
        "mathematical_equivalence_verified":False,
        "element_spoken_alignment_verified":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False}

def audit(*,source:Path,slides:Path)->dict:
    before=(_sha(Path(source).absolute()),_sha(Path(slides).absolute()))
    expression=extract_real_equation_pixel_matrix(source=source,slides=slides)
    operator=audit_source_to_slide_inverse_glyphs(source=source,slides=slides)
    result=compare_equation_operator_anchors(expression,operator)
    require((_sha(Path(source).absolute()),_sha(Path(slides).absolute()))==before,
            "Lecture assets changed during source equation registration")
    return {"source_sha256":before[0],"slides_sha256":before[1],
            "source_expression_match_unambiguous":
                expression["unambiguous_full_equation_pixel_matching_detected"],
            **result}
