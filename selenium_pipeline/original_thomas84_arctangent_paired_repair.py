"""Correct REAL §8.4 slide 6 inverse-function pedagogy and narration together.

Proof uses original publisher textbook Figure 8.3 / PR399 source labels
plus exact symbolic limits of atan(x/a) with a>0: horizontal, NOT vertical,
asymptotes at ±pi/2. In addition the trigonometric function needs a
one-to-one branch; its inverse is then one-to-one on its actual domain.

Fail-closed: corrected slides.tex, slides.pdf, script.txt are written only
to a separate scratch directory, all other original 16 slide raster pages
must be unchanged, original slide6.wav remains physically unmodified but
is declared STALE and prohibited for any corrected production video.
No TTS purchase or automatic student release.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from pathlib import Path

import pymupdf
from .figure_source_identity import require,_sha
from .runner import blocks
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_multiline_math_witness import EXPECTED_SOURCE_SHA

OLD_TEX=(r"\item Inverse trigonometric functions are restricted to specific "
         r"domains so they remain one-to-one.")
NEW_TEX=(r"\item Restrict trigonometric functions to one-to-one angle intervals "
         r"before using their inverses.")
OLD_WORDS=(
    "Because inverse trigonometric functions are not one to one over "
    "their entire domains, we must restrict them to specific intervals.",
    "The graph shown here illustrates this restricted arctangent function, "
    "which is continuous, increasing, and bounded horizontally by the "
    "vertical asymptotes at negative pi over two and positive pi over two."
)
NEW_WORDS=(
    "Because trigonometric functions are not one to one over their full "
    "domains, we restrict the substitution angle to a one to one interval "
    "before applying their inverse functions.",
    "The arctangent graph shown here is continuous and increasing, "
    "with horizontal asymptotes at negative pi over two and positive pi over two."
)
FIGURE_STATUS=("ORIGINAL_FIGURE83_THREE_VERTICAL_PANEL_CURVES_"
               "AND_INVERSE_GLYPHS_CORROBORATED")

def original_arctangent_math_proof()->dict:
    try:
        import sympy as s
    except ImportError:
        require(False,"Independent symbolic calculus required to correct graph narration")
    x=s.symbols("x",real=True)
    a=s.symbols("a",positive=True)
    y=s.atan(x/a)
    plus=s.limit(y,x,s.oo)
    minus=s.limit(y,x,-s.oo)
    derivative=s.simplify(s.diff(y,x)-a/(a*a+x*x))
    require(plus==s.pi/2 and minus==-s.pi/2 and derivative==0,
            "Original inverse tangent branch/math asymptote proof failed")
    return {"source_function":"u = arctan(x/a), a>0",
        "as_x_to_positive_infinity":"pi/2",
        "as_x_to_negative_infinity":"-pi/2",
        "asymptote_orientation":"horizontal",
        "exact_positive_derivative":"a/(a^2+x^2), for a>0",
        "symbolic_derivative_difference":"0",
        "source_geometry_proven":True}

def repair(*,original:Path,figure_receipt:Path,out:Path)->dict:
    original,figure_receipt,out=(Path(p).absolute()
                                  for p in (original,figure_receipt,out))
    source=original/"source.pdf"
    tex=original/"slides.tex"
    slides=original/"slides.pdf"
    script=original/"script.txt"
    wav=original/"slide6.wav"
    figures=[original/f"Figure 8.{i}.png" for i in range(2,7)]
    inputs=[source,tex,slides,script,wav,*figures,figure_receipt]
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and all(p.is_file() and not p.is_symlink() for p in inputs),
            "Only preexisting separate scratch directory and actual original inputs")
    digests={str(p):_sha(p) for p in inputs}
    require(_sha(source)==EXPECTED_SOURCE_SHA,
            "Original Thomas publisher source PDF identity changed")
    source_figure=json.loads(figure_receipt.read_text(encoding="utf8"))
    require(source_figure.get("status")==FIGURE_STATUS
            and source_figure.get("source_pdf_sha256")==_sha(source)
            and source_figure.get("original_slides_pdf_sha256")==_sha(slides)
            and source_figure.get(
                "three_source_printed_inverse_glyphs_uniquely_matched_to_slide") is True
            and source_figure.get("student_publication_authorized") is False
            and [q.get("verified_source_function_name")
                 for q in source_figure["curve_and_inverse_operator_evidence"]]
               ==["tangent","sine","secant"],
            "The original arctangent graph identity is not independently witnessed")
    mathematical=original_arctangent_math_proof()
    initial_tex=tex.read_text(encoding="utf8")
    initial_script=script.read_text(encoding="utf-8-sig")
    require(initial_tex.count(OLD_TEX)==1
            and all(initial_script.count(s)==1 for s in OLD_WORDS),
            "The original mathematical narration or source slide has drifted")
    orig_slide_text=dict(blocks(initial_script))[6]
    original_sentences,_=tokenize_reference_sentences(orig_slide_text)
    require(len(original_sentences)==4,
            "Original arctangent narration is no longer four sentences")
    revised_tex=initial_tex.replace(OLD_TEX,NEW_TEX)
    revised_script=initial_script
    for old,new in zip(OLD_WORDS,NEW_WORDS):
        revised_script=revised_script.replace(old,new)
    new_sentences,_=tokenize_reference_sentences(
        dict(blocks(revised_script))[6])
    require(len(new_sentences)==4
            and [i for i,(p,q) in enumerate(zip(
                original_sentences,new_sentences),1)
                if p["narration_fragment_sha256"]!=q["narration_fragment_sha256"]]
                ==[2,4],
            "Only the two scientifically wrong slide6 sentences may change")
    products=[out/"slides.tex",out/"slides.pdf",out/"script.txt",
              out/"original_slide6_paired_math_correction_no_audio.json",
              *(out/p.name for p in figures)]
    require(all(not p.exists() for p in products),
            "Never overwrite prior source-grounded academic repair or QA evidence")
    (out/"slides.tex").write_text(revised_tex,encoding="utf8")
    (out/"script.txt").write_text(revised_script,encoding="utf8")
    for figure in figures:
        shutil.copyfile(figure,out/figure.name)
    exe=shutil.which("pdflatex")
    require(exe is not None,"Native Windows LaTeX engine missing")
    # Original slide PDF was built once, with page header 'N / 1'.
    # Reproduce original compile count to preserve unaffected source pixels.
    result=subprocess.run([exe,"-interaction=nonstopmode",
                           "-halt-on-error","-no-shell-escape","slides.tex"],
                          cwd=out,capture_output=True,text=True,timeout=120)
    require(result.returncode==0,
            "Independent corrected Windows slide PDF failed to compile "+
            result.stdout[-950:])
    changed=[]
    with pymupdf.open(slides) as old,pymupdf.open(out/"slides.pdf") as fixed:
        require(len(old)==len(fixed)==17,
                "Corrected complete original source slide count changed")
        for i in range(17):
            before_page=old[i]
            after_page=fixed[i]
            aa=before_page.get_pixmap(alpha=False)
            bb=after_page.get_pixmap(alpha=False)
            require(aa.width==bb.width and aa.height==bb.height,
                    f"Original slide {i+1} pixel size changed")
            differs=aa.samples!=bb.samples
            if i!=5:
                require(not differs and before_page.get_text()==after_page.get_text(),
                        f"Original unrelated slide {i+1} visibly altered")
            else:
                require(differs
                        and "Restrict trigonometric functions" in after_page.get_text()
                        and "Inverse trigonometric functions are restricted"
                            not in after_page.get_text(),
                        "Original slide6 scientific correction not visible")
                changed.append(i+1)
    require(changed==[6],"Exactly source slide6 must have changed")
    require({str(p):_sha(p) for p in inputs}==digests,
            "Original publisher source/WAV/narration/figure evidence mutated")
    evidence={"schema_version":1,
        "status":"ORIGINAL_SLIDE6_MATH_AND_NARRATION_CORRECTED_AUDIO_STALE",
        "original_textbook_sha256":_sha(source),
        "original_slides_sha256":_sha(slides),
        "original_script_sha256":_sha(script),
        "original_audio_sha256":_sha(wav),
        "corrected_latex_sha256":_sha(out/"slides.tex"),
        "corrected_pdf_sha256":_sha(out/"slides.pdf"),
        "corrected_script_sha256":_sha(out/"script.txt"),
        "original_figure83_source_evidence_sha256":_sha(figure_receipt),
        "independent_calculus_proof":mathematical,
        "fixed_slide_numbers":changed,
        "unchanged_other_16_slides_have_exact_pdf_text_and_pixels":True,
        "corrected_narration_sentence_indices":[2,4],
        "old_slide6_wav_is_stale_and_not_safe_for_corrected_video":True,
        "corrected_slide6_wav_available":False,
        "new_tts_needed_before_source_corrected_video":True,
        "all_figure_axes_and_ticks_source_semantics_verified":False,
        "student_publication_authorized":False}
    with (out/"original_slide6_paired_math_correction_no_audio.json").open(
            "x",encoding="utf8") as f:
        json.dump(evidence,f,indent=2,ensure_ascii=True)
        f.write("\n")
    return evidence

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original","figure-receipt","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args(argv)
    r=repair(original=a.original,figure_receipt=a.figure_receipt,out=a.out)
    print(json.dumps({"status":r["status"],
                      "changed_slide":r["fixed_slide_numbers"],
                      "revoice_needed":r["new_tts_needed_before_source_corrected_video"]}))
if __name__=="__main__":
    main()
