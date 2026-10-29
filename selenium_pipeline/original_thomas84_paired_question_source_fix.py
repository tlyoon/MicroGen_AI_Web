"""Make source-safe paired LaTeX/PDF and TTS text correction for §8.4 slide17.

Never claim new voice audio exists. The original source stays untouched.
The corrected script and slide must be used together if TTS is generated.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import hashlib
from pathlib import Path
import pymupdf

from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .automatic_math_semantic_qa import inspect_math_semantics

STATUS="EXACT_PAIRED_SLIDE17_PDF_AND_NARRATION_TEXT_CORRECTION_AUDIO_NOT_YET_REGENERATED"
ORIGINAL_TEX=(r"\item For an integral containing $\sqrt{x^2 - 16}$ with $x > 4$, carry out Step 1 and Step 2 of the substitution procedure. What is the resulting trigonometric integrand?")
CORRECTED_TEX=(r"\item For $I=\int \frac{dx}{\sqrt{x^2 - 16}}$ with $x>4$, carry out Step 1 and Step 2 of the substitution procedure. What substitution, differential $dx$, and resulting trigonometric integrand do you obtain?")
ORIGINAL_NARRATION=("First, for an integral with the square root of x squared minus sixteen, determine the appropriate secant substitution and its differential to find the simplified trigonometric integrand.")
CORRECTED_NARRATION=("First, for the integral of d x over the square root of x squared minus sixteen with x greater than four, determine the appropriate secant substitution and its differential to obtain the resulting trigonometric integrand.")

def make_source_pair(*,original:Path,academic_report:Path,out:Path)->dict:
    root=Path(original).resolve()
    source=Path(academic_report).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and source.is_file()
            and not source.is_symlink()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Only safe new external original-source repair bundle")
    report=json.loads(source.read_text(encoding="utf8"))
    require(report.get("status")==
             "ALL66_SOURCE_PDF_NARRATION_MATH_RISK_AUDIT_ONE_UNDERSPECIFIED_EXERCISE_NO_RELEASE"
            and report.get("confirmed_source_question_underdefinition_issues")==1
            and report.get("source_underdefined_question_counterexample",{}).get(
                "mathematical_counterexample",{}).get(
                "two_distinct_valid_resulting_integrands_symbolically_proved") is True
            and report.get("student_publication_authorized") is False
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Cannot repair without genuine original mathematical source proof")
    originals={p.name:file_hash(p) for p in root.iterdir()
               if p.is_file() and p.suffix.lower() in (".tex",".pdf",".txt",".json",".wav",".png",".mp4")}
    text=(root/"slides.tex").read_text(encoding="utf8")
    narration=(root/"script.txt").read_text(encoding="utf8")
    tts=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    require(text.count(ORIGINAL_TEX)==1
            and narration.count(ORIGINAL_NARRATION)==1
            and len(tts["slides"])==17
            and tts["slides"][16]["tts_text"].count(ORIGINAL_NARRATION)==1,
            "Existing physical source-LaTeX/voice script is not the inspected original")
    dest.mkdir()
    newtex=text.replace(ORIGINAL_TEX,CORRECTED_TEX)
    newscript=narration.replace(ORIGINAL_NARRATION,CORRECTED_NARRATION)
    tts["slides"][16]["tts_text"]=tts["slides"][16]["tts_text"].replace(
        ORIGINAL_NARRATION,CORRECTED_NARRATION)
    require(CORRECTED_TEX in newtex and CORRECTED_NARRATION in newscript
            and CORRECTED_NARRATION in tts["slides"][16]["tts_text"],
            "Corrected source and narration are not paired")
    tts_original=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    for i in range(16):
        require(tts_original["slides"][i]==tts["slides"][i],
                "No other original slide narration may change")
    original_sentences,_=tokenize_reference_sentences(
        tts_original["slides"][16]["tts_text"])
    new_sentences,_=tokenize_reference_sentences(tts["slides"][16]["tts_text"])
    require(len(original_sentences)==len(new_sentences)==4,
            "Only one original Slide17 sentence replacement allowed")
    changed=[n for n,(a,b) in enumerate(zip(original_sentences,new_sentences),1)
             if a["narration_fragment_sha256"]!=b["narration_fragment_sha256"]]
    require(changed==[2],"Only known underdetermined source question may be revised")
    (dest/"slides.tex").write_text(newtex,encoding="utf8")
    (dest/"script.txt").write_text(newscript,encoding="utf8")
    (dest/"script_tts.json").write_text(
        json.dumps(tts,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    for figure in root.glob("Figure*.png"):
        shutil.copy2(figure,dest/figure.name)
    for figure in root.glob("figure*.png"):
        shutil.copy2(figure,dest/figure.name)
    exe=shutil.which("pdflatex")
    require(exe is not None,"Native Windows MikTeX pdflatex unavailable")
    for _ in range(2):
        check=subprocess.run(
            [exe,"-interaction=nonstopmode","-halt-on-error",
             "-output-directory",str(dest),str(dest/"slides.tex")],
            cwd=dest,capture_output=True,text=True,timeout=140)
        require(check.returncode==0,
                "MikTeX failed, see preserved private original-source bundle log")
    revised=dest/"slides.pdf"
    require(revised.is_file(),"Corrected genuine slide deck missing")
    with pymupdf.open(root/"slides.pdf") as orig,pymupdf.open(revised) as new:
        require(len(orig)==len(new)==17,
                "Corrected deck lost original slide count")
        for i in range(16):
            require(" ".join(orig[i].get_text().split())==
                    " ".join(new[i].get_text().split()),
                    "Unaffected original slide visible text changed")
            original_pix=orig[i].get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),
                                          alpha=False)
            updated_pix=new[i].get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),
                                         alpha=False)
            require(original_pix.width==updated_pix.width and
                    original_pix.height==updated_pix.height and
                    original_pix.samples==updated_pix.samples,
                    "An unmodified original slide has changed visible PDF pixels")
        page=" ".join(new[16].get_text().split())
        compact="".join(page.split())
        require("resulting trigonometric integrand" in page
                and "For I" in page
                and ("x2−16" in compact or "x2-16" in compact)
                and "with x > 4" in page,
                "Corrected full original integral not present")
        require("For an integral containing" not in page,
                "Underdefined original problem statement survived")
    # The fixed problem must not trip the generic pre-TTS anti-ambiguity rule.
    lint=inspect_math_semantics(
        "**Slide 1 [60 sec]:\n"+tts["slides"][16]["tts_text"],
        source_sha256=EXPECTED_SOURCE_SHA)
    require(not any(x["rule"]==
                "incomplete_integral_does_not_define_transformed_integrand"
                for x in lint["findings"]),
            "Original underdetermined question remains in corrected narration")
    for name,digest in originals.items():
        require(file_hash(root/name)==digest,
                "Protected original PDF/WAV source files changed during paired repair")
    result={
        "schema_version":1,"status":STATUS,
        "original_textbook_sha256":EXPECTED_SOURCE_SHA,
        "math_source_audit_sha256":file_hash(source),
        "corrected_tex_sha256":file_hash(dest/"slides.tex"),
        "corrected_pdf_sha256":file_hash(revised),
        "corrected_script_txt_sha256":file_hash(dest/"script.txt"),
        "corrected_script_tts_sha256":file_hash(dest/"script_tts.json"),
        "source_original_narration_slide":17,
        "exact_changed_source_original_sentence_indices":[2],
        "corrected_slide_pages":17,
        "other_16_original_PDF_page_texts_unchanged":True,
        "other_16_original_PDF_page_pixels_bit_identical":True,
        "real_synthesized_replacement_WAV_available":False,
        "original_all_other_WAVs_preserved":True,
        "correction_accepts_full_integral_and_domain":True,
        "pre_TTS_underdefined_integrand_guard_pass":True,
        "source_originals_modified":False,
        "student_publication_authorized":False,
        "release_eligible":False,
        "source_corrected_question_text":CORRECTED_TEX,
        "source_corrected_speech_text":CORRECTED_NARRATION,
    }
    with (dest/"PAIR_SOURCE_PROOF_NO_AUDIO.json").open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("original","academic_report","out"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    r=make_source_pair(**vars(p.parse_args()))
    print(json.dumps(r,indent=2))
if __name__=="__main__":main()
