"""Independent limited SymPy checks of four real §8.4 worked formulas.

Check selected textbook-visible source fragments and differentiated
antiderivatives under explicit valid real domains. This does NOT
certify every word/slide geometry or authorize student publication.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sympy as S
import pymupdf
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require

x=S.symbols("x",real=True)
a=S.symbols("a",positive=True,real=True)

EXAMPLE_SOURCE_ANCHORS={
 "example_1_log":(7,("Let x = 2 tan u","ln | sec u + tan u|"),
                  8,("Back-substitute into the antiderivative","4 + x2")),
 "example_2_asinh":(9,("Since sinh","Evaluating both sides at x = 0"),
                    9,("Therefore:","sinh")),
 "example_3_sine":(10,("Let x = 3 sin u","Apply the half-angle formula"),
                   11,("Rewrite sin 2u","9 −x2")),
 "example_4_secant":(12,("25x2 −4","Set x = 2"),
                     13,("ln | sec u + tan u|","With sec u =")),
}

def evaluate_worked_rules(antiderivatives:dict|None=None)->dict:
    """Symbolically prove selected source math AND sample valid branch values."""
    actual={
      "example_1_log":(
          S.log((x+S.sqrt(4+x*x))/2),
          1/S.sqrt(4+x*x),
          [S.Integer(-3),S.Integer(-1),S.Integer(0),S.Integer(1),S.Integer(3)]
      ),
      "example_2_asinh":(
          S.asinh(x/a)-S.log((x+S.sqrt(a*a+x*x))/a),
          S.Integer(0),
          [S.Integer(-3),S.Integer(-1),S.Integer(0),S.Integer(1),S.Integer(3)]
      ),
      "example_3_sine":(
          S.Rational(9,2)*S.asin(x/3) - x*S.sqrt(9-x*x)/2,
          x*x/S.sqrt(9-x*x),
          [-S.Rational(5,2),S.Integer(-1),S.Integer(0),
            S.Integer(1),S.Rational(5,2)]
      ),
      "example_4_secant":(
          S.Rational(1,5)*S.log((5*x+S.sqrt(25*x*x-4))/2),
          1/S.sqrt(25*x*x-4),
          [S.Rational(3,5),S.Integer(1),S.Integer(2),S.Integer(3)]
      ),
    }
    if antiderivatives is not None:
        require(set(antiderivatives)==set(actual),
                "Test override must contain all four original worked rules")
        actual={key:(antiderivatives[key],rhs,grid)
                for key,(_,rhs,grid) in actual.items()}
    results={}
    for key,(expression,expected,grid) in actual.items():
        if key=="example_2_asinh":
            # Equal derivatives and same x=0 value prove integration
            # constant zero on connected real line for a>0.
            algebra_ok=S.simplify(S.diff(expression,x))==0
            zero_ok=S.simplify(expression.subs(x,0))==0
        else:
            algebra_ok=S.simplify(S.trigsimp(S.diff(expression,x)-expected))==0
            zero_ok=True
        gridcheck=[]
        for val in grid:
            subs={x:val,a:2}
            left=S.N(S.diff(expression,x).subs(subs),14)
            right=S.N(expected.subs(subs),14)
            branch_valid=(bool(S.im(left).equals(0)) and
                           bool(S.im(right).equals(0)) and
                           abs(complex(left)-complex(right))<1e-9)
            gridcheck.append(branch_valid)
        results[key]={
            "differential_mathematics_identity_proved":bool(algebra_ok),
            "zero_constant_at_x0_proved":bool(zero_ok),
            "valid_real_domain_sample_checks_pass":bool(all(gridcheck)),
            "domain_sample_count":len(gridcheck),
            "limited_mathematics_result_pass":bool(algebra_ok and zero_ok
                                                     and all(gridcheck)),
            "full_original_visual_formula_semantics_approved":False,
        }
    return results

def checked_original_visible_source(page,anchors)->list[dict]:
    blocks=[b for b in page.get_text("blocks") if len(b)>=7 and b[6]==0]
    proof=[]
    for term in anchors:
        matches=[b for b in blocks if term.casefold() in
                 " ".join(str(b[4]).split()).casefold()]
        require(matches,"Original source-PDF math anchor absent: "+repr(term))
        selected=matches[0]
        rect=[float(n) for n in selected[:4]]
        require(0<=rect[0]<rect[2]<=page.rect.width+.1
                and 0<=rect[1]<rect[3]<=page.rect.height+.1,
                "Math formula cue not physically present")
        proof.append({
            "source_visible_text_fragment":term,
            "physically_original_pdf_bbox_pt":rect,
            "source_visible_text_block_sha256":__import__("hashlib").sha256(
                str(selected[4]).encode("utf8")).hexdigest(),
            "mathematics_speech_equivalence_approved":False,
        })
    return proof

def verify_worked_source_math(*,original:Path,out:Path)->dict:
    root=Path(original).resolve();dest=Path(out).absolute()
    require(root.is_dir() and dest.parent.is_dir()
            and not dest.exists() and not dest.is_relative_to(root.parent),
            "Source original or exclusive external proof output unsafe")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Protected original textbook source identity drift")
    rules=evaluate_worked_rules()
    require(set(rules)==set(EXAMPLE_SOURCE_ANCHORS)
            and all(z["limited_mathematics_result_pass"]
                    for z in rules.values()),
            "One or more actual worked mathematical substitutions incorrect")
    evidence={}
    with pymupdf.open(root/"slides.pdf") as pdf:
        require(len(pdf)==17,"Original source PDF slide count changed")
        for key,(first,terms1,second,terms2) in EXAMPLE_SOURCE_ANCHORS.items():
            evidence[key]={"mathematical_limited_proof":rules[key],
                  "original_pdf_fragments":[
                      {"slide":first,"fragments":
                       checked_original_visible_source(pdf[first-1],terms1)},
                      {"slide":second,"fragments":
                       checked_original_visible_source(pdf[second-1],terms2)},
                  ],
                  "full_formula_visual_reconstruction_approved":False}
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Protected textbook source modified during proof")
    result={
       "schema_version":1,
       "status":"FOUR_REAL_8_4_WORKED_IDENTITIES_LIMITED_DOMAIN_PROOF_NO_RELEASE",
       "original_source_pdf_sha256":EXPECTED_SOURCE_SHA,
       "actual_worked_example_formulas_limited_math_pass":len(evidence),
       "actual_source_original_pdf_fragment_anchors_verified":
           sum(len(p["fragments"]) for item in evidence.values()
               for p in item["original_pdf_fragments"]),
       "independent_mathematical_utterance_to_element_semantics_approved":False,
       "all_66_spoken_utterances_verified":False,
       "student_publication_authorized":False,
       "original_math_evidence":evidence,
    }
    with dest.open("x",encoding="utf8") as file:
        json.dump(result,file,indent=2,ensure_ascii=False)
        file.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    data=verify_worked_source_math(original=a.original,out=a.out)
    print(json.dumps({k:v for k,v in data.items()
                      if k!="original_math_evidence"},indent=2))
if __name__=="__main__":main()
