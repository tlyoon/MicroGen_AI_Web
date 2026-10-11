"""Conservative page-change impact planning for slide narration."""
from pathlib import Path
import pymupdf

def changed_pages(old_pdf: Path, new_pdf: Path) -> dict:
    with pymupdf.open(old_pdf) as old, pymupdf.open(new_pdf) as new:
        if len(old) != len(new):
            return {"page_count_changed": True, "affected": list(range(1, len(new)+1))}
        changed = []
        for index, (before, after) in enumerate(zip(old, new), 1):
            if before.get_text() != after.get_text() or len(before.get_images(full=True)) != len(after.get_images(full=True)):
                changed.append(index)
        return {"page_count_changed": False, "affected": changed,
                "requires_semantic_review": True}
