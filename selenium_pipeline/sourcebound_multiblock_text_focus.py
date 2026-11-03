"""Source-byte-bound visual focus across adjacent authored PDF text blocks.

A mathematical equation may render as two or three separate PyMuPDF text
blocks (subscripts, radicals, displayed fractions). Offering each tiny block
in isolation makes genuine narration-to-equation mapping impossible.

This reusable helper proposes bounded *visual groups* from real contiguous
author PDF blocks. It proves only physical identity and highlight geometry.
It never declares that the author equation, publisher original, spoken maths
or a figure's semantics are scientifically correct. Those remain in the
existing independent review/QA gates.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pymupdf


class TextGroupBlocked(ValueError):
    pass


def need(ok: bool, message: str) -> None:
    if not ok:
        raise TextGroupBlocked(message)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf8")).hexdigest()


def text_group_rect(page, anchor: dict) -> pymupdf.Rect:
    need(type(anchor) is dict and anchor.get("type") == "text_group",
         "Expected source-bound authored text-group anchor")
    indices=anchor.get("indices")
    digests=anchor.get("text_sha256")
    need(type(indices) is list and type(digests) is list
         and 2 <= len(indices) <= 3 and len(indices) == len(digests)
         and all(type(n) is int for n in indices)
         and sorted(indices) == indices
         and len(set(indices)) == len(indices),
         "Group indices must be 2–3 distinct ordered authored text blocks")
    blocks=page.get_text("blocks")
    need(indices[-1] < len(blocks), "Original author PDF text group changed")
    rects=[]
    for index,expected in zip(indices,digests):
        item=blocks[index]
        value=item[4] if len(item)>4 and isinstance(item[4],str) else None
        need(value is not None and _digest(value) == expected,
             "Authored PDF displayed equation/text block changed")
        rect=pymupdf.Rect(item[:4])
        need(not rect.is_empty and not rect.is_infinite,
             "Missing physical author text group geometry")
        rects.append(rect)
    for prev,current in zip(rects,rects[1:]):
        need(-8 <= current.y0 - prev.y1 <= 25,
             "Cannot group unrelated separated or overlapping PDF paragraphs")
        need(abs(current.x0 - prev.x0) <= 160,
             "Ambiguous cross-column / unrelated authored equation group")
    combined=pymupdf.Rect(rects[0])
    for r in rects[1:]:
        combined|=r
    need(page.rect.contains(combined)
         and combined.y0 >= 30
         and combined.y1 < page.rect.height - 17
         and combined.get_area() > 50
         and combined.get_area() < page.rect.get_area()*.50
         and combined.height < page.rect.height*.40,
         "Grouped highlight includes title/footer or oversized unsafe region")
    return combined


def discover_groups(page, slide: int, existing_targets: list[dict]) -> list[dict]:
    """Propose only actual adjacent authored blocks already separately found."""
    need(type(slide) is int and slide >= 1, "Invalid authored slide")
    blocks=page.get_text("blocks")
    ids={x.get("anchor",{}).get("index") for x in existing_targets
         if x.get("type")=="text_block"
         and x.get("anchor",{}).get("type")=="text_block"}
    indices=sorted(x for x in ids if type(x) is int and x < len(blocks))
    seen=set()
    proposals=[]
    for count in (2,3):
        for start in range(len(indices)-count+1):
            chosen=indices[start:start+count]
            # Do not jump across intervening original author PDF blocks,
            # including image/review-only segments between two equations.
            if any(b-a != 1 for a,b in zip(chosen,chosen[1:])):
                continue
            text=" ".join(" ".join(blocks[j][4].split()) for j in chosen)
            if len(text)<18 or len(text)>600:
                continue
            # The purpose is fragmented mathematical or explanatory content
            # that is NOT fully represented by any single PDF text block.
            if not any(re.search(r"[=+\u2212\u221a\u222b\u03b8\u03c0^]|"
                             r"\b(?:sin|cos|tan|sec|integral|theta|pi)\b",
                             str(blocks[j][4]),re.I) for j in chosen):
                continue
            anchor={"type":"text_group",
                    "indices":chosen,
                    "text_sha256":[_digest(blocks[j][4]) for j in chosen]}
            try:
                rect=text_group_rect(page,anchor)
            except TextGroupBlocked:
                continue
            key=tuple(chosen)
            if key in seen:
                continue
            seen.add(key)
            proposals.append({
                "draft_element_id":
                    f"s{slide:03d}.group."+("-".join(f"{x:03d}" for x in chosen)),
                "type":"text_group",
                "anchor":anchor,
                "rect_pt":[round(float(n),2) for n in rect],
                "visible_text":text[:600],
                "proposed_spoken_text":None,
                "mathematical_equivalence_proof_required":True,
                "figure_source_identity_verified":False,
                "review_required":True,
            })
            if len(proposals)>=28:
                return proposals
    return proposals
