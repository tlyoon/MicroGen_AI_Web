"""PDF-spatially witnessed fractions, REVIEW TARGETS ONLY.

This does not claim an equation is mathematically right, source-grounded, or
spoken correctly. It detects only a small, explicitly supported visual glyph
layout in the *original rendered PDF*: aligned 1 over 2, or L over T with
a smaller raised 2 directly to the right of T. Missing pixels/vertical
ordering or mismatched symbols produce no target, not a guessed equation.
"""
from __future__ import annotations
import hashlib
import math

import pymupdf


def _spans(page):
    result=[]
    for block_index,block in enumerate(page.get_text("dict")["blocks"]):
        if block.get("type")!=0:continue
        for line_index,line in enumerate(block.get("lines",[])):
            for span_index,span in enumerate(line.get("spans",[])):
                text=span.get("text","").strip()
                if text not in {"1","2","L","T"}:continue
                bbox=pymupdf.Rect(span.get("bbox",(0,0,0,0)))
                if (not bbox.is_empty and not bbox.is_infinite
                        and all(math.isfinite(v) for v in bbox)
                        and page.rect.contains(bbox)
                        and bbox.y0>=40 and bbox.y1<page.rect.height-18):
                    result.append({
                        "text":text,"bbox":bbox,"size":float(span["size"]),
                        "position":[block_index,line_index,span_index]})
    return result


def _stacked(upper,lower):
    top,bottom=upper["bbox"],lower["bbox"]
    return bool(
        4.0 <= bottom.y0-top.y0 <= 30.0
        and -1.1 <= bottom.y0-top.y1 <= 6.0
        and abs((top.x0+top.x1-bottom.x0-bottom.x1)/2)<=3.0
        and 0 < top.width <= 17 and 0 < bottom.width <= 17
        and top.y1<=bottom.y1-3.0)


def _superscript(base,expo):
    r,s=base["bbox"],expo["bbox"]
    return bool(expo["text"]=="2"
                and expo["size"]<base["size"]-.6
                and r.x1<=s.x0<=r.x1+4
                and r.y0-3<=s.y0<=r.y0+1.5
                and s.y1<=r.y1-1.0)


def physical_fraction_review_targets(page,slide_number:int)->list[dict]:
    if type(slide_number) is not int or not 1<=slide_number<=250:
        raise ValueError("Original slide number required for fraction targets")
    glyphs=_spans(page)
    results=[]
    seen=set()
    for upper in glyphs:
        if upper["text"] not in ("1","L"):
            continue
        bottom_letter="2" if upper["text"]=="1" else "T"
        for lower in glyphs:
            if lower["text"]!=bottom_letter or not _stacked(upper,lower):
                continue
            raised=None
            if upper["text"]=="L":
                available=[x for x in glyphs if _superscript(lower,x)]
                if len(available)!=1:
                    continue
                raised=available[0]
            chosen=[upper,lower]+([raised] if raised else [])
            indices=tuple(tuple(x["position"]) for x in chosen)
            if indices in seen:continue
            seen.add(indices)
            if len(results)>=12:
                # A heavily ambiguous page must not silently truncate to
                # arbitrarily preferred fraction glyphs.
                raise ValueError("Too many physically witnessed fractions")
            union=pymupdf.Rect(chosen[0]["bbox"])
            for item in chosen[1:]:
                union|=item["bbox"]
            union+=(-2,-2,2,2)
            if not page.rect.contains(union) or union.height>42:
                continue
            value=("1/2" if upper["text"]=="1" else "L/T^2")
            sha=hashlib.sha256(
                repr([(x["text"],tuple(round(v,4) for v in x["bbox"]),
                       x["position"]) for x in chosen]).encode("utf8")
                ).hexdigest()
            results.append({
                "draft_element_id":(
                    f"s{slide_number:03d}.fraction."
                    +"-".join(".".join(map(str,part)) for part in indices)),
                "kind":"math_fraction_review",
                "visible_text":value,
                "bbox_pdf_pt":[round(v,3) for v in union],
                "original_pdf_fraction_geometry_verified":True,
                "mathematical_semantics_verified":False,
                "independent_fraction_meaning_review_required":True,
                "anchor":{
                    "type":"physical_fraction_spans",
                    "original_glyph_locations":[list(x["position"])
                                                for x in chosen],
                    "original_glyph_text":[x["text"] for x in chosen],
                    "fraction_spans_sha256":sha,
                    "math_semantics_verified":False
                }
            })
    return results
