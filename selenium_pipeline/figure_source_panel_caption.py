"""Source-only corroboration of parent figure captions and panel-specific crops.

A Gemini mapping can use the parent caption "Figure 7.21" for both target
"Figure 7.21(a).png" and "(b).png". The target panel letter is NOT proof by
itself. Reconcile only if original PDF text plus SHA-bound Docling source-space
crop rectangles independently contain the same caption and unique, local
panel-letter marks. Any missing evidence leaves the existing figure-composite
fail-closed guard authoritative.

No model calls, OCR, source PDF edits, stitching or academic/media approval.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

_FIGURE = re.compile(r"(?i)\bfigure[\s._-]*(\d+)[\s._-]+(\d+)\b")
_TARGET = re.compile(
    r"(?i)^Figure\s+(\d+)\.(\d+)\(([a-z])\)\.png$")
_PARENT = re.compile(r"(?i)^Figure\s+(\d+)\.(\d+)\s*$")


class SourcePanelEvidenceError(ValueError):
    """Not enough independently authenticated source proof for a panel."""


def _sha(path: Path) -> str:
    if (not path.is_file() or path.is_symlink()
            or path.stat().st_size > 25_000_000):
        raise SourcePanelEvidenceError("Missing or unsafe source panel asset")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconcile_parent_caption_panels(
    *, mappings: list[tuple[str, str, str]], source_pdf: Path,
    page_png: Path, crops_dir: Path, geometry_manifest: Path,
) -> tuple[list[tuple[str, str, str]], dict | None]:
    """Supply a panel suffix only with independent source PDF letter evidence.

    A non-applicable mapping is returned unchanged. A candidate that needs
    panel reconciliation MUST pass all checks or raises before any file copy.
    """
    if not isinstance(mappings, list):
        raise SourcePanelEvidenceError("Expected ordered local crop mappings")
    groups: dict[str, list[tuple[int, str, str, str, str]]] = defaultdict(list)
    for index, item in enumerate(mappings):
        if not isinstance(item, (tuple, list)) or len(item) != 3:
            raise SourcePanelEvidenceError("Malformed figure-mapping identity")
        crop, label, target = item
        if not all(isinstance(x, str) for x in (crop, label, target)):
            raise SourcePanelEvidenceError("Non-text crop, label or destination")
        match = _TARGET.fullmatch(target.strip())
        if not match:
            continue
        num = f"{int(match[1])}.{int(match[2])}"
        panel = match[3].lower()
        if _PARENT.fullmatch(label.strip()) and (
            f"{int(_PARENT.fullmatch(label.strip())[1])}."
            f"{int(_PARENT.fullmatch(label.strip())[2])}" == num):
            groups[num].append((index, crop, label, target, panel))
    if not groups:
        return mappings, None

    # Never silently add labels when a parent figure also appears as a
    # non-panel or different figure-number target in the same source response.
    for number, entries in groups.items():
        if len(entries) < 2 or len(entries) > 8:
            raise SourcePanelEvidenceError("Insufficient or excessive source panel group")
        panels = [entry[4] for entry in entries]
        if (len(set(panels)) != len(panels)
                or set(panels) != set("abcdefgh"[:len(panels)])):
            raise SourcePanelEvidenceError("Incomplete or duplicate panel-letter sequence")
        if any(
            _FIGURE.search(label) and
            f"{int(_FIGURE.search(label)[1])}.{int(_FIGURE.search(label)[2])}" == number
            and idx not in {entry[0] for entry in entries}
            for idx, (_, label, _) in enumerate(mappings)
        ):
            raise SourcePanelEvidenceError("Mixed parent/other mapping for same figure")

    source_pdf, page_png = Path(source_pdf), Path(page_png)
    crops_dir, geometry_manifest = Path(crops_dir), Path(geometry_manifest)
    if (not geometry_manifest.is_file() or geometry_manifest.is_symlink()
            or geometry_manifest.stat().st_size > 2_000_000
            or crops_dir.is_symlink()):
        raise SourcePanelEvidenceError("Source crop geometry missing or unsafe")
    pdf_sha, image_sha, manifest_sha = (
        _sha(source_pdf), _sha(page_png), _sha(geometry_manifest))
    try:
        declared = json.loads(geometry_manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise SourcePanelEvidenceError("Malformed source-bound crop manifest") from exc
    if (not isinstance(declared, dict)
            or declared.get("schema_version") != 1
            or declared.get("status") !=
               "SOURCE_DECLARED_CROP_GEOMETRY_CANDIDATES_NOT_VERIFIED"
            or declared.get("original_source_pdf_sha256") != pdf_sha
            or declared.get("page_image_sha256") != image_sha
            or declared.get("source_crop_pixel_correspondence_verified") is not False
            or declared.get("figure_composite_layout_certified") is not False
            or declared.get("student_publication_authorized") is not False):
        raise SourcePanelEvidenceError("Unverified original source geometry identity")
    records = declared.get("crops")
    page_number = declared.get("page_number")
    if (not isinstance(records, list)
            or not isinstance(page_number, int) or page_number < 1
            or declared.get("crop_count") != len(records)):
        raise SourcePanelEvidenceError("Incomplete PDF page/crop inventory")
    indexed = {}
    for item in records:
        if (not isinstance(item, dict) or not isinstance(item.get("crop_file"), str)
                or item["crop_file"] in indexed
                or item.get("source_pdf_sha256") != pdf_sha
                or item.get("page_image_sha256") != image_sha
                or item.get("source_page") != page_number
                or item.get("status") != "DOCLING_SINGLE_SOURCE_RECT_CANDIDATE"
                or item.get("source_crop_pixel_correspondence_verified") is not False
                or item.get("original_caption_and_panel_semantics_verified") is not False
                or item.get("automatic_composite_or_publication_authorized") is not False
                or item.get("crop_sha256") != _sha(crops_dir / item["crop_file"])):
            raise SourcePanelEvidenceError("Missing or modified crop identity")
        coords = item.get("bbox_source_pdf_top_left_pt")
        size = item.get("source_page_size_pt")
        if (not isinstance(coords, list) or len(coords) != 4
                or not isinstance(size, list) or len(size) != 2
                or not all(type(v) in (int, float) and math.isfinite(v)
                           for v in coords + size)
                or not 0 <= coords[0] < coords[2] <= size[0]
                or not 0 <= coords[1] < coords[3] <= size[1]):
            raise SourcePanelEvidenceError("Invalid PDF source-space rectangle")
        indexed[item["crop_file"]] = item
    actual_crops = {p.name for p in crops_dir.glob("fig_*.png")}
    if len(indexed) != len(actual_crops) or set(indexed) != actual_crops:
        raise SourcePanelEvidenceError("Crop inventory is not source-identical")
    if set(name for name, _, _ in mappings) != actual_crops:
        raise SourcePanelEvidenceError("Model mapping omits source crops")

    try:
        import fitz
    except ImportError as exc:
        raise SourcePanelEvidenceError("Original PDF text geometry unavailable") from exc
    with fitz.open(str(source_pdf)) as pdf:
        if page_number > len(pdf):
            raise SourcePanelEvidenceError("Original PDF page missing")
        page = pdf[page_number - 1]
        words = page.get_text("words")
        blocks = page.get_text("blocks")
        all_records = []
        for number, entries in groups.items():
            # A genuine printed figure caption must BEGIN its own source text
            # block; references elsewhere in prose never authorize panels.
            caption_pat = re.compile(
                rf"(?i)^\s*Figure\s+{re.escape(number)}(?=\s|$)")
            captions = [block for block in blocks
                        if caption_pat.search(str(block[4]))]
            if len(captions) != 1:
                raise SourcePanelEvidenceError("Original single figure caption not verified")
            cap = captions[0]
            cap_text = str(cap[4])
            required = {part[4] for part in entries}
            caption_panels = set(re.findall(
                r"\(([a-z])\)", cap_text, flags=re.I))
            if not required.issubset({p.lower() for p in caption_panels}):
                raise SourcePanelEvidenceError("Caption lacks explicit source panel names")
            bottom = max(indexed[entry[1]]["bbox_source_pdf_top_left_pt"][3]
                         for entry in entries)
            left = min(indexed[entry[1]]["bbox_source_pdf_top_left_pt"][0]
                       for entry in entries)
            right = max(indexed[entry[1]]["bbox_source_pdf_top_left_pt"][2]
                        for entry in entries)
            if (cap[1] < bottom - 2 or cap[1] - bottom > 120
                    or cap[2] < left + 4 or cap[0] > right - 4):
                raise SourcePanelEvidenceError(
                    "Original caption not spatially adjacent to panel group")

            for index, crop, label, target, panel in entries:
                rect = indexed[crop]["bbox_source_pdf_top_left_pt"]
                width, height = rect[2] - rect[0], rect[3] - rect[1]
                # Author source panel marker must be located in the crop's
                # lower-left corner, not an unrelated text/table reference.
                anchors = [
                    w for w in words
                    if rect[0] - 1.5 <= w[0] <= rect[0] + .22 * width
                    and rect[1] + .76 * height <= w[1] <= rect[3] + 1.5
                    and w[2] <= rect[2] + 1.5
                    and w[3] <= rect[3] + 1.5
                    and re.fullmatch(r"[a-z]", str(w[4]).strip(), re.I)
                ]
                if len(anchors) != 1 or str(anchors[0][4]).lower() != panel:
                    raise SourcePanelEvidenceError(
                        "Original cropped panel letter absent or ambiguous")
                all_records.append({
                    "crop_file": crop,
                    "original_label": label, "panel_target": target,
                    "source_caption_figure": number,
                    "panel_letter": panel,
                    "crop_sha256": indexed[crop]["crop_sha256"],
                    "crop_rect_pdf_top_left_pt": rect,
                    "source_panel_marker_box_pdf_pt": [
                        round(float(v), 4) for v in anchors[0][:4]],
                    "source_caption_block_pdf_pt": [
                        round(float(v), 4) for v in cap[:4]],
                })
        new = [tuple(item) for item in mappings]
        for number, entries in groups.items():
            for index, crop, _label, target, panel in entries:
                new[index] = (crop, f"Figure {number}({panel})", target)
    witness = {
        "schema_version": 1,
        "status": "SOURCE_TEXT_AND_CROP_PANEL_MARKERS_CORROBORATED_NOT_FIGURE_QA",
        "source_pdf_sha256": pdf_sha,
        "page_image_sha256": image_sha,
        "source_crop_manifest_sha256": manifest_sha,
        "source_page_number": page_number,
        "original_mapping": [list(item) for item in mappings],
        "resolved_mapping": [list(item) for item in new],
        "source_panel_proof": all_records,
        "new_model_requests": 0,
        "full_source_crop_pixel_correspondence_verified": False,
        "independent_figure_semantics_certified": False,
        "automatic_merge_authorized": False,
        "student_publication_authorized": False,
    }
    return new, witness
