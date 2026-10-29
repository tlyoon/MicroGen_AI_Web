"""Independently reproduce the three standard trigonometric substitution laws.

Proof scope: symbolic substitutions/derivatives plus domain-restricted
sample sign tests, against a SHA-locked original textbook. This is NOT a
full proof of lecture narration, original source figure visual correctness
or student-release clearance.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sympy as S
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require

a = S.symbols("a",positive=True,real=True)
u = S.symbols("u",real=True)
x = S.symbols("x",real=True)
RULES = {
    "tangent_plus": {
        "substitution": a*S.tan(u),
        "radicand": a*a+x*x,
        "square_root_factor": a*S.sec(u),
        "differential": a*S.sec(u)**2,
        "domain_samples": [-S.pi/4,0,S.pi/4],
        "factor_sign": "strict_positive",
    },
    "sine_minus": {
        "substitution": a*S.sin(u),
        "radicand": a*a-x*x,
        "square_root_factor": a*S.cos(u),
        "differential": a*S.cos(u),
        "domain_samples": [-S.pi/2,-S.pi/4,0,S.pi/4,S.pi/2],
        "factor_sign": "nonnegative",
    },
    "secant_minus": {
        "substitution": a*S.sec(u),
        "radicand": x*x-a*a,
        "square_root_factor": a*S.tan(u),
        "differential": a*S.sec(u)*S.tan(u),
        "domain_samples": [0,S.pi/6,S.pi/4],
        "factor_sign": "nonnegative",
    },
}

def prove_rule(rule: dict) -> dict:
    expr=rule["substitution"]
    radical=S.trigsimp(rule["radicand"].subs(x,expr))
    factor=rule["square_root_factor"]
    differential=rule["differential"]
    algebra=S.simplify(S.trigsimp(radical-factor**2))==0
    derivative=S.simplify(S.trigsimp(S.diff(expr,u)-differential))==0
    sign_checks=[]
    for angle in rule["domain_samples"]:
        val=S.simplify(S.trigsimp(factor.subs({a:2,u:angle})))
        diff=S.simplify(S.sqrt(radical.subs({a:2,u:angle}))-val)
        observed_sign=bool(val.is_positive) if rule["factor_sign"]=="strict_positive" else bool(val.is_nonnegative)
        sign_checks.append({"angle":str(angle),"valid_nonnegative_or_positive_factor":
                           observed_sign,"radical_equals_domain_factor":bool(diff==0)})
    pass_flag=bool(algebra and derivative and all(
        p["valid_nonnegative_or_positive_factor"] and
        p["radical_equals_domain_factor"] for p in sign_checks))
    return {
        "symbolic_squared_radicand_identity":bool(algebra),
        "symbolic_dx_derivative_identity":bool(derivative),
        "domain_sign_and_sqrt_sample_checks":sign_checks,
        "limited_rule_proof_pass":pass_flag,
        "whole_lecture_math_or_visual_sync_approved":False,
    }

def independently_verify_three(*,original:Path,out:Path)->dict:
    root=Path(original).resolve(); dest=Path(out).absolute()
    require(root.is_dir() and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Missing source or unsafe report destination")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Original protected Thomas textbook identity changed")
    results={name:prove_rule(rule) for name,rule in RULES.items()}
    require(len(results)==3 and all(v["limited_rule_proof_pass"]
                                   for v in results.values()),
            "Mathematical trig substitution identity or sign proof failed")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Original textbook source changed during independent proof")
    evidence={
        "schema_version":1,
        "status":"THREE_TRIG_SUBSTITUTION_IDENTITIES_INDEPENDENTLY_PROVED_LIMITED_SCOPE",
        "original_source_pdf_sha256":EXPECTED_SOURCE_SHA,
        "rules_limited_symbolic_and_domain_passed":3,
        "rules":results,
        "full_lecture_math_verification":False,
        "proof_that_spoken_utterances_match_PDF_visual_elements":False,
        "student_publication_authorized":False,
        "model_requests":0,
    }
    with dest.open("x",encoding="utf8") as f:
        json.dump(evidence,f,indent=2,ensure_ascii=False);f.write("\n")
    return evidence

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(independently_verify_three(original=a.original,out=a.out),indent=2))
if __name__=="__main__": main()
