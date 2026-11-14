#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crop_figs.py
------------
Extracts and saves figures from source.pdf into pages/page_X/ directories.

This script:
  - Converts each page of source.pdf into both PNG and page-level PDF.
  - Uses Docling to extract figures.
  - Removes small figures (< ikB kB).
  - Produces only image crops (no LLM/API submission).
  
Fig croping is docling-installation dependence. Check and try out which version of docling works.
conda activate docling_3 in yoga hp works. 
"""

from pathlib import Path
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import PictureItem
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from selenium_pipeline.figure_crop_source_provenance import (
    build_crop_geometry_candidate, save_page_crop_geometry,
)

# stdout unicode safe
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')


# --- Configurations ---
## set ikB. PNG image of filesize smaller than ikB kB will be filtered out and not saved.
ikB = 2.55    ### ikb = 2.64 works for Serway v10.  This is the default.
#ikB = 4.9    ### ikb = 4.9 works for Resnick and Halliday.
#ikB = 4.0    ### ikb = 4.0 works for Thomas Calculus 13 ed.

import os
if os.path.isfile('source.pdf'):
    input_doc_path = Path("source.pdf")
else:
    input_doc_path = Path("problems.pdf")    
    
pages_root = Path("pages")
pages_root.mkdir(exist_ok=True)

print("📘 Starting figure extraction from:", input_doc_path)
print(f"⚙️  Minimum image size threshold: {ikB:.2f} kB")

# --- Convert PDF pages to PNGs and page-level PDFs ---
# Each phase is logged before blocking on external PDF/Docling work.
# The owning Windows runner sets PYTHONUNBUFFERED=1 so these lines survive
# a bounded stage timeout and can be classified without another model send.
print("[microgen-phase] LOCAL_FIGURE_PDF_RENDER_START", flush=True)
pdf_pages = convert_from_path(str(input_doc_path), dpi=200)
reader = PdfReader(str(input_doc_path))
print(f"[microgen-phase] LOCAL_FIGURE_PDF_RENDER_DONE pages={len(pdf_pages)}", flush=True)

# Docling's converter can process successive page PDFs. Constructing it
# inside the per-page loop repeatedly reloads costly model/pipeline state.
# Reuse the *same* configured converter, with all original OCR/picture flags.
print("[microgen-phase] LOCAL_FIGURE_DOCLING_INIT_START", flush=True)
pipeline_options = PdfPipelineOptions(
    images_scale=1.5,
    generate_page_images=False,
    generate_picture_images=True,
    do_ocr=False,
    do_table_structure=False,
)
doc_converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)
print("[microgen-phase] LOCAL_FIGURE_DOCLING_READY", flush=True)

for i, (page_image, pdf_page) in enumerate(zip(pdf_pages, reader.pages), start=1):
    page_dir = pages_root / f"page_{i}"
    page_dir.mkdir(exist_ok=True)

    # Save full-page PNG and PDF
    png_path = page_dir / f"page_{i}.png"
    pdf_path = page_dir / f"page_{i}.pdf"
    page_image.save(png_path, "PNG")

    writer = PdfWriter()
    writer.add_page(pdf_page)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    print(f"\n🖼️ Processing {pdf_path.name}...")

    # --- Extract figures using the single cached Docling converter ---
    print(f"[microgen-phase] LOCAL_FIGURE_CROP_PAGE_START page={i}", flush=True)
    try:
        conv_res = doc_converter.convert(pdf_path)
        doc = conv_res.document
        fig_counter = 0
        crop_geometry_candidates = []
        for item, _ in doc.iterate_items():
            if isinstance(item, PictureItem):
                fig_counter += 1
                fig_path = page_dir / f"fig_{fig_counter}.png"
                item.get_image(doc).save(fig_path, "PNG")

                if fig_path.stat().st_size < ikB * 1024:
                    fig_path.unlink()
                    print(f"🗑️ Removed small figure: {fig_path.name}")
                else:
                    print(f"✅ Saved figure: {fig_path.name}")
                    crop_geometry_candidates.append(build_crop_geometry_candidate(
                        picture=item, original_pdf=input_doc_path,
                        page_png=png_path, crop_png=fig_path,
                        page_number=i,
                        page_width_pt=float(pdf_page.mediabox.width),
                        page_height_pt=float(pdf_page.mediabox.height)))
        # Source-space coordinates are candidate-only evidence. Missing or
        # ambiguous Docling provenance MUST NOT be silently inferred from
        # image shapes or from a model-supplied figure number.
        save_page_crop_geometry(
            target=page_dir / f"page_{i}_crop_geometry.json",
            source_pdf=input_doc_path, page_png=png_path,
            records=crop_geometry_candidates, page_number=i)
        if fig_counter == 0:
            print("⚠️  No figures found on this page.")
        print(f"[microgen-phase] LOCAL_FIGURE_CROP_PAGE_DONE page={i}", flush=True)

    except Exception as e:
        # A partial crop page or missing provenance must never turn into a
        # successful figure-extraction receipt or a fresh Gemini mapping Send.
        print(f"❌ Error extracting figures from {pdf_path.name}: {e}", flush=True)
        raise RuntimeError(
            f"LOCAL_FIGURE_CROP_OR_PROVENANCE_FAILED page={i}") from e

print("\n✅ Figure extraction completed successfully.")


###
from pathlib import Path
import shutil

root = Path(".")                       # change if needed
pages_dir = root / "pages"
crops_dir = root / "crops"
crops_dir.mkdir(exist_ok=True)

# Find all page_* folders under pages/
for page_folder in sorted(pages_dir.glob("page_*")):
    if not page_folder.is_dir():
        continue
    # Make matching crops/page_*
    target = crops_dir / page_folder.name
    target.mkdir(parents=True, exist_ok=True)

    # Copy all PNGs from pages/page_* → crops/page_*
    for png in page_folder.glob("*.png"):
        dst = target / png.name
        shutil.copy2(png, dst)
        print(f"Copied: {png} -> {dst}")
    # Preserve the one-page Docling source-space candidate manifest with the
    # actual crop bytes used by the mapping worker, not just in pages/.
    geometry = page_folder / (page_folder.name + "_crop_geometry.json")
    if geometry.is_file() and not geometry.is_symlink():
        dest = target / geometry.name
        if dest.exists():
            if dest.read_bytes() != geometry.read_bytes():
                raise RuntimeError("Existing crop geometry provenance differs")
        else:
            shutil.copy2(geometry, dest)

