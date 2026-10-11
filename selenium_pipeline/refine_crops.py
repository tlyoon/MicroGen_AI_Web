"""Refine vector illustration crops by including nearby short diagram labels.

Preview-only; semantic correctness and caption identity remain unverified.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def refine(folder: Path) -> dict:
    import pymupdf
    src=folder/".microgen_figure_candidates"/"drawing_previews"/"proposals.json"
    data=json.loads(src.read_text(encoding="utf-8"))
    dest=folder/".microgen_figure_candidates"/"refined_previews"
    dest.mkdir(parents=True,exist_ok=True)
    result=[]
    with pymupdf.open(folder/"source.pdf") as pdf:
        for entry in data["proposals"]:
            page=pdf[entry["page"]-1]
            base=pymupdf.Rect(entry["bbox"])
            clip=base
            # Include short labels touching the drawing; exclude whole prose lines.
            for line in page.get_text("dict")["blocks"]:
                if line.get("type")!=0:
                    continue
                for row in line.get("lines",[]):
                    spans=row.get("spans",[])
                    content=" ".join(s["text"] for s in spans).strip()
                    if not content or len(content)>16 or len(content.split())>3:
                        continue
                    box=pymupdf.Rect(row["bbox"])
                    if box.width>95 or box.height>28:
                        continue
                    proximity=pymupdf.Rect(base.x0-18,base.y0-18,base.x1+18,base.y1+18)
                    if not (proximity & box).is_empty:
                        clip |= box
            clip=(clip+pymupdf.Rect(-5,-5,5,5)) & page.rect
            name=Path(entry["preview"]).name
            path=dest/name
            page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=clip,alpha=False).save(path)
            result.append(dict(reference=entry["reference"],page=entry["page"],
                               preview=str(path),bbox=list(clip),
                               status="unverified_refined_preview"))
    output=dict(proposals=result,verified=0)
    (dest/"proposals.json").write_text(json.dumps(output,indent=2),encoding="utf-8")
    return output

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("folder",type=Path)
    args=parser.parse_args()
    print("Refined previews:",len(refine(args.folder)["proposals"]))
