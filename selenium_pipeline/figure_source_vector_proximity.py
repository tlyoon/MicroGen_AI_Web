"""Original vector candidate proximity review, never a publication gate."""
import argparse
import json
import math
from pathlib import Path
import pymupdf
from .figure_source_identity import require
from .figure_transform_groups import audit_real_transform_groups
from .figure_pre_caption_vector_inventory import inventory_pre_caption_vectors

def classify_source_vector_proximity(objects, groups, padding_pt=8.0):
    """Bounding-box proximity is NOT proof of matching ink or figure identity."""
    require(isinstance(objects,list) and isinstance(groups,list)
            and len(objects)<=2000 and len(groups)<=20,
            "Unbounded candidate inventory")
    require(type(padding_pt) in (int,float)
            and math.isfinite(padding_pt) and 0<=padding_pt<=20,
            "Invalid proximity padding")
    regions=[]
    for group in groups:
        box=group.get("source_matched_keypoint_union_bbox_pdf")
        require(isinstance(box,list) and len(box)==4
                and all(type(v) in (int,float) and math.isfinite(v)
                        for v in box), "Malformed matched-keypoint extent")
        r=pymupdf.Rect(box)
        require(r.is_valid and not r.is_empty,"Invalid keypoint bbox")
        regions.append(pymupdf.Rect(
            r.x0-padding_pt,r.y0-padding_pt,r.x1+padding_pt,r.y1+padding_pt))
    output=[]
    seen=set()
    for row in objects:
        idx=row.get("drawing_index")
        box=row.get("bbox")
        require(type(idx) is int and idx>=0 and idx not in seen
                and isinstance(box,list) and len(box)==4
                and all(type(v) in (int,float) and math.isfinite(v)
                        for v in box),"Invalid or duplicate original drawing")
        seen.add(idx)
        r=pymupdf.Rect(box)
        require(r.is_valid and r.width>=0 and r.height>=0
                and (r.width>0 or r.height>0),
                "Invalid source drawing bbox")
        expanded=pymupdf.Rect(r.x0-.01,r.y0-.01,r.x1+.01,r.y1+.01)
        matches=[n for n,g in enumerate(regions) if g.intersects(expanded)]
        output.append({
            "drawing_index":idx,
            "nearby_registration_group_indices":matches,
            "classification":(
                "NO_NEARBY_SOURCE_FEATURES" if not matches else
                "AMBIGUOUS_MULTIPLE_GROUPS" if len(matches)>1 else
                "NEAR_ONE_UNVERIFIED_REGISTRATION_GROUP"),
            "figure_membership_verified":False,
        })
    return {
        "schema_version":1,
        "status":"ORIGINAL_VECTOR_PROXIMITY_REVIEW_REQUIRED",
        "source_vector_objects_total":len(output),
        "without_nearby_features":sum(not x["nearby_registration_group_indices"] for x in output),
        "ambiguous_multiple_groups":sum(len(x["nearby_registration_group_indices"])>1 for x in output),
        "near_single_group":sum(len(x["nearby_registration_group_indices"])==1 for x in output),
        "observations":output,
        "complete_original_graph_geometry_verified":False,
        "original_panel_ownership_verified":False,
        "all_strokes_in_slide_verified":False,
        "narrated_highlights_verified":False,
        "video_or_publication_authorized":False,
    }

def audit_original_vector_proximity(*,source:Path,slides:Path,
                                    source_page:int,slide_page:int,
                                    figure_id:str)->dict:
    groups=audit_real_transform_groups(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    inventory=inventory_pre_caption_vectors(
        source=source,page_number=source_page,figure_id=figure_id)
    require(groups["source_sha256"]==inventory["source_sha256"],
            "Source changed between vector and feature audits")
    result=classify_source_vector_proximity(
        inventory["pre_caption_drawing_objects"],
        groups["candidate_transform_groups"])
    return {**result,"source_sha256":groups["source_sha256"],
            "slides_sha256":groups["slides_sha256"],
            "source_page":source_page,"slide_page":slide_page,
            "figure_id":figure_id,
            "candidate_registration_groups":len(groups["candidate_transform_groups"])}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--source-page",type=int,required=True)
    p.add_argument("--slide-page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    a=p.parse_args(argv)
    report=audit_original_vector_proximity(
        source=a.source,slides=a.slides,source_page=a.source_page,
        slide_page=a.slide_page,figure_id=a.figure_id)
    print(json.dumps(report,indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
