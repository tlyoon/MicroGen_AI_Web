"""Independent source-PDF to slide-bitmap LOCAL FEATURE observations only.

Four arbitrary equal-width slide scan bins are NOT scientific panels.
ORB matches and RANSAC fits are hypotheses, not semantic source identity.
All source and lecture files are inspected read-only and SHA-preserved.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf

from .figure_source_identity import require, _sha
from .figure_pre_caption_vector_inventory import inventory_pre_caption_vectors
from .figure_slide_raster_visibility import audit_vector_source_slide_raster


def audit_local_feature_correspondence(*, source: Path, slides: Path,
                                       source_page: int, slide_page: int,
                                       figure_id: str) -> dict:
    """Require independent PDF/screen evidence, then fit bounded descriptors."""
    base = audit_vector_source_slide_raster(
        source=source, slides=slides, source_page=source_page,
        slide_page=slide_page, figure_id=figure_id)
    inventory = inventory_pre_caption_vectors(
        source=source, page_number=source_page, figure_id=figure_id)
    require(base["source_sha256"] == inventory["source_sha256"],
            "Source changed between independent audits")
    require(base["status"] == "VISIBLE_SLIDE_RASTER_ONLY_SOURCE_FIGURE_UNVERIFIED"
            and base["slide_reference_render_pixels_equal"] is True,
            "Slide bitmap display must be independently visible first")
    require(base["source_image_instances"] == 0
            and base["slide_material_image_instances"] == 1,
            "Expected original vector-to-visible-raster modality")
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {
            "schema_version": 1,
            "status": "LOCAL_FEATURE_DEPENDENCY_UNAVAILABLE_REVIEW_REQUIRED",
            "source_sha256": base["source_sha256"],
            "slides_sha256": base["slides_sha256"],
            "original_source_to_slide_identity_certified": False,
            "figure_panel_completeness_certified": False,
            "video_or_publication_authorized": False,
        }
    source_path, slide_path = Path(source).absolute(), Path(slides).absolute()
    scan_rect = pymupdf.Rect(inventory["candidate_scan_corridor"])
    require(scan_rect.is_valid and not scan_rect.is_empty
            and scan_rect.width * scan_rect.height <= 150_000,
            "Original source feature scan must remain bounded")
    with pymupdf.open(source_path) as book, pymupdf.open(slide_path) as deck:
        src = book[source_page - 1]
        slide = deck[slide_page - 1]
        pix = src.get_pixmap(matrix=pymupdf.Matrix(3, 3),
                             clip=scan_rect, alpha=False,
                             colorspace=pymupdf.csGRAY)
        require(pix.n == 1 and pix.width * pix.height <= 1_500_000,
                "Unbounded original source rendering")
        source_gray = np.frombuffer(pix.samples, np.uint8).reshape(
            pix.height, pix.width)
        materials = [i for i in slide.get_image_info(xrefs=True)
                     if int(i["width"]) >= 48 and int(i["height"]) >= 48
                     and pymupdf.Rect(i["bbox"]).width >= 50
                     and pymupdf.Rect(i["bbox"]).height >= 25]
        require(len(materials) == 1 and
                type(materials[0].get("xref")) is int and
                materials[0]["xref"] > 0,
                "Expected one material original slide raster")
        data = deck.extract_image(materials[0]["xref"])
        require(isinstance(data, dict) and
                isinstance(data.get("image"), bytes)
                and len(data["image"]) <= 15_000_000,
                "Bound embedded bitmap not available")
        slide_gray = cv2.imdecode(
            np.frombuffer(data["image"], np.uint8),
            cv2.IMREAD_GRAYSCALE)
        require(slide_gray is not None and slide_gray.ndim == 2
                and slide_gray.shape[0] >= 48 and
                slide_gray.shape[1] >= 48
                and slide_gray.size <= 4_000_000,
                "Unreadable or excessive slide raster")
    detector = cv2.ORB_create(nfeatures=2000)
    src_keypoints, src_descriptors = detector.detectAndCompute(
        source_gray, None)
    slide_keypoints, slide_descriptors = detector.detectAndCompute(
        slide_gray, None)
    candidate = []
    if src_descriptors is not None and slide_descriptors is not None:
        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
            slide_descriptors, src_descriptors, k=2)
        # Only distinct nearest-neighbor descriptors, never single
        # unqualified matches. Text/glyph coincidences can still survive.
        candidate = [
            m for pair in pairs if len(pair) == 2
            for m, n in [pair] if m.distance < .80 * n.distance
        ]
    result = []
    for i in range(4):
        start = i * slide_gray.shape[1] / 4
        stop = (i + 1) * slide_gray.shape[1] / 4
        group = [m for m in candidate
                 if start <= slide_keypoints[m.queryIdx].pt[0] < stop]
        receipt = {
            "scan_bin": i, "bin_slide_x_range_px": [round(start, 2),
                                                      round(stop, 2)],
            "descriptor_ratio_match_count": len(group),
            "ransac_inlier_count": 0,
            "geometrically_coherent_candidate": False,
            "source_keypoint_extent_pdf": None,
            "slide_keypoint_extent_px": None,
            "affine_source_render_to_slide_px": None,
            "panel_identity_or_membership_verified": False,
        }
        if len(group) >= 8:
            sp = np.float32([src_keypoints[m.trainIdx].pt for m in group])
            tp = np.float32([slide_keypoints[m.queryIdx].pt for m in group])
            matrix, mask = cv2.estimateAffinePartial2D(
                sp, tp, method=cv2.RANSAC,
                ransacReprojThreshold=3.0, maxIters=500,
                confidence=0.99)
            if mask is not None and matrix is not None:
                keep = mask.ravel().astype(bool)
                inliers = int(keep.sum())
                receipt["ransac_inlier_count"] = inliers
                if inliers >= 8:
                    left, right = sp[keep], tp[keep]
                    left_width = float(np.ptp(left[:, 0]))
                    left_height = float(np.ptp(left[:, 1]))
                    right_width = float(np.ptp(right[:, 0]))
                    right_height = float(np.ptp(right[:, 1]))
                    coherent = (inliers >= .4 * len(group)
                                and left_width >= 24
                                and left_height >= 24
                                and right_width >= 12
                                and right_height >= 12)
                    receipt["geometrically_coherent_candidate"] = coherent
                    if coherent:
                        bounds = [left[:, 0].min(), left[:, 1].min(),
                                  left[:, 0].max(), left[:, 1].max()]
                        # Convert 3x source render pixel coordinates to
                        # the actual PDF page coordinate frame.
                        receipt["source_keypoint_extent_pdf"] = [
                            round(float(v) / 3 +
                                  (scan_rect.x0 if j % 2 == 0
                                   else scan_rect.y0), 3)
                            for j, v in enumerate(bounds)]
                        receipt["slide_keypoint_extent_px"] = [
                            round(float(v), 3) for v in
                            (right[:, 0].min(), right[:, 1].min(),
                             right[:, 0].max(), right[:, 1].max())]
                        receipt["affine_source_render_to_slide_px"] = [
                            [round(float(v), 5) for v in row]
                            for row in matrix]
        result.append(receipt)
    require(_sha(source_path) == base["source_sha256"]
            and _sha(slide_path) == base["slides_sha256"],
            "Original source or slide PDF mutated during feature audit")
    count = sum(1 for item in result
                if item["geometrically_coherent_candidate"])
    return {
        "schema_version": 1,
        "status": ("GEOMETRIC_LOCAL_FEATURE_CANDIDATES_REVIEW_REQUIRED"
                   if count else "NO_COHERENT_LOCAL_FEATURE_EVIDENCE_REVIEW_REQUIRED"),
        "source_sha256": base["source_sha256"],
        "slides_sha256": base["slides_sha256"],
        "figure_id": figure_id, "source_page": source_page,
        "slide_page": slide_page,
        "source_scan_corridor": inventory["candidate_scan_corridor"],
        "source_orb_feature_count": len(src_keypoints),
        "slide_orb_feature_count": len(slide_keypoints),
        "tentative_descriptor_match_count": len(candidate),
        "arbitrary_four_width_bins": result,
        "geometrically_coherent_bin_count": count,
        "scan_bins_are_author_intended_panels": False,
        "candidate_source_region_authoritatively_owned": False,
        "complete_figure_and_panel_mapping_certified": False,
        "mathematical_semantics_verified": False,
        "narrated_highlights_verified": False,
        "encoded_video_duration_verified": False,
        "video_or_publication_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--slides", type=Path, required=True)
    p.add_argument("--source-page", type=int, required=True)
    p.add_argument("--slide-page", type=int, required=True)
    p.add_argument("--figure-id", required=True)
    a = p.parse_args(argv)
    print(json.dumps(audit_local_feature_correspondence(
        source=a.source, slides=a.slides,
        source_page=a.source_page, slide_page=a.slide_page,
        figure_id=a.figure_id), indent=2, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
