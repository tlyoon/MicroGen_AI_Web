"""Safely correct signed reference triangle in previously repaired §8.4 deck.

Start from source-locked PR355 Slide17 repair, preserving that full
integral and all unmodified visual slides. Mathematically sound opposite
side length is |x| while tan(u)=x/2 remains SIGNED; paired new Kore
sentence needed. No old source/voice overwrite, no premature release.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
import pymupdf
import sympy as S
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_all66_independent_semantic_matrix import STATUS as REVIEW_STATUS
from .automatic_math_semantic_qa import inspect_math_semantics

STATUS="PAIRED_SOURCE_LOCKED_SIGNED_REFERENCE_TRIANGLE_SLIDE8_PDF_SCRIPT_REPAIR_NO_AUDIO"
ORIGINAL_TEX=r"\text{opposite} = x"
CORRECTED_TEX=r"\text{opposite} = |x|"
ORIGINAL_SPOKEN=("From the substitution, tangent u equals x over two, defining the opposite and adjacent sides of a right triangle.")
CORRECTED_SPOKEN=("From the substitution, tangent u equals x over two; the reference right triangle has opposite side length the absolute value of x and adjacent side length two, while tangent u retains the sign of x.")

def signed_geometry_proof()->dict:
    # x=-2 => signed tangent = -1, but opposite length must be +2.
    x=S.Integer(-2); a=S.Integer(2)
    signed=S.simplify(x/a)
    hyp=S.sqrt(a*a+x*x)
    require(signed==-1 and abs(x)==2 and hyp==2*S.sqrt(2)
            and abs(x)/hyp==1/S.sqrt(2)
            and signed!=abs(x)/a,
            "Signed reference angle and positive side lengths not independently justified")
    return {"domain":"all real x, a=2>0, principal arctangent",
            "counterexample_x":-2,
            "actual_signed_tan_u":-1,
            "unsigned_opposite_side_length":2,
            "reference_triangle_hypotenuse":"sqrt(4+x^2)",
            "signed_trigonometric_ratio_must_remain_x_over_2":True,
            "physical_side_length_must_be_abs_x":True}

def repair_signed_triangle(*,original:Path,prior_pair:Path,
                           full_semantic:Path,out:Path)->dict:
    root=Path(original).resolve()
    previous=Path(prior_pair).resolve()
    math=Path(full_semantic).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and previous.is_dir() and math.is_file()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent)
            and not dest.is_relative_to(previous),
            "Protected originals and exclusive external mathematical source bundle required")
    prev=json.loads((previous/"PAIR_SOURCE_PROOF_NO_AUDIO.json").read_text(encoding="utf8"))
    review=json.loads(math.read_text(encoding="utf8"))
    require(prev.get("status")==
                 "EXACT_PAIRED_SLIDE17_PDF_AND_NARRATION_TEXT_CORRECTION_AUDIO_NOT_YET_REGENERATED"
            and review.get("status")==REVIEW_STATUS
            and review.get("source_math_signed_triangle_issues_to_repair")==2
            and review.get("exact_real_source_narration_utterances_reviewed")==66
            and prev.get("corrected_pdf_sha256")==file_hash(previous/"slides.pdf")
            and prev.get("corrected_script_tts_sha256")==file_hash(previous/"script_tts.json")
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Physical signed-triangle source proof or previous exact integral repair missing")
    latex=(previous/"slides.tex").read_text(encoding="utf8")
    script=(previous/"script.txt").read_text(encoding="utf8")
    saved=json.loads((previous/"script_tts.json").read_text(encoding="utf8"))
    before=json.loads((previous/"script_tts.json").read_text(encoding="utf8"))
    require(latex.count(ORIGINAL_TEX)==1
            and script.count(ORIGINAL_SPOKEN)==1
            and saved["slides"][7]["tts_text"].count(ORIGINAL_SPOKEN)==1
            and saved["slides"][16]["tts_text"].count(
                prev["source_corrected_speech_text"])==1,
            "Cannot revise a missing or already modified source original sentence")
    source_hashes={z:file_hash(root/z) for z in (
        "source.pdf","slides.pdf","slides.tex","script_tts.json",
        "slide8.wav","slide17.wav","slide11.wav")}
    dest.mkdir()
    (dest/"slides.tex").write_text(latex.replace(ORIGINAL_TEX,CORRECTED_TEX),
                                  encoding="utf8")
    (dest/"script.txt").write_text(script.replace(ORIGINAL_SPOKEN,CORRECTED_SPOKEN),
                                 encoding="utf8")
    saved["slides"][7]["tts_text"]=saved["slides"][7]["tts_text"].replace(
        ORIGINAL_SPOKEN,CORRECTED_SPOKEN)
    (dest/"script_tts.json").write_text(
        json.dumps(saved,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    before_sent,_=tokenize_reference_sentences(before["slides"][7]["tts_text"])
    after_sent,_=tokenize_reference_sentences(saved["slides"][7]["tts_text"])
    changes=[i for i,(a,b) in enumerate(zip(before_sent,after_sent),1)
             if a["narration_fragment_sha256"]!=b["narration_fragment_sha256"]]
    require(len(before_sent)==len(after_sent)==5 and changes==[2],
            "Only the math-invalid signed side-length sentence may be revoiced")
    for i in range(17):
        if i!=7:
            require(saved["slides"][i]==before["slides"][i],
                    "Original unaffected narrated slides mutated")
    for figure in previous.glob("*.png"):
        shutil.copy2(figure,dest/figure.name)
    pdflatex=shutil.which("pdflatex")
    require(pdflatex is not None,"Windows MiKTeX not present")
    for attempt in range(2):
        run=subprocess.run([pdflatex,"-interaction=nonstopmode","-halt-on-error",
                            "-output-directory",str(dest),str(dest/"slides.tex")],
                           cwd=dest,capture_output=True,text=True,timeout=140)
        require(run.returncode==0,"Windows source original-PDF math compilation failed")
    with pymupdf.open(previous/"slides.pdf") as old,pymupdf.open(dest/"slides.pdf") as new:
        require(len(old)==len(new)==17,"New full original mathematical deck lost slides")
        for i in range(17):
            old_pix=old[i].get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),alpha=False)
            new_pix=new[i].get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),alpha=False)
            require(old_pix.width==new_pix.width and old_pix.height==new_pix.height,
                    "Real PDF changes page geometry")
            if i!=7:
                require(old_pix.samples==new_pix.samples,
                        "Original other slides changed visible pixels")
            else:
                require(old_pix.samples!=new_pix.samples,
                        "Signed-triangle maths not really changed in PDF pixels")
                old_txt=" ".join(old[i].get_text().split())
                new_txt=" ".join(new[i].get_text().split())
                require("opposite = x" in old_txt and
                        "opposite = |x|" in new_txt and
                        "tan u = x" in new_txt,
                        "Signed triangle revised mathematical form incorrect")
        require("For I =" in new[16].get_text(),
                "Earlier source corrected full Slide17 original integral was lost")
    proof=signed_geometry_proof()
    lint=inspect_math_semantics(
        "**Slide 1 [60 sec]:\n"+saved["slides"][7]["tts_text"],
        source_sha256=EXPECTED_SOURCE_SHA)
    require(lint["blocking_count"]==0,
            "Math signed side length source repair still blocks pre-TTS QA")
    require(all(file_hash(root/name)==sha for name,sha in source_hashes.items()),
            "Protected original source/recorded WAVs changed during math repair")
    result={"schema_version":1,"status":STATUS,
      "original_textbook_sha256":EXPECTED_SOURCE_SHA,
      "prior_corrected_final_math_source_pdf_SHA256":file_hash(previous/"slides.pdf"),
      "new_corrected_signed_triangle_and_final_question_PDF_SHA256":file_hash(dest/"slides.pdf"),
      "new_corrected_exact_TTS_script_sha256":file_hash(dest/"script_tts.json"),
      "corrected_original_slide":8,
      "changed_actual_narration_sentence_indices":[2],
      "unchanged_other_16_source_slides_pixels_identical":True,
      "prior_source_corrected_Slide17_integral_preserved":True,
      "actual_negative_x_reference_triangle_proof":proof,
      "corrected_spoken_math_text":CORRECTED_SPOKEN,
      "corrected_source_tex":CORRECTED_TEX,
      "real_corrected_Kore_PCM_available":False,
      "actual_student_release_accepted":False,
      "student_publication_authorized":False,
      "source_originals_modified":False}
    with (dest/"SIGNED_TRIANGLE_SOURCE_REPAIR_NO_AUDIO.json").open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for k in ("original","prior_pair","full_semantic","out"):
        p.add_argument("--"+k.replace("_","-"),type=Path,required=True)
    r=repair_signed_triangle(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in r.items() if k!="corrected_spoken_math_text"},indent=2))
if __name__=="__main__":main()
