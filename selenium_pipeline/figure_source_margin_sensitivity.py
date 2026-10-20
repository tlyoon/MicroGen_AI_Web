"""Measure sensitivity of uncorroborated vector labels to scan padding.

Even a robust 'no nearby features' label cannot establish whether original
source ink appears in the slide or is part of the intended textbook figure.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .figure_source_identity import require, _sha
from .figure_source_vector_proximity import classify_source_vector_proximity
from .figure_transform_groups import audit_real_transform_groups
from .figure_pre_caption_vector_inventory import inventory_pre_caption_vectors

MARGINS = (0.0, 4.0, 8.0, 12.0, 20.0)


def compare_vector_proximity_margins(objects: list, groups: list) -> dict:
    runs=[classify_source_vector_proximity(objects,groups,padding_pt=p)
          for p in MARGINS]
    originals=[r["drawing_index"] for r in runs[0]["observations"]]
    require(len(set(originals))==len(originals),
            "Repeated source indices invalid")
    rows=[]
    for pos,index in enumerate(originals):
        nearby=[len(r["observations"][pos]["nearby_registration_group_indices"])
                for r in runs]
        require(all(nearby[i] <= nearby[i+1]
                    for i in range(len(nearby)-1)),
                "Non-monotone geometric padding classification")
        rows.append({
            "drawing_index":index,
            "group_count_by_margin":dict(zip((str(int(x)) for x in MARGINS),nearby)),
            "robustly_without_nearby_features_at_20pt":nearby[-1]==0,
            "acquires_first_group_at_margin_pt":next(
                (int(p) for p,n in zip(MARGINS,nearby) if n),None),
            "original_graph_membership_verified":False,
            "missing_from_slide_verified":False,
        })
    counts=[r["without_nearby_features"] for r in runs]
    return {
        "schema_version":1,
        "status":"SOURCE_VECTOR_PROXIMITY_THRESHOLD_SENSITIVITY_REVIEW_REQUIRED",
        "margin_points":list(MARGINS),
        "without_nearby_features_by_margin":counts,
        "robustly_unmatched_at_20pt":sum(x["robustly_without_nearby_features_at_20pt"]
                                         for x in rows),
        "sensitivity_rows":rows,
        "source_figure_membership_certified":False,
        "slide_omission_certified":False,
        "narrated_video_authorized":False,
    }


def audit_real_vector_margin_sensitivity(*,source:Path,slides:Path,
                                        source_page:int,slide_page:int,
                                        figure_id:str) -> dict:
    groups=audit_real_transform_groups(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    inv=inventory_pre_caption_vectors(
        source=source,page_number=source_page,figure_id=figure_id)
    require(inv["source_sha256"]==groups["source_sha256"],
            "Different source PDF data in audits")
    result=compare_vector_proximity_margins(
        inv["pre_caption_drawing_objects"],groups["candidate_transform_groups"])
    require(_sha(Path(source).absolute())==inv["source_sha256"]
            and _sha(Path(slides).absolute())==groups["slides_sha256"],
            "Original PDF changed during sensitivity review")
    return {**result,"source_sha256":inv["source_sha256"],
            "slides_sha256":groups["slides_sha256"],
            "source_page":source_page,"slide_page":slide_page,
            "figure_id":figure_id}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--source-page",type=int,required=True)
    p.add_argument("--slide-page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    a=p.parse_args(argv)
    print(json.dumps(audit_real_vector_margin_sensitivity(
        source=a.source,slides=a.slides,source_page=a.source_page,
        slide_page=a.slide_page,figure_id=a.figure_id),
        indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
