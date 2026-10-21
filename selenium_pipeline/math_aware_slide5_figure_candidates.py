"""Source-bound Figure 8.3 spoken inverse-function panel candidates.

Recognizes unique named trig branches in original narration and the
independently corroborated graph order; DOES NOT certify graph semantics.
"""
from __future__ import annotations
import re,hashlib,json
from pathlib import Path
from .figure83_original_inverse_label_identity import audit_original_inverse_labels
from .figure83_slide_inverse_glyph_correspondence import audit_source_to_slide_inverse_glyphs
from .figure83_original_equation_components import audit as audit_original_equation_components
from .figure83_full_expression_pixel_candidates import extract_real_equation_pixel_matrix
from .figure83_equation_operator_registration import compare_equation_operator_anchors
from .figure_three_graph_color_reflow import audit_real_three_graph_reflow
from .element_plan_autodraft import propose
from .figure_source_identity import require,_sha

BRANCHES={"tangent":re.compile(r"(?<![a-z])(?:tangent|arctan|tan)(?![a-z])",re.I),
          "sine":re.compile(r"(?<![a-z])(?:sine|arcsin|sin)(?![a-z])",re.I),
          "secant":re.compile(r"(?<![a-z])(?:secant|arcsec|sec)(?![a-z])",re.I)}
ORDER=("tangent","sine","secant")

def mentions(text:str)->list[str]:
    require(isinstance(text,str) and len(text)<20000,"Invalid bounded narration fragment")
    return [branch for branch,pattern in BRANCHES.items() if pattern.search(text)]

def audit(*,source:Path,slides:Path,script:Path,source_page:int=2,slide_page:int=5,
          figure_id:str="8.3")->dict:
    source,slides,script=(Path(x).absolute() for x in (source,slides,script))
    before=[_sha(p) for p in (source,slides,script)]
    labels=audit_original_inverse_labels(source=source,slides=slides,
        source_page=source_page,slide_page=slide_page,figure_id=figure_id)
    layout=audit_real_three_graph_reflow(source=source,slides=slides,
        source_page=source_page,slide_page=slide_page,figure_id=figure_id)
    operator_pixels=audit_source_to_slide_inverse_glyphs(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    equation_components=audit_original_equation_components(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    full_expressions=extract_real_equation_pixel_matrix(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    registration=compare_equation_operator_anchors(full_expressions,operator_pixels)
    draft=propose(source_pdf=source,slides_pdf=slides,script_txt=script)
    require([labels["source_sha256"],labels["slides_sha256"]]==before[:2]
            and [layout["original_pdf_sha256"],layout["existing_slides_pdf_sha256"]]==before[:2]
            and [operator_pixels["original_source_sha256"],
                 operator_pixels["existing_slides_sha256"]]==before[:2]
            and operator_pixels[
                "all_three_source_inverse_operator_glyphs_in_slide_verified"] is True
            and [equation_components["source_sha256"],
                 equation_components["slides_sha256"]]==before[:2]
            and equation_components["source_math_equation_components_inventory_complete"] is True
            and len(operator_pixels["source_operator_target_pixel_boxes_for_review"])==3
            and [full_expressions["source_sha256"],
                 full_expressions["slides_sha256"]]==before[:2]
            and registration["every_full_expression_template_registration_agrees_with_operator"] is True
            and len(full_expressions["image_match_details"])==3
            and len(full_expressions["printed_source_equations"])==3
            and draft["script_sha256"]==before[2]
            and len(labels["panels"])==layout["detected_graph_count"]==3
            and layout["three_graph_black_ink_geometry_plausible"] is True,
            "Original figure, 3-panel graph ink or script identity failed")
    slide=draft["slides"][slide_page-1]
    require(slide["slide_number"]==slide_page,"Source slide index changed")
    source_to_slide_expression_boxes=[]
    for i in range(3):
        start,end=full_expressions["existing_slide_bitmap_bounds"][i]
        peak=full_expressions["image_match_details"][i][i]
        x,y=peak["panel_local_top_left_px"]
        w,h=peak["template_size_px"]
        require(all(type(z) is int for z in (start,end,x,y,w,h))
                and 0<=start<end and 0<=x<x+w<=end-start
                and 0<=y and w>0 and h>0,
                "Untrusted full source equation review crop placement")
        source_to_slide_expression_boxes.append([start+x,y,start+x+w,y+h])
    results=[]
    for unit in slide["proposed_utterances"]:
        found=mentions(unit["verbatim_script_fragment"])
        # Panel family is independently read from ORIGINAL textbook PDF
        # inverse-function equation tokens, not hard-coded graphic order.
        mapped=(next((panel["graph_index"] for panel in labels["panels"]
                       if panel["original_printed_inverse_function_family"]==found[0]),None)
                if len(found)==1 else None)
        results.append({
            "utterance_id":unit["proposal_id"],"original_narration":unit["verbatim_script_fragment"],
            "function_names_explicitly_spoken":found,
            "candidate_ordered_graph_panel":mapped,
            "candidate_panel_identity_read_from_original_pdf":mapped is not None,
            "candidate_label_glyphs_matched_source_to_slide":mapped is not None,
            "candidate_matched_operator_pixel_bbox_for_review":(
                operator_pixels["source_operator_target_pixel_boxes_for_review"]
                    [mapped-1]["matched_original_glyph_bbox_on_existing_slide_bitmap_px"]
                if mapped is not None else None),
            "source_equation_and_axis_tokens_inventory_present":mapped is not None,
            "source_x_over_a_fraction_position_disambiguated":mapped is not None,
            "candidate_full_expression_bitmap_bbox_for_review":(
                source_to_slide_expression_boxes[mapped-1]
                if mapped is not None else None),
            "complete_equation_bitmap_unique_match_verified":False,
            "source_full_expression_to_slide_operator_registration_consistent":mapped is not None,
            "complete_equation_label_and_axis_mathematics_verified":False,
            "candidate_panel_original_words":(
                [labels["panels"][mapped-1]["original_printed_inverse_function_token"]]
                if mapped is not None else []),
            "ambiguous_due_to_multiple_or_no_named_functions":len(found)!=1,
            "author_confirmed_graph_function_identity":False,
            "original_to_slide_figure_mathematical_labels_verified":False,
            "narration_to_panel_semantics_verified":False,
            "paid_tts_authorized":False})
    require([_sha(p) for p in (source,slides,script)]==before,
            "Original source, slides or narration modified")
    return {"schema_version":1,
       "status":"NAMED_TRIG_BRANCH_TO_FIGURE_PANEL_HYPOTHESES_REVIEW_REQUIRED",
       "source_sha256":before[0],"slides_sha256":before[1],"script_sha256":before[2],
       "figure_id":figure_id,"slide_index":slide_page,
       "original_vertical_and_existing_horizontal_graph_count":3,
       "hypothesized_ordered_panel_names":list(ORDER),
       "original_graph_ink_reflow_independently_correlated":True,
       "original_source_printed_function_labels_verified":True,
       "original_slide_inverse_operator_glyph_correspondence_verified":True,
       "original_graph_semantics_independently_verified":False,
       "operator_glyph_review_boxes_only_not_spoken_word_timing":True,
       "original_source_equation_candidates_inventory_verified":True,
       "original_fraction_x_over_a_positions_independently_disambiguated":True,
       "full_equation_bitmap_pixel_uniqueness_verified":
            full_expressions["unambiguous_full_equation_pixel_matching_detected"],
       "full_equation_operator_anchor_registration_consistent":True,
       "original_figure_math_labels_verified":False,
       "utterances":results,
       "unique_single_function_hint_count":sum(x["candidate_ordered_graph_panel"] is not None for x in results),
       "unresolved_hint_count":sum(x["candidate_ordered_graph_panel"] is None for x in results),
       "figure_element_tts_authorized":False,
       "student_publication_authorized":False}
def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for x in ("source","slides","script"):p.add_argument("--"+x,type=Path,required=True)
    a=p.parse_args(argv)
    print(json.dumps(audit(source=a.source,slides=a.slides,script=a.script),
                     indent=2,sort_keys=True,ensure_ascii=True))
    return 2
if __name__=="__main__":raise SystemExit(main())
