"""Drawing-aware PDF figure proposals. Preview-only: never publish unverified crops."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from .caption_locator import locate

def propose(folder: Path) -> dict:
    import pymupdf
    source=locate(folder)
    output=folder/".microgen_figure_candidates"/"drawing_previews"
    output.mkdir(parents=True,exist_ok=True)
    proposals=[]
    with pymupdf.open(folder/"source.pdf") as pdf:
        for cap in source["caption_candidates"]:
            if not re.match(r"(?i)^\s*figure\s+\d+\s*[.]\s*\d+\b",cap["text"]):
                continue
            page=pdf[cap["page"]-1]
            cx0,cy0,cx1,cy1=cap["block_bbox"]
            rects=page.cluster_drawings()
            # The illustration may sit beside its caption. Candidate regions are
            # derived from actual vector clusters, not a fixed upward strip.
            eligible=[]
            for rect in rects:
                if rect.width < 35 or rect.height < 35:
                    continue
                if rect.y1 > cy1+120 or rect.y0 < cy0-300:
                    continue
                distance=((rect.x0+rect.x1)/2-(cx0+cx1)/2)**2 + ((rect.y0+rect.y1)/2-(cy0+cy1)/2)**2
                eligible.append((distance,rect))
            eligible.sort(key=lambda item:item[0])
            for rank,(_,rect) in enumerate(eligible[:3],1):
                clip=(rect+pymupdf.Rect(-8,-8,8,8)) & page.rect
                name=re.sub(r"[^A-Za-z0-9]+","_",cap["reference"]).strip("_")
                target=output/f"{name}_page{cap['page']}_candidate{rank}.png"
                page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=clip,alpha=False).save(target)
                proposals.append(dict(reference=cap["reference"],page=cap["page"],
                                      preview=str(target),bbox=list(clip),
                                      status="unverified_vector_cluster_candidate"))
    result=dict(source_sha256=source["source_sha256"],proposals=proposals,verified=0)
    (output/"proposals.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("folder",type=Path)
    args=parser.parse_args()
    result=propose(args.folder)
    print("Vector-region proposals:",len(result["proposals"]))
