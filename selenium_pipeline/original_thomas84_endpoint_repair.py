"""Read-only original Thomas 8.4 textbook-domain witness and isolated TeX repair.

A textbook source PDF plus the independently generated original slide
source must agree on distinct sine/tangent inverse ranges. This module
never alters originals or falsely approves other figures/equations.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import pymupdf

from .figure_source_identity import require, _sha

SOURCE_SHA="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
OLD=(r"such as $-\frac{\pi}{2} < \theta < \frac{\pi}{2}$ for sine and tangent")
NEW=(r"such as $-\frac{\pi}{2} < \theta < \frac{\pi}{2}$ for tangent"
     r" versus $-\frac{\pi}{2} \le \theta \le \frac{\pi}{2}$ for sine")

def prove_domain_distinction(*,source:Path,tex:str)->dict:
    require(_sha(source)==SOURCE_SHA, "Unrecognized original Thomas textbook PDF")
    with pymupdf.open(source) as textbook:
        require(len(textbook)>1, "Missing textbook source domain discussion")
        page=textbook[1].get_text()
    # The extraction preserves strict tangent vs inclusive arcsine using
    # numeral 6 for < and ellipsis for <= in the publisher's embedded font.
    tan=re.search(
        r"x = a tan u\s+requires\s+u = tan-1.*?"
        r"- p\s+2 6 u 6 p\s+2",
        page,re.S)
    sin=re.search(
        r"x = a sin u\s+requires\s+u = sin-1.*?"
        r"- p\s+2 … u … p\s+2",
        page,re.S)
    require(tan is not None and sin is not None,
            "Original source does not independently support tangent/sine bounds")
    require(r"For $x = a \sin \theta$" in tex
            and r"$-\frac{\pi}{2} \le \theta \le \frac{\pi}{2}$" in tex
            and r"For $x = a \tan \theta$" in tex
            and r"$-\frac{\pi}{2} < \theta < \frac{\pi}{2}$" in tex,
            "Original authored slide domain facts absent")
    require(tex.count(OLD)==1,
            "Unrecognized review question; no silent source modification")
    return {"source_textbook_page":2,
            "tangent_domain":"-pi/2 < theta < pi/2",
            "sine_domain":"-pi/2 <= theta <= pi/2",
            "original_review_question_incorrect":True,
            "scientific_mismatch_proven":True}

def fix(*,originals:Path,destination:Path)->dict:
    originals,destination=(Path(x).absolute() for x in (originals,destination))
    require(originals.is_dir() and destination.is_dir() and not destination.is_symlink()
            and not destination.is_relative_to(originals),
            "Only preexisting separate scratch folder can receive repaired output")
    source=originals/"source.pdf"
    old_tex=originals/"slides.tex"
    slidepdf=originals/"slides.pdf"
    assets=[originals/f"Figure 8.{i}.png" for i in range(2,7)]
    inputs=[source,old_tex,slidepdf,*assets]
    require(all(f.is_file() and not f.is_symlink() for f in inputs),
            "Missing original textbook, LaTeX, rendered slides or original figure")
    sha={p.name:_sha(p) for p in inputs}
    tex=old_tex.read_text(encoding="utf-8")
    evidence=prove_domain_distinction(source=source,tex=tex)
    # Do not overwrite any prior QA, even a partial failed compilation.
    outputs=[destination/"slides.tex",destination/"slides.pdf",
             destination/"source_domain_endpoint_repair_receipt.json",*(
             destination/p.name for p in assets)]
    require(all(not p.exists() for p in outputs),
            "Exclusive isolated output required; prior evidence must be preserved")
    edited=tex.replace(OLD,NEW)
    require(edited!=tex and edited.replace(NEW,OLD)==tex,
            "Only the proven textbook-domain wording may change")
    (destination/"slides.tex").write_text(edited,encoding="utf-8")
    for f in assets:
        shutil.copyfile(f,destination/f.name)
    exe=shutil.which("pdflatex")
    require(exe is not None, "Windows native pdfLaTeX required")
    # The preserved generated deck was compiled in one pass (its existing
    # headline says N / 1). A second run changes every slide's counter.
    # Reproduce the original compile count here; require pixel parity below.
    for _ in range(1):
        command=[exe,"-interaction=nonstopmode","-halt-on-error",
                 "-no-shell-escape","slides.tex"]
        done=subprocess.run(command,cwd=destination,capture_output=True,
                            text=True,timeout=120)
        require(done.returncode==0,
                "Isolated Windows TeX repair compilation failed: "+done.stdout[-1400:])
    output_pdf=destination/"slides.pdf"
    require(output_pdf.is_file(),"Isolated corrected PDF not generated")
    with pymupdf.open(slidepdf) as before,pymupdf.open(output_pdf) as after:
        require(len(before)==len(after)==17,
                "Corrected material changed original lecture slide count")
        unchanged=[]
        for idx in range(16):
            old_text=before[idx].get_text()
            new_text=after[idx].get_text()
            require(old_text==new_text,
                    f"Original slide {idx+1} content changed during one-slide repair")
            oldpix=before[idx].get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False)
            newpix=after[idx].get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False)
            require(oldpix.width==newpix.width and oldpix.height==newpix.height
                    and oldpix.samples==newpix.samples,
                    f"Original slide {idx+1} rendered pixels changed")
            unchanged.append(idx+1)
        final=after[16].get_text()
        require("for tangent" in final and "for sine" in final
                and "≤" in final,
                "Compiled corrected review slide lacks correct inclusive sine domain")
        require("sine and tangent" not in final,
                "Incorrect shared strict sine/tangent range persisted")
    require({_p.name:_sha(_p) for _p in inputs}==sha,
            "Protected original source/slide/media changed during fix")
    result={"status":"ORIGINAL_SOURCE_PROVEN_ISOLATED_SLIDE17_ENDPOINT_REPAIRED",
            "source_sha256":sha["source.pdf"],
            "source_slides_sha256":sha["slides.pdf"],
            "source_tex_sha256":sha["slides.tex"],
            "corrected_slides_sha256":_sha(output_pdf),
            "corrected_tex_sha256":_sha(destination/"slides.tex"),
            "textbook_semantic_witness":evidence,
            "only_changed_slide":17,
            "unchanged_slide_raster_pages":unchanged,
            "original_wavs_modified":False,
            "other_mathematical_formulas_approved":False,
            "figure_panels_approved":False,
            "student_publication_authorized":False}
    out=destination/"source_domain_endpoint_repair_receipt.json"
    out.write_text(json.dumps(result,indent=2,ensure_ascii=True)+"\n",encoding="utf-8")
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--originals",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(argv)
    result=fix(originals=args.originals,destination=args.output_dir)
    print(json.dumps({"status":result["status"],
                      "unchanged_slide_count":len(result["unchanged_slide_raster_pages"]),
                      "only_changed_slide":result["only_changed_slide"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
