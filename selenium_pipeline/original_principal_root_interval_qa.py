"""Exact conditional principal-root branch theorem for Thomas 8.4 review.

This proves the sign of candidate replacements only under EXPLICIT, fixed
a>0 and angle domains. A source-independent mathematical lemma is not an
AI/human check of whether the source PDF or narration satisfies the lemma.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .figure_source_identity import _sha, require
from .original_figure82_symbolic_branch_qa import (
    _FAMILIES, exact_squared_identities, inspect_original_figure82_exact_squares,
)

_DOMAINS=(
    {
        "kind":"TANGENT_PLUS_FORM",
        "utterance_id":"s003.utterance.002",
        "left":"-pi/2","right":"pi/2",
        "left_closed":False,"right_closed":False,
        "required_cos_range":"Interval.Lopen(0, 1)",
        "required_tan_range":None,
        "replacement_nonnegative_reason":"a>0 divided by strictly positive cos(u)",
    },
    {
        "kind":"SINE_MINUS_FORM",
        "utterance_id":"s003.utterance.003",
        "left":"-pi/2","right":"pi/2",
        "left_closed":True,"right_closed":True,
        "required_cos_range":"Interval(0, 1)",
        "required_tan_range":None,
        "replacement_nonnegative_reason":"a>0 multiplied by nonnegative cos(u)",
    },
    {
        "kind":"SECANT_DIFFERENCE_FORM",
        "utterance_id":"s003.utterance.004",
        "left":"0","right":"pi/2",
        "left_closed":True,"right_closed":False,
        "required_cos_range":"Interval.Lopen(0, 1)",
        "required_tan_range":"Interval(0, oo)",
        "replacement_nonnegative_reason":"a>0 multiplied by nonnegative tan(u); cos(u)>0",
    },
)


def audit_exact_principal_root_domains(domains=None)->dict:
    """Check exact trig value ranges, not finite samples or text/OCR guesses."""
    requested=tuple(_DOMAINS if domains is None else domains)
    require(len(requested)==3
            and all(type(x) is dict for x in requested)
            and all(a==b for a,b in zip(requested,_DOMAINS)),
            "Changed original-source radical sign theorem/domain contract")
    squared=exact_squared_identities()
    if squared["exact_symbolic_squared_identities_verified"] is not True:
        return {
            "status":"SYMPY_NOT_AVAILABLE_DOMAIN_THEOREM_NOT_PROVED",
            "squared_identities_proven":False,
            "conditional_principal_root_branches_proven":False,
            "independent_source_math_review_approved":False,
            "student_publication_authorized":False,
        }
    try:
        import sympy as sp
        from sympy.calculus.util import function_range
    except ImportError:
        return {
            "status":"SYMPY_NOT_AVAILABLE_DOMAIN_THEOREM_NOT_PROVED",
            "squared_identities_proven":False,
            "conditional_principal_root_branches_proven":False,
            "independent_source_math_review_approved":False,
            "student_publication_authorized":False,
        }
    a,u=sp.symbols("a u",real=True)
    replacements=(a/sp.cos(u),a*sp.cos(u),a*sp.tan(u))
    results=[]
    for i,(domain,replacement) in enumerate(zip(requested,replacements)):
        bounds=(
            (-sp.pi/2,sp.pi/2),
            (-sp.pi/2,sp.pi/2),
            (sp.Integer(0),sp.pi/2),
        )[i]
        d=sp.Interval(bounds[0],bounds[1],
                       left_open=not domain["left_closed"],
                       right_open=not domain["right_closed"])
        cos_range=function_range(sp.cos(u),u,d)
        tan_range=function_range(sp.tan(u),u,d) if i==2 else None
        require(str(cos_range)==domain["required_cos_range"]
                and (str(tan_range) if tan_range is not None else None)
                    ==domain["required_tan_range"],
                "Exact trigonometric interval image changed")
        require(domain["kind"]==_FAMILIES[i]["kind"]
                and domain["utterance_id"]==_FAMILIES[i]["utterance_id"],
                "Source-bound substitution case drift")
        # sqrt(z²)=|z| for real z, including zeros. This is conditional
        # on denominators existing; all three chosen cos domains guarantee it.
        identity=sp.simplify(sp.sqrt(replacement**2)-sp.Abs(replacement))
        require(identity==0,"Principal-root absolute-value lemma failed")
        # Exact interval ranges and elementary positivity of multiplying /
        # dividing by a positive real prove candidate >=0, given a>0.
        cos_is_positive=not bool(cos_range.contains(0))
        cos_is_nonnegative=bool(cos_range.inf>=0)
        tan_is_nonnegative=(tan_range is not None
                            and bool(tan_range.inf>=0))
        case_valid=(
            cos_is_positive if i==0
            else cos_is_nonnegative if i==1
            else (cos_is_positive and tan_is_nonnegative)
        )
        require(case_valid,"Principal-root candidate may be negative on domain")
        results.append({
            "kind":domain["kind"],
            "original_utterance_id":domain["utterance_id"],
            "positive_parameter_hypothesis":"a > 0",
            "angle_interval":_FAMILIES[i]["angle_interval"],
            "exact_cos_range":str(cos_range),
            "exact_tan_range":str(tan_range) if tan_range is not None else None,
            "sqrt_replacement_squared_equals_abs_replacement":True,
            "candidate_replacement_nonnegative_under_hypotheses":True,
            "branch_nonnegative_lemma":domain["replacement_nonnegative_reason"],
            "conditional_principal_root_equality_proved_for_stated_domain":True,
            "unconditional_principal_root_equality_proved":False,
            "source_pdf_radical_operator_decoded":False,
            "human_or_independent_AI_math_review_approved":False,
        })
    return {
        "status":"EXACT_PRINCIPAL_ROOT_BRANCH_LEMMA_ONLY_SOURCE_APPROVAL_PENDING",
        "sympy_version":sp.__version__,
        "exact_squared_substitution_identities_verified":True,
        "conditional_principal_root_branches_proven":True,
        "conditional_principal_root_branch_count":len(results),
        "proof_hypotheses":"a > 0 and precisely the separately reported angle interval",
        "families":results,
        "all_angles_or_negative_parameter_cases_approved":False,
        "source_pdf_radical_notation_fully_verified":False,
        "independent_source_math_review_approved":False,
        "author_human_academic_approval":False,
        "new_provider_request_sent":False,
        "student_publication_authorized":False,
    }


def inspect_original_exact_root_branches(*,folder:Path)->dict:
    root=Path(folder).absolute()
    sources=[root/n for n in ("source.pdf","slides.pdf","script.txt")]
    hashes=tuple(_sha(p) for p in sources)
    previous=inspect_original_figure82_exact_squares(folder=root)
    require((previous["original_source_sha256"],
             previous["original_slides_sha256"],
             previous["original_script_sha256"])==hashes
            and previous["source_figure_radical_glyph_verified"] is False
            and previous["independent_two_pass_original_math_agreements_added"]==0,
            "Original source and literal radical ambiguity must be preserved")
    result=audit_exact_principal_root_domains()
    require(tuple(_sha(p) for p in sources)==hashes,
            "Original source changed during conditional radical review")
    return {
        **result,
        "original_source_sha256":hashes[0],
        "original_slides_sha256":hashes[1],
        "original_script_sha256":hashes[2],
        "original_source_physical_page":1,
        "original_slide":3,
        "original_formula_count":3,
        "independent_source_math_agreements_added":0,
        "real_per_utterance_audio_timing_verified":False,
        "real_element_highlight_encoded_mp4_verified":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    args=p.parse_args(argv)
    print(json.dumps(inspect_original_exact_root_branches(folder=args.folder),
                     indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
