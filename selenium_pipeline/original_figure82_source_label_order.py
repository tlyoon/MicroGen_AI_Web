"""Original Figure 8.2 printed label ordering vs Slide4 raster strip candidates.

Read only. A three-column order correlation is review evidence, NOT proof
that the actual triangle art or narrated highlighter matches the source.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha
from .original_composite_gutter_proposals import inspect_original_composite_gutters
from .original_substitution_source_formula_witness import inspect_original_three_formula_source
from .pdf_text_source_span_witness import prove_source_quote_occurrence


_CAPTION_NUMBER = "FIGURE 8.2"
_CAPTION_BODY = "Reference triangles for the three basic substitutions"
_LABELS = ("tan","sin","sec")


def source_diagram_labels(*,page) -> dict:
    markers=page.search_for(_CAPTION_NUMBER)
    body_hits=page.search_for(_CAPTION_BODY)
    require(len(markers)==2 and len(body_hits)==1,
            "Original printed Figure 8.2 markers or caption body changed")
    body=body_hits[0]
    nearby=[m for m in markers if m.is_valid
            and abs(m.y0-body.y0)<14
            and m.x1<body.x0]
    require(len(nearby)==1,
            "Cannot uniquely associate printed Figure 8.2 marker to caption text")
    caption=nearby[0]
    require(caption.y0>45 and page.rect.contains(caption)
            and page.rect.contains(body)
            and abs(body.y0-caption.y0)<25
            and body.x0>=caption.x0-5,
            "Figure number and caption body are not geometrically associated")
    candidates={}
    for w in page.get_text("words",sort=True):
        x0,y0,x1,y1,word,block,line,number=w
        if not (caption.y0-45<=y0<=caption.y0-16
                and caption.x0-15<=x0<=caption.x0+320
                and y1<caption.y0):
            continue
        candidates.setdefault((block,line),[]).append(w)
    records=[]
    for (block,line),group in candidates.items():
        tokens=[str(w[4]) for w in group]
        for label in _LABELS:
            if tokens == ["x","=","a",label,"u"]:
                x0=min(w[0] for w in group)
                x1=max(w[2] for w in group)
                y0=min(w[1] for w in group)
                y1=max(w[3] for w in group)
                require(x1-x0>=20 and y1-y0>=5,
                        "Original source figure label has implausible geometry")
                records.append({
                    "source_label_formula":"x = a "+label+" u",
                    "source_label_x_center_pdf_pt":round((x0+x1)/2,4),
                    "source_label_bbox_pdf_pt":[round(v,4) for v in (x0,y0,x1,y1)],
                    "source_text_block":block,
                    "source_text_line":line,
                    "printed_label_semantics_academically_approved":False,
                })
    records.sort(key=lambda r:r["source_label_x_center_pdf_pt"])
    require(len(records)==len(_LABELS)
            and [r["source_label_formula"] for r in records]
            ==["x = a "+name+" u" for name in _LABELS],
            "Source Figure 8.2 vector label order ambiguous or misidentified")
    require(all(a["source_label_bbox_pdf_pt"][2] < b["source_label_bbox_pdf_pt"][0]
                for a,b in zip(records,records[1:])),
            "Source figure formula label boxes overlap")
    return {
        "original_source_caption_bbox_pdf_pt":[round(v,4) for v in caption],
        "printed_formula_labels":records,
        "printed_label_count":len(records),
        "source_label_order_analyzed":True,
        "author_intended_triangle_semantics_verified":False,
    }


def inspect_original_figure82_label_order(*,folder:Path)->dict:
    root=Path(folder).absolute()
    source,slides,script=(root/n for n in
                          ("source.pdf","slides.pdf","script.txt"))
    hashes=(_sha(source),_sha(slides),_sha(script))
    math=inspect_original_three_formula_source(folder=root)
    gutters=inspect_original_composite_gutters(folder=root,slide=4)
    require((math["original_source_sha256"],math["original_slides_sha256"],
             math["original_script_sha256"])==hashes
            and (gutters["original_source_sha256"],
                 gutters["original_slides_sha256"],
                 gutters["original_script_sha256"])==hashes,
            "Original source identities differ between formula and figure audits")
    caption_number=prove_source_quote_occurrence(
        source_pdf=source,expected_sha256=hashes[0],
        page_number=1,verbatim_quote=_CAPTION_NUMBER)
    caption_body=prove_source_quote_occurrence(
        source_pdf=source,expected_sha256=hashes[0],
        page_number=1,verbatim_quote=_CAPTION_BODY)
    require(caption_number["quote_occurrences"]==1
            and caption_body["quote_occurrences"]==1,
            "Figure number or descriptive caption not uniquely source witnessed")
    with pymupdf.open(source) as doc:
        require(len(doc)>0, "Original textbook page missing")
        labels=source_diagram_labels(page=doc[0])
    strips=gutters["candidate_strips"]
    require(len(strips)==len(labels["printed_formula_labels"])==3
            and gutters["status"]=="VERTICAL_GUTTER_STRIP_PROPOSALS_ONLY",
            "Three distinct original slide raster strip proposals required")
    placements=[]
    for index,(label,strip) in enumerate(zip(labels["printed_formula_labels"],strips),1):
        require(strip["candidate_index"]==index and
                strip["right_triangle_semantics_verified"] is False,
                "Unapproved figure strip candidate or unexpected ordering")
        placements.append({
            "candidate_ordinal":index,
            "source_printed_label":label["source_label_formula"],
            "original_label_bbox_pdf_pt":label["source_label_bbox_pdf_pt"],
            "slide_image_candidate_bbox_pdf_pt":strip["candidate_slide_bbox_pdf_pt"],
            "slide_image_candidate_native_sha256":strip["panel_native_pixel_sha256"],
            "source_to_slide_order_consistent":True,
            "source_triangle_side_geometry_verified":False,
            "slide_panel_contains_printed_source_formula_verified":False,
            "narration_to_panel_alignment_approved":False,
        })
    require((_sha(source),_sha(slides),_sha(script))==hashes,
            "Source assets changed during source diagram order candidate audit")
    return {
        "status":"ORIGINAL_FIGURE82_LABEL_TO_SLIDE_STRIP_ORDER_CANDIDATES_REVIEW_ONLY",
        "source_sha256":hashes[0],
        "slides_sha256":hashes[1],
        "script_sha256":hashes[2],
        "original_source_physical_page":1,
        "original_slide":4,
        "caption_number_quote_sha256":caption_number["quote_sha256"],
        "caption_body_quote_sha256":caption_body["quote_sha256"],
        "printed_label_count":3,
        "candidate_slide_strips_count":3,
        "source_caption_geometry":labels["original_source_caption_bbox_pdf_pt"],
        "ordered_review_candidates":placements,
        "author_semantic_panel_count_verified":False,
        "source_to_slide_pixel_equivalence_verified":False,
        "independent_math_consensus_verified":False,
        "genuine_Kore_TTS_authorized":False,
        "student_publication_authorized":False,
        "new_provider_request_sent":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    args=p.parse_args(argv)
    print(json.dumps(inspect_original_figure82_label_order(folder=args.folder),
                     indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
