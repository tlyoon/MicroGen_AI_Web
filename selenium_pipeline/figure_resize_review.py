"""Fail-closed isolated LaTeX figure enlargement (review only, no publication).

Never changes lecture source folders, merges PRs, or updates existing MP4s.
Requires an explicit single-image height substitution, compiles in a fresh
folder, and proves all OTHER rendered slides remain pixel-identical.
"""
from __future__ import annotations
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
import pymupdf
from .academic_visual_preflight import inspect

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as src:
        for chunk in iter(lambda:src.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def require(cond,msg):
    if not cond:raise ValueError(msg)

def figure_box(page):
    images=page.get_images(full=True)
    require(len(images)==1,"Exactly one target-page raster image expected")
    rectangles=page.get_image_rects(images[0][0])
    require(len(rectangles)==1,"Image placement missing or ambiguous")
    return rectangles[0]

def make(*,source:Path,dest:Path,image_name:str,
         old_height:float,new_height:float,slide_number:int,
         width_threshold:float=.18,
         compact_after_image_pt:float=0.0,
         compact_before_image_pt:float=0.0)->dict:
    source,dest=Path(source).resolve(),Path(dest).resolve()
    require(source.is_dir() and (source/"slides.tex").is_file()
            and (source/"slides.pdf").is_file(),"Source LaTeX/PDF missing")
    require(dest!=source and not dest.exists() and dest.parent.is_dir()
            and not dest.is_relative_to(source) and
            not source.is_relative_to(dest),"Destination must be new and isolated")
    require(re.fullmatch(r"[A-Za-z0-9_ .-]+\.(png|jpe?g)",image_name,re.I)
            is not None,"Unsafe image filename")
    require((source/image_name).is_file(),"Figure source asset missing")
    require(0.05<=old_height<new_height<=.60
            and 0<width_threshold<.5
            and -12<=compact_after_image_pt<=12
            and 0<=compact_before_image_pt<=12,
            "Figure sizing parameters invalid")
    latex=(source/"slides.tex").read_text(encoding="utf8")
    old=f"height={old_height:.2f}\\textheight,keepaspectratio]{{{image_name}}}"
    new=f"height={new_height:.2f}\\textheight,keepaspectratio]{{{image_name}}}"
    require(latex.count(old)==1,"Image sizing expression not uniquely matched")
    source_sha={name:sha(source/name) for name in ("slides.tex","slides.pdf",image_name)}
    dest.mkdir()
    for suffix in (".png",".jpg",".jpeg"):
        for p in source.glob("*"+suffix):
            require(p.is_file() and not p.is_symlink(),"Invalid source image")
            shutil.copy2(p,dest/p.name)
    updated=latex.replace(old,new)
    if compact_before_image_pt:
        marker=rf"\IfFileExists{{{image_name}}}"
        check_index=updated.index(new)
        marker_at=updated.rfind(marker,0,check_index)
        require(marker_at>=0 and updated.count(marker)==1,
                "Could not uniquely find target image conditional")
        updated=(updated[:marker_at]+
                 rf"\vspace{{-{compact_before_image_pt:g}pt}}"+"\n  "+
                 updated[marker_at:])
    if compact_after_image_pt:
        # Avoid globally tightening unrelated itemize blocks; only the first
        # list which follows the exact target image in this LaTeX frame.
        position=updated.index(new)+len(new)
        itemize=updated.find(r"\begin{itemize}",position)
        frame_end=updated.find(r"\end{frame}",position)
        require(itemize>=0 and frame_end>itemize,
                "Target figure has no following in-frame itemize list")
        updated=(updated[:itemize]
                 +rf"\vspace{{{-compact_after_image_pt:g}pt}}"+"\n  "
                 +updated[itemize:])
    (dest/"slides.tex").write_text(updated,encoding="utf8")
    cmd=["pdflatex","-interaction=nonstopmode","-halt-on-error","slides.tex"]
    try:
        result=subprocess.run(cmd,cwd=str(dest),capture_output=True,
                              text=True,errors="replace",timeout=120,check=False)
    except (OSError,subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Isolated LaTeX compilation could not finish") from exc
    require(result.returncode==0 and (dest/"slides.pdf").is_file(),
            "Candidate LaTeX compile failed (see slides.log)")
    with pymupdf.open(source/"slides.pdf") as before, pymupdf.open(dest/"slides.pdf") as after:
        require(len(before)==len(after)
                and 1<=slide_number<=len(before),"Slide count changed")
        old_rect=figure_box(before[slide_number-1])
        new_rect=figure_box(after[slide_number-1])
        old_fraction=old_rect.width/before[slide_number-1].rect.width
        new_fraction=new_rect.width/after[slide_number-1].rect.width
        require(new_fraction>old_fraction and
                new_fraction>=width_threshold,"Figure remains too narrow")
        changed=[]
        for i in range(len(before)):
            original=before[i].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
            candidate=after[i].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
            if (original.width!=candidate.width or
                original.height!=candidate.height or
                hashlib.sha256(original.samples).digest()!=
                    hashlib.sha256(candidate.samples).digest()):
                changed.append(i+1)
        require(changed==[slide_number],
                "Unintended slides changed in isolated compiled deck: "+str(changed))
        before[slide_number-1].get_pixmap(matrix=pymupdf.Matrix(2,2),
            alpha=False).save(dest/"target_slide_before.png")
        after[slide_number-1].get_pixmap(matrix=pymupdf.Matrix(2,2),
            alpha=False).save(dest/"target_slide_after.png")
        count=len(before)
    qa=inspect(dest/"slides.pdf")
    require(qa["blocker_count"]==0,"Rendered PDF includes technical clipping")
    require(not any(f.get("reason")=="figure_small_on_slide"
        for f in qa["details"][slide_number-1]["findings"]),
        "Visual preflight still flags figure on target slide")
    require(all(sha(source/name)==digest for name,digest in source_sha.items()),
            "Original lecture files changed during evaluation")
    receipt={"status":"REVIEW_ONLY_ISOLATED_FIGURE_RESIZE",
       "source_folder":str(source),"derived_folder":str(dest),
       "source_slides_sha256":source_sha["slides.pdf"],
       "derived_slides_sha256":sha(dest/"slides.pdf"),
       "original_slide_count":count,
       "changed_rendered_slide_numbers":changed,
       "target_slide":slide_number,"image":image_name,
       "before_width_fraction":round(old_fraction,4),
        "after_width_fraction":round(new_fraction,4),
        "compact_after_image_pt":compact_after_image_pt,
        "compact_before_image_pt":compact_before_image_pt,
       "technical_pdf_blockers":qa["blocker_count"],
       "human_academic_approval":False,"production_approved":False,
       "narration_and_video_reverification_required":True}
    with (dest/"figure_resize_receipt.json").open("x",encoding="utf8") as out:
        json.dump(receipt,out,indent=2);out.write("\n")
    return receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--destination",type=Path,required=True)
    p.add_argument("--image",required=True)
    p.add_argument("--old-height",type=float,required=True)
    p.add_argument("--new-height",type=float,required=True)
    p.add_argument("--slide",type=int,required=True)
    p.add_argument("--compact-after-image-pt",type=float,default=0.0)
    p.add_argument("--compact-before-image-pt",type=float,default=0.0)
    args=p.parse_args()
    print(json.dumps(make(source=args.source,dest=args.destination,
         image_name=args.image,old_height=args.old_height,
         new_height=args.new_height,slide_number=args.slide,
         compact_after_image_pt=args.compact_after_image_pt,
         compact_before_image_pt=args.compact_before_image_pt),indent=2))

if __name__=="__main__":main()
