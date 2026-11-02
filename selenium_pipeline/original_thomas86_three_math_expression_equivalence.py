"""Independent exact mathematics for original publisher Thomas §8.6 slides 5,7,8.

Checks physically pinned publisher Example 2/Table 29b, Reduction Formulas,
Example 4, exact authored TeX equation clauses, and symbolic derivatives.
All assertions are conditional real-domain identities; this does NOT certify
unrelated slide mathematics, all narration phonetics, or production release.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from .figure_source_identity import require,_sha
from .original_thomas85_86_first_math_highlights import SOURCE

STATUS="ORIGINAL_THOMAS86_THREE_SOURCE_TABLE_REDUCTION_EXAMPLES_EXACT_MATH_NONPRODUCTION"
CLAUSES={
    5:(
        r"\int \frac{dx}{x\sqrt{2x-4}}",
        r"\int \frac{dx}{x\sqrt{ax-b}}",
        r"\frac{2}{\sqrt{b}} \tan^{-1}\sqrt{\frac{ax-b}{b}}",
        r"\tan^{-1}\sqrt{\frac{x-2}{2}}",
    ),
    7:(
        r"\int \tan^n x",
        r"\frac{1}{n-1} \tan^{n-1} x",
        r"\int \tan^{n-2} x",
        r"\int (\ln x)^n",
        r"\int \sin^n x \cos^m x",
        r"\quad (n \neq -m)",
    ),
    8:(
        r"\int \tan^5 x",
        r"\frac{1}{4} \tan^4 x - \int \tan^3 x",
        r"\frac{1}{2} \tan^2 x + \ln|\cos x|",
        r"\frac{1}{4} \tan^4 x - \frac{1}{2} \tan^2 x - \ln|\cos x|",
    ),
}
PUBLISHER_TERMS={
    5:("EXAMPLE 2","Formula 29b","b is positive"),
    7:("Reduction Formulas","tann x dx","(ln x)n dx","sinn x cosm x dx"),
    8:("EXAMPLE 4","tan5 x dx","tan3 x dx","ln 0 cos x0"),
}

def exact_symbolic_derivative_identity(*,primitive,integrand,variable)->bool:
    """Exact symbolic equality; combine trigonometric and rational canonicalization.

    A single unfinished trigsimp intermediate must not become a spurious
    science error. Approximate numeric equality alone is NOT enough to pass.
    """
    import sympy as s
    return s.simplify(s.trigsimp(s.diff(primitive,variable)-integrand))==0


def symbolic_source_mathematics()->dict:
    try: import sympy as s
    except ImportError as exc:
        require(False,f"Independent exact symbolic CAS required: {exc}")
    x=s.symbols("x",real=True)
    y=s.symbols("y",positive=True)
    a,b=s.symbols("a b",positive=True)
    atan_source=2/s.sqrt(b)*s.atan(s.sqrt((a*y-b)/b))
    derivative=s.diff(atan_source,y)-1/(y*s.sqrt(a*y-b))
    # The first textbook expression is interpreted for y>b/a.
    # Test exact rational substitutions, not floats.
    for vals in ((2,4,3),(2,4,5),(3,6,7),(2,4,10)):
        aa,bb,xx=vals
        require(s.simplify(derivative.subs({a:aa,b:bb,y:xx}))==0,
                "Publisher Formula29b derivative fails on positive real domain")
    example=s.atan(s.sqrt((x-2)/2))
    for point in (3,5,10):
        require(s.simplify(
            (s.diff(example,x)-1/(x*s.sqrt(2*x-4))).subs(x,point))==0,
            "Author original Example2 Formula29b substitution is not an antiderivative")
    # Under -pi/2 < x < pi/2, cos(x)>0, so log|cos x|=log(cos x).
    tan=s.tan(x)
    for n in (3,5):
        condition=s.diff(tan**(n-1)/s.Integer(n-1),x)-tan**(n-2)-tan**n
        require(s.trigsimp(condition)==0,
                "Publisher reduction ∫tan^n identity fails at n=3/5")
    logarithm=s.log(y)
    require(s.simplify(
        s.diff(y*logarithm**3,y)-3*logarithm**2-logarithm**3)==0,
        "Publisher logarithm n=3 reduction identity false")
    n,m=3,1
    primitive=-s.sin(x)**(n-1)*s.cos(x)**(m+1)/s.Integer(m+n)
    residual=s.Rational(n-1,m+n)*s.sin(x)**(n-2)*s.cos(x)**m
    require(s.trigsimp(s.diff(primitive,x)+residual-
                       s.sin(x)**n*s.cos(x)**m)==0,
            "Publisher sine/cosine n=3,m=1 reduction formula false")
    I3=tan**2/s.Integer(2)+s.log(s.cos(x))
    I5=tan**4/s.Integer(4)-tan**2/s.Integer(2)-s.log(s.cos(x))
    # SymPy trigsimp can leave mathematically zero tan^5 combinations
    # expressed in mixed sin/cos/tan. Apply a second exact simplification
    # before classifying a source identity as mathematically false.
    require(exact_symbolic_derivative_identity(
                primitive=I3,integrand=tan**3,variable=x)
            and exact_symbolic_derivative_identity(
                primitive=I5,integrand=tan**5,variable=x),
            "Publisher Example4 ∫tan^3 or ∫tan^5 full result wrong")
    require(s.trigsimp(I5-(tan**4/s.Integer(4)-I3))==0,
            "Two-step textbook reduction composition inconsistent")
    return {
        "slide5_table29b_general_and_substituted_positive_domain_derivatives":True,
        "slide7_tangent_reduction_n3_n5_and_log_n3_and_sincos_n3m1":True,
        "slide8_example4_two_independent_primitives_and_composed_chain":True,
        "checked_identity_categories":9,
        "source_table29b_domain":"a>0, b>0, x>b/a (positive x)",
        "example2_domain":"x>2",
        "tangent_logcos_real_branch":"-pi/2 < x < pi/2",
        "complete_publisher_math_proof_for_all_lecture_formulas":False,
    }

def audit_source(*,folder:Path)->dict:
    import pymupdf
    root=Path(folder).absolute()
    require(root.is_dir() and not root.is_symlink()
            and _sha(root/"source.pdf")==SOURCE["8.6"]["publisher_sha"]
            and _sha(root/"slides.pdf")==SOURCE["8.6"]["slides_pdf_sha"],
            "Not the frozen original publisher/author §8.6 corpus")
    files=[root/p for p in ("source.pdf","slides.pdf","slides.tex","script.txt")]
    files.extend(root/f"slide{s}.wav" for s in (5,7,8))
    require(all(path.is_file() and not path.is_symlink() for path in files),
            "Source must include untouched original book, TeX and WAVs")
    before={str(path):_sha(path) for path in files}
    tex=(root/"slides.tex").read_text(encoding="utf8")
    frames=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",tex,re.S)
    require(len(frames)==13,"Original lecturer slide count changed")
    with pymupdf.open(root/"source.pdf") as publisher, pymupdf.open(
            root/"slides.pdf") as slides:
        require(len(publisher)==6 and len(slides)==13,
                "Original course source PDF page count changed")
        page1=" ".join(publisher[0].get_text().split())
        page2=" ".join(publisher[1].get_text().split())
        map_page={5:page1,7:page2,8:page2}
        records={}
        for slide,parts in CLAUSES.items():
            frame=frames[slide-1]
            source_text=map_page[slide]
            require(all(piece in frame for piece in parts),
                    f"Authored original slide {slide} source mathematical clause changed")
            require(all(term in source_text for term in PUBLISHER_TERMS[slide]),
                    f"Original textbook source page for slide {slide} example missing")
            actual_text=slides[slide-1].get_text()
            require(len(actual_text)>80,
                    "Source-matched math slide did not physically render")
            records[str(slide)]={
                "publisher_original_source_page":1 if slide==5 else 2,
                "publisher_physical_example_or_reduction_terms":list(PUBLISHER_TERMS[slide]),
                "authored_beamer_equation_clauses_checked":len(parts),
                "original_rendered_author_pdf_contains_mathematics":True,
                "original_author_script_and_audio_hash_preserved":True,
                "exact_source_math_derivative_independently_checked":True,
                "all_mathematical_glyphs_and_full_wav_word_alignment_verified":False,
            }
    science=symbolic_source_mathematics()
    require(before=={str(path):_sha(path) for path in files},
            "Source publisher/author/audio mutated during symbolic audit")
    return {
        "status":STATUS,"original_publisher_sha256":SOURCE["8.6"]["publisher_sha"],
        "original_author_slides_pdf_sha256":SOURCE["8.6"]["slides_pdf_sha"],
        "publisher_edition_physical_pages_verified":[1,2],
        "independently_checked_original_source_slides":[5,7,8],
        "author_beamer_source_clauses_verified":sum(map(len,CLAUSES.values())),
        "symbolic_proofs":science,"per_slide_source_science_records":records,
        "all_other_original_source_lecture_math_accepted":False,
        "every_spoken_word_pronunciation_accepted":False,
        "full_production_academic_gate_passed":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    require(a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(a.original.absolute()),
            "Publisher academic proof requires external exclusive output")
    result=audit_source(folder=a.original)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({
        "status":STATUS,"original_academic_source_slides":3,
        "beamer_mathematical_equation_clauses":result["author_beamer_source_clauses_verified"],
        "symbolic_identity_categories":9,
        "student_publication_authorized":False,
    }))
if __name__=="__main__":
    main()
