"""Publisher-authentic original §8.6 slides 6 and 12 source/math audit.

This proves specified science and script/slide correspondence, not audio timing,
per-element visual highlighting, full lecture equivalence, or publication.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from .figure_source_identity import require, _sha
from .original_thomas85_86_first_math_highlights import SOURCE

HEADING_TERMS={
    "integral_tables":("integral tables",0),
    "example_three":("example 3",0),
    "formula_106":("formula 106",0),
    "formula_49":("formula 49",1),
    "reduction_formulas":("reduction formulas",1),
    "computer_algebra":("integration with a cas",2),
    "nonelementary":("nonelementary integrals",3),
    "tank_applications":("62. volume",5),
}
SUMMARY_BULLETS=(
    "integral tables provide rapid access",
    "reduction formulas systematically lower powers",
    "computer algebra systems offer symbolic and numerical solutions",
    "nonelementary integrals arise frequently",
    "tank volume calculations",
)

def textbook_headings_proven(pages:list[str])->dict:
    require(len(pages)==6,"Only exact original six §8.6 publisher pages accepted")
    result={}
    for key,(phrase,page_index) in HEADING_TERMS.items():
        found=phrase in " ".join(pages[page_index].lower().split())
        require(found, f"Original publisher source missing {key} on page {page_index+1}")
        result[key]={"page":page_index+1,"source_phrase":phrase,
                     "publisher_page_source_verified":True}
    return result

def exact_example_three_math()->dict:
    try:
        import sympy as s
    except ImportError as exc:
        require(False,f"Original example 3 needs independent exact SymPy QA: {exc}")
    x=s.symbols("x",real=True)
    result=(x*x/s.Integer(2)-s.Rational(1,4))*s.asin(x)+x*s.sqrt(1-x*x)/4
    remaining=s.asin(x)/2-x*s.sqrt(1-x*x)/2
    require(s.simplify(s.diff(result,x)-x*s.asin(x))==0,
            "Publisher Example 3 combined antiderivative is not an antiderivative")
    require(s.simplify(s.diff(remaining,x)-x*x/s.sqrt(1-x*x))==0,
            "Publisher Formula 49 residual integral is incorrect")
    return {"symbolic_antiderivative_exact":True,
            "formula49_remaining_integral_exact":True,
            "real_domain":"-1 < x < 1"}

def verify_source(*,folder:Path)->dict:
    import pymupdf
    folder=Path(folder)
    require(folder.is_dir() and not folder.is_symlink(),
            "Original source section absent")
    for name in ("source.pdf","slides.pdf","slides.tex","script.txt",
                 "slide6.wav","slide12.wav"):
        p=folder/name
        require(p.is_file() and not p.is_symlink(),
                f"Original source/author/narration file missing: {name}")
    require(_sha(folder/"source.pdf")==SOURCE["8.6"]["publisher_sha"]
            and _sha(folder/"slides.pdf")==SOURCE["8.6"]["slides_pdf_sha"],
            "Wrong publisher or original authored §8.6 slide snapshot")
    frames=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",
                      (folder/"slides.tex").read_text(encoding="utf8"),re.S)
    require(len(frames)==13, "Wrong original 13-slide author lecture")
    six,twelve=frames[5],frames[11]
    require("Example 3: Combining Formulas" in six
            and r"\int x \sin^{-1} x" in six
            and "Formula 106" in six and "Formula 49" in six
            and r"\frac{x^2}{2}" in six
            and r"\sqrt{1-x^2}" in six,
            "Authored slide6 missing textbook formula106/49 mathematics")
    twelve_text=" ".join(twelve.lower().split())
    for phrase in SUMMARY_BULLETS:
        require(phrase in twelve_text,
                f"Original summary slide missing textbook topic: {phrase}")
    script=(folder/"script.txt").read_text(encoding="utf8")
    six_script=re.search(r"\*\*Slide 6\b.*?(?=\*\*Slide 7\b)",script,re.S)
    twelve_script=re.search(r"\*\*Slide 12\b.*?(?=\*\*Slide 13\b)",script,re.S)
    require(six_script is not None and twelve_script is not None,
            "Original slide6 and slide12 narration scripts absent")
    require(all(t in six_script.group(0).lower()
                for t in ("inverse sine","integral","reduction formula",
                          "constant of integration"))
            and all(t in twelve_script.group(0).lower()
                    for t in ("integral tables","reduction formulas",
                              "computer algebra systems",
                              "nonelementary integrals","tank volumes")),
            "Original authored slide6/12 scripts do not cover verified science")
    with pymupdf.open(folder/"source.pdf") as publisher:
        texts=[p.get_text() for p in publisher]
    source_headings=textbook_headings_proven(texts)
    mathematics=exact_example_three_math()
    with pymupdf.open(folder/"slides.pdf") as slides:
        require(len(slides)==13 and slides[5].get_text()
                and slides[11].get_text(),
                "Original slide6 and slide12 missing from authored PDF")
    return {
        "status":"ORIGINAL_THOMAS86_SLIDES6_12_TEXTBOOK_SCIENCE_AND_SCRIPT_PROVEN_NONPRODUCTION",
        "publisher_pinned_source_sha":SOURCE["8.6"]["publisher_sha"],
        "author_original_pinned_pdf_sha":SOURCE["8.6"]["slides_pdf_sha"],
        "verified_source_heading_page_map":source_headings,
        "slide6": {"publisher_example3_formulas106_49_author_math_verified":True,
                   "authored_narration_script_math_topic_match":True,
                   **mathematics},
        "slide12":{"five_publisher_topics_author_slides_script_matched":True},
        "individual_WAV_word_time_highlight_verified":False,
        "full_production_gate_passed":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    require(a.out.parent.is_dir() and not a.out.exists(),
            "Original source science output must be a fresh versioned path")
    report=verify_source(folder=a.folder)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":report["status"],"student_publication":False,
                      "slide6_math":True,"slide12_topics":True}))

if __name__=="__main__":
    main()
