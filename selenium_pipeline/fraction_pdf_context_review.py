"""Physically witnessed context for identical PDF fraction review choices.

This prepares concise evidence for the independent visual/physics reviewer.
It does not rank, select, time, semantically interpret or approve anything.
Only exact source-PDF text extraction and geometry are used; no OCR or API.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pymupdf

MAX_CONTEXT_LINES = 6
MAX_CHOICES = 12


def _sha(text: str)->str:
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def _physical_lines(page):
    result=[]
    for block in page.get_text("dict").get("blocks",[]):
        if block.get("type")!=0:
            continue
        for line in block.get("lines",[]):
            raw="".join(str(x.get("text","")) for x in line.get("spans",[]))
            content=" ".join(raw.split())
            if not content or len(content)>500:
                continue
            bbox=line.get("bbox",())
            if len(bbox)!=4 or not all(
                    type(x) in (int,float) and math.isfinite(x) for x in bbox):
                continue
            rect=pymupdf.Rect(bbox)
            # The slide title at the top and Beamer counters are not useful
            # anchors for local mathematical source-context review.
            if (rect.is_empty or rect.is_infinite
                    or rect.y0<30 or rect.y1>page.rect.height-18
                    or not page.rect.contains(rect)):
                continue
            result.append((content,rect))
    return result


def _gap_y(a,b):
    return max(0.0,a.y0-b.y1,b.y0-a.y1)


def physically_witnessed_fraction_context(*,slides_pdf:Path,slide:int,
                                          choices:list[dict])->list[dict]:
    """Source-locked physical line witnesses, never a suggested semantic choice.

    Each choice comes from the already validated candidate map and must
    contain the existing exact physical-fraction span SHA and bounding box.
    No extra target is created or selected.
    """
    path=Path(slides_pdf)
    if (not path.is_file() or path.is_symlink()
            or not 1<=path.stat().st_size<=32_000_000
            or type(slide) is not int
            or not 1<=len(choices)<=MAX_CHOICES):
        raise ValueError("Original unlinked PDF and finite choice list required")
    seen=set()
    with pymupdf.open(path) as doc:
        if not 1<=slide<=len(doc):
            raise ValueError("Fraction choice slide outside original PDF")
        page=doc[slide-1]
        from .physical_fraction_review_targets import (
            physical_fraction_review_targets)
        direct={x["draft_element_id"]:x for x in
                physical_fraction_review_targets(page,slide)}
        lines=_physical_lines(page)
        items=[]
        for choice in choices:
            if (type(choice) is not dict
                    or choice.get("kind")!="math_fraction_review"
                    or choice.get("original_pdf_fraction_geometry_verified") is not True
                    or choice.get("mathematical_semantics_verified") is not False
                    or choice.get("independent_fraction_meaning_review_required") is not True):
                raise ValueError("Unverified physical fraction candidate")
            name=choice.get("draft_element_id")
            anchor=choice.get("anchor") or {}
            bbox=choice.get("bbox_pdf_pt")
            if (type(name) is not str or name in seen
                    or type(bbox) is not list or len(bbox)!=4
                    or any(type(v) not in (int,float) or not math.isfinite(v)
                           for v in bbox)
                    or anchor.get("type")!="physical_fraction_spans"
                    or type(anchor.get("fraction_spans_sha256")) is not str
                    or len(anchor["fraction_spans_sha256"])!=64
                    or anchor.get("math_semantics_verified") is not False):
                raise ValueError("Incomplete or repeated physical fraction provenance")
            # Reconstruct the physical glyph spans INDEPENDENTLY from the
            # exact PDF, not from the candidate map flag alone.
            original=direct.get(name)
            if (original is None or original["bbox_pdf_pt"]!=bbox
                    or original["anchor"]["fraction_spans_sha256"]!=
                       anchor["fraction_spans_sha256"]
                    or original["visible_text"]!=choice.get("visible_text")):
                raise ValueError("Original PDF does not witness this exact fraction")
            seen.add(name)
            bound=pymupdf.Rect(bbox)
            if (bound.is_empty or bound.is_infinite
                    or not page.rect.contains(bound)):
                raise ValueError("Unverified physical fraction bbox")
            around=[]
            for visible,rect in lines:
                distance=_gap_y(bound,rect)
                if distance>32:
                    continue
                around.append((distance,abs(rect.y0-bound.y0),rect.y0,
                               visible,rect))
            around.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
            witnesses=[]
            for distance,_,__,visible,rect in around[:MAX_CONTEXT_LINES]:
                witnesses.append({
                    "physical_line_text":visible,
                    "physical_line_sha256":_sha(visible),
                    "bbox_pdf_pt":[round(v,3) for v in rect],
                    "vertical_gap_pdf_pt":round(distance,3),
                    "source_semantics_approved":False,
                })
            items.append({
                "target_id":name,
                "visible_literal_fraction":choice.get("visible_text"),
                "fraction_bbox_pdf_pt":[round(v,3) for v in bound],
                "fraction_spans_sha256":anchor["fraction_spans_sha256"],
                "nearby_physical_pdf_lines":witnesses,
                "context_is_only_spatial_evidence":True,
                "selected_target_id":None,
                "independent_semantic_choice_required":True,
                "source_semantics_approved":False,
                "paid_tts_authorized":False,
            })
    return items

def verify_saved_context_packet(packet:object,choice_ids:object)->bool:
    """Validate persisted witness shape, IDs and text digests fail-closed.

    This is structural authenticity only; the source-locked producing routine
    separately reconstructs PDF glyphs. It is never model science acceptance.
    """
    if (type(packet) is not list or type(choice_ids) is not list
            or not 1<=len(packet)<=MAX_CHOICES
            or len(packet)!=len(choice_ids)
            or len(set(choice_ids))!=len(choice_ids)
            or any(type(n) is not str or not n for n in choice_ids)):
        return False
    if ({v.get("target_id") for v in packet if type(v) is dict}
            !=set(choice_ids)):
        return False
    for item in packet:
        if (type(item) is not dict
                or item.get("selected_target_id") is not None
                or item.get("independent_semantic_choice_required") is not True
                or item.get("source_semantics_approved") is not False
                or item.get("paid_tts_authorized") is not False
                or item.get("context_is_only_spatial_evidence") is not True
                or item.get("visible_literal_fraction") not in ("1/2","L/T^2")):
            return False
        spans=item.get("fraction_spans_sha256")
        bbox=item.get("fraction_bbox_pdf_pt")
        witnesses=item.get("nearby_physical_pdf_lines")
        if (type(spans) is not str or len(spans)!=64
                or any(c not in "0123456789abcdef" for c in spans)
                or type(bbox) is not list or len(bbox)!=4
                or any(type(v) not in (int,float) or not math.isfinite(v)
                       for v in bbox)
                or bbox[0]>=bbox[2] or bbox[1]>=bbox[3]
                or type(witnesses) is not list
                or len(witnesses)>MAX_CONTEXT_LINES):
            return False
        for witness in witnesses:
            if type(witness) is not dict:
                return False
            text=witness.get("physical_line_text")
            coords=witness.get("bbox_pdf_pt")
            gap=witness.get("vertical_gap_pdf_pt")
            if (type(text) is not str or not 1<=len(text)<=500
                    or _sha(text)!=witness.get("physical_line_sha256")
                    or type(coords) is not list or len(coords)!=4
                    or any(type(v) not in (int,float) or not math.isfinite(v)
                           for v in coords)
                    or coords[0]>=coords[2] or coords[1]>=coords[3]
                    or type(gap) not in (int,float) or not 0<=gap<=32
                    or witness.get("source_semantics_approved") is not False):
                return False
    return True
