"""Source-hash-bound, bounded *numerical* pilot for three trig substitutions.

These are independent arithmetic regression checks, NOT textbook-page
citations, full symbolic mathematical proof or scientific approval.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .ai_academic_web_review import build_review_job
from .math_identity_preflight import numeric
from .figure_source_identity import require, _sha

_CASES = (
    {
        "kind": "TANGENT_PLUS_FORM",
        "utterance_phrase": ("a-squared plus x-squared", "x equal to a tangent u"),
        "x_expr": "a*tan(u)",
        "radical_expr": "sqrt(a*a+x*x)",
        "signed_replacement": "a/cos(u)",
        "valid_angles": (-1.1, -0.6, -0.2, 0.2, 0.6, 1.1),
        "counterexample_angle": 2.1,
    },
    {
        "kind": "SINE_MINUS_FORM",
        "utterance_phrase": ("a-squared minus x-squared", "x equal to a sine u"),
        "x_expr": "a*sin(u)",
        "radical_expr": "sqrt(a*a-x*x)",
        "signed_replacement": "a*cos(u)",
        "valid_angles": (-1.1, -0.6, -0.2, 0.2, 0.6, 1.1),
        "counterexample_angle": 2.1,
    },
    {
        "kind": "SECANT_DIFFERENCE_FORM",
        "utterance_phrase": ("x-squared minus a-squared", "x equal to a secant u"),
        "x_expr": "a/cos(u)",
        "radical_expr": "sqrt(x*x-a*a)",
        "signed_replacement": "a*tan(u)",
        "valid_angles": (0.1, 0.3, 0.5, 0.7, 1.0, 1.2),
        "counterexample_angle": -0.5,
    },
)


def _relative_error(left, right):
    return abs(left - right) / max(1.0, abs(left), abs(right))


def check_formula_family(case: dict) -> dict:
    """Test radical sign branch and one adversarial outside-domain sample."""
    checked = []
    negative = []
    for a in (1.0, 2.0, 3.0):
        for angle in (*case["valid_angles"],):
            value = {"a": a, "u": angle}
            x = numeric(case["x_expr"], value)
            lhs = numeric(case["radical_expr"], {**value, "x": x})
            rhs = numeric(case["signed_replacement"], value)
            checked.append(_relative_error(lhs, rhs))
        bad_angle = case["counterexample_angle"]
        value = {"a": a, "u": bad_angle}
        x = numeric(case["x_expr"], value)
        lhs = numeric(case["radical_expr"], {**value, "x": x})
        rhs = numeric(case["signed_replacement"], value)
        negative.append(_relative_error(lhs, rhs))
    if (len(checked) != 18 or len(negative) != 3
        or any(not math.isfinite(z) for z in (*checked, *negative))):
        raise ValueError("Invalid bounded numerical substitution sampling")
    if max(checked) > 1e-8 or min(negative) < 0.1:
        raise ValueError("Incorrect radical branch or missing domain counterexample")
    return {
        "kind": case["kind"],
        "inside_branch_numeric_samples": len(checked),
        "inside_branch_max_relative_error": max(checked),
        "outside_branch_counterexamples": len(negative),
        "outside_branch_min_relative_error": min(negative),
        "domain_restriction_matters": True,
        "all_global_sign_equalities_proven": False,
        "mathematical_identity_formally_proven": False,
    }


def inspect_original_trig_substitutions(*, folder:Path, slide:int=3) -> dict:
    original = Path(folder).absolute()
    require(slide == 3 and original.is_dir() and not original.is_symlink(),
            "Explicit original Slide 3 scope only for real trig identities")
    assets = (original/"source.pdf", original/"slides.pdf", original/"script.txt")
    require(all(p.is_file() and not p.is_symlink() for p in assets),
            "Original source lineage missing")
    hashes = tuple(_sha(p) for p in assets)
    job = build_review_job(folder=original, slide_numbers=[slide])
    require((job["source_sha256"],job["slides_sha256"],
             job["script_sha256"]) == hashes,
            "Review job must reference actual source, slide and narration hashes")
    spoken = job["slides"][0]["utterances"]
    require(len(spoken) >= 3, "Source-bound independent math examples missing")
    outputs = []
    used = set()
    for case in _CASES:
        matches = [u for u in spoken
                   if all(phrase in " ".join(u["spoken_text"].casefold().split())
                          for phrase in case["utterance_phrase"])]
        require(len(matches) == 1,
                "No uniquely anchored original narrator phrase for trig substitution")
        unit = matches[0]
        require(unit["id"] not in used, "Substitution cases cannot share a narration unit")
        used.add(unit["id"])
        sample = check_formula_family(case)
        outputs.append({
            **sample,
            "original_utterance_id":unit["id"],
            "original_spoken_sha256":unit["spoken_sha256"],
            "original_source_quote_matched":False,
            "slide_element_semantics_verified":False,
        })
    require(tuple(_sha(p) for p in assets) == hashes,
            "Original textbook inputs changed during numeric math preflight")
    return {
        "status":"THREE_ORIGINAL_TRIG_SUBSTITUTION_NUMERICAL_CHECKS_NOT_ACADEMIC_APPROVAL",
        "source_sha256":hashes[0],
        "slides_sha256":hashes[1],
        "script_sha256":hashes[2],
        "slide":slide,
        "original_utterances_total_on_slide":len(spoken),
        "anchored_numerical_checks":len(outputs),
        "all_tested_numeric_samples_consistent":True,
        "checks":outputs,
        "source_textbook_equivalence_certified":False,
        "formal_mathematical_proof":False,
        "independent_source_math_consensus_verified":False,
        "human_academic_approval":False,
        "new_Gemini_request_sent":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    args=p.parse_args(argv)
    report=inspect_original_trig_substitutions(folder=args.folder)
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
