"""Generate an exhaustive, provenance-labelled vector-cluster gallery for review.

Do not infer figure numbers from proximity: captions can be in adjacent columns.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def gallery(folder: Path) -> dict:
    import pymupdf
    source=folder/"source.pdf"
    target=folder/".microgen_figure_candidates"/"cluster_gallery"
    target.mkdir(parents=True,exist_ok=True)
    items=[]
    with pymupdf.open(source) as pdf:
        for page_num,page in enumerate(pdf,1):
            for index,rect in enumerate(page.cluster_drawings(),1):
                if rect.width<30 or rect.height<30:
                    continue
                clip=(rect+pymupdf.Rect(-9,-9,9,9)) & page.rect
                filename=f"page_{page_num:03d}_cluster_{index:03d}.png"
                page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=clip,alpha=False).save(target/filename)
                items.append(dict(page=page_num,cluster=index,bbox=list(clip),
                                  image=str(target/filename),figure_id=None,
                                  status="unassigned_unverified"))
    report=dict(candidates=items,approved=0)
    (target/"gallery.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("folder",type=Path)
    args=parser.parse_args()
    result=gallery(args.folder)
    print("Unassigned vector clusters:",len(result["candidates"]))
