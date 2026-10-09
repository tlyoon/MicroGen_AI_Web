#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# MicroGen_AI Educational Automation Package
# © 2025 Dr. Yoon Tiem Leong, School of Physics, Universiti Sains Malaysia.
# This file is part of the MicroGen_AI package.
# Licensed under the MIT License (see LICENSE file in the project root).
# You may not use this file except in compliance with the License.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.


"""
png_dimensions_to_json_v4.py

Scan the current directory for *.png files and generate a JSON file
containing image dimensions plus layout hints for LaTeX / Beamer /
Gemini-based slide generation.

New in v4:
- Also reads slides.pdf if present
- Extracts slide page size
- Adds figure fit recommendations relative to the slide/page size

Usage:
    python png_dimensions_to_json_v4.py

Optional:
    python png_dimensions_to_json_v4.py output_name.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from PIL import Image

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


# ------------------------------------------------------------
# Basic figure classification
# ------------------------------------------------------------
def classify_orientation(width: int, height: int) -> str:
    ratio = width / height
    if ratio > 1.2:
        return "landscape"
    if ratio < 0.8:
        return "portrait"
    return "square"


def classify_figure_category(filename: str, width: int, height: int) -> str:
    name = filename.lower()
    ratio = width / height

    if any(k in name for k in ["charles", "coulomb", "newton", "einstein", "portrait", "photo"]):
        return "portrait_photo"

    if any(k in name for k in ["diagram", "schematic", "circuit", "setup", "apparatus"]):
        return "diagram"

    if any(k in name for k in ["graph", "plot", "chart"]):
        return "graph"

    if "figure" in name:
        if ratio > 1.6:
            return "wide_figure"
        if ratio < 0.75:
            return "tall_figure"
        return "standard_figure"

    return "unknown"


# ------------------------------------------------------------
# Read PDF page size from slides.pdf
# ------------------------------------------------------------
def read_pdf_page_size(pdf_path: Path) -> Optional[Dict[str, Any]]:
    if not pdf_path.exists():
        return None

    if PdfReader is None:
        return {
            "error": "PyPDF2 not installed. Install with: pip install PyPDF2"
        }

    try:
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return {"error": "slides.pdf exists but has no pages"}

        page0 = reader.pages[0]
        mediabox = page0.mediabox

        width_pt = float(mediabox.width)
        height_pt = float(mediabox.height)

        width_in = width_pt / 72.0
        height_in = height_pt / 72.0
        aspect_ratio = width_pt / height_pt if height_pt else None

        return {
            "file": pdf_path.name,
            "page_width_pt": round(width_pt, 3),
            "page_height_pt": round(height_pt, 3),
            "page_width_in": round(width_in, 3),
            "page_height_in": round(height_in, 3),
            "page_aspect_ratio": round(aspect_ratio, 3) if aspect_ratio else None,
        }

    except Exception as e:
        return {"error": str(e)}


# ------------------------------------------------------------
# Compute fit hints relative to slide canvas
# ------------------------------------------------------------
def compute_slide_fit(
    img_width_px: int,
    img_height_px: int,
    slide_width_pt: Optional[float],
    slide_height_pt: Optional[float],
) -> Dict[str, Any]:
    """
    Estimate how much of the slide the image should occupy if fitted
    by width or by height while keeping aspect ratio.

    Since image files are in pixels and PDF pages are in points,
    this is only a relative guidance calculation based on aspect ratios.
    """
    img_ratio = img_width_px / img_height_px

    if not slide_width_pt or not slide_height_pt:
        return {
            "fit_guidance_available": False
        }

    slide_ratio = slide_width_pt / slide_height_pt

    # If fit by width, resulting normalized height fraction is:
    # (slide_width / img_ratio) / slide_height = slide_ratio / img_ratio
    height_fraction_if_fit_width = slide_ratio / img_ratio

    # If fit by height, resulting normalized width fraction is:
    # (img_ratio * slide_height) / slide_width = img_ratio / slide_ratio
    width_fraction_if_fit_height = img_ratio / slide_ratio

    fit_by_width_safe = height_fraction_if_fit_width <= 0.82
    fit_by_height_safe = width_fraction_if_fit_height <= 0.9

    if fit_by_width_safe:
        recommended_fit_mode = "width"
    elif fit_by_height_safe:
        recommended_fit_mode = "height"
    else:
        recommended_fit_mode = "bounded_box"

    return {
        "fit_guidance_available": True,
        "image_aspect_ratio": round(img_ratio, 3),
        "slide_aspect_ratio": round(slide_ratio, 3),
        "height_fraction_if_fit_width": round(height_fraction_if_fit_width, 3),
        "width_fraction_if_fit_height": round(width_fraction_if_fit_height, 3),
        "fit_by_width_safe": fit_by_width_safe,
        "fit_by_height_safe": fit_by_height_safe,
        "recommended_fit_mode": recommended_fit_mode,
    }


# ------------------------------------------------------------
# LaTeX / Beamer recommendation
# ------------------------------------------------------------
def determine_latex_settings(
    width: int,
    height: int,
    category: str,
    slide_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ratio = width / height
    orientation = classify_orientation(width, height)

    slide_width_pt = None
    slide_height_pt = None
    if slide_info and "page_width_pt" in slide_info and "page_height_pt" in slide_info:
        slide_width_pt = slide_info["page_width_pt"]
        slide_height_pt = slide_info["page_height_pt"]

    fit_info = compute_slide_fit(width, height, slide_width_pt, slide_height_pt)

    suggested_width = None
    suggested_height = None
    suggested_option = None
    beamer_scale = None
    recommended_columns_layout = None

    if category == "portrait_photo":
        suggested_height = "0.68\\textheight"
        suggested_option = f"height={suggested_height}"
        beamer_scale = 0.68
        recommended_columns_layout = "two_columns"

    elif category == "graph":
        suggested_width = "0.78\\textwidth"
        suggested_option = f"width={suggested_width}"
        beamer_scale = 0.78
        recommended_columns_layout = "single_column"

    elif category == "diagram":
        suggested_width = "0.82\\textwidth"
        suggested_option = f"width={suggested_width}"
        beamer_scale = 0.82
        recommended_columns_layout = "single_column"

    elif orientation == "landscape":
        if ratio > 2.0:
            suggested_width = "0.92\\textwidth"
            beamer_scale = 0.92
        else:
            suggested_width = "0.85\\textwidth"
            beamer_scale = 0.85
        suggested_option = f"width={suggested_width}"
        recommended_columns_layout = "single_column"

    elif orientation == "portrait":
        suggested_height = "0.70\\textheight"
        suggested_option = f"height={suggested_height}"
        beamer_scale = 0.70
        recommended_columns_layout = "two_columns"

    else:
        suggested_width = "0.62\\textwidth"
        suggested_option = f"width={suggested_width}"
        beamer_scale = 0.62
        recommended_columns_layout = "single_column"

    # Refine based on slide-fit analysis
    if fit_info.get("fit_guidance_available"):
        mode = fit_info["recommended_fit_mode"]

        if mode == "height" and orientation in {"portrait", "square"}:
            suggested_height = "0.68\\textheight"
            suggested_width = None
            suggested_option = f"height={suggested_height}"
        elif mode == "bounded_box":
            suggested_option = "width=0.82\\textwidth,height=0.68\\textheight,keepaspectratio"
            suggested_width = "0.82\\textwidth"
            suggested_height = "0.68\\textheight"

    return {
        "aspect_ratio": round(ratio, 3),
        "orientation": orientation,
        "suggested_latex_width": suggested_width,
        "suggested_latex_height": suggested_height,
        "suggested_latex_option": suggested_option,
        "suggested_beamer_scale": beamer_scale,
        "recommended_columns_layout": recommended_columns_layout,
        "slide_fit": fit_info,
    }


# ------------------------------------------------------------
# Build record for one PNG
# ------------------------------------------------------------
def build_record(png_file: Path, slide_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    with Image.open(png_file) as img:
        width, height = img.size

    category = classify_figure_category(png_file.name, width, height)
    latex_info = determine_latex_settings(width, height, category, slide_info)

    record: Dict[str, Any] = {
        "width_px": width,
        "height_px": height,
        "figure_category": category,
        **latex_info,
        "latex_example": (
            f"\\includegraphics[{latex_info['suggested_latex_option']}]"
            f"{{{png_file.name}}}"
        ),
    }
    return record


# ------------------------------------------------------------
# Scan directory
# ------------------------------------------------------------
def scan_png_files(folder: Path) -> Dict[str, Any]:
    png_files = sorted(folder.glob("*.png"))
    slide_info = read_pdf_page_size(folder / "slides.pdf")

    data: Dict[str, Any] = {
        "directory": str(folder.resolve()),
        "unit": "pixels",
        "generator": "png_dimensions_to_json_v4.py",
        "purpose": (
            "Image metadata for Gemini / LaTeX / Beamer slide generation. "
            "Use as layout hints, not strict rules."
        ),
        "slide_reference": slide_info,
        "files": {}
    }

    for png_file in png_files:
        try:
            data["files"][png_file.name] = build_record(png_file, slide_info)
        except Exception as e:
            data["files"][png_file.name] = {"error": str(e)}

    return data


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main() -> None:
    current_dir = Path.cwd()

    if len(sys.argv) > 1:
        out_json = Path(sys.argv[1])
    else:
        out_json = current_dir / "png_dimensions.json"

    data = scan_png_files(current_dir)

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Current directory : {current_dir}")
    print(f"[INFO] PNG files scanned : {len(data['files'])}")
    print(f"[INFO] JSON written to  : {out_json.resolve()}")

    slide_ref = data.get("slide_reference", {})
    if isinstance(slide_ref, dict) and "error" not in slide_ref and slide_ref:
        print(
            "[INFO] Slide reference  : "
            f"{slide_ref.get('file')} "
            f"({slide_ref.get('page_width_in')} in x {slide_ref.get('page_height_in')} in)"
        )
    elif isinstance(slide_ref, dict) and "error" in slide_ref:
        print(f"[WARN] Slide reference  : {slide_ref['error']}")


if __name__ == "__main__":
    main()