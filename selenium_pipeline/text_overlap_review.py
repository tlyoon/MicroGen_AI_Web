"""Flag source-PDF figure crop previews that overlap selectable textbook text.

This is a conservative rejection gate, not proof of semantic correctness.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def check(folder: Path) -> dict:
    import pymupdf
    source=folder/".microgen_figure_candidates"/"drawing_previews"/"proposals.json"
    report=json.loads(source.read_text(encoding="utf-8"))
    results=[]
    with pymupdf.open(folder/"source.pdf") as pdf:
        for entry in report["proposals"]:
            page=pdf[entry["page"]-1]
            clip=pymupdf.Rect(entry["bbox"])
            overlaps=[]
            for word in page.get_text("words"):
                word_rect=pymupdf.Rect(word[:4])
                intersection=clip & word_rect
                if intersection.is_empty or word_rect.get_area() <= 0:
                    continue
                if intersection.get_area()/word_rect.get_area() >= 0.65:
                    overlaps.append(str(word[4]))
            results.append(dict(reference=entry["reference"],preview=entry["preview"],
                                text_words=len(overlaps),sample_text=" ".join(overlaps[:24]),
                                review_status="needs_visual_review",
                                text_contamination_flag=len(overlaps)>10))
    result=dict(proposals=results,approved=0)
    target=source.parent/"text_overlap_review.json"
    target.write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("folder",type=Path)
    args=parser.parse_args()
    result=check(args.folder)
    for entry in result["proposals"]:
        print(entry["reference"],"words:",entry["text_words"],
              "contaminated:",entry["text_contamination_flag"],
              entry["sample_text"][:85].encode("ascii", "backslashreplace").decode("ascii"))

