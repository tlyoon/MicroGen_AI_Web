"""Source-concept-checked original review-question narration visual focus.

Questions are not algebraic proofs. Publisher source topics, intact authored
question text, original WAV genuinely heard word windows and independently
decoded ON/OFF real video frames are REQUIRED. Other mathematical slide
elements and course production not thereby approved.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from .original_thomas85_86_derivation_audio_pixels import create

CASES={
 ("8.5",11):{
  "source_pages":(
    (2,("General Description of the Method",
        "The degree of ƒ(x) must be less than the degree of g(x).",
        "proper.",
        "irreducible if it cannot be written as")),
  ),
  "math_tex":(
    "What initial algebraic step must be taken if the degree of the numerator in a rational function is greater than or equal to the degree of the denominator?",
    "How do the partial fraction contributions differ between a nonrepeated linear factor and an irreducible quadratic factor raised to the first power?",
  ),
  "events":(
    ("source_proper_fraction_long_division_review",2,[19.5,97.,352.8,140.],
     ("what initial algebraic step","degree of the numerator",
      "greater than or equal to the degree of the denominator"),9.0),
    ("source_irreducible_quadratic_vs_linear_review",3,[19.5,141.3,352.4,184.],
     ("partial fraction contributions differ","nonrepeated linear factor",
      "irreducible quadratic factor"),20.0),
  ),
 },
 ("8.6",13):{
  "source_pages":(
    (2,("Reduction Formulas",
        "The time required for repeated integrations by parts",
        "tann x dx")),
    (4,("Nonelementary Integrals",
        "Integrals of functions that do not have elementary antideriva-",
        "tives are called nonelementary integrals.",
        "infinite series")),
  ),
  "math_tex":(
    "How do reduction formulas simplify the evaluation of integrals involving powers of trigonometric functions or logarithmic terms, and what foundational technique underlies their derivation?",
    "What is a nonelementary integral, why do such functions possess antiderivatives despite lacking elementary formulas, and how are they typically evaluated in practice?",
  ),
  "events":(
    ("original_reduction_formula_integration_by_parts_review",2,
     [19.5,97.,352.4,140.],
     ("reduction formulas simplify","trigonometric functions or logarithmic terms",
      "foundational calculus technique"),10.0),
    ("original_nonelementary_antiderivative_review",3,
     [19.5,141.3,352.4,184.],
     ("nonelementary integral","possess antiderivatives",
      "lacking elementary formulas"),25.0),
  ),
 },
}
STATUS="TWO_ORIGINAL_PUBLISHER_REVIEW_QUESTION_SOURCE_WAV_PIXEL_QA_PASS"
RECEIPT="ORIGINAL_PUBLISHER_TWO_REVIEW_QUESTION_AUDIO_PIXEL_QA.json"

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("root","timing-receipt","out"):
        p.add_argument("--"+n,type=Path,required=True)
    args=p.parse_args(argv)
    return create(root=args.root,timing_receipt=args.timing_receipt,
        out=args.out,cases=CASES,
        identities={
            "original_textbook_proper_fraction_and_reduction_concepts_present":True,
            "authored_review_questions_are_not_unproven_math_answers":True,
            "all_intermediate_figure_and_math_formulas_approved":False,
        },
        status=STATUS,receipt_name=RECEIPT,
        minimum_word_anchor_fraction=.86)

if __name__=="__main__":
    main()
