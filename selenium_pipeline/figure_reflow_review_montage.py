"""Build read-only textbook-to-slide plot comparison PNG in isolated scratch.

The annotated montage is a review aid, NEVER an automatic figure replacement.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

from .figure_source_identity import _sha, require
from .figure_three_graph_color_reflow import audit_real_three_graph_reflow


def source_slide_plot_montage(*, source:Path, slides:Path, source_page:int,
                              slide_page:int, figure_id:str, output:Path) ->dict:
    spath, dpath, dest = map(lambda p:Path(p).absolute(), (source,slides,output))
    require(spath!=dpath and spath.is_file() and dpath.is_file(),
            "Two distinct original PDF files required")
    require(not dest.exists() and dest.parent.is_dir(),
            "New empty scratch folder path required")
    require(not dest.is_relative_to(spath.parent)
            and not dest.is_relative_to(dpath.parent),
            "Review output must not lie in original lecture folders")
    for path in (spath,dpath,dest,dest.parent):
        for part in (path,*path.parents):
            require(not part.is_symlink() and
                    not getattr(part,"is_junction",lambda:False)(),
                    "Linked originals or output folders disallowed")
    before=(_sha(spath),_sha(dpath))
    analysis=audit_real_three_graph_reflow(
        source=spath,slides=dpath,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    require(analysis["original_pdf_sha256"]==before[0]
            and analysis["existing_slides_pdf_sha256"]==before[1],
            "Stale or conflicting source and slide identities")
    count=analysis.get("detected_graph_count")
    require(type(count) is int and 2<=count<=6
            and analysis.get("three_graph_black_ink_geometry_plausible") is True
            and len(analysis["graph_correspondence_evidence"])==count,
            "Complete bounded and independently corroborated graph layout required")
    sx=analysis["source_scan_pixel_x_bounds"]
    require(type(sx) is list and len(sx)==2
            and all(type(x) is int for x in sx),
            "Missing original page render x bounds")
    with pymupdf.open(spath) as book, pymupdf.open(dpath) as deck:
        pix=book[source_page-1].get_pixmap(
            matrix=pymupdf.Matrix(3,3),colorspace=pymupdf.csRGB,alpha=False)
        source_image=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
        slide_instances=[i for i in deck[slide_page-1].get_image_info(xrefs=True)
                         if int(i["width"])>=48 and int(i["height"])>=48
                         and pymupdf.Rect(i["bbox"]).width>=50
                         and pymupdf.Rect(i["bbox"]).height>=25]
        require(len(slide_instances)==1
                and int(slide_instances[0].get("xref",0))>0,
                "Unique actual displayed slide bitmap required")
        with Image.open(io.BytesIO(
                deck.extract_image(slide_instances[0]["xref"])["image"])) as im:
            require(im.width*im.height<=2_000_000,
                    "Oversized original bitmap")
            slide_image=im.convert("RGB")
    require(0<=sx[0]<sx[1]<=source_image.width,
            "Invalid source horizontal crop bounds")
    plots=[]
    for i,pair in enumerate(analysis["graph_correspondence_evidence"]):
        sy=pair["source_scan_band_px"]
        tx=pair["slide_bitmap_scan_band_px"]
        require(type(sy) is list and type(tx) is list
                and len(sy)==2 and len(tx)==2
                and all(type(x) is int for x in sy+tx)
                and 0<=sy[0]<sy[1]<=source_image.height
                and 0<=tx[0]<tx[1]<=slide_image.width,
                "Invalid independently measured source-to-slide crop bands")
        original=source_image.crop((sx[0],sy[0],sx[1],sy[1]))
        existing=slide_image.crop((tx[0],0,tx[1],slide_image.height))
        require(original.width*original.height<=1_000_000 and
                existing.width*existing.height<=1_000_000,
                "Oversized plot crop")
        plots.append((original,existing))
    # Preserve exact original rendered pixels in left image and exact
    # original slide bitmap pixels on right; NO resampling or correction.
    first_width=max(a.width for a,_ in plots)
    second_width=max(b.width for _,b in plots)
    width=first_width+second_width+64
    height=sum(max(a.height,b.height)+30 for a,b in plots)+20
    require(width*height<=12_000_000,"Oversized comparison preview")
    montage=Image.new("RGB",(width,height),(250,250,250))
    painter=ImageDraw.Draw(montage)
    y=10
    for i,(a,b) in enumerate(plots,1):
        painter.text((12,y),f"Source original plot {i}",fill=(0,0,0))
        painter.text((first_width+44,y),f"Existing slide plot {i}",fill=(0,0,0))
        montage.paste(a,(10,y+17))
        montage.paste(b,(first_width+42,y+17))
        y+=max(a.height,b.height)+30
    stream=io.BytesIO()
    montage.save(stream,format="PNG")
    png=stream.getvalue()
    require(_sha(spath)==before[0] and _sha(dpath)==before[1],
            "Original files changed before preview output")
    receipt={
        "schema_version":1,
        "status":"SOURCE_BOUND_MULTIGRAPH_REVIEW_ONLY",
        "source_sha256":before[0],"slides_sha256":before[1],
        "source_page":source_page,"slide_page":slide_page,"figure_id":figure_id,
        "detected_graph_count":count,
        "source_to_slide_graph_bands":analysis["graph_correspondence_evidence"],
        "montage_file":"source_slide_comparison.png",
        "montage_sha256":hashlib.sha256(png).hexdigest(),
        "actual_axes_and_math_label_correctness_verified":False,
        "source_figure_complete_verified":False,
        "automatic_source_or_slide_replacement":False,
        "encoded_video_accepted":False,
        "publication_authorized":False,
    }
    dest.mkdir()
    try:
        with (dest/"source_slide_comparison.png").open("xb") as fh:
            fh.write(png)
        with (dest/"review_manifest.json").open("x",encoding="utf8") as fh:
            json.dump(receipt,fh,indent=2,sort_keys=True)
        require(_sha(spath)==before[0] and _sha(dpath)==before[1],
                "Original files changed during review output")
    except Exception:
        shutil.rmtree(dest)
        raise
    return receipt


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--source-page",type=int,required=True)
    p.add_argument("--slide-page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    print(json.dumps(source_slide_plot_montage(
        source=a.source,slides=a.slides,
        source_page=a.source_page,slide_page=a.slide_page,
        figure_id=a.figure_id,output=a.output),indent=2,sort_keys=True))
    return 2


if __name__=="__main__":
    raise SystemExit(main())
