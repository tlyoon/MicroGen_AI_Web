"""Source-PDF-only inverse-expression token geometry; never infer slide equivalence."""
from __future__ import annotations
import math
from pathlib import Path
from .figure_original_math_labels import audit_original_graph_labels
from .figure83_original_inverse_label_identity import INVERSE_LABEL,_normalized_word
from .figure_source_identity import require,_sha

def inspect_original_equations(panels:list)->list[dict]:
    require(type(panels) is list and len(panels)==3,
            "Original three-panel source geometry required")
    result=[]
    for i,p in enumerate(panels,1):
        require(type(p) is dict and p.get("graph_index")==i
                and type(p.get("original_printed_tokens")) is list,
                "Mismatched original figure panels")
        words=p["original_printed_tokens"]
        candidates={token:[] for token in ("u","=","x","a","inverse")}
        for word in words:
            token=_normalized_word(word["text"])
            if INVERSE_LABEL.fullmatch(token):token="inverse"
            if token not in candidates:continue
            box=word["original_bbox_pt"]
            require(type(box) is list and len(box)==4
                    and all(type(v) in (int,float) and math.isfinite(v) for v in box)
                    and box[0]<box[2] and box[1]<box[3],
                    "Original source equation has malformed word coordinates")
            candidates[token].append({"token":word["text"],"bbox":box})
        require(len(candidates["="])==len(candidates["inverse"])==1
                and all(candidates[t] for t in ("u","x","a")),
                "Missing unique original inverse equation operator or equals")
        # Axes also print u, x and a. Preserve *all* candidates instead of
        # falsely declaring a particular fraction or axis tick identified.
        result.append({"panel_index":i,"unique_equals_and_inverse_in_source":True,
            "original_equation_and_axis_token_candidates":candidates,
            "fraction_x_over_a_disambiguated_from_axis_labels":False,
            "existing_slide_full_equation_verified":False})
    return result

def audit(*,source:Path,slides:Path,source_page:int=2,
          slide_page:int=5,figure_id:str="8.3")->dict:
    before=(_sha(Path(source).absolute()),_sha(Path(slides).absolute()))
    raw=audit_original_graph_labels(source=source,slides=slides,
                                   source_page=source_page,slide_page=slide_page,
                                   figure_id=figure_id)
    require([raw["source_sha256"],raw["slides_sha256"]]==list(before),
            "Original source changed before word inspection")
    result=inspect_original_equations(raw["panels"])
    require((_sha(Path(source).absolute()),_sha(Path(slides).absolute()))==before,
            "Original PDFs changed during source-only equation inventory")
    return {"status":"ORIGINAL_EQUATION_TOKENS_FOUND_SLIDE_MATH_REVIEW_PENDING",
            "source_sha256":before[0],"slides_sha256":before[1],
            "panels":result,"source_math_equation_components_inventory_complete":True,
            "slide_equation_semantics_verified":False,
            "narration_alignment_verified":False,"paid_tts_authorized":False,
            "student_publication_authorized":False}
