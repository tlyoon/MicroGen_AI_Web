"""Independently read the actual inverse-function labels printed on Figure 8.3.

No handwritten function-order assumption; original PDF text glyphs are
extractable without OCR. Proof covers source LABELS, not slide bitmap
characters, graph equation correctness or TTS speech alignment.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from .figure_original_math_labels import audit_original_graph_labels
from .figure_source_identity import require, _sha

INVERSE_LABEL = re.compile(r"^(tan|sin|sec)[\u2212\-]1$")
FAMILIES = {"tan":"tangent","sin":"sine","sec":"secant"}

def _normalized_word(value:str)->str:
    require(isinstance(value,str) and len(value)<=128,
            "Invalid PDF mathematical label token")
    return unicodedata.normalize("NFKC",value).replace(" ","").casefold()

def identify_original_panel_labels(panels:list)->list[dict]:
    """Derive per-panel names from real parsed PDF equation tokens.

    A complete printed equation includes an inverse-function symbol
    and neighboring u = and numerator/denominator x/a tokens.
    No lexical narration information enters this decision.
    """
    require(isinstance(panels,list) and len(panels)==3,
            "Original three-panel figure label inventory required")
    found=[]
    for position,panel in enumerate(panels,1):
        require(type(panel) is dict and panel.get("graph_index")==position
                and type(panel.get("original_printed_tokens")) is list,
                "Source graph index/word identity inconsistent")
        tokens=panel["original_printed_tokens"]
        normalized=[_normalized_word(word["text"]) for word in tokens]
        inverse=[(token,FAMILIES[m.group(1)])
                 for token,word in zip(normalized,tokens)
                 if (m:=INVERSE_LABEL.fullmatch(token))]
        require(len(inverse)==1,
                "Original graph does not contain exactly one inverse label")
        # PDF extractable, *printed* expression must include the
        # dependent variable, equals glyph and x-over-a fraction.
        require("u" in normalized and "=" in normalized
                and "x" in normalized and "a" in normalized,
                "Incomplete original figure function equation")
        coordinates=[word.get("original_bbox_pt") for word in tokens]
        require(all(type(box) is list and len(box)==4
                    and all(type(v) in (float,int) for v in box)
                    and box[0]<box[2] and box[1]<box[3]
                    for box in coordinates),
                "Original mathematical PDF label lost position evidence")
        family=inverse[0][1]
        found.append({
            "graph_index":position,
            "original_printed_inverse_function_family":family,
            "original_printed_inverse_function_token":inverse[0][0],
            "u_equals_inverse_of_x_over_a_tokens_extracted":True,
            "original_pdf_label_identity_evidenced":True,
            "original_curve_mathematical_correctness_verified":False,
            "existing_slide_bitmap_equation_labels_verified":False,
            "narration_semantic_element_alignment_verified":False,
        })
    require(len(set(p["original_printed_inverse_function_family"]
                    for p in found))==3,
            "Missing/duplicated inverse-trigonometric source identities")
    return found

def audit_original_inverse_labels(*,source:Path,slides:Path,
                                  source_page:int=2,slide_page:int=5,
                                  figure_id:str="8.3")->dict:
    source,slides=Path(source).absolute(),Path(slides).absolute()
    before=(_sha(source),_sha(slides))
    evidence=audit_original_graph_labels(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    require((evidence["source_sha256"],evidence["slides_sha256"])==tuple(before)
            and evidence["graph_count"]==3,
            "Original PDF page and existing slide graph layout identity changed")
    identified=identify_original_panel_labels(evidence["panels"])
    require((_sha(source),_sha(slides))==before,
            "Original source or slides changed during label audit")
    return {
        "schema_version":1,
        "status":"ORIGINAL_FIGURE_INVERSE_LABEL_IDENTITIES_VERIFIED_SLIDE_REVIEW_REQUIRED",
        "source_sha256":before[0],"slides_sha256":before[1],
        "source_page":source_page,"slide_page":slide_page,
        "figure_id":figure_id,
        "original_pdf_graph_count":3,
        "original_source_printed_function_identities_verified":True,
        "panels":identified,
        "original_graph_curve_semantic_equation_accuracy_verified":False,
        "existing_slide_bitmap_equation_glyphs_verified":False,
        "spoken_element_highlight_sync_verified":False,
        "element_tts_authorized":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("source","slides"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args(argv)
    print(json.dumps(audit_original_inverse_labels(
        source=a.source,slides=a.slides),indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
