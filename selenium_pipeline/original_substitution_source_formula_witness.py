"""Real-textbook three-formula provenance for Thomas 8.4 Slide 3.

Binds unique physically coherent ORIGINAL PDF sentence to exact narrator IDs
and independent numerical domain checks. Never infer independent AI or human
academic agreement from a literal source quotation or numerical sampling.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .figure_source_identity import _sha, require
from .original_trig_substitution_numeric_preflight import inspect_original_trig_substitutions
from .pdf_text_source_span_witness import prove_source_quote_occurrence

# The actual original 8.4 source uses ONE unique context sentence containing
# all three substitutions. Short isolated equations repeat on the same page
# and are ambiguous source witnesses, so require the whole coherent sentence.
_SOURCE_SENTENCE = (
    "The most common substitutions are x = a tan u, x = a sin u, "
    "and x = a sec u."
)
_FORMS = (
    ("TANGENT_PLUS_FORM", "x = a tan u", "s003.utterance.002"),
    ("SINE_MINUS_FORM", "x = a sin u", "s003.utterance.003"),
    ("SECANT_DIFFERENCE_FORM", "x = a sec u", "s003.utterance.004"),
)


def inspect_original_three_formula_source(*, folder: Path) -> dict:
    root = Path(folder).absolute()
    require(root.is_dir() and not root.is_symlink(), "Immutable original folder required")
    source, slides, script = (root / name for name in
                              ("source.pdf", "slides.pdf", "script.txt"))
    hashes = (_sha(source), _sha(slides), _sha(script))
    pilot = inspect_original_trig_substitutions(folder=root, slide=3)
    require((pilot["source_sha256"],pilot["slides_sha256"],
             pilot["script_sha256"]) == hashes,
            "Original numerical pilot and source evidence disagree on source identity")
    require(pilot["anchored_numerical_checks"] == len(_FORMS)
            and pilot["original_utterances_total_on_slide"] == 5
            and pilot["all_tested_numeric_samples_consistent"] is True,
            "Original narration or numerical three-form pilot incomplete")
    citation = prove_source_quote_occurrence(
        source_pdf=source,
        expected_sha256=hashes[0],
        page_number=1,
        verbatim_quote=_SOURCE_SENTENCE,
    )
    require(citation["status"] == "EXACT_ORIGINAL_PDF_PAGE_QUOTE_PRESENT"
            and citation["quote_occurrences"] == 1
            and citation["chosen_occurrence"] == 0,
            "Original source paragraph citation is not unique and spatially coherent")
    units = {r["kind"]:r for r in pilot["checks"]}
    require(len(units) == len(pilot["checks"]) == len(_FORMS),
            "Unexpected repeated or missing numerical substitution")
    matches = []
    for kind, literal, expected_utterance in _FORMS:
        require(_SOURCE_SENTENCE.count(literal) == 1,
                "Canonical formula not individually present in source quote")
        row=units.get(kind)
        require(isinstance(row,dict)
                and row["original_utterance_id"] == expected_utterance
                and type(row["original_spoken_sha256"]) is str
                and len(row["original_spoken_sha256"]) == 64
                and row["inside_branch_numeric_samples"] == 18
                and row["outside_branch_counterexamples"] == 3
                and row["domain_restriction_matters"] is True,
                "Original narrator/formula/order or domain sample binding changed")
        matches.append({
            "original_utterance_id":expected_utterance,
            "original_utterance_sha256":row["original_spoken_sha256"],
            "formula_kind":kind,
            "source_formula_literal":literal,
            "source_physical_page":1,
            "shared_context_quote_sha256":citation["quote_sha256"],
            "numeric_in_domain_sample_count":row["inside_branch_numeric_samples"],
            "numeric_out_of_domain_counterexample_count":row["outside_branch_counterexamples"],
            "spatially_coherent_original_text_presence":True,
            "independently_verified_math_derivation":False,
            "textbook_figure_semantics_verified":False,
        })
    require((_sha(source), _sha(slides), _sha(script)) == hashes,
            "Original source changed during citation-to-math association")
    return {
        "status":"THREE_ORIGINAL_MATH_FORMULAS_SOURCE_TEXT_WITNESSED_REVIEW_PENDING",
        "original_source_sha256":hashes[0],
        "original_slides_sha256":hashes[1],
        "original_script_sha256":hashes[2],
        "original_slide":3,
        "original_utterance_count_on_slide":5,
        "source_physical_page":1,
        "source_context_quote_sha256":citation["quote_sha256"],
        "spatially_coherent_unique_context_citation":True,
        "textbook_formulas_matched_as_text":len(matches),
        "in_domain_numeric_samples_total":sum(x["numeric_in_domain_sample_count"] for x in matches),
        "out_of_domain_counterexamples_total":sum(x["numeric_out_of_domain_counterexample_count"] for x in matches),
        "formula_witnesses":matches,
        "source_equations_are_formally_proven":False,
        "independent_original_source_AI_math_consensus":False,
        "independent_human_academic_approval":False,
        "source_figure_panel_meaning_verified":False,
        "new_Gemini_review_request_sent":False,
        "genuine_Kore_TTS_authorized":False,
        "student_publication_authorized":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    args=p.parse_args(argv)
    print(json.dumps(inspect_original_three_formula_source(folder=args.folder),
                     indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
