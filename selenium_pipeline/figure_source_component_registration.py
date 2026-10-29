"""Compare independent connected source vector regions to measured transforms.

Geometry-only component-to-registration overlap; never an academic figure
panel mapping and never a source-to-slide pixel equivalence certificate.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .figure_source_connected_components import audit_real_source_components
from .figure_transform_groups import audit_real_transform_groups


def crosscheck_component_registration(components:list, groups:list)->dict:
    require(type(components) is list and type(groups) is list
            and len(components)<=500 and len(groups)<=20,
            "Invalid bounded component and registration lists")
    registration=[]
    for group in groups:
        bounds=group.get("source_matched_keypoint_union_bbox_pdf")
        require(type(bounds) is list and len(bounds)==4,
                "Missing independently matched group bbox")
        r=pymupdf.Rect(bounds)
        require(r.is_valid and not r.is_empty,"Invalid fitted extent")
        registration.append(r)
    rows=[]
    seen=set()
    for c in components:
        ids=c.get("drawing_indices")
        box=c.get("union_bbox")
        require(type(ids) is list and ids
                and all(type(x) is int and x>=0 and x not in seen for x in ids)
                and ids==sorted(set(ids)),
                "Invalid or duplicate component object identities")
        seen.update(ids)
        require(type(box) is list and len(box)==4,
                "Missing candidate component bbox")
        rect=pymupdf.Rect(box)
        require(rect.is_valid and rect.width>=0 and rect.height>=0
                and (rect.width>0 or rect.height>0),
                "Malformed connected source bbox")
        # An isolated original PDF graph line can have zero height or
        # width. Expand the observation footprint only, NOT source geometry.
        footprint=pymupdf.Rect(rect.x0-.01,rect.y0-.01,
                               rect.x1+.01,rect.y1+.01)
        touched=[i for i,reg in enumerate(registration)
                 if reg.intersects(footprint)]
        rows.append({
            "drawing_indices":ids,
            "union_bbox":box,
            "registration_groups_intersecting_bbox":touched,
            "classification":("COMPONENT_WITHOUT_NEARBY_MEASURED_REGISTRATION"
                              if not touched else
                              "COMPONENT_SPANS_MULTIPLE_REGISTRATION_GROUPS"
                              if len(touched)>1 else
                              "COMPONENT_NEAR_ONE_MEASURED_REGISTRATION_GROUP"),
            "actual_source_stroke_pixels_seen_in_slide":False,
            "original_author_figure_membership_certified":False,
        })
    return {
        "schema_version":1,
        "status":"SOURCE_COMPONENT_REGISTRATION_INTERSECTION_REVIEW_REQUIRED",
        "components_total":len(rows),
        "components_without_matched_registration":sum(
            not x["registration_groups_intersecting_bbox"] for x in rows),
        "observations":rows,
        "original_complete_figure_verified":False,
        "original_panel_boundaries_verified":False,
        "original_stroke_to_slide_pixel_equality_verified":False,
        "encoded_highlighted_video_authorized":False,
        "publication_authorized":False,
    }


def audit_component_registration(*,source:Path,slides:Path,
                                 source_page:int,slide_page:int,
                                 figure_id:str)->dict:
    original=audit_real_source_components(
        source=source,page_number=source_page,figure_id=figure_id)
    matched=audit_real_transform_groups(
        source=source,slides=slides,
        source_page=source_page,slide_page=slide_page,figure_id=figure_id)
    require(original["source_sha256"]==matched["source_sha256"],
            "Original PDF identity inconsistency")
    report=crosscheck_component_registration(
        original["candidate_components"],
        matched["candidate_transform_groups"])
    require(_sha(Path(source).absolute())==original["source_sha256"]
            and _sha(Path(slides).absolute())==matched["slides_sha256"],
            "Textbook/slide modified during component registration")
    return {**report,"source_sha256":original["source_sha256"],
            "slides_sha256":matched["slides_sha256"],
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
    print(json.dumps(audit_component_registration(
        source=a.source,slides=a.slides,source_page=a.source_page,
        slide_page=a.slide_page,figure_id=a.figure_id),
        indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
