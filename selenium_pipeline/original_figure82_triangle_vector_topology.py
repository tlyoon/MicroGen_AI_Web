"""Original Figure 8.2 triangle vector edge/topology evidence (review-only).

No inference of an unextracted missing triangle edge or correct mathematical
side labels. The source page is authoritative; a positive bitmap correlation
does not establish triangle closure or right-angle geometry by itself.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha
from .original_figure82_source_label_order import inspect_original_figure82_label_order
from .original_figure82_pixel_registration import inspect_original_figure82_pixel_registration


def classify_panel_segments(segments, *, label_x:float)->dict:
    """Derive axis-aligned legs and diagonal from original PDF line geometry."""
    require(type(label_x) in (int,float) and math.isfinite(label_x),
            "Invalid original source printed formula center")
    hits={"HORIZONTAL":[],"VERTICAL":[],"DIAGONAL":[]}
    for value in segments:
        require(type(value) in (tuple,list) and len(value)==4,
                "Invalid extracted original line endpoint")
        x0,y0,x1,y1=map(float,value)
        require(all(math.isfinite(z) for z in (x0,y0,x1,y1)),
                "Nonfinite original vector geometry")
        dx=abs(x1-x0);dy=abs(y1-y0)
        if min(dx,dy)<0.18 and max(dx,dy)>=30:
            if dy<0.18:
                hits["HORIZONTAL"].append(value)
            else:
                hits["VERTICAL"].append(value)
        elif 40<=dx<=95 and 28<=dy<=75:
            # The textbook motif slants up-right: rightmost endpoint is above
            # leftmost. Do not silently accept a reflected triangle.
            if (x1-x0)*(y1-y0)>=0:
                raise ValueError("Original diagonal direction was reflected")
            hits["DIAGONAL"].append(value)
    require(len(hits["DIAGONAL"])==1
            and len(hits["HORIZONTAL"])<=1
            and len(hits["VERTICAL"])<=1,
            "Unexpected original vector triangle segment topology")
    diagonal=hits["DIAGONAL"][0]
    diag_width=abs(diagonal[2]-diagonal[0])
    diag_height=abs(diagonal[3]-diagonal[1])
    require(abs(diag_width-66)<1.0 and abs(diag_height-48)<1.0,
            "Original textbook triangle hypotenuse geometry changed")
    leg_count=len(hits["HORIZONTAL"])+len(hits["VERTICAL"])
    explicit_right_angle=(leg_count==2)
    if explicit_right_angle:
        horiz=hits["HORIZONTAL"][0];vert=hits["VERTICAL"][0]
        def ends(line):
            return ((line[0],line[1]),(line[2],line[3]))
        def joined(a,b):
            return any(math.hypot(x[0]-y[0],x[1]-y[1])<1
                       for x in ends(a) for y in ends(b))
        require(joined(horiz,vert) and joined(horiz,diagonal)
                and joined(vert,diagonal),
                "Source lines do not form a closed right-angle triangle")
    return {
        "printed_formula_x_center_pdf_pt":round(label_x,4),
        "explicit_horizontal_edge_count":len(hits["HORIZONTAL"]),
        "explicit_vertical_edge_count":len(hits["VERTICAL"]),
        "explicit_diagonal_count":1,
        "diagonal_width_pt":round(diag_width,4),
        "diagonal_height_pt":round(diag_height,4),
        "explicit_axis_aligned_corner_witnessed":explicit_right_angle,
        "all_three_triangle_edges_explicitly_witnessed":explicit_right_angle,
        "side_length_label_meanings_verified":False,
        "mathematical_right_triangle_approved":False,
    }


def original_panel_line_observations(page, label_centers:tuple[float,...]):
    require(len(label_centers)==3 and all(
        type(x) in (int,float) for x in label_centers),
        "Exactly three printed source panel label centers required")
    segments=[]
    for drawing in page.get_drawings():
        for line in drawing["items"]:
            if line[0]!="l":
                continue
            p,q=line[1:3]
            x0,y0,x1,y1=map(float,(p.x,p.y,q.x,q.y))
            if (min(y0,y1)<505 or max(y0,y1)>558
                or min(x0,x1)<260 or max(x0,x1)>505):
                continue
            if math.hypot(x1-x0,y1-y0)<28:
                continue
            segments.append((x0,y0,x1,y1))
    require(len(segments)>=7 and len(segments)<=12,
            "Original source vector evidence incomplete or unexpectedly duplicated")
    results=[]
    for i,center in enumerate(label_centers):
        # Independent source formula labels occur at 300/384/468 PDF pt;
        # source triangle panels have corresponding nonoverlapping x intervals.
        selected=[s for s in segments
                  if center-42<=min(s[0],s[2])
                  and max(s[0],s[2])<=center+42]
        results.append({
            "panel_ordinal":i+1,
            **classify_panel_segments(selected,label_x=center),
        })
    require(all(r["explicit_diagonal_count"]==1 for r in results),
            "All three source triangle diagonals must be physically present")
    require(sum(r["explicit_axis_aligned_corner_witnessed"]
                for r in results)>=1,
            "No source original geometric right-angle anchor")
    return results


def inspect_original_figure82_triangle_topology(*,folder:Path)->dict:
    root=Path(folder).absolute()
    source,slides,script=(root/n for n in ("source.pdf","slides.pdf","script.txt"))
    hashes=tuple(_sha(p) for p in (source,slides,script))
    pixel=inspect_original_figure82_pixel_registration(folder=root)
    labels=inspect_original_figure82_label_order(folder=root)
    require((pixel["source_sha256"],pixel["slides_sha256"],
             pixel["script_sha256"])==hashes
            and (labels["source_sha256"],labels["slides_sha256"],
                 labels["script_sha256"])==hashes
            and pixel["original_source_to_slide_pixel_similarity_accepted"] is True,
            "Original textbook Figure 8.2 pixel/source identities are not approved")
    centers=tuple(sum(label["original_label_bbox_pdf_pt"][j] for j in (0,2))/2
                  for label in labels["ordered_review_candidates"])
    with pymupdf.open(source) as pdf:
        source_panels=original_panel_line_observations(pdf[0],centers)
    require(tuple(_sha(p) for p in (source,slides,script))==hashes,
            "Original source changed during vector topology inspection")
    return {
        "status":"ORIGINAL_FIGURE82_SOURCE_VECTOR_TOPOLOGY_REVIEW_ONLY",
        "source_sha256":hashes[0],
        "slides_sha256":hashes[1],
        "script_sha256":hashes[2],
        "source_physical_page":1,
        "slide_page":4,
        "triangle_vector_candidate_count":len(source_panels),
        "complete_explicit_three_edge_panel_count":sum(
            x["all_three_triangle_edges_explicitly_witnessed"] for x in source_panels),
        "all_three_triangle_geometries_explicitly_verified":all(
            x["all_three_triangle_edges_explicitly_witnessed"] for x in source_panels),
        "source_vector_candidate_panels":source_panels,
        "source_to_slide_pixel_similarity_verified":True,
        "mathematical_triangle_side_labels_verified":False,
        "independent_source_academic_consensus_verified":False,
        "genuine_Kore_TTS_authorized":False,
        "student_publication_authorized":False,
        "new_Gemini_review_request_sent":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    args=p.parse_args(argv)
    print(json.dumps(inspect_original_figure82_triangle_topology(folder=args.folder),
                     indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
