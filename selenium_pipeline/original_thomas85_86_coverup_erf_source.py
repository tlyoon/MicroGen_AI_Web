"""Two publisher-grounded original math/audio focus videos: cover-up and erf.

Reuse the source-authorized strict original-textbook/TeX/PDF/PCM/Vosk/FFmpeg
pixel QA engine. Claim only specific correct mathematical regions, never a
proof of non-elementarity for all listed functions or full source accuracy.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from .figure_source_identity import require
from .original_thomas85_86_derivation_audio_pixels import create

CASES={
 ("8.5",9):{
  "source_pages":(
    (6,("EXAMPLE 7","Use the Heaviside Method to evaluate",
        "x3 + 3x2 - 10x")),
    (7,("The roots of g(x) are r1 = 0, r2 = 2, and r3 = -5.",
        "= -2","= 3","35 ln 0 x + 50 + C.")),
  ),
  "math_tex":(
    r"A_1 = -\frac{2}{5}, \quad A_2 = \frac{3}{7}, \quad A_3 = -\frac{1}{35}",
    r"-\frac{2}{5}\ln|x| + \frac{3}{7}\ln|x-2| - \frac{1}{35}\ln|x+5| + C",
  ),
  "events":(
    ("source_heaviside_factorized_denominator",3,[31.,110.,218.,141.],
     ("integrating x plus four","first factor the denominator",
      "x minus two","x plus five"),30.),
    ("source_heaviside_three_residue_coefficients",4,[111.,163.,272.,195.],
     ("negative two fifths","three sevenths","negative one thirty-fifth"),42.),
  ),
 },
 ("8.6",10):{
  "source_pages":(
    (4,("Nonelementary Integrals",
        "Integrals of functions that do not have elementary antideriva-",
        "tives are called nonelementary integrals.",
        "error function (which",
        "erf (x) =",
        "sin x2 dx")),
  ),
  "math_tex":(
    r"Integrals whose antiderivatives cannot be expressed as finite combinations of elementary functions",
    r"\operatorname{erf}(x) = \frac{2}{\sqrt{\pi}} \int_0^x e^{-t^2} dt",
  ),
  "events":(
    ("source_nonelementary_definition",1,[31.,73.,328.,116.],
     ("antiderivatives","finite combinations of elementary functions",
      "trig functions"),6.),
    ("source_error_function_integral_definition",4,[53.,142.,215.,164.],
     ("famous examples","error function","probabilities of random errors"),34.),
  ),
 },
}
STATUS="TWO_MORE_PUBLISHER_COVERUP_AND_ERF_REAL_SOURCE_MATH_PIXEL_EVENTS_PASS"
RECEIPT="ORIGINAL_THOMAS_HEAVISIDE_ERF_SOURCE_MATH_PIXEL_QA.json"


def mathematical_proof()->dict:
    try:
        import sympy as s
    except ImportError:
        require(False,"SymPy independent proof required, no math acceptance")
    x=s.symbols("x",real=True)
    integrand=(x+4)/(x*(x-2)*(x+5))
    partial=-s.Rational(2,5)/x+s.Rational(3,7)/(x-2)-s.Rational(1,35)/(x+5)
    require(s.cancel(integrand-partial)==0,
            "Original publisher Heaviside coefficients fail algebraic identity")
    primitive=-s.Rational(2,5)*s.log(abs(x))+s.Rational(3,7)*s.log(abs(x-2))-s.Rational(1,35)*s.log(abs(x+5))
    for q in (-6,-3,1,4):
        require(s.simplify(s.diff(primitive,x).subs(x,q)-integrand.subs(x,q))==0,
                "Cover-up result fails on real interval around roots -5,0,2")
    t=s.symbols("t",real=True)
    erf=2/s.sqrt(s.pi)*s.Integral(s.exp(-t*t),(t,0,x))
    require(s.simplify(s.diff(erf,x)-2*s.exp(-x*x)/s.sqrt(s.pi))==0,
            "Original textbook erf function normalization/calculus invalid")
    return {
        "85_exact_heaviside_partial_fraction_coefficients":True,
        "85_log_primitive_four_pole_separated_intervals":True,
        "86_error_function_normalization_and_derivative":True,
        "86_full_nonnelementary_classification_proved":False,
    }


def main(argv=None):
    a=argparse.ArgumentParser(description=__doc__)
    for key in ("root","timing-receipt","out"):
        a.add_argument("--"+key,type=Path,required=True)
    args=a.parse_args(argv)
    return create(root=args.root,timing_receipt=args.timing_receipt,
                  out=args.out,cases=CASES,identities=mathematical_proof(),
                  status=STATUS,receipt_name=RECEIPT)

if __name__=="__main__":
    main()
