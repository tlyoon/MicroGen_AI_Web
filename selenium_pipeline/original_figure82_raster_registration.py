"""Real original Thomas 8.4 Figure 8.2 vector-to-slide bitmap comparison.

This is a conservative foreground-shape registration hypothesis for the three
textbook reference triangles. Source text/labels and panel identities remain
unapproved even when a raster descriptor similarity exceeds a control.
"""
from __future__ import annotations
import argparse
import io
import json
import math
from pathlib import Path
from PIL import Image
import pymupdf
from .figure_source_identity import require,_sha

_ORIGINAL_SOURCE_SHA="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
_SOURCE_CROP=pymupdf.Rect(256,496,542,594)

def binary(image:Image.Image)->bytes:
    resized=image.convert("L").resize((125,41),Image.Resampling.BILINEAR)
    return bytes(int(v<205) for v in resized.tobytes())

def dice(original:bytes,slide:bytes)->float:
    require(len(original)==len(slide)==5125,"Invalid independently resized bitmap grid")
    a=sum(original);b=sum(slide)
    return (2*sum(int(x and y) for x,y in zip(original,slide))/(a+b)
            if a+b else 0.)

def register(source:Image.Image,slide:Image.Image)->dict:
    reference=binary(slide)
    baseline=binary(source.crop((0,0,175,135)))
    control=dice(baseline,reference)
    proposals=[]
    for x0 in range(0,51,5):
        for y0 in range(0,31,5):
            for x1 in range(source.width-51,source.width,5):
                for y1 in range(source.height-30,source.height,5):
                    if x1-x0<400 or y1-y0<130:
                        continue
                    part=binary(source.crop((x0,y0,x1,y1)))
                    value=dice(part,reference)
                    proposals.append((value,(x0,y0,x1,y1)))
    require(bool(proposals),"No bounded foreground registration hypotheses")
    best,window=max(proposals)
    return {"source_to_slide_foreground_dice_best":round(best,5),
            "unrelated_source_corner_control_dice":round(control,5),
            "best_source_crop_internal_pixels":list(window),
            "tested_bounded_registration_windows":len(proposals),
            "shape_correspondence_candidate":bool(best>=.25 and best>=4*control),
            "figure_panel_labels_scientifically_proven":False,
            "figure_completeness_certified":False}

def inspect(*,source:Path,slides:Path,output_dir:Path)->dict:
    source,slides,output_dir=(Path(x).absolute() for x in
                              (source,slides,output_dir))
    require(output_dir.is_dir() and not output_dir.is_symlink()
            and not output_dir.is_relative_to(source.parent),
            "Only an external, preexisting, isolated QA output directory")
    original_hash=_sha(source);slide_hash=_sha(slides)
    require(original_hash==_ORIGINAL_SOURCE_SHA,
            "Only hash-pinned authentic Thomas 8.4 source supported")
    images=[output_dir/"figure82_original_source_vector_raster.png",
            output_dir/"figure82_visible_slide_original_bitmap.png"]
    receipt=output_dir/"figure82_source_raster_registration_review_only.json"
    require(all(not p.exists() for p in [*images,receipt]),
            "Never overwrite original or prior figure comparison evidence")
    with pymupdf.open(source) as book,pymupdf.open(slides) as deck:
        require(len(book)>=1 and len(deck)>=4,"Original figure source/pages missing")
        page=book[0]
        rect=page.rect
        require(rect.contains(_SOURCE_CROP),
                "Pinned source figure geometric corridor outside textbook page")
        # Three independent reference-triangle line/path bundles from textbook.
        drawing_rects=[pymupdf.Rect(x["rect"]) for x in page.get_drawings()]
        triangles=[(267.5,508.,333.5,556.),
                   (351.5,508.,417.5,556.),
                   (435.5,508.,501.5,556.)]
        require(all(any(abs(r.x0-x0)<1 and abs(r.y0-y0)<1
                        and abs(r.x1-x1)<1 and abs(r.y1-y1)<1
                        for r in drawing_rects)
                    for x0,y0,x1,y1 in triangles),
                "Three original figure vector triangles missing or changed")
        require(any(h.y0>590 and h.y1<615
                    for h in page.search_for("FIGURE 8.2")),
                "Original textbook caption nearest three triangles missing")
        material=[x for x in deck[3].get_image_info(xrefs=True)
                  if x["width"]>=300 and x["height"]>=100 and
                  int(x.get("xref",0))>0]
        require(len(material)==1,"Expected exactly one original slide figure bitmap")
        data=deck.extract_image(material[0]["xref"])
        require(len(data["image"])<6_000_000,"Slide figure bitmap unbounded")
        slide_bitmap=Image.open(io.BytesIO(data["image"])).convert("RGB")
        require(slide_bitmap.size==(409,134),
                "Original three-triangle source slide bitmap dimensions drift")
        source_pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),
                                   clip=_SOURCE_CROP,alpha=False)
        source_bitmap=Image.frombytes("RGB",
             (source_pix.width,source_pix.height),source_pix.samples)
        mapping=register(source_bitmap,slide_bitmap)
        source_bitmap.save(images[0])
        slide_bitmap.save(images[1])
    require(_sha(source)==original_hash and _sha(slides)==slide_hash,
            "Original textbook/slide PDFs mutated during pixel registration")
    report={"status":"SOURCE_FIGURE82_SHAPE_REGISTRATION_REVIEW_ONLY",
            "original_source_sha256":original_hash,
            "original_slides_sha256":slide_hash,
            "original_source_page":1,"original_slide_number":4,
            "source_pdf_crop_pt":list(_SOURCE_CROP),
            "source_pdf_triangle_bundles_found":3,
            "embedded_original_slide_image_pixels":[409,134],
            **mapping,
            "source_figure_identity_verified":False,
            "mathematical_and_panel_semantics_verified":False,
            "slide_highlighting_authorized":False,
            "student_publication_authorized":False}
    with receipt.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("source","slides","output-dir"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args(argv)
    result=inspect(source=a.source,slides=a.slides,output_dir=a.output_dir)
    print(json.dumps({"status":result["status"],
        "foreground_dice":result["source_to_slide_foreground_dice_best"],
        "control_dice":result["unrelated_source_corner_control_dice"],
        "correspondence_hypothesis":result["shape_correspondence_candidate"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
