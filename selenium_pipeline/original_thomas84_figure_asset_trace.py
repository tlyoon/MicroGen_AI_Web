"""Original Thomas 8.4 source-caption, figure file, and slide bitmap trace.

Verifies exact decoded bitmap equality for all FIVE generated figure files
against the actual original PDF placements plus separately located original
textbook captions. A source FIGURE caption and an identical slide-local
asset do NOT prove cropped panel completeness or mathematical source-body
identity. Every such approval flag is false by design.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
from PIL import Image,ImageChops
import pymupdf
from .figure_source_identity import require,_sha

SOURCE_SHA="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
# Physical source page indexes independently found in original textbook.
EXPECTED={("8.2",4):1,("8.3",6):2,("8.4",10):3,
          ("8.5",13):4,("8.6",15):4}

def pixels_equal(asset:Image.Image,encoded:Image.Image)->bool:
    a,b=asset.convert("RGB"),encoded.convert("RGB")
    return a.size==b.size and ImageChops.difference(a,b).getbbox() is None

def audit(*,source:Path,slides:Path,latex:Path,figure_directory:Path)->dict:
    source,slides,latex,figure_directory=(Path(x).absolute()
                                        for x in (source,slides,latex,figure_directory))
    input_paths=[source,slides,latex]
    require(all(p.is_file() and not p.is_symlink() for p in input_paths),
            "Original source, slide PDF, and original LaTeX required")
    require(_sha(source)==SOURCE_SHA,
            "Original Thomas textbook identity changed")
    files={key[0]:figure_directory/f"Figure {key[0]}.png" for key in EXPECTED}
    require(all(p.is_file() and not p.is_symlink() for p in files.values()),
            "One or more original named source figure assets missing")
    inputs=[*input_paths,*files.values()]
    before={str(p):_sha(p) for p in inputs}
    tex=latex.read_text(encoding="utf8")
    results=[]
    with pymupdf.open(source) as original,pymupdf.open(slides) as rendered:
        require(len(rendered)==17 and len(original)>=4,
                "Wrong original textbook section or lecture deck")
        for (label,slide_num),original_page in EXPECTED.items():
            assertname=f"Figure {label}.png"
            # Check named original authoring resource is actually referenced.
            require(tex.count(r"\IfFileExists{"+assertname+"}")==1
                    and tex.count("{"+assertname+"}")==2,
                    "Figure authoring filename references missing or duplicated")
            matches=[i+1 for i,page in enumerate(original)
                     if re.search(r"\bFIGURE\s+"+re.escape(label)+r"\b",
                                  page.get_text())]
            require(matches==[original_page],
                    f"Figure {label} textbook caption not uniquely witnessed")
            figures=[i for i in rendered[slide_num-1].get_image_info(xrefs=True)
                     if int(i.get("width",0))>=70 and int(i.get("height",0))>=50
                     and int(i.get("xref",0))>0]
            require(len(figures)==1,
                    f"Slide {slide_num} has missing/ambiguous actual figure bitmap")
            figure=figures[0]
            rect=pymupdf.Rect(figure["bbox"])
            require(rect.is_valid and not rect.is_empty
                    and rendered[slide_num-1].rect.contains(rect),
                    "Embedded figure does not fit original slide page")
            original_encoded=rendered.extract_image(figure["xref"])["image"]
            asset=files[label]
            with Image.open(asset) as image,Image.open(io.BytesIO(original_encoded)) as embed:
                require(pixels_equal(image,embed),
                        f"Embedded slide figure {label} does not match its named original PNG")
                size=list(image.size)
            results.append({
                "figure_id":label,"source_textbook_caption_page":original_page,
                "original_slide_number":slide_num,"original_named_figure_file":assertname,
                "original_asset_sha256":_sha(asset),
                "actual_embedded_slide_image_dimensions":size,
                "actual_embedded_slide_rect_pt":[round(float(x),3) for x in rect],
                "decoded_asset_pixels_identical_to_embedded_slide_bitmap":True,
                "original_source_pdf_figure_crop_correspondence_certified":False,
                "multi_panel_completeness_certified":False,
                "mathematical_figure_labels_verified":False,
                "source_figure_semantics_approved":False
            })
    require({str(p):_sha(p) for p in inputs}==before,
            "Original textbook/deck/figure assets mutated during audit")
    return {
        "schema_version":1,
        "status":"FIVE_ORIGINAL_FIGURE_ASSETS_BITMAP_IDENTICAL_SOURCE_CAPTIONS_FOUND",
        "original_source_pdf_sha256":_sha(source),
        "original_slides_pdf_sha256":_sha(slides),
        "figure_asset_to_embedded_bitmap_identity_count":len(results),
        "figures":results,
        "full_figures_source_pdf_equivalence_accepted":False,
        "full_lecture_semantics_accepted":False,
        "highlighted_video_accepted":False,
        "student_publication_authorized":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("source","slides","latex","figure-directory","out"):
        p.add_argument("--"+arg,required=True,type=Path)
    a=p.parse_args(argv)
    out=a.out.absolute()
    require(out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(a.source.absolute().parent),
            "Never overwrite originals or prior QA receipt")
    report=audit(source=a.source,slides=a.slides,
                 latex=a.latex,figure_directory=a.figure_directory)
    with out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"status":report["status"],
        "identical_assets":report["figure_asset_to_embedded_bitmap_identity_count"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
