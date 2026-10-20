"""Independent original PDF drawing-operations audit for uncorroborated vectors.

A path's geometry, ink and nearby words do NOT certify textbook figure
membership, a missing panel, or absence from a slide bitmap.
"""
from __future__ import annotations
from pathlib import Path
import math
import pymupdf
from .figure_source_vector_proximity import audit_original_vector_proximity
from .figure_source_identity import require, _sha


def characterize_unmatched_drawing_objects(*, observations: list,
                                           drawings: list, words: list) -> dict:
    require(type(observations) is list and type(drawings) is list
            and type(words) is list and len(drawings) <= 2000,
            "Invalid bounded source drawing inventories")
    rows = []
    seen = set()
    for row in observations:
        require(type(row) is dict and type(row.get("drawing_index")) is int,
                "Invalid source drawing reference")
        index = row["drawing_index"]
        require(0 <= index < len(drawings) and index not in seen,
                "Invalid or duplicate source drawing index")
        seen.add(index)
        if row.get("classification") != "NO_NEARBY_SOURCE_FEATURES":
            continue
        drawing = drawings[index]
        rect = pymupdf.Rect(drawing["rect"])
        require(rect.is_valid and not rect.is_infinite
                and rect.width >= 0 and rect.height >= 0,
                "Invalid source PDF drawing geometry")
        items = drawing.get("items", [])
        require(type(items) is list and len(items) <= 3000,
                "Excessively complex source vector object")
        ops = {}
        for item in items:
            require(isinstance(item, tuple) and len(item) >= 1
                    and isinstance(item[0], str),
                    "Invalid original vector operation")
            key=item[0]
            ops[key] = ops.get(key,0) + 1
        neighbors = 0
        for w in words:
            require(len(w) >= 4, "Invalid original PDF word rectangle")
            if pymupdf.Rect(w[:4]).intersects(
                pymupdf.Rect(rect.x0-2,rect.y0-2,rect.x1+2,rect.y1+2)):
                neighbors += 1
        rows.append({
            "drawing_index": index,
            "bbox": [round(float(z), 3) for z in rect],
            "drawing_type": str(drawing.get("type", "")),
            "operations": ops,
            "operation_count": len(items),
            "line_or_curve_like": (rect.width < 1.5 or rect.height < 1.5),
            "has_text_word_overlap_within_2pt": neighbors > 0,
            "nearby_word_count": neighbors,
            "original_figure_membership_proven": False,
            "missing_from_slide_proven": False,
        })
    rows.sort(key=lambda r:r["drawing_index"])
    return {
        "schema_version":1,
        "status":"UNMATCHED_SOURCE_VECTOR_OPERATIONS_REQUIRE_REVIEW",
        "unmatched_object_count":len(rows),
        "line_or_curve_like_count":sum(r["line_or_curve_like"] for r in rows),
        "nearby_word_overlap_count":sum(r["has_text_word_overlap_within_2pt"]
                                        for r in rows),
        "unmatched_source_drawings":rows,
        "original_figure_membership_verified":False,
        "missing_slide_strokes_verified":False,
        "complete_original_figure_verified":False,
        "narrated_video_authorized":False,
    }


def audit_unmatched_vector_operations(*, source:Path, slides:Path,
                                      source_page:int, slide_page:int,
                                      figure_id:str) -> dict:
    base=audit_original_vector_proximity(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    source_path=Path(source).absolute()
    with pymupdf.open(source_path) as doc:
        page=doc[source_page-1]
        data=characterize_unmatched_drawing_objects(
            observations=base["observations"],
            drawings=page.get_drawings(),words=page.get_text("words"))
    require(data["unmatched_object_count"]==base["without_nearby_features"],
            "Missing or inconsistent unmatched objects")
    require(_sha(source_path)==base["source_sha256"],
            "Source changed while characterizing original paths")
    return {**data,"source_sha256":base["source_sha256"],
            "slides_sha256":base["slides_sha256"],
            "source_page":source_page,"slide_page":slide_page,
            "figure_id":figure_id}


def main(argv=None) -> int:
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--source-page",type=int,required=True)
    p.add_argument("--slide-page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    a=p.parse_args(argv)
    print(json.dumps(audit_unmatched_vector_operations(
        source=a.source,slides=a.slides,source_page=a.source_page,
        slide_page=a.slide_page,figure_id=a.figure_id),
        indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
