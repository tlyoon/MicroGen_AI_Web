"""Read-only source-numbered figure/example label geometry for focus drafting.

A source PDF header + unique rendered label is evidence of the LABEL only.
It never certifies equation correctness, image-panel identity, word-level
narration timing or an approved highlighted video. Ambiguity fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import pymupdf
from .runner import blocks

HEADER = re.compile(
    r"(?im)^[ \t]*(?:(?P<example>EXAMPLE)[ \t]+(?P<exnum>\d{1,2})"
    r"|(?P<figure>FIGURE)[ \t]+(?P<fignum>\d{1,2}[.-]\d{1,2}))\b"
)
VISIBLE = re.compile(
    r"(?i)\b(?:(?P<example>EXAMPLE)[ \t]+(?P<exnum>\d{1,2})"
    r"|(?P<figure>FIGURE|FIG\.?)[ \t\n]+(?P<fignum>\d{1,2}[.-]\d{1,2}))\b"
)


class SourceLabelGeometryError(ValueError):
    pass


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise SourceLabelGeometryError(reason)


def _hash(path: Path) -> str:
    _require(path.is_file() and not path.is_symlink(),
             f"Unsafe or missing original asset: {path.name}")
    digest=hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda:f.read(1024*1024),b""):
            digest.update(piece)
    return digest.hexdigest()


def _normalized(kind: str, value: str) -> str:
    if kind == "example":
        return f"Example {int(value)}"
    a,b=re.split(r"[.-]",value)
    return f"Figure {int(a)}.{int(b)}"


def _source_headers(source: pymupdf.Document) -> dict[str,list[int]]:
    result=defaultdict(list)
    for page_number,page in enumerate(source,1):
        for m in HEADER.finditer(page.get_text()):
            kind="example" if m.group("example") else "figure"
            number=m.group("exnum") if kind=="example" else m.group("fignum")
            result[_normalized(kind,number)].append(page_number)
    return dict(result)


def _slide_labels(page:pymupdf.Page)->list[str]:
    labels=set()
    for m in VISIBLE.finditer(page.get_text()):
        kind="example" if m.group("example") else "figure"
        number=m.group("exnum") if kind=="example" else m.group("fignum")
        labels.add(_normalized(kind,number))
    return sorted(labels)


def inspect(*,source:Path,slides:Path,script:Path)->dict:
    paths=[Path(x).absolute() for x in (source,slides,script)]
    _require(len({str(x) for x in paths})==3,"Original assets must be separate")
    before=[_hash(x) for x in paths]
    utterances=blocks(paths[2].read_text(encoding="utf-8-sig"))
    rows=[]
    with pymupdf.open(paths[0]) as source_doc,pymupdf.open(paths[1]) as slide_doc:
        _require(len(source_doc)>0 and len(slide_doc)==len(utterances),
                 "Original source/slide/narration page count invalid")
        headers=_source_headers(source_doc)
        for (number,_speech),page in zip(utterances,slide_doc):
            _require(number==len(rows)+1,
                     "Original slide numbering must be ordered and complete")
            objects=[]
            for label in _slide_labels(page):
                loc=headers.get(label,[])
                rects=page.search_for(label)
                # PyMuPDF may return split text rectangles when a label is
                # broken across lines, or repeated labels. Neither is a
                # single safely highlightable label geometry.
                unique=len(loc)==1 and len(rects)==1
                if unique:
                    r=rects[0]
                    w,h=page.rect.width,page.rect.height
                    bbox=[round(float(v),3) for v in (r.x0,r.y0,r.x1,r.y1)]
                    unique=(0<=r.x0<r.x1<=w and 0<=r.y0<r.y1<=h)
                else:
                    bbox=None
                objects.append({
                    "label":label,
                    "kind":"example_label" if label.startswith("Example") else "figure_caption_label",
                    "original_header_source_pages":loc,
                    "unique_source_header_and_visible_bbox":bool(unique),
                    "source_pdf_page":loc[0] if unique else None,
                    "label_bbox_pdf_pt":bbox if unique else None,
                    "candidate_source_visual_id":(
                        hashlib.sha256(("|".join(before)+"|"+
                                        f"{number}|{label}|{bbox}").encode()).hexdigest()[:24]
                        if unique else None),
                    "reason":("UNIQUE_EXACT_LABEL_CANDIDATE_ONLY" if unique
                              else "AMBIGUOUS_SOURCE_OR_SLIDE_LABEL_GEOMETRY"),
                    "figure_body_geometry_verified":False,
                    "mathematical_semantics_verified":False,
                    "narrated_word_timing_verified":False,
                    "highlight_approved":False,
                })
            rows.append({"slide":number,"labels":objects,
                         "read_only_source_label_candidates":sum(
                             x["unique_source_header_and_visible_bbox"] for x in objects),
                         "element_focus_approved":False})
    _require([_hash(x) for x in paths]==before,
             "Original source, slide or narration mutated during mapping")
    found=sum(r["read_only_source_label_candidates"] for r in rows)
    return {
        "schema_version":1,
        "status":"SOURCE_VERIFIABLE_EXAMPLE_FIGURE_LABEL_GEOMETRY_ONLY",
        "source_sha256":before[0],"slides_sha256":before[1],
        "script_sha256":before[2],"slide_count":len(rows),
        "labels_detected":sum(len(r["labels"]) for r in rows),
        "uniquely_source_grounded_label_count":found,
        "ambiguous_label_count":sum(len(r["labels"]) for r in rows)-found,
        "slides":rows,
        "full_mathematical_figure_mapping_verified":False,
        "word_timing_verified":False,
        "encoded_pixel_highlight_verified":False,
        "production_video_approved":False,
        "student_publication_authorized":False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("source","slides","script","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args(argv)
    output=a.output.absolute()
    _require(output.parent.is_dir() and not output.exists() and not output.is_symlink(),
             "Original sidecar output must be newly created in existing directory")
    _require(output.parent not in {a.source.absolute().parent,
                                   a.slides.absolute().parent,
                                   a.script.absolute().parent},
             "Never write into original production folder")
    report=inspect(source=a.source,slides=a.slides,script=a.script)
    with output.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k:report[k] for k in (
        "slide_count","labels_detected","uniquely_source_grounded_label_count",
        "ambiguous_label_count","production_video_approved")}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
