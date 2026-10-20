"""Source-bound Figure 8.3 spoken inverse-function panel candidates.

Recognizes unique named trig branches in original narration and the
independently corroborated graph order; DOES NOT certify graph semantics.
"""
from __future__ import annotations
import re,hashlib,json
from pathlib import Path
from .figure83_original_inverse_label_identity import audit_original_inverse_labels
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
    draft=propose(source_pdf=source,slides_pdf=slides,script_txt=script)
    require([labels["source_sha256"],labels["slides_sha256"]]==before[:2]
            and [layout["original_pdf_sha256"],layout["existing_slides_pdf_sha256"]]==before[:2]
            and draft["script_sha256"]==before[2]
            and len(labels["panels"])==layout["detected_graph_count"]==3
            and layout["three_graph_black_ink_geometry_plausible"] is True,
            "Original figure, 3-panel graph ink or script identity failed")
    slide=draft["slides"][slide_page-1]
    require(slide["slide_number"]==slide_page,"Source slide index changed")
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
       "original_graph_semantics_independently_verified":False,
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
