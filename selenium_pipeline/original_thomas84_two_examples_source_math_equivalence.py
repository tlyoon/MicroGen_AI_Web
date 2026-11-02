"""Original publisher Thomas §8.4 Example2 and Example3 exact calculus QA.

Proves selected source-authored expressions on original slides 11,12,13:
asinh/log derivative, substitution domain/positive radical and final
sine-substitution antiderivative. Source pages, original author TeX,
rendered PDF and figure SHA physically pinned. Not full math-label/WAV QA.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from .figure_source_identity import require,_sha
from .recover_pinned_original_thomas_corpus import ORIGINAL_PINS

STATUS="ORIGINAL_THOMAS84_EXAMPLES2_3_POSITIVE_DOMAIN_SOURCE_EXACT_MATH_NONPRODUCTION"
CLAUSES={
    11:(r"\sinh^{-1}\left(\frac{x}{a}\right)",
        r"\ln\left(\frac{\sqrt{a^{2} + x^{2}}}{a} + \frac{x}{a}\right)",
        r"\int \frac{dx}{\sqrt{a^{2} + x^{2}}}"),
    12:(r"\int \frac{x^{2} \, dx}{\sqrt{9 - x^{2}}}",
        r"x = 3 \sin \theta",r"9 - x^{2} = 9 \cos^{2} \theta",
        r"9 \int \sin^{2} \theta"),
    13:(r"\frac{9}{2}(\theta - \sin \theta \cos \theta)",
        r"\sin \theta = \frac{x}{3}",
        r"\cos \theta = \frac{\sqrt{9-x^2}}{3}",
        r"\frac{9}{2}\sin^{-1}\left(\frac{x}{3}\right)",
        r"\frac{x}{2}\sqrt{9 - x^{2}}",
        "Figure 8.5.png"),
}

def check_exact_math()->dict:
    try: import sympy as s
    except ImportError as exc:
        require(False,f"Independent exact symbolic proof requires SymPy: {exc}")
    x=s.symbols("x",real=True)
    a=s.symbols("a",positive=True)
    primitive=s.log((s.sqrt(a*a+x*x)+x)/a)
    other=s.asinh(x/a)
    f=1/s.sqrt(a*a+x*x)
    require(s.simplify(s.diff(primitive,x)-f)==0
            and s.simplify(s.diff(other,x)-f)==0
            and s.simplify(primitive.subs(x,0)-other.subs(x,0))==0,
            "Original inverse hyperbolic sine/log primitive or constant incorrect")
    theta=s.symbols("theta",real=True)
    for sample in (s.Integer(0),s.pi/6,s.pi/4):
        # Original -pi/2 < theta < pi/2, hence cos>0 and
        # sqrt(9cos²theta)=3cos(theta), not an unrestricted identity.
        require(s.simplify(
            s.sqrt(9*s.cos(sample)**2)-3*s.cos(sample))==0,
            "Original sine substitution positive cos branch violated")
        require(s.simplify(
            9*s.sin(sample)**2*3*s.cos(sample)/
            s.sqrt(9*s.cos(sample)**2)-9*s.sin(sample)**2)==0,
            "Original sine-substitution Jacobian denominator incorrect")
    result=s.Rational(9,2)*s.asin(x/3)-x*s.sqrt(9-x*x)/2
    exact=s.diff(result,x)-x*x/s.sqrt(9-x*x)
    require(s.simplify(exact)==0,
            "Publisher Example3 final radical/sine antiderivative is incorrect")
    for val in (-2,-1,0,1,2):
        require(s.simplify(exact.subs(x,val))==0,
                "Publisher sine-substitution antiderivative fails inside |x|<3")
    return {
        "inverse_hyperbolic_log_formula_same_derivative_and_zero_constant":True,
        "sine_substitution_jacobian_and_positive_cos_branch_exact":True,
        "publisher_example3_final_radical_integral_exact_derivative":True,
        "positive_parameter_domain":"a > 0",
        "sine_substitution_domain":"-3 < x < 3; -pi/2 < theta < pi/2",
        "mathematical_source_independent_identity_categories":3,
        "whole_original_41_slide_math_and_figure_labels_accepted":False,
    }

def audit_original(*,folder:Path)->dict:
    import pymupdf
    folder=Path(folder).absolute()
    require(folder.is_dir() and not folder.is_symlink(),
            "Frozen original Thomas source section absent")
    pdf_sha,slides_sha=ORIGINAL_PINS["8.4"]
    originals=[folder/name for name in (
        "source.pdf","slides.pdf","slides.tex","script.txt",
        "Figure 8.5.png","slide11.wav","slide12.wav","slide13.wav")]
    require(all(p.is_file() and not p.is_symlink() for p in originals)
            and _sha(folder/"source.pdf")==pdf_sha
            and _sha(folder/"slides.pdf")==slides_sha,
            "Wrong publisher original/author slide source or missing physical WAV/figure")
    old={str(p):_sha(p) for p in originals}
    tex=(folder/"slides.tex").read_text("utf8")
    frames=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",tex,re.S)
    require(len(frames)==17,
            "Original textbook author 17-slide physical source changed")
    with pymupdf.open(folder/"source.pdf") as publisher, pymupdf.open(
            folder/"slides.pdf") as slides:
        require(len(publisher)==6 and len(slides)==17,
                "Original §8.4 textbook/source document wrong")
        text3=" ".join(publisher[2].get_text().split())
        text4=" ".join(publisher[3].get_text().split())
        require(all(term in text3 for term in ("EXAMPLE 2","sinh-1","EXAMPLE 3","x = 3 sin"))
                and all(term in text4 for term in ("FIGURE 8.5","9 - x2","sin-1")),
                "Original publisher Example2, Example3 and Figure8.5 source pages unverified")
        for slide,fragments in CLAUSES.items():
            require(all(snippet in frames[slide-1] for snippet in fragments),
                    f"Original authored mathematical source changed on slide{slide}")
            require(len(slides[slide-1].get_text())>80,
                    f"Original source mathematics not rendered on slide{slide}")
        img=slides[12].get_image_info(xrefs=True)
        require(any(x.get("xref",0)>0 and x.get("width",0)>=70 for x in img),
                "Original authored Example3 slide13 Figure8.5 bitmap missing")
    math=check_exact_math()
    require(old=={str(p):_sha(p) for p in originals},
            "Original textbook PDF, lecture, figure or PCM mutated")
    return {
        "status":STATUS,"publisher_original_sha256":pdf_sha,
        "author_original_slide_sha256":slides_sha,
        "publisher_source_physical_pages":[3,4],
        "original_source_slides_with_independent_selected_mathematics":[11,12,13],
        "selected_original_beamer_formula_source_clauses":sum(map(len,CLAUSES.values())),
        "original_figure85_SHA256":_sha(folder/"Figure 8.5.png"),
        "source_mathematics":math,
        "all_original_figure_axes_symbols_source_semantics_accepted":False,
        "every_original_wav_word_pronunciation_verified":False,
        "full_production_academic_gate_passed":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args(argv)
    require(a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(a.original.absolute()),
            "Fresh exclusive source-scientific receipt required")
    result=audit_original(folder=a.original)
    with a.out.open("x",encoding="utf8") as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False);stream.write("\n")
    print(json.dumps({"status":STATUS,"source_slides":3,
                     "exact_identity_categories":3,
                     "production":False}))
if __name__=="__main__":
    main()
