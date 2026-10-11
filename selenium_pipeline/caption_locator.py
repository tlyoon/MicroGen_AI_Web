"""Locate source-PDF figure captions with page and bounding-box provenance.

A caption location is not evidence of the exact illustration boundary.
Do not promote these candidates into lecture outputs without verification.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from .figure_audit import audit_one

def locate(folder: Path) -> dict:
    import pymupdf
    audit = audit_one(folder)
    missing = [x["reference"] for x in audit["graphics"] if x["status"] != "present"]
    targets = {}
    for name in missing:
        m = re.search(r"(\d+)[._ ]+(\d+)", name)
        if m:
            targets[name] = (m.group(1), m.group(2))
    matches = []
    with pymupdf.open(folder / "source.pdf") as pdf:
        for index, page in enumerate(pdf):
            blocks = page.get_text("blocks")
            for raw, (chapter, number) in targets.items():
                pattern = re.compile(r"(?i)\b(?:fig(?:ure)?\.?\s*)?" + re.escape(chapter) + r"\s*[.\-]\s*" + re.escape(number) + r"\b")
                for block in blocks:
                    content = str(block[4])
                    if pattern.search(content):
                        matches.append(dict(reference=raw, page=index+1,
                                            block_bbox=[round(float(v),2) for v in block[:4]],
                                            text=content[:250], status="caption_candidate_unverified"))
    report = dict(source_sha256=audit["source_sha256"], missing_references=missing,
                  caption_candidates=matches, verified_matches=0)
    out = folder / ".microgen_figure_candidates"
    out.mkdir(exist_ok=True)
    (out / "caption_locations.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("folder",type=Path)
    args=parser.parse_args()
    report=locate(args.folder)
    print("Missing:",len(report["missing_references"]),"caption candidates:",len(report["caption_candidates"]))
    for c in report["caption_candidates"]:
        print(c["reference"],"page",c["page"],repr(c["text"][:70]))
