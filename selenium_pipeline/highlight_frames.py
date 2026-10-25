"""Render static visual-emphasis frames from verified PDF rectangles and timing.

This preview renderer does NOT claim full audiovisual synchronization:
a future composer must encode frames at the exact WAV sample-derived times.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw
import pymupdf

from .pdf_element_geometry import ElementGeometryError
from .storyboard_gate import canonical_sha256


def emphasize_source_rectangles(image: Image.Image, rectangles: list, *,
                                scale: float) -> Image.Image:
    """Draw the exact normal highlight style, with NO invented timecode."""
    if not (0.5<=scale<=4.0) or not rectangles:
        raise ElementGeometryError("Invalid visual emphasis scale or empty regions")
    rgba=image.convert("RGBA")
    overlay=Image.new("RGBA",rgba.size,(0,0,0,0))
    draw=ImageDraw.Draw(overlay,"RGBA")
    for rect in rectangles:
        if not (type(rect) in (tuple,list) and len(rect)==4):
            raise ElementGeometryError("Expected four PDF point coordinates")
        x0,y0,x1,y1=(v*scale for v in rect)
        m=min(3*scale,x0,y0,rgba.width-x1,rgba.height-y1)
        if m<=0 or x0>=x1 or y0>=y1:
            raise ElementGeometryError("Highlight box invalid or clips page boundary")
        draw.rounded_rectangle(
            (x0-m,y0-m,x1+m,y1+m),radius=3*scale,
            fill=(245,197,42,25),
            outline=(235,151,7,240),width=max(2,round(2*scale)))
    return Image.alpha_composite(rgba,overlay).convert("RGB")


def render_highlight_frames(
    clean_pdf: str | Path, storyboard: dict, geometry: dict,
    alignment: dict, *, output_dir: str | Path, scale: float = 2.0,
) -> list[dict]:
    """Render one PNG per semantic speech event; no existing output overwritten."""
    if not (0.5 <= scale <= 4.0):
        raise ElementGeometryError("Rendering scale must be 0.5..4.0")
    if (geometry["storyboard_sha256"] != canonical_sha256(storyboard)
            or alignment["storyboard_sha256"] != geometry["storyboard_sha256"]):
        raise ElementGeometryError("Highlight metadata no longer matches storyboard")
    targets = {e["element_id"]: e for e in geometry["elements"]}
    out = Path(output_dir)
    if not out.is_dir():
        raise ElementGeometryError("Preview output directory does not exist")
    plans = []
    with pymupdf.open(clean_pdf) as pdf:
        if len(pdf) != len(storyboard["slides"]):
            raise ElementGeometryError("PDF page count differs from storyboard")
        for idx, event in enumerate(alignment["events"], 1):
            sid = event["slide_id"]
            eids = event["element_ids"]
            if not eids or len(set(eids)) != len(eids):
                raise ElementGeometryError("Empty/duplicate highlight targets")
            boxes = []
            for eid in eids:
                item = targets.get(eid)
                if item is None or item["slide_id"] != sid:
                    raise ElementGeometryError("Speech references wrong slide/geometry")
                boxes.append(item["rect_pt"])
            page_index = targets[eids[0]]["page_index"]
            if any(targets[eid]["page_index"] != page_index for eid in eids):
                raise ElementGeometryError("One event cannot highlight multiple slides")
            output = out/f"event_{idx:04d}.png"
            if output.exists():
                raise ElementGeometryError("Refusing to overwrite an existing highlight frame")
            plans.append((event, page_index, boxes, output))

        result = []
        for event, page_index, boxes, output in plans:
            pix = pdf[page_index].get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
            base = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            image = emphasize_source_rectangles(base, boxes, scale=scale)
            with output.open("xb") as stream:
                image.save(stream, format="PNG")
            result.append({
                "file": str(output), "slide_id": event["slide_id"],
                "segment_id": event["segment_id"],
                "start_ms": event["start_ms"], "end_ms": event["end_ms"],
                "element_ids": event["element_ids"],
            })
        return result
