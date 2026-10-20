"""Textbook mathematical figure-token inventory; no slide bitmap OCR/claims.

Uses the PDF's original separately extractable words inside each independently
detected source graph panel. Token presence does not certify their pixel or
semantic equivalents in a reflowed slide bitmap.
"""
from __future__ import annotations
from pathlib import Path
import math
import pymupdf
from .figure_source_identity import require, _sha
from .figure_three_graph_color_reflow import audit_real_three_graph_reflow

def classify_original_panel_words(*, words:list, bands:list, source_x:list, scale:float=3.0)->dict:
    require(type(words) is list and type(bands) is list and 2<=len(bands)<=6
            and len(words)<=3000 and type(source_x) is list and len(source_x)==2
            and all(type(x) is int for x in source_x)
            and source_x[0]<source_x[1]
            and type(scale) in (int,float) and math.isfinite(scale)
            and 0<scale<=4,"Invalid bounded source figure text")
    panels=[]
    for i,band in enumerate(bands,1):
        require(type(band) is list and len(band)==2
                and all(type(y) is int for y in band)
                and 0<=band[0]<band[1],"Invalid original source panel band")
        tokens=[]
        for w in words:
            require(len(w)>=5,"Invalid original word data")
            x0,y0,x1,y1,word=w[:5]
            require(all(math.isfinite(float(v)) for v in (x0,y0,x1,y1))
                    and isinstance(word,str),"Malformed source text coordinates")
            px=(x0+x1)*scale/2
            py=(y0+y1)*scale/2
            if source_x[0]<=px<=source_x[1] and band[0]<=py<=band[1]:
                require(len(word)<=128,"Oversized original mathematical word")
                tokens.append({"text":word,"original_bbox_pt":[
                    round(float(v),2) for v in (x0,y0,x1,y1)]})
        panels.append({"graph_index":i,"original_word_count":len(tokens),
                       "original_printed_tokens":tokens,
                       "slide_bitmap_token_identity_verified":False,
                       "math_notation_semantics_verified":False})
    return {"schema_version":1,"status":"ORIGINAL_GRAPH_LABELS_EXTRACTED_SLIDE_SEMANTICS_REVIEW",
            "panels":panels,"graph_count":len(panels),
            "slide_bitmap_OCR_performed":False,"original_slide_labels_equivalent":False,
            "full_graph_axes_verified":False,"publication_authorized":False}

def audit_original_graph_labels(*,source:Path,slides:Path,
                                source_page:int,slide_page:int,
                                figure_id:str)->dict:
    raw=audit_real_three_graph_reflow(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    bands=[x["source_scan_band_px"] for x in raw["graph_correspondence_evidence"]]
    with pymupdf.open(source) as pdf:
        words=pdf[source_page-1].get_text("words")
    result=classify_original_panel_words(
        words=words,bands=bands,source_x=raw["source_scan_pixel_x_bounds"])
    require(_sha(Path(source).absolute())==raw["original_pdf_sha256"]
            and _sha(Path(slides).absolute())==raw["existing_slides_pdf_sha256"],
            "Original scientific files changed during label inventory")
    return {**result,"source_sha256":raw["original_pdf_sha256"],
            "slides_sha256":raw["existing_slides_pdf_sha256"],
            "source_page":source_page,"slide_page":slide_page,
            "figure_id":figure_id}

def main(argv=None):
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--source-page",type=int,required=True)
    p.add_argument("--slide-page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    a=p.parse_args(argv)
    print(json.dumps(audit_original_graph_labels(
        source=a.source,slides=a.slides,source_page=a.source_page,
        slide_page=a.slide_page,figure_id=a.figure_id),
        ensure_ascii=True,indent=2,sort_keys=True))
    return 2
if __name__=="__main__":
    raise SystemExit(main())
