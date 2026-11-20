"""Original-source, full-LaTeX, independent symbolic antiderivative audit.

The publisher's Thomas Calculus §8.4 source.pdf has math glyph extraction
loss on large, multi-line integrals. This avoids false verbatim PDF text
failure by verifying:
  (1) original textbook SHA and actual source example / figure context;
  (2) exact integral and displayed complete LaTeX result in the slide source;
  (3) independent exact symbolic differentiation, declared real/positive
      assumptions and additive-constant evaluation at x=0 where needed.
It neither hallucinates the textbook's nonextractable TeX nor accepts every
intermediate manipulation or every source figure panel.

Run on a pinned isolated Dell-115 Windows Python with SymPy installed.
Original source and generated slide TeX never modified.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

import pymupdf
from .figure_source_identity import require,_sha

EXPECTED_SOURCE_SHA="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"

# Actual original authored TeX, not a restatement of mathematics by LLM.
EXPECTED={
    "example_1":{
        "source_page":3,
        "source_context":"From Fig. 8.4",
        "input_slide":9,
        "result_slide":10,
        "input":r"\int \frac{dx}{\sqrt{4 + x^{2}}}",
        "final":r"\ln\left|\frac{\sqrt{4+x^{2}}}{2} + \frac{x}{2}\right| + C",
    },
    "example_2":{
        "source_page":3,
        "source_context":"EXAMPLE 2",
        "input_slide":11,
        "result_slide":11,
        "input":r"\frac{1}{\sqrt{a^{2} + x^{2}}}",
        "final":r"\sinh^{-1}\left(\frac{x}{a}\right) = \ln\left(\frac{\sqrt{a^{2} + x^{2}}}{a} + \frac{x}{a}\right)",
    },
    "example_3":{
        "source_page":4,
        "source_context":"From Fig. 8.5",
        "input_slide":12,
        "result_slide":13,
        "input":r"\int \frac{x^{2} \, dx}{\sqrt{9 - x^{2}}}",
        "final":r"\frac{9}{2}\sin^{-1}\left(\frac{x}{3}\right) - \frac{x}{2}\sqrt{9 - x^{2}} + C",
    },
    "example_4":{
        "source_page":4,
        "source_context":"EXAMPLE 4",
        "input_slide":14,
        "result_slide":15,
        "input":r"\int \frac{dx}{\sqrt{25x^{2} - 4}}",
        "final":r"\frac{1}{5}\ln\left|\frac{5x}{2} + \frac{\sqrt{25x^{2}-4}}{2}\right| + C",
    },
}
FRAME=re.compile(r"\\begin\{frame\}(?:\[[^\]]*\])?(?:\{[^}]*\})?(.*?)\\end\{frame\}",re.S)

def math_compact(value:str)->str:
    return re.sub(r"\s+","",value)

def assert_original_math_present(*,frames:list[str],source_pages:list[str])->list[dict]:
    require(len(frames)==17 and len(source_pages)>=4,
            "Original Thomas §8.4 slide count or textbook context changed")
    proved=[]
    for name,entry in EXPECTED.items():
        page=entry["source_page"]
        require(entry["source_context"] in source_pages[page-1],
                f"Original textbook {name} example source anchor missing")
        require(math_compact(entry["input"]) in math_compact(
            frames[entry["input_slide"]-1]),
            f"Original generated {name} integral/input math changed")
        require(math_compact(entry["final"]) in math_compact(
            frames[entry["result_slide"]-1]),
            f"Original generated {name} complete multiline result changed")
        proved.append({"example":name,"original_publisher_source_page":page,
                       "original_source_context":entry["source_context"],
                       "original_input_slide":entry["input_slide"],
                       "original_complete_result_slide":entry["result_slide"],
                       "exact_complete_slide_source_math_present":True})
    return proved

def symbolic_proofs()->list[dict]:
    try:
        import sympy as s
    except ImportError as exc:
        require(False,"Independent SymPy not available on authorized Windows Python")
    x=s.symbols("x",real=True)
    a=s.symbols("a",positive=True)
    sqrt=s.sqrt
    forms=[
        ("example_1",s.log((sqrt(4+x*x)+x)/2),
         1/sqrt(4+x*x),"x any real; radicand positive"),
        ("example_2",s.asinh(x/a),
         1/sqrt(a*a+x*x),"a>0, x any real"),
        ("example_2_log",s.log((sqrt(a*a+x*x)+x)/a),
         1/sqrt(a*a+x*x),"a>0, x any real; log argument positive"),
        ("example_3",s.Rational(9,2)*s.asin(x/3)-x*sqrt(9-x*x)/2,
         x*x/sqrt(9-x*x),"-3<x<3"),
        ("example_4",s.log((5*x+sqrt(25*x*x-4))/2)/5,
         1/sqrt(25*x*x-4),"x>2/5"),
    ]
    records=[]
    for name,anti,integrand,domain in forms:
        symbolic=s.simplify(s.diff(anti,x)-integrand)
        require(symbolic==0,
                f"Independent symbolic full antiderivative identity failed: {name}")
        records.append({"example":name,
            "independent_symbolic_derivative_residual":"0",
            "expected_source_integrand":str(integrand),
            "symbolic_candidate_antiderivative":str(anti),
            "mathematical_domain_assumption":domain,
            "derivative_identity_proved":True})
    # Same derivative implies additive constant; at x=0 both forms are
    # zero for every a>0. This is the textbook's inverse-sinh normalization.
    asinh0=s.simplify(s.asinh(x/a).subs(x,0))
    log0=s.simplify(s.log((sqrt(a*a+x*x)+x)/a).subs(x,0))
    require(asinh0==log0==0,
            "Inverse hyperbolic sine logarithm does not agree at x=0")
    records.append({"example":"inverse_sinh_constant_at_zero",
        "mathematical_domain_assumption":"a>0",
        "both_forms_value_at_x0":"0",
        "constant_of_integration_difference_proved_zero":True})
    return records

def audit(*,source:Path,latex:Path)->dict:
    source,latex=Path(source).absolute(),Path(latex).absolute()
    require(source.is_file() and latex.is_file()
            and not source.is_symlink() and not latex.is_symlink(),
            "Original publisher PDF and physical authored lecture LaTeX required")
    before=(_sha(source),_sha(latex))
    require(before[0]==EXPECTED_SOURCE_SHA,
            "Refuse to infer calculus from wrong publisher PDF source")
    authored=latex.read_text(encoding="utf-8")
    frames=[m.group(1) for m in FRAME.finditer(authored)]
    with pymupdf.open(source) as original:
        pages=[pg.get_text() for pg in original]
    source_bound=assert_original_math_present(frames=frames,source_pages=pages)
    calculus=symbolic_proofs()
    require((_sha(source),_sha(latex))==before,
            "Source publisher or authored lecture math changed during proof")
    return {"schema_version":1,
        "status":"FOUR_ORIGINAL_MULTILINE_WORKED_EXAMPLES_SOURCE_ANCHORED_SYMBOLICALLY_PROVED",
        "source_pdf_sha256":before[0],
        "original_slide_latex_sha256":before[1],
        "source_context_math_witnesses":source_bound,
        "independent_symbolic_identity_proofs":calculus,
        "complete_worked_examples_proved":4,
        "differentiated_antiderivative_formulas_proved":5,
        "source_pdf_nonextractable_math_reconstructed_verbatim":False,
        "all_intermediate_algebra_source_equivalent":False,
        "all_remaining_lecture_math_verified":False,
        "original_figure_panel_semantics_verified":False,
        "spoken_element_alignment_verified":False,
        "student_publication_authorized":False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source","latex","out"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args(argv)
    out=args.out.absolute()
    require(out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(args.source.absolute().parent),
            "Exclusive original-source-independent evidence path required")
    report=audit(source=args.source,latex=args.latex)
    with out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=True)
        f.write("\n")
    print(json.dumps({"status":report["status"],
                      "source_anchored_examples":report["complete_worked_examples_proved"],
                      "symbolic_formula_proofs":report[
                          "differentiated_antiderivative_formulas_proved"]}))
if __name__=="__main__":
    main()
