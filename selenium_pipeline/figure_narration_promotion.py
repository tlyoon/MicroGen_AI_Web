"""Contract boundary: no unverified figure candidates in production MP4s.

Older author-specified figure anchors remain useful for review-only previews.
No candidate raster/vector/source-box receipt in PR140-146 certifies *author-
intended* complete panels or scientific figure semantics. Consequently none
may be promoted by simply adding a self-declared "approved" boolean.
"""
from __future__ import annotations


class FigureNarrationPromotionBlocked(ValueError):
    """The source/figure semantic and complete panel proof is not sufficient."""


_FIGURE_ANCHORS = frozenset((
    "image_whole", "image_panel", "vector_figure",
    "figure", "figure_panel", "diagram_region",
))
_TEXT_ANCHORS = frozenset(("text_block",))


def check_production_anchor_provenance(plan: dict) -> dict:
    """Review a complete authoring plan, fail closed on every figure anchor.

    This gate is intentionally *not* satisfied by an arbitrary dict field
    saying "approved", "author_intended_complete_panel_boundaries_certified"
    or "tts_or_video_authorized": those are untrusted producer assertions.
    A future independent trusted verifier may extend this only after real
    scientific source proof is implemented and independently tested.
    """
    def need(ok: bool, reason: str):
        if not ok:
            raise FigureNarrationPromotionBlocked(reason)

    need(isinstance(plan,dict),"Invalid authoring plan object")
    parts=plan.get("parts")
    need(isinstance(parts,list) and bool(parts),
         "Missing ordered part list in authoring plan")
    count=0
    for pidx,part in enumerate(parts,1):
        need(isinstance(part,dict)
             and isinstance(part.get("slides"),list)
             and len(part["slides"])>0,
             f"Invalid part {pidx}: slide records missing")
        for slide in part["slides"]:
            need(isinstance(slide,dict)
                 and type(slide.get("slide")) is int
                 and isinstance(slide.get("elements"),list)
                 and bool(slide["elements"]),
                 "Missing slide number or narrated element records")
            for element in slide["elements"]:
                need(isinstance(element,dict)
                     and isinstance(element.get("anchor"),dict),
                     "Missing explicit source-bound spoken element anchor")
                kind=element["anchor"].get("type")
                need(isinstance(kind,str), "Anchor type must be an explicit string")
                if kind in _FIGURE_ANCHORS:
                    raise FigureNarrationPromotionBlocked(
                        f"Slide {slide['slide']}: figure anchor '{kind}' "
                        "is review-only: author-intended original complete "
                        "panels and scientific source mapping are not independently "
                        "certified; self-declared approval fields cannot bypass QA")
                need(kind in _TEXT_ANCHORS,
                     f"Slide {slide['slide']}: unverified anchor type "
                     f"{kind!r} cannot enter production")
                count+=1
    need(count>0,"No narrated elements")
    return {
        "schema_version":1,
        "status":"FIGURE_FREE_TEXT_ANCHORS_ONLY_PRODUCTION_PROMOTION_ELIGIBLE",
        "narrated_text_anchor_count":count,
        "figure_anchor_count":0,
        "self_declared_figure_approvals_accepted":False,
    }
