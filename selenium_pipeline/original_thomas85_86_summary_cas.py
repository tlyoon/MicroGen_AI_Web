"""Source grounded original §8.5 summary + §8.6 CAS semantic focus events.

Each original visible idea must appear in the publisher text, in original
author-TeX, in a distinct PDF text region, and in an actually independently
timed original WAV sentence. Concept focus is not approval of all math/figures.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from .original_thomas85_86_derivation_audio_pixels import create

CASES={
 ("8.5",10):{
  "source_pages":(
    (2,("General Description of the Method",
        "The degree of ƒ(x) must be less than the degree of g(x).",
        "linear factors and real quadratic factors")),
    (4,("EXAMPLE 4","irreducible quadratic factor",
        "ln (x2 + 1) + tan-1 x")),
  ),
  "math_tex":(
    "Partial fraction decomposition breaks complex rational functions into simpler, directly integrable parts.",
    "Always verify proper fraction status via long division before applying decomposition.",
    "Linear factors generate logarithmic terms; repeated linear and quadratic factors yield powers and inverse tangent components.",
  ),
  "events":(
    ("publisher_partial_fraction_summary",1,[31.,73.,349.,100.],
     ("partial fraction decomposition","complex rational functions",
      "simpler, directly integrable parts"),5.),
    ("publisher_proper_fraction_long_division_summary",2,[31.,103.,349.,131.],
     ("verify that a fraction is proper","polynomial long division"),12.),
    ("publisher_real_factor_logarithm_summary",3,[31.,133.,342.,162.],
     ("linear factors generate logarithmic terms","quadratic factors yield inverse tangent"),21.),
  ),
 },
 ("8.6",9):{
  "source_pages":(
    (3,("Maple","Mathematica")),
    (4,("differing from the Maple answer. Both answers are correct.",
        "neither Maple nor Mathematica returns an arbitrary constant",
        "extremely difficult to use or")),
  ),
  "math_tex":(
    "Computer algebra systems (e.g., Maple, Mathematica) provide powerful symbolic integration capabilities",
    "Different CAS software may output different equivalent forms",
    r"CAS does not automatically include the arbitrary constant $+C$.",
  ),
  "events":(
    ("original_maple_mathematica_cas_capability",1,[31.,64.,344.,116.],
     ("computer algebra systems","maple or mathematica",
      "symbolic and numerical integration"),4.),
    ("original_cas_equivalent_forms_caveat",4,[53.,174.,339.,199.],
     ("different software programs","equivalent mathematical answers",
      "different forms"),29.),
    ("original_cas_arbitrary_constant_not_returned",5,[53.,202.,339.,237.],
     ("arbitrary constant of integration",
      "extremely complex or difficult to interpret"),40.),
  ),
 },
}
STATUS="TWO_ORIGINAL_SOURCE_SUMMARY_CAS_NARRATION_REAL_PIXEL_QA_PASS"
RECEIPT="ORIGINAL_THOMAS_SUMMARY_CAS_SOURCE_AUDIO_PIXEL_QA.json"

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("root","timing-receipt","out"):
        p.add_argument("--"+n,type=Path,required=True)
    args=p.parse_args(argv)
    return create(root=args.root,timing_receipt=args.timing_receipt,out=args.out,
                  cases=CASES,
                  identities={
                    "original_publisher_partial_fraction_source_topic_existence":True,
                    "original_publisher_cas_limitations_original_textbook_exists":True,
                    "all_summary_bullets_scientifically_and_wordwise_approved":False,
                    "all_other_lecture_mathematics_and_graphs_approved":False,
                  },
                  status=STATUS,receipt_name=RECEIPT)

if __name__=="__main__":
    main()
