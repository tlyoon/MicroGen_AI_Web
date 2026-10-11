"""Conservative PDF change planner, resilient to recompilation metadata."""
from pathlib import Path
import hashlib
import pymupdf

def _page_signature(page):
    words = [(round(w[0], 1), round(w[1], 1), round(w[2], 1),
              round(w[3], 1), w[4]) for w in page.get_text("words")]
    images = []
    for item in page.get_image_info(hashes=True):
        images.append((tuple(round(x, 1) for x in item["bbox"]),
                       item["digest"].hex()))
    images.sort()
    return words, images

def changed_pages(old_pdf: Path, new_pdf: Path) -> dict:
    with pymupdf.open(old_pdf) as old, pymupdf.open(new_pdf) as new:
        if len(old) != len(new):
            return {"page_count_changed": True,
                    "affected": list(range(1, len(new) + 1)),
                    "requires_semantic_review": True}
        affected = [index for index, (before, after) in
                    enumerate(zip(old, new), 1)
                    if _page_signature(before) != _page_signature(after)]
        return {"page_count_changed": False, "affected": affected,
                "requires_semantic_review": bool(affected)}
