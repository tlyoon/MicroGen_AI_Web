"""Merge two ORIGINAL publisher-grounded real lecture academic fixes safely.

One isolated replacement bundle with BOTH the corrected arctangent figure6
narration/slide and corrected principal-arcsine review question narration/slide.
Neither original slide6.wav nor slide17.wav can be reused against changed
spoken words. No TTS bill, no student media, no implicit publication.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .original_thomas84_endpoint_repair import OLD as OLD_SL17,NEW as NEW_SL17
from .original_thomas84_arctangent_paired_repair import (
    FIGURE_STATUS,OLD_WORDS,NEW_WORDS)
from .inverse_trig_principal_domain_guard import inspect_tex
from .automatic_math_semantic_qa import _detect
from .runner import blocks
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences

OLD_REVIEW_SPEECH=(
    "Second, why are domain restrictions strictly enforced on substitution "
    "angles, such as theta being between negative pi over two and positive pi "
    "over two for sine and tangent, and how do these restrictions affect the "
    "elimination of radical absolute value bars?"
)
CORRECT_REVIEW_SPEECH=(
    "Second, why do we restrict tangent substitution angles strictly between "
    "negative pi over two and positive pi over two, while the principal arcsine "
    "interval includes both endpoints, and how do valid angle restrictions "
    "help simplify radicals without incorrect absolute value signs?"
)

def join(*,original:Path,slide17_fix:Path,slide6_fix:Path,out:Path)->dict:
    original,slide17_fix,slide6_fix,out=(Path(x).absolute() for x in
                                         (original,slide17_fix,slide6_fix,out))
    source=original/"source.pdf"
    tex=original/"slides.tex"
    script=original/"script.txt"
    slides=original/"slides.pdf"
    original_wav6=original/"slide6.wav"
    original_wav17=original/"slide17.wav"
    fixes=[slide17_fix/"source_domain_endpoint_repair_receipt.json",
           slide6_fix/"original_slide6_paired_math_correction_no_audio.json"]
    figure_assets=[original/f"Figure 8.{j}.png" for j in range(2,7)]
    protected=[source,tex,script,slides,original_wav6,original_wav17,
               slide17_fix/"slides.tex",slide17_fix/"slides.pdf",
               slide6_fix/"slides.tex",slide6_fix/"slides.pdf",
               slide6_fix/"script.txt",*fixes,*figure_assets]
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and not out.is_relative_to(slide17_fix)
            and not out.is_relative_to(slide6_fix)
            and all(x.is_file() and not x.is_symlink() for x in protected),
            "Only a separate empty destination and immutable source revisions")
    originals={str(f):_sha(f) for f in protected}
    earlier=json.loads(fixes[0].read_text(encoding="utf8"))
    later=json.loads(fixes[1].read_text(encoding="utf8"))
    require(earlier.get("status")
                =="ORIGINAL_SOURCE_PROVEN_ISOLATED_SLIDE17_ENDPOINT_REPAIRED"
            and later.get("status")
                =="ORIGINAL_SLIDE6_MATH_AND_NARRATION_CORRECTED_AUDIO_STALE"
            and earlier["source_sha256"]==later["original_textbook_sha256"]==_sha(source)
            and earlier["source_slides_sha256"]==later["original_slides_sha256"]==_sha(slides)
            and later["fixed_slide_numbers"]==[6]
            and later["old_slide6_wav_is_stale_and_not_safe_for_corrected_video"] is True,
            "Mismatched or unreviewed source academic fixes cannot be combined")
    source_tex=tex.read_text(encoding="utf8")
    source_script=script.read_text(encoding="utf-8-sig")
    tex6=(slide6_fix/"slides.tex").read_text(encoding="utf8")
    tex17=(slide17_fix/"slides.tex").read_text(encoding="utf8")
    repaired6=(slide6_fix/"script.txt").read_text(encoding="utf8")
    require(source_tex.count(OLD_SL17)==1
            and tex6.count(OLD_SL17)==1
            and tex17.count(NEW_SL17)==1
            and source_script.count(OLD_REVIEW_SPEECH)==1
            and repaired6.count(OLD_REVIEW_SPEECH)==1
            and len([a for a in OLD_WORDS if a in repaired6])==0
            and all(q in repaired6 for q in NEW_WORDS),
            "Original textual corrections no longer agree with physical sources")
    cumulative_tex=tex6.replace(OLD_SL17,NEW_SL17)
    require(cumulative_tex.replace(NEW_SL17,OLD_SL17)==tex6,
            "Combining source academic changes altered unrelated math")
    cumulative_script=repaired6.replace(OLD_REVIEW_SPEECH,CORRECT_REVIEW_SPEECH)
    require(cumulative_script.replace(CORRECT_REVIEW_SPEECH,OLD_REVIEW_SPEECH)
            ==repaired6,"Combining voice text altered unrelated narration")
    old_units=dict(blocks(source_script))
    new_units=dict(blocks(cumulative_script))
    require(len(old_units)==len(new_units)==17,
            "Cumulative source correction dropped a narration slide")
    changes={}
    for n in range(1,18):
        old,_=tokenize_reference_sentences(old_units[n])
        new,_=tokenize_reference_sentences(new_units[n])
        require(len(old)==len(new),
                f"Source narration sentence structure unexpectedly changed on slide {n}")
        altered=[j for j,(a,b) in enumerate(zip(old,new),1)
                 if a["narration_fragment_sha256"]!=b["narration_fragment_sha256"]]
        if altered:
            changes[n]=altered
    require(changes=={6:[2,4],17:[3]},
            "Only exactly three source-repaired spoken sentences may differ")
    require(inspect_tex(cumulative_tex)["blocking_count"]==0
            and _detect(6,new_units[6])==[],
            "Merged original source still contains known mathematical confusion")
    products=[out/"slides.tex",out/"slides.pdf",out/"script.txt",
              out/"original_two_slides_source_corrected_audio_stale.json",
              *[out/x.name for x in figure_assets]]
    require(all(not file.exists() for file in products),
            "Exclusive output; never overwrite corrected teaching artifacts")
    (out/"slides.tex").write_text(cumulative_tex,encoding="utf8")
    (out/"script.txt").write_text(cumulative_script,encoding="utf8")
    for item in figure_assets:
        shutil.copyfile(item,out/item.name)
    pdflatex=shutil.which("pdflatex")
    require(pdflatex is not None,"Only native Windows MiKTeX is approved")
    build=subprocess.run([pdflatex,"-interaction=nonstopmode",
                          "-halt-on-error","-no-shell-escape","slides.tex"],
                         cwd=out,capture_output=True,text=True,timeout=150)
    require(build.returncode==0,
            "Merged source lecture pdf compile failed: "+build.stdout[-1100:])
    changed=[]
    with pymupdf.open(slides) as previous,pymupdf.open(
            slide6_fix/"slides.pdf") as fixed6,pymupdf.open(
            slide17_fix/"slides.pdf") as fixed17,pymupdf.open(
            out/"slides.pdf") as merged:
        require(len(previous)==len(fixed6)==len(fixed17)==len(merged)==17,
                "Original complete lesson page count drift")
        for index in range(17):
            original=previous[index]
            merged_page=merged[index]
            must=(fixed6[index] if index==5 else
                  fixed17[index] if index==16 else original)
            # No single-pixel unintended edits permitted, including figures,
            # title counters, mathematical equations or pagination.
            a=must.get_pixmap(alpha=False)
            b=merged_page.get_pixmap(alpha=False)
            require(a.width==b.width and a.height==b.height
                    and a.samples==b.samples
                    and must.get_text()==merged_page.get_text(),
                    f"Original merged academic correction changes unrelated slide {index+1}")
            if index in (5,16):
                old=original.get_pixmap(alpha=False)
                require(old.samples!=b.samples,
                        "Corrected scientific slide did not visibly change")
                changed.append(index+1)
    require(changed==[6,17],
            "Expected exact two corrected source slide images")
    require({str(x):_sha(x) for x in protected}==originals,
            "Protected original WAV, original/source PDFs or reviewed repairs mutated")
    result={
        "schema_version":1,
        "status":"CUMULATIVE_ORIGINAL_SLIDES_6_AND_17_MATH_PAIRED_AUDIO_STALE",
        "original_textbook_sha256":_sha(source),
        "original_slides_sha256":_sha(slides),
        "original_script_sha256":_sha(script),
        "corrected_slides_pdf_sha256":_sha(out/"slides.pdf"),
        "corrected_script_sha256":_sha(out/"script.txt"),
        "original_two_verified_revision_receipts_sha256":[_sha(q) for q in fixes],
        "only_corrected_slides":[6,17],
        "changed_narration_sentences_by_slide":{"6":[2,4],"17":[3]},
        "unaltered_fifteen_slide_rasters_equal_original":True,
        "corrected_two_slide_rasters_equal_independently_reviewed_fixes":True,
        "stale_original_wav_sha256":{"6":_sha(original_wav6),
                                     "17":_sha(original_wav17)},
        "old_original_wavs_reuse_prohibited":[6,17],
        "fresh_faithful_tts_required":[6,17],
        "fresh_corrected_audio_verified":False,
        "complete_section_source_and_figure_semantics_accepted":False,
        "all_original_lecture_highlights_accepted":False,
        "student_publication_authorized":False,
    }
    with (out/"original_two_slides_source_corrected_audio_stale.json").open(
            "x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=True)
        f.write("\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original","slide17-fix","slide6-fix","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args(argv)
    receipt=join(original=a.original,slide17_fix=a.slide17_fix,
                 slide6_fix=a.slide6_fix,out=a.out)
    print(json.dumps({"status":receipt["status"],
                      "changed_slides":receipt["only_corrected_slides"],
                      "revoice_required":receipt["fresh_faithful_tts_required"]}))
if __name__=="__main__":
    main()
