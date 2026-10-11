"""Conservative source-page region proposals near figure captions.

Proposals are previews, not verified figure crops. Never publish automatically.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from .caption_locator import locate

def propose(folder: Path) -> dict:
    import pymupdf
    report=locate(folder)
    output=folder/".microgen_figure_candidates"/"region_previews"
    output.mkdir(parents=True,exist_ok=True)
    results=[]
    with pymupdf.open(folder/"source.pdf") as pdf:
        for candidate in report["caption_candidates"]:
            if not re.match(r"(?i)^\s*figure\s+\d+\s*[.]\s*\d+\b",candidate["text"]):
                continue
            page=pdf[candidate["page"]-1]
            x0,y0,x1,y1=candidate["block_bbox"]
            # Preview only: restrict to caption's horizontal column and preceding vertical region.
            width=page.rect.width
            column_left=0 if x0 < width/2 else width/2
            column_right=width/2 if x0 < width/2 else width
            region=pymupdf.Rect(max(column_left,x0-12),max(0,y0-230),
                                min(column_right,x1+12),max(0,y0-5))
            if region.width < 40 or region.height < 40:
                continue
            name=re.sub(r"[^a-zA-Z0-9]+","_",candidate["reference"]).strip("_")
            filename=f"{name}_page_{candidate['page']}.png"
            pix=page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),clip=region,alpha=False)
            pix.save(output/filename)
            results.append(dict(reference=candidate["reference"],source_page=candidate["page"],
                                preview=str(output/filename),bbox=list(region),
                                status="unverified_preview_not_for_publication"))
    result=dict(source_sha256=report["source_sha256"],proposals=results,verified=0)
    (output/"proposals.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path)
    args=p.parse_args()
    result=propose(args.folder)
    print("Unverified region previews:",len(result["proposals"]))
