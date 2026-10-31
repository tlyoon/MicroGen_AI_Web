"""Original Thomas §8.4 reference-triangle vector/bitmap body comparison.

Use the actual source PDF paths and labels, a source-local bounded raster
registration search, and an unrelated source crop control. A better match
than a negative control is a *hypothesis*, not proof of exact panel identity.
Never approve publication or assume cropped images are complete.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from PIL import Image
import pymupdf
from .figure_source_identity import require,_sha

_SOURCE_SHA="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
CASES=(
    {"id":"8.4","page":3,"slide":10,"center":(94.,93.),"width":100.,
     "vector":(53.9,74.1,124.4,113.7),"labels":("u","x","2")},
    {"id":"8.5","page":4,"slide":13,"center":(63.,105.),"width":100.,
     "vector":(29.9,74.7,97.9,122.7),"labels":("u","x","3")},
    {"id":"8.6","page":4,"slide":15,"center":(62.,627.),"width":102.,
     "vector":(30.4,592.1,58.6,655.9),"labels":("u","5x","2")},
)

def foreground(image:Image.Image)->bytes:
    smaller=image.convert("L").resize((100,100),Image.Resampling.BILINEAR)
    return bytes(1 if value<198 else 0 for value in smaller.tobytes())

def overlap_dice(a:bytes,b:bytes)->float:
    require(len(a)==len(b)==10000,"Raster evidence grid changed")
    denom=sum(a)+sum(b)
    return 2*sum(1 for x,y in zip(a,b) if x and y)/denom if denom else 0.

def register(source:Image.Image,target:Image.Image,
             *,center:tuple[float,float],width:float)->dict:
    reference=foreground(target)
    control=foreground(source.crop((620,160,800,320))) # source PT (310,80,400,160) at 2x
    baseline=overlap_dice(reference,control)
    observations=[]
    for w in (width-20,width-10,width,width+10,width+20):
        h=w*target.height/target.width
        for dx in (-15,-9,-3,3,9,15):
            for dy in (-15,-9,-3,3,9,15):
                x,y=center[0]+dx,center[1]+dy
                rect=(int((x-w/2)*2),int((y-h/2)*2),
                      int((x+w/2)*2),int((y+h/2)*2))
                if min(rect)<0 or rect[2]>source.width or rect[3]>source.height:
                    continue
                match=overlap_dice(reference,foreground(source.crop(rect)))
                observations.append((match,[round(v/2,1) for v in rect]))
    require(len(observations)>=100,"Insufficient original source local raster search")
    score,bounds=max(observations)
    # This is deliberately only shape/crop hypothesis, NEVER semantic approval.
    return {"best_source_local_foreground_dice":round(score,5),
            "unrelated_source_control_dice":round(baseline,5),
            "source_crop_hypothesis_pt":bounds,
            "registration_windows_tested":len(observations),
            "shape_matches_control_by_factor_gt_2_5":bool(score>2.5*baseline),
            "original_figure_crop_exactly_proven":False,
            "triangle_source_label_to_bitmap_equivalence_approved":False}

def audit(*,source:Path,slides:Path,assets:Path)->dict:
    source,slides,assets=(Path(p).absolute() for p in (source,slides,assets))
    require(source.is_file() and slides.is_file() and assets.is_dir(),
            "Original source, slides and authored PNGs required")
    require(_sha(source)==_SOURCE_SHA,"Unknown source: refuse diagram identity inference")
    originals=[source,slides,*[assets/f"Figure {x['id']}.png" for x in CASES]]
    require(all(p.is_file() and not p.is_symlink() for p in originals),
            "Original figure bitmap or source not found")
    before=[_sha(p) for p in originals]
    results=[]
    with pymupdf.open(source) as book,pymupdf.open(slides) as deck:
        require(len(book)>=4 and len(deck)==17,"Wrong publisher or lecture version")
        for item in CASES:
            page=book[item["page"]-1]
            bounds=pymupdf.Rect(item["vector"])
            require(any(all(abs(a-b)<1. for a,b in
                            zip(pymupdf.Rect(d["rect"]),bounds))
                        for d in page.get_drawings()),
                    f"Original textbook triangle vectors missing for {item['id']}")
            words=[str(w[4]) for w in page.get_text("words")
                   if pymupdf.Rect(w[:4]).intersects(
                     pymupdf.Rect(item["center"][0]-70,item["center"][1]-70,
                                  item["center"][0]+70,item["center"][1]+70))]
            require(all(label in words for label in item["labels"]),
                    f"Original figure {item['id']} scientific side labels absent")
            actual=[info for info in deck[item["slide"]-1].get_image_info(xrefs=True)
                    if info["width"]>=70 and info["height"]>=50]
            require(len(actual)==1,
                    "Ambiguous original visible slide figure image")
            figure=assets/f"Figure {item['id']}.png"
            with Image.open(figure) as image:
                target=image.convert("RGB")
            pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
            rendered=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
            evidence=register(rendered,target,center=item["center"],width=item["width"])
            require(evidence["shape_matches_control_by_factor_gt_2_5"]
                    and evidence["best_source_local_foreground_dice"]>=.25,
                    f"Original figure {item['id']} body not distinguishable from unrelated source")
            results.append({
                "figure_id":item["id"],
                "original_textbook_page":item["page"],
                "original_slide_number":item["slide"],
                "original_vector_path_bbox_pt":list(item["vector"]),
                "source_visible_label_tokens":list(item["labels"]),
                "slide_bitmap_pixels":list(target.size),
                **evidence})
    require([_sha(p) for p in originals]==before,
            "Protected original textbook/slides/figures changed")
    return {"status":"THREE_TRIANGLE_SOURCE_BODY_SHAPE_CANDIDATES_REVIEW_ONLY",
            "source_pdf_sha256":before[0],"slides_pdf_sha256":before[1],
            "original_triangle_body_candidates":results,
            "original_figure_panel_semantics_approved":False,
            "automated_student_release_approved":False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ("source","slides","assets","out"):
        parser.add_argument("--"+flag,required=True,type=Path)
    args=parser.parse_args(argv)
    out=args.out.absolute()
    require(out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(args.source.absolute().parent),
            "Exclusive external QA receipt needed")
    result=audit(source=args.source,slides=args.slides,assets=args.assets)
    with out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    print(json.dumps({"status":result["status"],
                      "figures":[(x["figure_id"],
                                  x["best_source_local_foreground_dice"],
                                  x["unrelated_source_control_dice"])
                                 for x in result["original_triangle_body_candidates"]]}))
if __name__=="__main__":
    main()
