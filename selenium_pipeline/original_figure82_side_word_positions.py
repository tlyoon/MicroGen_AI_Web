"""Review-only printed side-label positioning on real Figure 8.2 triangles.

Uses source PDF word boxes adjacent to independently proved vector contours.
PDF radical glyph extraction is lossy, so no symbolic radical/academic approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf

from .figure_source_identity import require,_sha
from .original_figure82_triangle_vector_topology import (
    inspect_original_figure82_triangle_topology,
)


def _normalize_text(token):
    return str(token).replace("−","-").replace("²","2").strip(' "\u221a')


def _relative_tokens(words,rect,rel,side):
    x0,y0,x1,y1=rect
    xa,ya,xb,yb=rel
    ybase=y1 if side=="base" else y0
    return [w for w in words
            if x0+xa<=(w[0]+w[2])/2<=x0+xb
            and ybase+ya<=(w[1]+w[3])/2<=ybase+yb]


# The three source triangles have identical 66 x 48 point vector topology.
# Expected printed symbols are transcription CANDIDATES, not radical proofs.
_EXPECTED=(
    {"formula":"x = a tan u",
     "base":(("a",),(15,1,54,14)),
     "right":(("x",),(67,12,82,36)),
     "diagonal":(("a2","+","x2"),(-4,10,39,38))},
    {"formula":"x = a sin u",
     "base":(("a2","-x2"),(0,1,62,14)),
     "right":(("x",),(67,12,82,36)),
     "diagonal":(("a",),(19,10,53,35))},
    {"formula":"x = a sec u",
     "base":(("a",),(15,1,54,14)),
     "right":(("x2","-a2"),(67,10,107,38)),
     "diagonal":(("x",),(19,10,53,35))},
)


def verify_panel_word_positions(words, source_panels:list)->list:
    """Reject moved/missing/swapped source symbols rather than infer missing glyph."""
    require(type(source_panels) is list and len(source_panels)==3,
            "Three original vector triangle panels required")
    results=[]
    for i,(panel,expected) in enumerate(zip(source_panels,_EXPECTED),1):
        require(panel["panel_ordinal"]==i
                and panel["all_three_triangle_edges_explicitly_witnessed"] is True,
                "Only previously source-bound closed triangle contours may be annotated")
        bbox=panel["triangle_vertex_bounds_pdf_pt"]
        require(len(bbox)==4 and
                abs(bbox[2]-bbox[0]-66)<1 and abs(bbox[3]-bbox[1]-48)<1,
                "Source original triangle vertex bounds changed")
        positions={}
        for side in ("base","right","diagonal"):
            needed,rel=expected[side]
            matched=sorted(_relative_tokens(words,bbox,rel,side),
                           key=lambda w:w[0])
            normalized=tuple(_normalize_text(w[4]) for w in matched)
            require(all(-0.5<=b[0]-a[2]<=8
                        and abs((b[1]+b[3]-a[1]-a[3])/2)<8
                        for a,b in zip(matched,matched[1:])),
                    "Source side-label tokens are not physically contiguous")
            require(normalized==needed,
                    f"Original source printed {side} token geometry diverged")
            positions[side]={
                "observed_pdf_word_tokens":list(normalized),
                "printed_word_bbox_pdf_pt":[
                    round(min(w[0] for w in matched),4),
                    round(min(w[1] for w in matched),4),
                    round(max(w[2] for w in matched),4),
                    round(max(w[3] for w in matched),4)],
                "correct_symbol_mathematics_approved":False,
                "radical_operator_proven_from_pdf_text":False,
            }
        results.append({
            "panel_ordinal":i,
            "original_source_formula_label":expected["formula"],
            "physical_source_position_candidates":positions,
            "printed_labels_physically_witnessed":True,
            "triangle_side_symbol_semantics_approved":False,
            "complete_radical_notation_proven":False,
        })
    return results


def inspect_original_figure82_side_word_positions(*,folder:Path)->dict:
    root=Path(folder).absolute()
    source,slides,script=(root/p for p in ("source.pdf","slides.pdf","script.txt"))
    original_hashes=tuple(_sha(p) for p in (source,slides,script))
    geometry=inspect_original_figure82_triangle_topology(folder=root)
    require((geometry["source_sha256"],geometry["slides_sha256"],
             geometry["script_sha256"])==original_hashes
            and geometry["complete_explicit_three_edge_panel_count"]==3,
            "Source-to-slide topology proof absent or source identity changed")
    with pymupdf.open(source) as pdf:
        source_words=pdf[0].get_text("words",sort=True)
        side_candidates=verify_panel_word_positions(
            source_words,geometry["source_vector_candidate_panels"])
    require(tuple(_sha(p) for p in (source,slides,script))==original_hashes,
            "Original assets changed while examining source printed word locations")
    return {
        "status":"SOURCE_FIGURE82_PRINTED_SIDE_WORD_POSITIONS_WITNESSED_REVIEW_ONLY",
        "source_sha256":original_hashes[0],
        "slides_sha256":original_hashes[1],
        "script_sha256":original_hashes[2],
        "physical_textbook_page":1,
        "original_slide":4,
        "source_triangle_vector_geometry_verified":True,
        "original_source_to_slide_pixel_similarity_verified":True,
        "printed_side_position_candidate_count":len(side_candidates),
        "side_position_candidates":side_candidates,
        "source_pdf_radical_operator_text_not_reliable":True,
        "mathematical_side_length_relationships_independently_verified":False,
        "independent_mathematical_academic_consensus_approved":False,
        "narration_highlight_timing_verified":False,
        "student_publication_authorized":False,
        "new_Gemini_request_sent":False,
    }


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",required=True,type=Path)
    args=parser.parse_args(argv)
    print(json.dumps(inspect_original_figure82_side_word_positions(folder=args.folder),
                     indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
