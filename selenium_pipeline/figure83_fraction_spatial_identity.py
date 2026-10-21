from pathlib import Path
from selenium_pipeline.figure_source_identity import require
from selenium_pipeline.figure83_original_inverse_label_identity import INVERSE_LABEL,_normalized_word
from selenium_pipeline.figure83_original_equation_components import inspect_original_equations
import math

def _center(box):
    return ((box[0]+box[2])/2,(box[1]+box[3])/2)

def disambiguate_original_fraction(panels:list)->list[dict]:
    """Geometrically select x/a printed after inverse operator, not graph axes."""
    evidence=inspect_original_equations(panels)
    answer=[]
    for panel,review in zip(panels,evidence):
        words=panel["original_printed_tokens"]
        indexed=[(j,_normalized_word(w["text"]),w["original_bbox_pt"])
                 for j,w in enumerate(words)]
        operators=[(i,b) for i,t,b in indexed if INVERSE_LABEL.fullmatch(t)]
        require(len(operators)==1,"Original inverse operator must be unique")
        op_idx,op=operators[0]
        eqs=[(i,b) for i,t,b in indexed if t=="="]
        us=[(i,b) for i,t,b in indexed if t=="u"]
        require(len(eqs)==1,"Original equation equality must be unique")
        eq_idx,eq=eqs[0]
        # Same printing baseline and strict left-to-right u = inverse(x/a).
        leading=[(i,b) for i,b in us if b[2]<eq[0] and
                 abs(_center(b)[1]-_center(eq)[1])<=8]
        require(len(leading)==1 and eq[2]<=op[0]
                and 0<=op[0]-eq[2]<=6
                and abs(_center(op)[1]-_center(eq)[1])<=9,
                "Ambiguous original equation u = inverse baseline geometry")
        pairs=[]
        for xi,t,xb in indexed:
            if t!="x":continue
            for ai,at,ab in indexed:
                if t=="a" or at!="a" or xi==ai:continue
                cx,cy=_center(xb)
                ax,ay=_center(ab)
                if (op[2] <= xb[0] <= op[2]+6
                    and abs(cy-_center(op)[1])<=9
                    and abs(cx-ax)<=2
                    and 4<=ay-cy<=10
                    and xb[0]<=ab[2] and ab[0]<=xb[2]):
                    pairs.append((xi,ai,xb,ab))
        require(len(pairs)==1,"Could not uniquely assign original x/a fraction")
        xi,ai,xb,ab=pairs[0]
        rectangle=[min(leading[0][1][0],eq[0],op[0],xb[0],ab[0]),
                   min(leading[0][1][1],eq[1],op[1],xb[1],ab[1]),
                   max(leading[0][1][2],eq[2],op[2],xb[2],ab[2]),
                   max(leading[0][1][3],eq[3],op[3],xb[3],ab[3])]
        require(rectangle[2]-rectangle[0]<=130
                and rectangle[3]-rectangle[1]<=32,
                "Original equation text region oversized/ambiguous")
        answer.append({
            "panel_index":panel["graph_index"],
            "source_equation_bbox_pt":[round(v,2) for v in rectangle],
            "source_numerator_x_bbox_pt":xb,
            "source_denominator_a_bbox_pt":ab,
            "source_equals_bbox_pt":eq,
            "source_inverse_operator_bbox_pt":op,
            "source_fraction_x_over_a_spatially_disambiguated":True,
            "existing_slide_bitmap_equation_verified":False,
            "spoken_element_alignment_verified":False,
            "paid_tts_authorized":False,
            "student_publication_authorized":False})
    return answer
