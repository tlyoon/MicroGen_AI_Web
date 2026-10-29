"""Candidate connected vector drawing components in original textbook PDF.

Connected geometry is NOT a mathematical panel, complete source
figure, graph axis or source-to-slide correspondence certificate.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,math
import pymupdf
from .figure_pre_caption_vector_inventory import inventory_pre_caption_vectors
from .figure_source_identity import require,_sha


def connected_source_drawings(objects:list, *, gap_pt:float=2.0)->dict:
    require(type(objects) is list and len(objects)<=500
            and type(gap_pt) in (int,float) and math.isfinite(gap_pt)
            and 0<=gap_pt<=6,"Invalid bounded source geometry")
    coords=[]
    seen=set()
    for obj in objects:
        require(type(obj) is dict
                and type(obj.get("drawing_index")) is int
                and obj["drawing_index"]>=0
                and obj["drawing_index"] not in seen,
                "Duplicate/invalid drawing identity")
        seen.add(obj["drawing_index"])
        vals=obj.get("bbox")
        require(type(vals) is list and len(vals)==4
                and all(type(v) in (int,float) and math.isfinite(v) for v in vals),
                "Nonfinite source bbox")
        rect=pymupdf.Rect(vals)
        require(rect.is_valid and not rect.is_infinite
                and rect.width>=0 and rect.height>=0
                and rect.width+rect.height>0,
                "Invalid source stroke geometry")
        coords.append((obj["drawing_index"],rect))
    parent=list(range(len(coords)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    def union(a,b):
        x,y=root(a),root(b)
        if x!=y: parent[max(x,y)]=min(x,y)
    for i,(_,a) in enumerate(coords):
        for j in range(i+1,len(coords)):
            b=coords[j][1]
            dx=max(0,a.x0-b.x1,b.x0-a.x1)
            dy=max(0,a.y0-b.y1,b.y0-a.y1)
            if math.hypot(dx,dy)<=gap_pt:
                union(i,j)
    groups={}
    for i,(idx,rect) in enumerate(coords):
        groups.setdefault(root(i),[]).append((idx,rect))
    components=[]
    for entries in groups.values():
        bbox=[min(r.x0 for _,r in entries),
              min(r.y0 for _,r in entries),
              max(r.x1 for _,r in entries),
              max(r.y1 for _,r in entries)]
        components.append({
            "drawing_indices":sorted(idx for idx,_ in entries),
            "drawing_count":len(entries),
            "union_bbox":[round(float(v),3) for v in bbox],
            "author_intended_panel_certified":False,
            "original_figure_membership_certified":False,
        })
    components.sort(key=lambda c:c["drawing_indices"][0])
    return {
        "schema_version":1,"status":"UNTRUSTED_SOURCE_VECTOR_COMPONENTS_REQUIRE_REVIEW",
        "drawing_count":len(coords),"gap_pt":gap_pt,
        "candidate_connected_component_count":len(components),
        "candidate_components":components,
        "complete_source_figure_verified":False,
        "panel_count_and_labels_verified":False,
        "slide_equivalence_verified":False,
        "video_or_publication_authorized":False,
    }


def audit_real_source_components(*,source:Path,page_number:int,
                                  figure_id:str)->dict:
    inventory=inventory_pre_caption_vectors(
        source=source,page_number=page_number,figure_id=figure_id)
    result=connected_source_drawings(
        inventory["pre_caption_drawing_objects"])
    require(_sha(Path(source).absolute())==inventory["source_sha256"],
            "Source changed during topology audit")
    return {**result,"source_sha256":inventory["source_sha256"],
            "source_page":page_number,"figure_id":figure_id}


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    a=p.parse_args(argv)
    print(json.dumps(audit_real_source_components(
        source=a.source,page_number=a.page,figure_id=a.figure_id),
        indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
