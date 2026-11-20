"""Source-space crop bounds from original Docling PictureItem provenance.

No Gemini calls, no invented panel grouping, and no automatic publication.
The vendor crop worker writes this *candidate* evidence alongside original
crops so later figure-composite gates need not guess missing source geometry.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path


def _sha(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Source geometry asset missing or symlinked")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda: f.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def declared_picture_rect(*, item: object, page_width_pt: float,
                          page_height_pt: float) -> list[float] | None:
    """Normalize one declared single-page Docling box into PDF top-left units.

    A bounding box is source provenance only, NOT proof that the crop contains
    all author panels or that a model caption is correct. Ambiguity returns
    None and MUST NOT be replaced with guessed coordinates.
    """
    try:
        if not all(math.isfinite(float(v)) and float(v) > 0
                   for v in (page_width_pt, page_height_pt)):
            return None
    except (ValueError, TypeError, OverflowError):
        return None
    provenance = getattr(item, "prov", None)
    if not isinstance(provenance, (list, tuple)) or len(provenance) != 1:
        return None
    origin = provenance[0]
    if getattr(origin, "page_no", None) != 1:  # one-page PDF
        return None
    box = getattr(origin, "bbox", None)
    if box is None:
        return None
    try:
        l, r, t, b = (float(getattr(box, key)) for key in ("l", "r", "t", "b"))
        if not all(math.isfinite(x) for x in (l, r, t, b)):
            return None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None
    direction = str(getattr(box, "coord_origin", "")).split(".")[-1].upper()
    if direction not in {"BOTTOMLEFT", "TOPLEFT"}:
        return None
    if direction == "BOTTOMLEFT":
        y0, y1 = float(page_height_pt) - max(t, b), float(page_height_pt) - min(t, b)
    else:
        y0, y1 = min(t, b), max(t, b)
    rect = [l, y0, r, y1]
    if not (0 <= l < r <= float(page_width_pt) and
            0 <= y0 < y1 <= float(page_height_pt)):
        return None
    if r - l < 1 or y1 - y0 < 1:
        return None
    return [round(x, 5) for x in rect]


def build_crop_geometry_candidate(
    *, picture: object, original_pdf: Path, page_png: Path, crop_png: Path,
    page_number: int, page_width_pt: float, page_height_pt: float,
) -> dict:
    """Make an independently SHA-bound candidate for one *saved* crop."""
    if type(page_number) is not int or page_number < 1:
        raise ValueError("Original page number required")
    pdf_sha, page_sha, crop_sha = (
        _sha(Path(path)) for path in (original_pdf, page_png, crop_png))
    rect = declared_picture_rect(item=picture, page_width_pt=page_width_pt,
                                 page_height_pt=page_height_pt)
    return {
        "schema_version": 1,
        "status": ("DOCLING_SINGLE_SOURCE_RECT_CANDIDATE" if rect is not None
                   else "SOURCE_CROP_BBOX_UNVERIFIED"),
        "source_pdf_sha256": pdf_sha,
        "source_page": page_number,
        "page_image_sha256": page_sha,
        "crop_file": Path(crop_png).name,
        "crop_sha256": crop_sha,
        "source_page_size_pt": [round(float(page_width_pt), 5),
                                round(float(page_height_pt), 5)],
        "bbox_source_pdf_top_left_pt": rect,
        "source_crop_pixel_correspondence_verified": False,
        "original_caption_and_panel_semantics_verified": False,
        "automatic_composite_or_publication_authorized": False,
    }


def save_page_crop_geometry(*, target: Path, source_pdf: Path, page_png: Path,
                            records: list[dict], page_number: int) -> dict:
    """New-file-only SHA-bound manifest; never clobber previous attempt."""
    dest = Path(target)
    if (not dest.parent.is_dir() or dest.parent.is_symlink()
            or dest.is_symlink()):
        raise ValueError("Crop geometry manifest path untrusted")
    if type(page_number) is not int or page_number < 1:
        raise ValueError("Invalid original page")
    original_sha, page_sha = _sha(Path(source_pdf)), _sha(Path(page_png))
    if not isinstance(records, list):
        raise ValueError("Expected crop geometry records")
    seen = set()
    for record in records:
        if (type(record) is not dict
                or record.get("source_pdf_sha256") != original_sha
                or record.get("source_page") != page_number
                or record.get("page_image_sha256") != page_sha
                or type(record.get("crop_file")) is not str
                or record["crop_file"] in seen
                or Path(record["crop_file"]).name != record["crop_file"]
                or not record["crop_file"].startswith("fig_")
                or not record["crop_file"].endswith(".png")
                or record.get("automatic_composite_or_publication_authorized") is not False
                or record.get("source_crop_pixel_correspondence_verified") is not False
                or record.get("original_caption_and_panel_semantics_verified") is not False
                or record.get("status") not in {
                    "DOCLING_SINGLE_SOURCE_RECT_CANDIDATE",
                    "SOURCE_CROP_BBOX_UNVERIFIED",
                }):
            raise ValueError("Invalid crop geometry source identity or duplication")
        crop_path = dest.parent / record["crop_file"]
        if (_sha(crop_path) != record.get("crop_sha256")
                or record["status"] == "DOCLING_SINGLE_SOURCE_RECT_CANDIDATE"
                and record.get("bbox_source_pdf_top_left_pt") is None
                or record["status"] == "SOURCE_CROP_BBOX_UNVERIFIED"
                and record.get("bbox_source_pdf_top_left_pt") is not None):
            raise ValueError("Crop provenance cannot be reconciled with actual pixels")
        seen.add(record["crop_file"])
    report = {
        "schema_version": 1,
        "status": "SOURCE_DECLARED_CROP_GEOMETRY_CANDIDATES_NOT_VERIFIED",
        "original_source_pdf_sha256": original_sha,
        "page_number": page_number,
        "page_image_sha256": page_sha,
        "crop_count": len(records),
        "all_crops_have_declared_bbox": bool(records) and all(
            item["bbox_source_pdf_top_left_pt"] is not None for item in records),
        "crops": records,
        "source_crop_pixel_correspondence_verified": False,
        "figure_composite_layout_certified": False,
        "student_publication_authorized": False,
    }
    encoded = (json.dumps(report, ensure_ascii=False, sort_keys=True,
                          indent=2) + "\n").encode("utf8")
    if dest.exists():
        # Idempotent local pre-Send resume only: never overwrite an
        # immutable page-geometry witness, and never authorize Gemini retry.
        if dest.is_file() and dest.read_bytes() == encoded:
            return report
        raise ValueError("Existing source geometry differs; no overwrite")
    with dest.open("xb") as f:
        f.write(encoded)
        f.flush()
        os.fsync(f.fileno())
    return report


def inspect_source_locked_composite_candidates(
    *, manifest: Path, source_pdf: Path, page_png: Path,
    crops_dir: Path, mappings: list[tuple[str, str, str]],
) -> dict:
    """Read-only source-coordinate report for colliding figure targets.

    Only Docling-declared candidate boxes and immutable asset hashes are
    established. Even disjoint boxes cannot prove two crops are both parts of
    a named author figure, or that text/math inside each crop is correct.
    No image is stitched, renamed, approved, or published here.
    """
    manifest = Path(manifest)
    crops_dir = Path(crops_dir)
    if (not manifest.is_file() or manifest.is_symlink()
            or manifest.stat().st_size > 2_000_000):
        raise ValueError("Untrusted crop geometry manifest")
    try:
        report = json.loads(manifest.read_text(encoding="utf8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Unparseable crop geometry manifest") from exc
    if (type(report) is not dict or report.get("schema_version") != 1
            or report.get("status") != "SOURCE_DECLARED_CROP_GEOMETRY_CANDIDATES_NOT_VERIFIED"
            or report.get("original_source_pdf_sha256") != _sha(Path(source_pdf))
            or report.get("page_image_sha256") != _sha(Path(page_png))
            or report.get("source_crop_pixel_correspondence_verified") is not False
            or report.get("figure_composite_layout_certified") is not False
            or report.get("student_publication_authorized") is not False):
        raise ValueError("Source-geometry manifest identity or authority mismatch")
    records = report.get("crops")
    if (type(records) is not list or len(records) != report.get("crop_count")
            or type(report.get("page_number")) is not int):
        raise ValueError("Source-geometry crop inventory incomplete")
    names = {path.name for path in crops_dir.glob("fig_*.png")}
    if len(records) != len(names):
        raise ValueError("Crop inventory changed after source geometry recording")
    indexed = {}
    for item in records:
        if (type(item) is not dict or type(item.get("crop_file")) is not str
                or item["crop_file"] not in names or item["crop_file"] in indexed
                or item.get("source_pdf_sha256") != report["original_source_pdf_sha256"]
                or item.get("page_image_sha256") != report["page_image_sha256"]
                or item.get("source_page") != report["page_number"]
                or item.get("source_crop_pixel_correspondence_verified") is not False
                or item.get("original_caption_and_panel_semantics_verified") is not False
                or item.get("automatic_composite_or_publication_authorized") is not False
                or item.get("crop_sha256") != _sha(crops_dir / item["crop_file"])):
            raise ValueError("Crop identity or bytes no longer match manifest")
        coords = item.get("bbox_source_pdf_top_left_pt")
        if coords is not None:
            size = item.get("source_page_size_pt")
            if (type(size) is not list or len(size) != 2
                    or not all(type(v) in (int, float) and math.isfinite(v) and v > 0
                               for v in size)
                    or type(coords) is not list or len(coords) != 4
                    or not all(type(v) in (int, float) and math.isfinite(v)
                               for v in coords)
                    or not 0 <= coords[0] < coords[2] <= size[0]
                    or not 0 <= coords[1] < coords[3] <= size[1]
                    or item.get("status") != "DOCLING_SINGLE_SOURCE_RECT_CANDIDATE"):
                raise ValueError("Untrusted declared PDF rectangle")
        elif item.get("status") != "SOURCE_CROP_BBOX_UNVERIFIED":
            raise ValueError("Untrusted missing PDF rectangle")
        indexed[item["crop_file"]] = item
    if set(indexed) != names:
        raise ValueError("Incomplete hashed source-crop identity")
    groups = {}
    for crop, _label, target in mappings:
        if crop not in indexed:
            raise ValueError("Mapping includes crop absent from source provenance")
        groups.setdefault(target.casefold(), []).append((target, crop))
    candidates = []
    for members in groups.values():
        if len(members) <= 1:
            continue
        rects = [(crop, indexed[crop]["bbox_source_pdf_top_left_pt"])
                 for _target, crop in members]
        disjoint = all(rect is not None for _name, rect in rects)
        if disjoint:
            for index, (_name_a, a) in enumerate(rects):
                for _name_b, b in rects[index + 1:]:
                    overlap_w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
                    overlap_h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
                    if overlap_w * overlap_h > 0:
                        disjoint = False
        candidates.append({
            "target": members[0][0],
            "crops": [{"file": crop, "crop_sha256": indexed[crop]["crop_sha256"],
                       "declared_bbox_pdf_pt": indexed[crop]["bbox_source_pdf_top_left_pt"]}
                      for _, crop in members],
            "docling_declared_boxes_nonoverlapping": disjoint,
            "same_author_figure_and_panel_order_verified": False,
            "automatic_merge_authorized": False,
        })
    return {
        "schema_version": 1,
        "status": "HASH_BOUND_DOCLING_GEOMETRY_CANDIDATES_NOT_SEMANTIC_PROOF",
        "source_pdf_sha256": report["original_source_pdf_sha256"],
        "page_image_sha256": report["page_image_sha256"],
        "manifest_sha256": _sha(manifest),
        "duplicate_target_candidates": candidates,
        "original_crop_hashes_verified": True,
        "source_crop_pixel_correspondence_verified": False,
        "same_author_figure_verified": False,
        "automatic_stitch_or_publication_authorized": False,
    }
