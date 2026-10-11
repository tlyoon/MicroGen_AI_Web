"""Conservative extraction of embedded PDF image candidates, never automatic caption assignment."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path

def extract_candidates(folder: Path) -> dict:
    import pymupdf
    from PIL import Image
    source = folder / "source.pdf"
    dest = folder / ".microgen_figure_candidates"
    records = []
    with pymupdf.open(source) as doc:
        if len(doc) > 250:
            raise ValueError("Source exceeds bounded 250-page extraction limit")
        dest.mkdir(exist_ok=True)
        seen = set()
        for index, page in enumerate(doc):
            for item in page.get_images(full=True):
                xref = item[0]
                if xref in seen:
                    continue
                seen.add(xref)
                raw = doc.extract_image(xref)["image"]
                try:
                    with Image.open(io.BytesIO(raw)) as im:
                        im.load()
                        if min(im.size) < 24:
                            continue
                        filename = f"page_{index+1:03d}_xref_{xref}.png"
                        output = dest / filename
                        im.convert("RGB").save(output)
                        width, height = im.size
                except (OSError, ValueError):
                    continue
                records.append(dict(page=index+1, xref=xref, width=width, height=height,
                                    path=str(output), sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                                    match_status="unverified"))
    manifest = dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    candidates=records, verified_matches=0)
    (dest / "inventory.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder", type=Path)
    args=p.parse_args()
    result=extract_candidates(args.folder)
    print(f"Extracted {len(result['candidates'])} unverified PDF image candidates")
