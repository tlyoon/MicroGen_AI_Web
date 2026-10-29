"""Conservatively separate repeated Beamer template ink from content paths.

Only an identical PDF vector appearing on every slide and confined to the
header/footer or entire canvas can be called *decorative template* here.
A one-off equation stroke, figure or SVG on one page is never waived.
Images, inline images and real mathematical figures are unaffected.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import pymupdf

def _decorative_region(draw:dict,page_rect:pymupdf.Rect)->bool:
    r=draw["rect"]
    area=r.get_area()/max(1.0,page_rect.get_area())
    return bool(area>=0.9
                or r.y1<=page_rect.y0+0.24*page_rect.height
                or r.y0>=page_rect.y0+0.85*page_rect.height)

def _signature(draw:dict)->tuple:
    r=draw["rect"]
    def color(c):
        return tuple(round(float(v),3) for v in c) if c else None
    # Include exact subpath operation descriptions; two different strokes
    # sharing an approximate rectangle must not become indistinguishable.
    items=tuple(str(x) for x in draw.get("items",()))
    return (round(r.x0,2),round(r.y0,2),round(r.x1,2),round(r.y1,2),
            str(draw.get("type")),round(float(draw.get("width") or 0),2),
            color(draw.get("color")),color(draw.get("fill")),items)

def distinguish_template(page_list:list)->list[dict]:
    """Per-page actual semantic candidates, with no figure approval.

    For a one-page deck there is no independent template repeat evidence;
    all vectors remain source identity candidates.
    """
    if not page_list:
        raise ValueError("Nonempty PDF pages required")
    pages=list(page_list)
    entries=[]
    common=None
    for page in pages:
        drawings=page.get_drawings()
        can=Counter(_signature(x) for x in drawings
                    if _decorative_region(x,page.rect))
        common=can if common is None else (common & can)
        entries.append(drawings)
    if len(pages)<2:
        common=Counter()
    result=[]
    for page,drawings in zip(pages,entries):
        remaining=common.copy()
        semantic=[]
        decorative=[]
        for i,draw in enumerate(drawings):
            key=_signature(draw)
            if _decorative_region(draw,page.rect) and remaining.get(key,0):
                remaining[key]-=1
                decorative.append(i)
            else:
                semantic.append(i)
        result.append({
            "all_vector_path_count":len(drawings),
            "verified_repeated_margin_template_vector_count":len(decorative),
            "non_template_vector_path_count":len(semantic),
            "non_template_vector_indices":semantic,
            "template_only_heuristic_not_figure_semantic_proof":True,
        })
    return result
