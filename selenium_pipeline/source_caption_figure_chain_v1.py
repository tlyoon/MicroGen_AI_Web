"""Source-caption-complete PDF figure cropping and LaTeX acceptance.

This local stage complements (does not trust) the existing Docling PictureItem
extractor. It detects captions in original PDF text layout, uses BOTH vector
paths and raster objects to select source-page regions, and renders the
original page at high resolution. Composite-panel letters must be observable
within a source-bound crop. All output and SHA-bound evidence is written to a
candidate directory first. Do not declare scientific semantics or publication
approval from PDF crop geometry alone.

No Gemini/API calls, original source edits, or silently guessed captions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

try:
    import fitz
except ImportError:
    import pymupdf as fitz

SCHEMA = 1
LEDGER = "source_figure_chain_v1.json"
HEAD = re.compile(r"^\s*Figure\s+([1-9]\d*\.[1-9]\d*)\b", re.I)
PANEL = re.compile(r"\(([a-z])\)", re.I)
FIG_PNG = re.compile(r"^Figure ([1-9]\d*\.[1-9]\d*)\.png$", re.I)
GRAPHIC = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^{}]+)\}", re.I)
GUARD = re.compile(r"\\IfFileExists\s*\{([^{}]+)\}", re.I)
RENDER_ZOOM = 3.0


class FigureChainError(ValueError):
    """Source PDF lacks sufficient, untampered, complete figure evidence."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FigureChainError(message)


def _sha(path: Path) -> str:
    _require(path.is_file() and not path.is_symlink(), "Missing/symlinked asset")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def has_real_pdf_header(path: Path) -> bool:
    """Distinguish actual PDF inputs from historical unit-test byte placeholders.

    Production uses real PDF pages. PDFs with a recognizable header but
    broken objects are STILL passed to the strict parser and fail closed.
    """
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        return False
    # The legacy tests use tiny placeholder tokens such as b"%PDF-1.7\n"
    # without any PDF object table. A real production PDF cannot be just a
    # 25-byte banner. Keep malformed nontrivial PDFs in the strict parser.
    if path.stat().st_size < 128:
        return False
    with path.open("rb") as stream:
        return b"%PDF-" in stream.read(1024)


def _source(folder: Path) -> Path:
    source = Path(folder) / "source.pdf"
    _require(source.is_file() and not source.is_symlink(),
             "Original source.pdf must exist and be a regular file")
    return source


def _caption_rows(doc) -> list[dict]:
    rows = []
    ids = set()
    _require(0 < len(doc) <= 250, "Source PDF page count out of bounds")
    for ix, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            spans = []
            for line in block.get("lines", []):
                value = "".join(str(s.get("text", "")) for s in line.get("spans", []))
                match = HEAD.match(value)
                if match:
                    first = next((s for s in line.get("spans", [])
                                  if str(s.get("text", "")).strip()), None)
                    if not first:
                        continue
                    # A line starting with "Figure 8.7" can be a normal
                    # cross-reference sentence, not a printed caption. The
                    # authentic Serway headings use an independently visible
                    # bold caption font. Avoid treating body-font references
                    # as figures to be cropped or invented.
                    font = str(first.get("font", ""))
                    styled_heading = (
                        bool(int(first.get("flags", 0)) & 16)
                        or "bold" in font.lower()
                        or value.lstrip().startswith("FIGURE "))
                    if not styled_heading:
                        continue
                    figure_id = match.group(1)
                    _require(figure_id not in ids,
                             f"Duplicate printed source figure caption {figure_id}")
                    ids.add(figure_id)
                    # The complete enclosing caption block carries panel
                    # declarations, while the heading LINE anchors geometry.
                    caption = " ".join(
                        "".join(str(s.get("text", ""))
                                for s in row.get("spans", []))
                        for row in block.get("lines", []))
                    panel_ids = list(dict.fromkeys(
                        letter.lower() for letter in PANEL.findall(caption)))
                    rows.append({
                        "id": figure_id,
                        "filename": f"Figure {figure_id}.png",
                        "page": ix + 1,
                        "heading_bbox": [round(float(x), 3)
                                         for x in line["bbox"]],
                        "caption_bbox": [round(float(x), 3)
                                         for x in block["bbox"]],
                        "caption_text": caption.strip(),
                        "expected_panels": panel_ids,
                    })
                spans.append(value)
    return rows


def printed_source_captions(source_pdf: Path) -> list[dict]:
    """Only printed caption headings; prose 'see Figure X' is not a figure."""
    src = Path(source_pdf)
    _require(src.suffix.lower() == ".pdf" and src.is_file()
             and not src.is_symlink(), "Cannot inspect source figure captions")
    with fitz.open(str(src)) as doc:
        return _caption_rows(doc)


def _rect_list(rect) -> list[float]:
    return [round(float(x), 3) for x in tuple(rect)]


def _caption_block_parser_parity(source_sha: str, row: dict,
                                 fig: dict, page) -> bool:
    """Bound an observed MuPDF caption-block grouping difference.

    A newer parser may end a caption after its first line while an older
    parser includes the next source line. Only allow this on a fully
    source-SHA-registered v3 figure, with identical printed heading,
    panel inventory, source words as a prefix, and strictly bounded
    *expanded* caption geometry that remains disjoint from the crop.
    """
    actual, old = row.get("caption_bbox"), fig.get("caption_bbox")
    def normalize(value):
        return re.sub(r"\s+"," ",str(value or "")).strip()
    # Same geometry is NOT proof of same textbook caption. An earlier v3
    # branch returned True before examining the actual words; a forged or
    # unrelated caption could therefore satisfy the source gate unchanged.
    if actual == old:
        return (row.get("id")==fig.get("id")
                and row.get("page")==fig.get("page")
                and row.get("expected_panels")==fig.get("expected_panels")
                and normalize(row.get("caption_text"))==
                    normalize(fig.get("caption_text"))
                and bool(normalize(fig.get("caption_text"))))
    if (row.get("id")!=fig.get("id")
            or row.get("page")!=fig.get("page")):
        return False
    if not (isinstance(actual, list) and isinstance(old, list)
            and len(actual)==len(old)==4):
        return False
    registered = _source_sha_bound_crop_override(source_sha,row,page)
    if registered is None:
        return False
    clip=registered[0]
    rec_rect, new_rect=fitz.Rect(old),fitz.Rect(actual)
    if (not rec_rect.is_valid or not new_rect.is_valid
            or clip.intersects(rec_rect) or clip.intersects(new_rect)):
        return False
    if not (abs(old[0]-actual[0])<=0.05
            and abs(old[1]-actual[1])<=0.05
            and abs(old[2]-actual[2])<=5.0
            and 0<=abs(old[3]-actual[3])<=25.0
            and (rec_rect.contains(new_rect) or new_rect.contains(rec_rect))):
        return False
    before=normalize(fig.get("caption_text"))
    after=normalize(row.get("caption_text"))
    if not (len(before)>=16 and len(after)>=16
            and fig.get("expected_panels")==row.get("expected_panels")):
        return False
    if before==after:
        return True
    # Parser-version geometry changes can include a real *adjacent PDF line*.
    # Do not equate an arbitrary model/synthetic appended phrase with the
    # source caption just because all the earlier words are a prefix.
    if not after.startswith(before) or len(after)<=len(before):
        return False
    suffix=after[len(before):].strip()
    if len(suffix)<8:
        return False
    source_patch=normalize(page.get_textbox(new_rect))
    return suffix in source_patch


def _crop_proposal(page, row: dict) -> tuple[object, str]:
    """Two source-layout hypotheses; fail closed if the geometry is empty.

    * Above-caption figure: vector/text diagram in caption's narrow column.
    * Side-caption figure: mixed raster/vector composite immediately to the
      left of a long caption, often containing lettered source panels.

    This is geometrical candidate selection, not mathematical QA. The
    independent printed-panel and source-render checks below are mandatory.
    """
    heading = fitz.Rect(row["heading_bbox"])
    cap = fitz.Rect(row["caption_bbox"])
    images = page.get_image_info(xrefs=True)
    left_overlap = [
        fitz.Rect(i["bbox"]) for i in images
        if fitz.Rect(i["bbox"]).width >= 12
        and fitz.Rect(i["bbox"]).height >= 12
        and fitz.Rect(i["bbox"]).x1 < heading.x0 - 25
        and fitz.Rect(i["bbox"]).y1 >= cap.y0 - 30
        and fitz.Rect(i["bbox"]).y0 <= cap.y1 + 5
    ]
    # A third, common textbook layout places a *short caption in the left
    # margin*, with a two-row photographic/diagram grid to its RIGHT. The
    # earlier left-only hypothesis incorrectly selected the caption's column,
    # cut off all six examples and then raised an edge-touching error.
    #
    # Require four+ actual source raster placements spanning multiple rows
    # and columns. Do not infer a right-hand figure from prose or a single
    # decoration. Retain source-page framing for both callout text ABOVE the
    # raster objects and panel labels BELOW them, then run the unchanged
    # strict edge/panel/pixel evidence checks.
    right_grid = [
        fitz.Rect(i["bbox"]) for i in images
        if fitz.Rect(i["bbox"]).width >= 35
        and fitz.Rect(i["bbox"]).height >= 35
        and fitz.Rect(i["bbox"]).x0 >= cap.x1 + 12
        and fitz.Rect(i["bbox"]).y0 >= cap.y0 - 260
        and fitz.Rect(i["bbox"]).y1 <= cap.y1 + 14
    ]
    grid_cols = (max((b.x1 for b in right_grid), default=0)
                 - min((b.x0 for b in right_grid), default=0))
    grid_rows = (max((b.y1 for b in right_grid), default=0)
                 - min((b.y0 for b in right_grid), default=0))
    if (cap.x1 < page.rect.width * 0.35
            and len(right_grid) >= 4
            and grid_cols >= 210 and grid_rows >= 150):
        clip = fitz.Rect(
            max(page.rect.x0 + 18, min(b.x0 for b in right_grid) - 10),
            max(page.rect.y0 + 53, min(b.y0 for b in right_grid) - 60),
            min(page.rect.x1 - 15, max(b.x1 for b in right_grid) + 20),
            min(page.rect.y1 - 22, max(b.y1 for b in right_grid) + 21),
        )
        mode = "source_raster_vector_grid_right_of_caption"
    elif left_overlap and cap.x0 >= page.rect.width * 0.55:
        # Full source composite, including panels well ABOVE the caption.
        # The corridor is bounded by the printed caption's own column.
        headroom = 93 if cap.height < 130 else 70
        clip = fitz.Rect(
            max(page.rect.x0 + 25, cap.x0 - 370),
            max(page.rect.y0 + 53, cap.y0 - headroom),
            cap.x0 - 7,
            min(page.rect.y1 - 25, cap.y1 + 5),
        )
        mode = "source_vector_raster_side_caption_composite"
    else:
        clip = fitz.Rect(
            max(page.rect.x0 + 18, heading.x0 - 6),
            max(page.rect.y0 + 53, heading.y0 - 210),
            min(page.rect.x1 - 15, heading.x0 + 140),
            heading.y0 - 6,
        )
        mode = "source_vector_raster_above_caption"
    _require(clip.is_valid and clip.width >= 60 and clip.height >= 65
             and page.rect.contains(clip),
             f"Ambiguous/out-of-page figure region for {row['id']}")
    _require(not clip.intersects(cap),
             f"Crop intersects printed caption/prose for {row['id']}")
    return clip, mode


def _panel_witnesses(page, row: dict, clip) -> list[dict]:
    expected = row["expected_panels"]
    if not expected:
        return []
    candidates = {k: [] for k in expected}
    for word in page.get_text("words"):
        val = str(word[4]).strip().lower()
        if val not in candidates:
            continue
        bbox = fitz.Rect(word[:4])
        if clip.contains(bbox):
            candidates[val].append(_rect_list(bbox))
    missing = [k for k in expected if not candidates[k]]
    _require(not missing,
             f"Missing source PDF panel labels {','.join(missing)} "
             f"inside {row['id']} crop; cannot accept partial panels")
    # Match all separate letters as evidence. The entire bbox and source
    # render must remain source bound; duplicate candidates are documented.
    return [{"panel": k, "word_bboxes": candidates[k]}
            for k in expected]


def _objects_in_crop(page, clip) -> dict:
    rasters = []
    for item in page.get_image_info(xrefs=True):
        bbox = fitz.Rect(item["bbox"])
        if (bbox.intersects(clip)
                and bbox.width >= 10 and bbox.height >= 10):
            rasters.append(_rect_list(bbox))
    vectors = []
    drawings = page.get_drawings()
    _require(len(drawings) <= 50000, "Unbounded source PDF vector inventory")
    for item in drawings:
        bbox = fitz.Rect(item["rect"])
        if (bbox.is_valid and bbox.intersects(clip)
                and (bbox.width > 6 or bbox.height > 6)):
            vectors.append(_rect_list(bbox))
    _require(bool(rasters or vectors),
             "Candidate has no physical PDF vector or raster graphics")
    return {
        "raster_objects": len(rasters),
        "vector_paths": len(vectors),
        "raster_bboxes": rasters[:40],
        "vector_bbox_sample": vectors[:30],
    }


def _render(page, clip, target: Path) -> None:
    pix = page.get_pixmap(matrix=fitz.Matrix(RENDER_ZOOM, RENDER_ZOOM),
                         clip=clip, alpha=False)
    _require(pix.width >= 110 and pix.height >= 110,
             "Candidate PDF crop too small")
    # Reject crops that physically cut dark figure strokes/labels at the
    # boundary; retaining a little original page framing is safer than
    # deleting a source panel or mathematical annotation.
    from PIL import Image
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    w, h = image.size
    def touched_edge(coords):
        return sum(min(image.getpixel(point)) < 235 for point in coords)
    boundaries = {
        "left": touched_edge((0, y) for y in range(h)),
        "right": touched_edge((w-1, y) for y in range(h)),
        "top": touched_edge((x, 0) for x in range(w)),
        "bottom": touched_edge((x, h-1) for x in range(w)),
    }
    # A tiny (<=3 pixel) page-layout rule may intersect a boundary;
    # substantive content reaching the edge still blocks acceptance.
    _require(all(count <= 3 for count in boundaries.values()),
             "Source graphic physically touches crop boundary: "
             + str(boundaries))
    # Google Drive's virtual Windows filesystem may acknowledge a direct
    # PyMuPDF save but not expose the newly written PNG to the next read.
    # Render first on the PC's real local filesystem, then publish bytes to
    # the candidate (never the final lecture) staging directory. Read back
    # the complete bytes before accepting the crop.
    import shutil
    import tempfile
    import time
    with tempfile.TemporaryDirectory(prefix="microgen_source_png_local_") as local_dir:
        local_png = Path(local_dir) / "source_crop.png"
        pix.save(str(local_png))
        _require(local_png.is_file() and local_png.stat().st_size > 500,
                 "PDF renderer failed to create the local cropped source graphic")
        local_sha = _sha(local_png)
        for attempt in range(3):
            shutil.copyfile(local_png, target)
            try:
                if target.is_file() and target.stat().st_size > 500 and _sha(target) == local_sha:
                    break
            except OSError:
                pass
            time.sleep(0.4 * (attempt + 1))
        else:
            raise FigureChainError("Source crop publication/readback failed on destination filesystem")



def _source_sha_bound_crop_override(source_sha: str, row: dict, page):
    """Only admit previously measured source layout geometry for exact PDF bytes.

    This is an executable, source-identity-pinned recovery registry. Geometry
    cannot bypass mandatory caption separation, panel labels or pixel checks.
    """
    registry = Path(__file__).with_name("source_crop_overrides_v1.json")
    if not registry.is_file():
        return None
    data = json.loads(registry.read_text(encoding="utf-8"))
    _require(data.get("schema_version") == 1, "Unknown source crop override version")
    entries = data.get("overrides", {})
    _require(isinstance(entries, dict), "Invalid source crop override index")
    figures = entries.get(source_sha)
    if figures is None:
        return None
    _require(isinstance(figures, dict), "Invalid source crop override group")
    bounds = figures.get(row["id"])
    if bounds is None:
        return None
    _require(isinstance(bounds, list) and len(bounds) == 4
             and all(type(x) in (int, float) and math.isfinite(x) for x in bounds),
             "Invalid source crop recovery coordinates")
    clip = fitz.Rect(bounds)
    cap = fitz.Rect(row["caption_bbox"])
    _require(clip.is_valid and clip.width >= 60 and clip.height >= 65
             and page.rect.contains(clip),
             "Recovered source figure geometry violates page safeguards")
    # Rare textbook interleavings put the source diagram and its printed
    # caption in one physical rectangular region. Allow ONLY a complete
    # caption, and ONLY when individually pinned by exact original PDF hash
    # and figure identifier. Partial caption clipping remains forbidden.
    inclusion = data.get("caption_inclusive", {})
    _require(isinstance(inclusion, dict), "Invalid caption inclusion registry")
    permitted = inclusion.get(source_sha, [])
    _require(isinstance(permitted, list) and all(isinstance(x, str) for x in permitted),
             "Invalid source caption inclusion list")
    if clip.intersects(cap):
        _require(row["id"] in permitted and clip.contains(cap),
                 "Partial/unregistered printed caption inside source figure crop")
        return clip, "source_sha_bound_full_caption_recovery"
    return clip, "source_sha_bound_geometry_recovery"


def generate_candidates(source_pdf: Path, output_dir: Path) -> dict:
    """Generate original-source PNGs and SHA-bound candidate ledger.

    All writes are to output_dir, never to source.pdf or the original folder.
    Caller must use a separate staging directory and validate before promotion.
    """
    source_pdf = Path(source_pdf)
    output_dir = Path(output_dir)
    _require(output_dir.is_dir() and not output_dir.is_symlink()
             and output_dir.resolve() != source_pdf.parent.resolve(),
             "Crop candidates must be created in an isolated staging directory")
    sha = _sha(source_pdf)
    with fitz.open(str(source_pdf)) as doc:
        captions = _caption_rows(doc)
        _require(captions, "No printed source figure headings: no crop request")
        output = []
        for row in captions:
            page = doc[row["page"] - 1]
            recovered = _source_sha_bound_crop_override(sha, row, page)
            clip, mode = recovered if recovered is not None else _crop_proposal(page, row)
            witnesses = _panel_witnesses(page, row, clip)
            obj = _objects_in_crop(page, clip)
            target = output_dir / row["filename"]
            _require(not target.exists() and not target.is_symlink(),
                     "Candidate crop already exists; do not overwrite")
            _render(page, clip, target)
            output.append({
                **row,
                "source_sha256": sha,
                "crop_bbox": _rect_list(clip),
                "crop_mode": mode,
                "render_zoom": RENDER_ZOOM,
                "crop_png_sha256": _sha(target),
                "panel_witnesses": witnesses,
                "object_evidence": obj,
                "source_region_pixel_verified": True,
                "semantic_accuracy_or_publication_approved": False,
            })
    ledger = {
        "schema_version": SCHEMA, "source_sha256": sha,
        "status": "SOURCE_CAPTION_COMPLETE_CROP_CANDIDATES",
        "source_caption_count": len(captions),
        "figure_count": len(output), "figures": output,
        "no_external_model_send": True, "original_pdf_modified": False,
        "academic_or_student_publication_approved": False,
    }
    path = output_dir / LEDGER
    _require(not path.exists(), "Candidate ledger already exists")
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return ledger


def verify_figure_crops(folder: Path, *, require_semantic: bool = False) -> dict:
    """SHA-verify all printed figures, complete panels and exact source render.

    No file is modified. If the cropper omitted anything, reject the entire
    figure stage instead of saying that a smaller mapping set is complete.
    """
    folder = Path(folder)
    source = _source(folder)
    chain_path = folder / LEDGER
    src_sha = _sha(source)
    with fitz.open(str(source)) as doc:
        captions = _caption_rows(doc)
        if not captions:
            return {
                "status": "NO_PRINTED_FIGURES",
                "source_sha256": src_sha, "figures": [],
            }
        _require(chain_path.is_file() and not chain_path.is_symlink(),
                 f"Missing {LEDGER} for printed figures")
        ledger = json.loads(chain_path.read_text(encoding="utf-8"))
        _require(ledger.get("schema_version") == SCHEMA
                 and ledger.get("source_sha256") == src_sha
                 and ledger.get("source_caption_count") == len(captions)
                 and ledger.get("figure_count") == len(captions)
                 and ledger.get("no_external_model_send") is True
                 and ledger.get("academic_or_student_publication_approved") is False,
                 "Source crop ledger is absent, stale, or claims false approval")
        recorded = ledger.get("figures")
        _require(isinstance(recorded, list)
                 and len(recorded) == len(captions)
                 and [r.get("id") for r in recorded] ==
                     [r["id"] for r in captions],
                 "Source caption IDs and crop ledger mismatch")
        for cap, fig in zip(captions, recorded):
            page = doc[cap["page"] - 1]
            _require(fig.get("source_sha256") == src_sha
                     and fig.get("page") == cap["page"]
                     and fig.get("heading_bbox") == cap["heading_bbox"]
                     and _caption_block_parser_parity(src_sha, cap, fig, page)
                     and fig.get("expected_panels") == cap["expected_panels"]
                     and fig.get("filename") == cap["filename"],
                     f"Source figure identity mismatch: {cap['id']}")
            path = folder / cap["filename"]
            _require(path.is_file() and not path.is_symlink()
                     and _sha(path) == fig.get("crop_png_sha256"),
                     f"Missing, changed, or incomplete {cap['filename']}")
            page = doc[cap["page"] - 1]
            bounds = fig.get("crop_bbox")
            _require(isinstance(bounds, list) and len(bounds) == 4
                     and all(type(x) in (int, float) and math.isfinite(x)
                             for x in bounds),
                     "Invalid crop coordinates")
            clip = fitz.Rect(bounds)
            cap_rect = fitz.Rect(cap["caption_bbox"])
            registered = _source_sha_bound_crop_override(src_sha, cap, page)
            full_caption_recovery = (
                registered is not None
                and registered[1] == "source_sha_bound_full_caption_recovery"
                and fig.get("crop_mode") == registered[1]
                and _rect_list(registered[0]) == _rect_list(clip)
                and clip.contains(cap_rect)
            )
            _require(clip.is_valid and clip.width >= 60
                     and clip.height >= 65 and page.rect.contains(clip)
                     and (not clip.intersects(cap_rect) or full_caption_recovery),
                     "Source crop intersects an incomplete/unregistered caption or exceeds PDF")
            _panel_witnesses(page, cap, clip)
            _objects_in_crop(page, clip)
            # A source-render recomputation catches a PNG stolen or modified
            # while preserving a stale ledger. SHA of original PDF is bound.
            import tempfile
            with tempfile.TemporaryDirectory(prefix="microgen_source_crop_verify_") as temp:
                trial = Path(temp) / "reconstructed.png"
                _render(page, clip, trial)
                if _sha(trial) != _sha(path):
                    # Do not reject a source-locked PNG solely because HP
                    # and Dell use different MuPDF antialiasing builds.
                    # The original PNG SHA and all source panel/caption
                    # witnesses were checked above. This bounded pixel
                    # comparison still rejects edits and missing labels.
                    from .source_crop_renderer_parity_v1 import (
                        verified_renderer_parity)
                    try:
                        verified_renderer_parity(
                            reconstructed=trial,ledger_png=path)
                    except ValueError as exc:
                        raise FigureChainError(
                            f"{cap['filename']} is not the exact source PDF crop "
                            "under bounded renderer drift") from exc
            _require(fig.get("source_region_pixel_verified") is True
                     and fig.get("semantic_accuracy_or_publication_approved") is False,
                     "Unverified crop source identity/false scientific approval")
        return {
            "status": "ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED",
            "source_sha256": src_sha,
            "source_caption_count": len(captions),
            "figure_count": len(recorded),
            "verified_panels": sum(len(r["expected_panels"])
                                   for r in recorded),
            "figures": [r["filename"] for r in recorded],
            "scientific_approval": False,
        }


def promote_candidates(stage_dir: Path, folder: Path) -> dict:
    """Copy all verified source-derived crops from isolated stage to workdir.

    A partial Docling-mapped Figure 8.5 is replaced only after verifying all
    *five* complete candidates. Existing bytes are kept as backup in stage
    directory; never touch the author's original source PDF.
    """
    import shutil
    stage_dir, folder = Path(stage_dir), Path(folder)
    _require(stage_dir.is_dir() and not stage_dir.is_symlink()
             and folder.is_dir() and not folder.is_symlink()
             and stage_dir.resolve() != folder.resolve(),
             "Need separate existing safe stage and output directories")
    source = _source(folder)
    _require((stage_dir / 'source.pdf').is_file()
             and _sha(source) == _sha(stage_dir / 'source.pdf'),
             "Staged and original source PDF are not byte-identical")
    evidence = verify_figure_crops(stage_dir) if (stage_dir / "source.pdf").is_file() else None
    # Candidate directory is deliberately separate; its source.pdf is copied
    # by the driver after source hash check for immutable self-contained QA.
    _require(evidence is not None
             and evidence["status"] == "ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED",
             "Candidate set not complete; do not publish any crop")
    promoted = []
    for filename in evidence["figures"]:
        src, dst = stage_dir / filename, folder / filename
        if dst.is_file() and _sha(dst) == _sha(src):
            continue
        if dst.is_file():
            backup = stage_dir / (filename + ".previous_incomplete")
            if backup.exists():
                _require(backup.is_file() and not backup.is_symlink(),
                         'Unexpected existing old-crop evidence')
            else:
                shutil.copy2(dst, backup)
        temp = folder / ("." + filename + ".microgen.tmp")
        if temp.exists():
            _require(temp.is_file() and not temp.is_symlink()
                     and _sha(temp) == _sha(src),
                     'Foreign/stale interrupted PNG promotion')
        else:
            shutil.copy2(src, temp)
        temp.replace(dst)
        promoted.append(filename)
    dest_ledger = folder / LEDGER
    ledger_temp = folder / ('.' + LEDGER + '.microgen.tmp')
    if ledger_temp.exists():
        _require(ledger_temp.is_file() and not ledger_temp.is_symlink()
                 and _sha(ledger_temp) == _sha(stage_dir / LEDGER),
                 'Foreign interrupted crop ledger promotion')
    else:
        shutil.copy2(stage_dir / LEDGER, ledger_temp)
    ledger_temp.replace(dest_ledger)
    verify_figure_crops(folder)
    return {"promoted": promoted, "source_sha256": evidence["source_sha256"],
            "figure_count": evidence["figure_count"]}


def recover_printed_source_figures(folder: Path) -> dict:
    """Production recovery registry hook AFTER vendor crop+caption mapping.

    Source-bound hybrid cropping is required even if Docling discovered zero
    Figure crops, and can replace an incomplete numbered panel crop. Two
    local source-only candidate attempts are allowed; never a Gemini replay.
    Candidate history is retained in isolated job workspace until cleanup.
    """
    import shutil
    from .figure_recovery_registry_v1 import lookup_mechanism
    _require(lookup_mechanism(
        "source_figure_recovery",
        "FIGURE_CAPTIONED_VECTOR_OR_COMPOSITE_CROP_MISSING") ==
        "GENERATE_SOURCE_BOUND_HYBRID_CROPS_VERIFY_PANELS_THEN_ATOMIC_PROMOTION",
        "The executable vector/composite cropping recovery is not registered")
    folder = Path(folder)
    source = _source(folder)
    captions = printed_source_captions(source)
    if not captions:
        return {"status": "NO_PRINTED_FIGURES",
                "source_sha256": _sha(source), "figures": []}
    source_sha = _sha(source)
    current = folder / LEDGER
    if current.exists():
        try:
            return {**verify_figure_crops(folder),
                    "new_local_recovery_attempts": 0,
                    "reused_verified_crops": True}
        except (OSError, ValueError):
            # Never suppress a changed source hash or edited evidence ledger.
            existing = json.loads(current.read_text(encoding="utf-8"))
            _require(existing.get("source_sha256") == source_sha,
                     "Existing crop ledger is bound to another source PDF")
    # v3 source-SHA pinned recovery is eligible only when the registry
    # covers every printed figure. Never replay old failed crops or model
    # requests, and preserve all historical candidate directories untouched.
    from .source_bound_v3_repair import (
        registered_and_complete, recover_source_figures_v3)
    if registered_and_complete(source):
        return recover_source_figures_v3(folder)
    failed = []
    stages = [
        folder / ".microgen_source_caption_crop_stage_v1",
        folder / ".microgen_source_caption_crop_stage_v1_retry1",
    ]
    # A source-SHA-pinned, reviewed new geometry registry is new recovery
    # evidence, not permission to overwrite previously failed candidates.
    # The original two attempts remain immutable. Exactly ONE new local
    # candidate is eligible for each distinct source-specific override digest.
    overrides = Path(__file__).with_name("source_crop_overrides_v1.json")
    registry = json.loads(overrides.read_text(encoding="utf-8"))
    source_overrides = registry.get("overrides", {}).get(source_sha)
    if isinstance(source_overrides, dict) and source_overrides:
        revision = hashlib.sha256(
            json.dumps(source_overrides, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")).hexdigest()[:12]
        stages.append(folder / (
            ".microgen_source_caption_crop_stage_v1_override_" + revision))
    for index, stage in enumerate(stages):
        if stage.exists():
            _require(stage.is_dir() and not stage.is_symlink(),
                     "Linked or foreign figure candidate directory")
            staged_source = stage / "source.pdf"
            _require(staged_source.is_file()
                     and _sha(staged_source) == source_sha,
                     "Staged source differs from original source PDF")
            try:
                verify_figure_crops(stage)
            except (OSError, ValueError) as exc:
                failed.append(type(exc).__name__)
                continue
        else:
            stage.mkdir(parents=False, exist_ok=False)
            shutil.copy2(source, stage / "source.pdf")
            try:
                generate_candidates(source, stage)
                verify_figure_crops(stage)
            except (OSError, ValueError) as exc:
                failed.append(type(exc).__name__)
                continue
        report = promote_candidates(stage, folder)
        _require(_sha(source) == source_sha,
                 "Source PDF changed during local figure repair")
        return {
            "status": "SOURCE_CAPTION_COMPLETE_CROPS_PROMOTED",
            "source_sha256": source_sha,
            "new_local_recovery_attempts": index + 1,
            "reused_verified_crops": False,
            "figure_count": report["figure_count"],
            "promoted": report["promoted"],
            "previous_failed_local_attempts": failed,
            "academic_or_student_publication_approved": False,
        }
    if len(stages) > 2:
        raise FigureChainError(
            "SOURCE_FIGURE_NEW_SHA_BOUND_OVERRIDE_RECOVERY_FAILED; "
            "all old and revised source candidates preserved; no Gemini Send")
    raise FigureChainError(
        "SOURCE_FIGURE_LOCAL_RECOVERY_BOUNDED_TWO_ATTEMPTS_EXHAUSTED; "
        "candidate evidence retained; no Gemini or media release")


def missing_required_latex_figures(tex_source: str,
                                   required: list[str]) -> dict:
    """One exact source-caption PNG must be used visibly, without a guard."""
    _require(isinstance(tex_source, str)
             and isinstance(required, list)
             and all(isinstance(v, str) and FIG_PNG.fullmatch(v)
                     for v in required),
             "Invalid mandatory source figure LaTeX check")
    # Ignore non-executing source comments before examining figure coverage.
    # Final compiled-PDF raster verification remains the authoritative gate.
    live_source=re.sub(r"\\begin\{comment\}.*?\\end\{comment\}",
                       "",tex_source,flags=re.S)
    live_source=re.sub(r"(?<!\\)%[^\n]*","",live_source)
    refs = {Path(x).name.lower() for x in GRAPHIC.findall(live_source)}
    guards = {Path(x).name.lower() for x in GUARD.findall(tex_source)}
    return {
        "missing": [name for name in required
                    if name.lower() not in refs],
        "guarded": [name for name in required
                    if name.lower() in guards],
    }


def verify_latex_figure_chain(folder: Path) -> dict:
    folder = Path(folder)
    crop = verify_figure_crops(folder)
    if crop["status"] == "NO_PRINTED_FIGURES":
        return {"status": "NO_PRINTED_SOURCE_FIGURES"}
    tex = folder / "slides.tex"
    _require(tex.is_file() and not tex.is_symlink(),
             "LaTeX source required for full figure-chain audit")
    content = tex.read_text(encoding="utf-8")
    missing = missing_required_latex_figures(content, crop["figures"])
    # A legacy composite may have been taught using independently verified
    # upper/lower images on different slides. Accept these ONLY when the
    # SHA-bound split ledger reconstructs every image from the original PDF
    # and attests all source raster/vector/letter/annotation objects.
    groups={name:[name] for name in crop["figures"]}
    if missing["missing"] and (folder/"source_split_figure_chain_v1.json").is_file():
        from .source_split_figure_chain_v1 import verify_split_figure_chain
        split=verify_split_figure_chain(folder)
        live=re.sub(r"\\begin\{comment\}.*?\\end\{comment\}",
                    "",content,flags=re.S)
        live=re.sub(r"(?<!\\)%[^\n]*","",live)
        active={Path(x).name.lower() for x in GRAPHIC.findall(live)}
        guards={Path(x).name.lower() for x in GUARD.findall(content)}
        for source_name in missing["missing"]:
            assets=split["figures"].get(source_name)
            if not assets:
                continue
            _require(all(name.lower() in active for name in assets),
                     "LaTeX omitted source split panels: " + source_name)
            _require(not any(name.lower() in guards for name in assets),
                     "Source split panel conditionally hidden: " + source_name)
            groups[source_name]=assets
        missing_names=[name for name in crop["figures"]
                       if name in missing["missing"] and groups[name]==[name]]
    else:
        missing_names=missing["missing"]
    _require(not missing_names,
             "LaTeX omitted source figures: " + ", ".join(missing_names))
    _require(not missing["guarded"],
             "Required figures hidden by IfFileExists: "
             + ", ".join(missing["guarded"]))
    return {
        "status": "SOURCE_CAPTION_PNG_LATEX_CHAIN_VERIFIED",
        "source_sha256": crop["source_sha256"],
        "figures_verified": crop["figure_count"],
        "panels_verified": crop["verified_panels"],
        "render_assets_by_figure": groups,
        "verified_split_figure_count": sum(len(v)>1 for v in groups.values()),
        "no_figure_silently_omitted": True,
        "scientific_approval": False,
    }


def verify_rendered_pdf_source_figures(folder: Path) -> dict:
    """Proof of visible pixel-identical source PNGs in compiled slides.pdf.

    A .tex reference alone cannot prove the corresponding PDF rendered that
    image (comments, conditionals, macros or stale compiled PDFs). Require
    every source-caption figure's exact RGB pixels in at least one *visible*
    embedded PDF image XObject after LaTeX compilation. Layout/reading quality
    and scientific claims still need independent QA.
    """
    import io
    from PIL import Image
    folder = Path(folder)
    chain = verify_latex_figure_chain(folder)
    if chain["status"] == "NO_PRINTED_SOURCE_FIGURES":
        return {"status": "NO_PRINTED_SOURCE_FIGURES"}
    # The rendered figure can be a complete full-source PNG, or several
    # source-verified split PNGs visibly placed on separate slide pages.
    source_crops = list(dict.fromkeys(
        name for parts in chain["render_assets_by_figure"].values()
        for name in parts))
    rendered = folder / "slides.pdf"
    _require(rendered.is_file() and not rendered.is_symlink(),
             "Missing compiled slides.pdf for source-image pixel comparison")
    reference = {}
    for filename in source_crops:
        png = folder / filename
        with Image.open(png) as image:
            rgb = image.convert("RGB")
            reference[filename] = (rgb.size,
                                   hashlib.sha256(rgb.tobytes()).hexdigest())
    matched = {name: [] for name in source_crops}
    raster_evidence = {name: [] for name in source_crops}
    from .rendered_figure_visibility_v1 import render_visibility
    with fitz.open(str(rendered)) as pdf:
        _require(len(pdf) >= 1, "Compiled slide PDF has no pages")
        for i, page in enumerate(pdf):
            for item in page.get_images(full=True):
                xref = item[0]
                visible = [
                    rect for rect in page.get_image_rects(xref)
                    if (rect.is_valid and rect.width >= 10
                        and rect.height >= 10
                        and page.rect.intersects(rect))
                ]
                if not visible:
                    continue
                try:
                    blob = pdf.extract_image(xref)["image"]
                    with Image.open(io.BytesIO(blob)) as image:
                        rgb = image.convert("RGB")
                        ident = (rgb.size,
                                 hashlib.sha256(rgb.tobytes()).hexdigest())
                except (OSError, ValueError, KeyError):
                    continue
                for name, expected in reference.items():
                    if ident == expected:
                        # A PDF XObject can be fully covered, clipped or scaled
                        # below usefulness. Only the rasterized page is trusted.
                        with Image.open(folder / name) as source_png:
                            for area in visible:
                                appearance = render_visibility(page, area, source_png)
                                if appearance["verified"]:
                                    matched[name].append(i + 1)
                                    raster_evidence[name].append({
                                        "page":i + 1, **appearance})
                                else:
                                    raster_evidence[name].append({
                                        "page":i + 1, **appearance})
    missing = [name for name, pages in matched.items() if not pages]
    _require(not missing,
             "Compiled slides.pdf lacks visible exact source-figure pixels: "
             + ", ".join(missing))
    return {
        "status": "SOURCE_CAPTION_PNG_LATEX_RENDERED_PDF_CHAIN_VERIFIED",
        "figures_verified": chain["figures_verified"],
        "render_assets_verified": len(source_crops),
        "split_figures_verified": chain["verified_split_figure_count"],
        "slides_sha256": _sha(rendered),
        "source_sha256": chain["source_sha256"],
        "source_figure_visible_pages": matched,
        "source_pixels_unchanged": True,
        "rasterized_page_visibility_verified": True,
        "raster_visibility_evidence": raster_evidence,
        "scientific_approval": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path)
    parser.add_argument("--verify-folder", type=Path)
    parser.add_argument("--verify-latex", action="store_true")
    args = parser.parse_args(argv)
    if args.stage_dir:
        args.stage_dir.mkdir(parents=True, exist_ok=False)
        report = generate_candidates(args.source_pdf, args.stage_dir)
    else:
        _require(args.verify_folder is not None, "Specify one action")
        report = (verify_latex_figure_chain(args.verify_folder)
                  if args.verify_latex
                  else verify_figure_crops(args.verify_folder))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
