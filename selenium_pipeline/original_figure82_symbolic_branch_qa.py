"""Exact squared-radical identities, with explicit principal-root sign gates.

Source-derived *formula transcription candidates* are tied to real textbook,
slide and narration hashes. SymPy checks exact algebra after squaring; this
DOES NOT establish that the source PDF's lossy radical glyph was correct,
that the sign restriction automatically holds, or independent academic QA.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .figure_source_identity import _sha, require
from .original_substitution_source_formula_witness import (
    inspect_original_three_formula_source,
)
from .original_figure82_side_word_positions import (
    inspect_original_figure82_side_word_positions,
)

_FAMILIES = (
    {
        "kind":"TANGENT_PLUS_FORM",
        "utterance_id":"s003.utterance.002",
        "formula":"x = a tan u",
        "squared_radical":"a²+x²",
        "candidate_replacement":"a / cos(u)",
        "positive_root_condition":"a > 0 and cos(u) > 0",
        "angle_interval":"-pi/2 < u < pi/2",
        "principal_root_sign_from_domain_fully_certified":False,
    },
    {
        "kind":"SINE_MINUS_FORM",
        "utterance_id":"s003.utterance.003",
        "formula":"x = a sin u",
        "squared_radical":"a²-x²",
        "candidate_replacement":"a cos(u)",
        "positive_root_condition":"a > 0 and cos(u) >= 0",
        "angle_interval":"-pi/2 <= u <= pi/2",
        "principal_root_sign_from_domain_fully_certified":False,
    },
    {
        "kind":"SECANT_DIFFERENCE_FORM",
        "utterance_id":"s003.utterance.004",
        "formula":"x = a sec u",
        "squared_radical":"x²-a²",
        "candidate_replacement":"a tan(u)",
        "positive_root_condition":"a > 0 and cos(u) > 0 and tan(u) >= 0",
        "angle_interval":"0 <= u < pi/2",
        "principal_root_sign_from_domain_fully_certified":False,
    },
)


def exact_squared_identities(families=None):
    """Exact symbolic *squared* identities only; fail closed if SymPy absent."""
    provided=tuple(_FAMILIES if families is None else families)
    require(len(provided)==3 and all(type(c) is dict for c in provided),
            "Exactly three bounded original formula families required")
    require(all(given == canonical for given,canonical in zip(provided,_FAMILIES)),
            "Original source formula or principal-root domain contract mutated")
    try:
        import sympy as sp
    except ImportError:
        return {
            "status":"SYMPY_NOT_INSTALLED_EXACT_MATH_NOT_CHECKED",
            "exact_symbolic_squared_identities_verified":False,
            "independent_academic_consensus":False,
        }
    a,u,x=sp.symbols("a u x",real=True)
    candidates=(
        (a*sp.tan(u), a*a+x*x,a/sp.cos(u)),
        (a*sp.sin(u), a*a-x*x,a*sp.cos(u)),
        (a/sp.cos(u),x*x-a*a,a*sp.tan(u)),
    )
    checked=[]
    for i,(family,(substitution,radicand,candidate)) in enumerate(
            zip(provided,candidates)):
        original=_FAMILIES[i]
        require(family==original,
                "Original source formula or branch sign contract was mutated")
        squared=sp.trigsimp(sp.cancel(
            sp.expand(radicand.subs(x,substitution)-candidate**2)))
        require(squared==sp.Integer(0),
                "Exact symbolic radical-square identity failed")
        # Numeric sign requirements must remain a separate, explicit gate:
        # Squaring alone NEVER justifies sqrt(t²)=t without t>=0.
        require(family["positive_root_condition"]
                and family["angle_interval"]
                and family["principal_root_sign_from_domain_fully_certified"] is False,
                "Source radical sign branch cannot be globally approved")
        checked.append({
            **family,
            "exact_squared_radicand_minus_replacement_squared":"0",
            "squared_identity_exact_sympy_pass":True,
            "principal_radical_equality_auto_approved":False,
            "source_pdf_radical_glyph_mathematically_decoded":False,
            "independent_original_academic_math_approval":False,
        })
    return {
        "status":"THREE_EXACT_SYMBOLIC_SQUARED_IDENTITIES_WITH_SIGN_GATES",
        "sympy_version":sp.__version__,
        "exact_symbolic_squared_identities_verified":True,
        "squared_identity_count":len(checked),
        "families":checked,
        "principal_root_sign_conditions_academically_approved":False,
        "unconditional_global_radical_equalities_proven":False,
        "independent_academic_consensus":False,
    }


def inspect_original_figure82_exact_squares(*,folder:Path) -> dict:
    root=Path(folder).absolute()
    require(root.is_dir() and not root.is_symlink(),
            "Immutable original Thomas 8.4 folder required")
    source,slides,script=(root/name for name in
                          ("source.pdf","slides.pdf","script.txt"))
    hashes=tuple(_sha(p) for p in (source,slides,script))
    formulas=inspect_original_three_formula_source(folder=root)
    side=inspect_original_figure82_side_word_positions(folder=root)
    require((formulas["original_source_sha256"],formulas["original_slides_sha256"],
             formulas["original_script_sha256"])==hashes
            and (side["source_sha256"],side["slides_sha256"],
                 side["script_sha256"])==hashes,
            "Original formula and figure derivation have different sources")
    require(formulas["textbook_formulas_matched_as_text"]==3
            and side["printed_side_position_candidate_count"]==3
            and side["source_pdf_radical_operator_text_not_reliable"] is True,
            "Source figure radical symbols cannot be silently promoted")
    for i,(family,unit,figure) in enumerate(zip(
            _FAMILIES,formulas["formula_witnesses"],
            side["side_position_candidates"]),1):
        require(unit["original_utterance_id"]==family["utterance_id"]
                and unit["formula_kind"]==family["kind"]
                and unit["source_formula_literal"]==family["formula"]
                and figure["panel_ordinal"]==i
                and figure["original_source_formula_label"]==family["formula"]
                and figure["triangle_side_symbol_semantics_approved"] is False,
                "Source formula/figure/utterance lineage mismatch")
    symbolic=exact_squared_identities()
    require(tuple(_sha(p) for p in (source,slides,script))==hashes,
            "Original source/slide/narration modified during exact-square audit")
    return {
        **symbolic,
        "original_source_sha256":hashes[0],
        "original_slides_sha256":hashes[1],
        "original_script_sha256":hashes[2],
        "original_source_physical_page":1,
        "original_lecture_slides_checked":[3,4],
        "original_narration_formula_utterances":[
            x["original_utterance_id"] for x in formulas["formula_witnesses"]],
        "source_figure_radical_glyph_verified":False,
        "independent_two_pass_original_math_agreements_added":0,
        "genuine_Kore_TTS_authorized":False,
        "student_publication_authorized":False,
        "new_provider_request_sent":False,
    }


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",required=True,type=Path)
    args=parser.parse_args(argv)
    print(json.dumps(inspect_original_figure82_exact_squares(folder=args.folder),
                     indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
