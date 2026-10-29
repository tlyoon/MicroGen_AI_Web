"""Optional source-grounded layout-reflow recovery for figure QA.

The only safe automatic correction is *diagnostic*: a valid reflow should not
be failed solely for whole-crop aspect mismatch. Correcting mathematical ink,
drawing content, published slides or videos requires independent provenance,
semantic and time-coded acceptance checks, never a color-shape guess.
"""
from __future__ import annotations

from pathlib import Path

from .figure_source_identity import FigureIdentityReviewRequired


def classify_layout_evidence(report: dict) -> dict:
    """Return a bounded disposition, never production authorization."""
    count = report.get("detected_graph_count", report.get("original_vertical_graph_run_count")) if type(report) is dict else None
    matched = (type(report) is dict and
               type(count) is int and 2 <= count <= 6 and
               report.get("status") in {
                   "THREE_GRAPH_COLOR_AND_BLACK_INK_REFLOW_CORROBORATED_REVIEW_REQUIRED",
                   "MULTI_GRAPH_COLOR_AND_BLACK_INK_REFLOW_CORROBORATED_REVIEW_REQUIRED",
               } and
               (count == 3 or report["status"].startswith("MULTI_GRAPH_")) and
               report.get("three_graph_black_ink_geometry_plausible") is True and
               report.get("original_vertical_graph_run_count") == count and
               report.get("slide_horizontal_graph_run_count") == count and
               report.get("three_graph_curve_shape_sequence_coherent") is True and
               type(report.get("graph_correspondence_evidence")) is list and
               len(report["graph_correspondence_evidence"]) == count and
               all(type(x) is dict and x.get("blue_red_curve_shapes_coherent") is True
                   and x.get("black_ink_geometry_plausible") is True
                   and type(x.get("black_axes_and_label_ink_shape_diagnostic")) in (int,float)
                   and 0 <= x["black_axes_and_label_ink_shape_diagnostic"] <= .045
                   and x.get("original_math_axis_and_labels_verified") is False
                   for x in report["graph_correspondence_evidence"]) and
               report.get("full_source_figure_equivalence_certified") is False and
               report.get("video_or_publication_authorized") is False)
    result = {
        "schema_version": 1,
        "status": ("THREE_GRAPH_REFLOW_DETECTED_SEMANTIC_REVIEW_PENDING"
                   if matched else "FIGURE_LAYOUT_REQUIRES_MORE_EVIDENCE"),
        "layout_reflow_detected": bool(matched),
        "detected_graph_count": count if matched else None,
        "previous_whole_source_crop_aspect_mismatch_resolved_as_layout_only": bool(matched),
        "safe_automatic_resolution": (
            "DISMISS_ASPECT_ONLY_REJECTION_PRESERVE_ORIGINAL_SLIDE"
            if matched else "KEEP_FIGURE_BLOCKED_AND_PREPARE_REVIEW"),
        "next_action": (
            "INDEPENDENTLY_VALIDATE_ORIGINAL_MATH_AXES_LABELS_AND_COMPLETE_FIGURE"
            if matched else
            "RECOVER_SOURCE_BOUND_PANEL_GEOMETRY_OR_REGENERATE_TO_ISOLATED_REVIEW_CANDIDATE"),
        "auto_replacement_or_source_mutation": False,
        "complete_author_figure_certified": False,
        "actual_math_label_semantics_certified": False,
        "spoken_visual_highlight_certified": False,
        "encoded_sub_600s_mp4_certified": False,
        "academic_listening_qa_certified": False,
        "publication_authorized": False,
    }
    if matched:
        result["graph_correspondence_evidence"] = report["graph_correspondence_evidence"]
        result["source_sha256"] = report.get("original_pdf_sha256")
        result["slides_sha256"] = report.get("existing_slides_pdf_sha256")
    return result


def discover_source_slide_reflow(*, source: Path, slides: Path,
                                 source_page: int, slide_page: int,
                                 figure_id: str) -> dict:
    """Run only when upstream verified source-page and slide-raster exist.

    Missing computer-vision dependencies and other technical failures are
    explicit review states, never empty success or permission to skip QA.
    """
    try:
        from .figure_three_graph_color_reflow import audit_real_three_graph_reflow
        raw = audit_real_three_graph_reflow(
            source=source, slides=slides, source_page=source_page,
            slide_page=slide_page, figure_id=figure_id)
        return classify_layout_evidence(raw)
    except Exception as exc:
        # The source-slide identity gate is validated *before* this optional
        # image diagnostic. A backend-specific OpenCV exception must never
        # release a publication gate or stall all lecture QA.
        return {
            **classify_layout_evidence({}),
            "status": "AUTOMATIC_LAYOUT_DIAGNOSTIC_UNAVAILABLE_REVIEW_REQUIRED",
            "diagnostic_exception_type": type(exc).__name__,
        }
