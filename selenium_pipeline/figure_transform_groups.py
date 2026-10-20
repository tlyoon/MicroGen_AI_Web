"""Group adjacent slide SCAN bins with independently similar fitted transforms.

An affine-transform group is a registration hypothesis, NOT author-intended
figure panel identity or proof of complete textbook artwork.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .figure_local_feature_correspondence import audit_local_feature_correspondence
from .figure_source_identity import require


def group_coherent_scan_transforms(audit: dict) -> dict:
    require(type(audit) is dict and type(audit.get("arbitrary_four_width_bins")) is list
            and len(audit["arbitrary_four_width_bins"]) == 4,
            "Expected an independently checked four-bin local-feature audit")
    bins = audit["arbitrary_four_width_bins"]
    eligible = []
    for i, row in enumerate(bins):
        if not row.get("geometrically_coherent_candidate"):
            eligible.append(None)
            continue
        m = row.get("affine_source_render_to_slide_px")
        source = row.get("source_keypoint_extent_pdf")
        slide = row.get("slide_keypoint_extent_px")
        require(row.get("scan_bin") == i and type(m) is list
                and len(m) == 2 and all(type(r) is list and len(r) == 3 for r in m)
                and type(source) is list and len(source) == 4
                and type(slide) is list and len(slide) == 4
                and all(type(v) in (int, float) and math.isfinite(v)
                        for r in m for v in r)
                and all(type(v) in (int, float) and math.isfinite(v)
                        for v in source + slide),
                "Malformed measured transform or keypoint extent")
        require(int(row.get("ransac_inlier_count", 0)) >= 8,
                "No independently coherent inlier evidence")
        eligible.append(row)

    def compatible(a: dict, b: dict) -> bool:
        ma, mb = a["affine_source_render_to_slide_px"], b["affine_source_render_to_slide_px"]
        # Distinct source regions with same scaled orientation/translation
        # are one potential reflow transform, not proof of panel count.
        linear_delta = max(abs(ma[i][j] - mb[i][j]) for i in range(2) for j in range(2))
        tx, ty = ma[0][2] - mb[0][2], ma[1][2] - mb[1][2]
        return linear_delta <= .015 and math.hypot(tx, ty) <= 5.0

    raw_groups = []
    current = []
    for row in eligible:
        if row is None:
            if current:
                raw_groups.append(current)
            current = []
        elif not current:
            current = [row]
        elif compatible(current[-1], row):
            current.append(row)
        else:
            raw_groups.append(current)
            current = [row]
    if current:
        raw_groups.append(current)
    groups = []
    for rows in raw_groups:
        src = [row["source_keypoint_extent_pdf"] for row in rows]
        dst = [row["slide_keypoint_extent_px"] for row in rows]
        groups.append({
            "slide_scan_bin_indices": [int(row["scan_bin"]) for row in rows],
            "joint_ransac_inlier_count": sum(row["ransac_inlier_count"] for row in rows),
            "source_matched_keypoint_union_bbox_pdf": [
                min(v[0] for v in src), min(v[1] for v in src),
                max(v[2] for v in src), max(v[3] for v in src)],
            "slide_matched_keypoint_union_bbox_px": [
                min(v[0] for v in dst), min(v[1] for v in dst),
                max(v[2] for v in dst), max(v[3] for v in dst)],
            "arbitrary_scan_bins_combined_not_panel_certified": True,
            "original_author_panel_ownership_verified": False,
        })
    return {
        "schema_version": 1,
        "status": "SCAN_TRANSFORM_GROUPS_CANDIDATE_REVIEW_REQUIRED",
        "geometrically_coherent_scan_bin_count": sum(row is not None for row in eligible),
        "candidate_transform_group_count": len(groups),
        "candidate_transform_groups": groups,
        "source_figure_panel_count_certified": False,
        "complete_source_graphs_verified": False,
        "source_to_slide_full_coverage_verified": False,
        "narrated_visual_highlight_verified": False,
        "video_or_publication_authorized": False,
    }


def audit_real_transform_groups(*, source: Path, slides: Path,
                                source_page: int, slide_page: int,
                                figure_id: str) -> dict:
    observed = audit_local_feature_correspondence(
        source=source, slides=slides, source_page=source_page,
        slide_page=slide_page, figure_id=figure_id)
    require(observed["video_or_publication_authorized"] is False
            and observed["complete_figure_and_panel_mapping_certified"] is False,
            "Upstream correspondence claims invalid semantic approval")
    return {**group_coherent_scan_transforms(observed),
            "source_sha256": observed["source_sha256"],
            "slides_sha256": observed["slides_sha256"],
            "source_page": source_page,
            "slide_page": slide_page,
            "figure_id": figure_id,
            "initial_tentative_descriptor_matches":
                observed["tentative_descriptor_match_count"]}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--slides", type=Path, required=True)
    p.add_argument("--source-page", type=int, required=True)
    p.add_argument("--slide-page", type=int, required=True)
    p.add_argument("--figure-id", required=True)
    a = p.parse_args(argv)
    print(json.dumps(audit_real_transform_groups(
        source=a.source, slides=a.slides, source_page=a.source_page,
        slide_page=a.slide_page, figure_id=a.figure_id), indent=2, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
