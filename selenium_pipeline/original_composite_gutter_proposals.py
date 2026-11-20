"""Evidence-scoped native pixel gutter proposals from original slide composites.

This detector identifies ONLY long near-white vertical separators; it cannot
infer author-intended number of panels, triangle side labels or source truth.
Every consumer must treat these as REVIEW-ONLY candidates.
"""
from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path

import pymupdf
from PIL import Image

from .figure_source_identity import require, _sha
from .original_figure_raster_preflight import inspect_original_slide_figure


def propose_native_vertical_gutters(image:Image.Image, *, expected_panels:int=3,
                                     min_panel_width:int=60,
                                     min_gutter_width:int=5)->dict:
    """Fail closed on missing/extra gutters rather than divide image evenly."""
    if (type(expected_panels) is not int or expected_panels not in range(2,7)
        or type(min_panel_width) is not int or min_panel_width<30
        or type(min_gutter_width) is not int or min_gutter_width<4):
        raise ValueError("Invalid bounded proposal parameters")
    gray=image.convert("L")
    width,height=gray.size
    require(150<=width<=2000 and 60<=height<=1600 and width*height<=2_000_000,
            "Unsupported original composite native image dimensions")
    pix=gray.load()
    ys=range(2,height-2)
    ink=[sum(pix[x,y]<225 for y in ys) for x in range(width)]
    runs=[]
    start=None
    for x,count in enumerate(ink):
        if count<=1 and start is None:
            start=x
        elif count>1 and start is not None:
            if x-start>=min_gutter_width:
                runs.append([start,x])
            start=None
    if start is not None and width-start>=min_gutter_width:
        runs.append([start,width])
    internal=[r for r in runs if r[0]>=min_panel_width
              and r[1]<=width-min_panel_width]
    require(len(internal)==expected_panels-1,
            "Unique author-neutral gutter candidates not established")
    separators=[(a+b)//2 for a,b in internal]
    partitions=[0,*separators,width]
    require(all(b-a>=min_panel_width
                for a,b in zip(partitions,partitions[1:])),
            "Candidate panels too narrow or overlapping")
    records=[]
    identifiers=set()
    for i,(a,b) in enumerate(zip(partitions,partitions[1:]),1):
        crop=gray.crop((a,0,b,height))
        raw=crop.tobytes()
        digest=hashlib.sha256(raw).hexdigest()
        require(digest not in identifiers,
                "Indistinguishable panel candidates")
        identifiers.add(digest)
        pixel_count=(b-a)*height
        occupancy=sum(v<225 for v in raw)/pixel_count
        require(0.015<=occupancy<=0.90,
                "Blank or saturated candidate panel")
        records.append({
            "candidate_index":i,
            "native_bbox_px":[a,0,b,height],
            "panel_native_pixel_sha256":digest,
            "visible_ink_fraction":round(occupancy,6),
            "right_triangle_semantics_verified":False,
            "author_panel_label_verified":False,
            "original_textbook_provenance_verified":False,
        })
    return {
        "status":"VERTICAL_GUTTER_STRIP_PROPOSALS_ONLY",
        "native_composite_width":width,
        "native_composite_height":height,
        "detected_long_empty_vertical_runs_px":internal,
        "candidate_separator_x_px":separators,
        "candidate_strips":records,
        "author_intended_panel_count_verified":False,
        "all_source_panel_semantics_verified":False,
        "approved_for_narration_highlight":False,
        "publication_authorized":False,
    }


def inspect_original_composite_gutters(*,folder:Path,slide:int=4)->dict:
    root=Path(folder).absolute()
    require(slide==4, "Pilot must remain original reference-triangle Slide 4")
    parent=inspect_original_slide_figure(folder=root,slide=slide)
    require(parent["technical_figure_bbox_and_contrast_accepted"] is True
            and parent["material_figure_count"]==1,
            "Unambiguous original figure preflight required")
    source,slides,script=(root/name for name in
                          ("source.pdf","slides.pdf","script.txt"))
    hashes=tuple(_sha(p) for p in (source,slides,script))
    require((parent["original_source_sha256"],
             parent["original_slide_pdf_sha256"],
             parent["original_script_sha256"])==hashes,
            "Source-bound raster audit identity drift")
    with pymupdf.open(slides) as doc:
        page=doc[slide-1]
        images=[img for img in page.get_image_info(xrefs=True)
                if img["width"]>=48 and img["height"]>=48]
        require(len(images)==1 and type(images[0].get("xref")) is int
                and images[0]["xref"]>0,
                "Exactly one original embedded bitmap required")
        bitmap_data=doc.extract_image(images[0]["xref"])["image"]
        with Image.open(BytesIO(bitmap_data)) as original:
            img=original.convert("RGB")
        proposal=propose_native_vertical_gutters(img)
        rect=pymupdf.Rect(images[0]["bbox"])
        mapped=[]
        for record in proposal["candidate_strips"]:
            x0,_,x1,_=record["native_bbox_px"]
            mapped.append({
                **record,
                "candidate_slide_bbox_pdf_pt":[
                    round(rect.x0+rect.width*x0/img.width,4),
                    round(rect.y0,4),
                    round(rect.x0+rect.width*x1/img.width,4),
                    round(rect.y1,4)],
            })
    require(tuple(_sha(p) for p in (source,slides,script))==hashes,
            "Original source changed during gutter audit")
    return {
        **proposal,
        "candidate_strips":mapped,
        "original_source_sha256":hashes[0],
        "original_slides_sha256":hashes[1],
        "original_script_sha256":hashes[2],
        "original_slide":slide,
        "material_original_raster_count":1,
        "original_embedded_pixel_sha256":hashlib.sha256(img.tobytes()).hexdigest(),
        "individual_triangle_meaning_verified":False,
        "new_Gemini_request_sent":False,
        "student_publication_authorized":False,
    }


def main(argv=None)->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--folder",type=Path,required=True)
    ap.add_argument("--slide",type=int,default=4)
    args=ap.parse_args(argv)
    print(json.dumps(inspect_original_composite_gutters(
        folder=args.folder,slide=args.slide),indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
