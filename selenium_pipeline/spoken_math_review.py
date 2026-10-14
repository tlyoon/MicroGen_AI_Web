"""Offline advisory narration review; never an approval receipt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CATEGORIES = {
    "Radical scope": ("square root", "radical", "nth root"),
    "Fraction scope": ("divided by", "over", "numerator", "denominator"),
    "Cancellation domain": ("cancel", "common factor", "factor"),
    "Inequalities and bounds": ("less than", "greater than", "bound", "strict"),
    "Multipart figure": ("figure", "panel", "graph"),
    "Rounding versus proof": ("calculator", "rounding", "rounded", "table"),
}


class NarrationReviewError(ValueError):
    """Source or slide linkage is insufficient for a review packet."""


def build_review(storyboard: dict, source: dict | None = None) -> str:
    """Create a markdown checklist; no semantic approval or model invocation."""
    if not isinstance(storyboard, dict) or storyboard.get("schema_version") != 1:
        raise NarrationReviewError("Expected schema-version 1 storyboard")
    slides = storyboard.get("slides", [])
    segments = storyboard.get("narration_segments", [])
    if not slides or not segments:
        raise NarrationReviewError("Slides and narration are required")
    bindings = source.get("bindings", {}) if source is not None else None
    if source is not None and not isinstance(bindings, dict):
        raise NarrationReviewError("Source binding mapping required")
    by_slide, known = {}, set()
    for slide in slides:
        sid = slide["slide_id"]
        if sid in by_slide or not slide.get("elements"):
            raise NarrationReviewError("Duplicate or empty slide")
        by_slide[sid] = slide
        for element in slide["elements"]:
            eid, page = element["element_id"], element["source_page"]
            if eid in known or type(page) is not int or page < 1:
                raise NarrationReviewError("Invalid element id/page")
            known.add(eid)
            if bindings is not None:
                bind = bindings.get(eid)
                if not isinstance(bind, dict) or bind.get("source_pdf_page") != page:
                    raise NarrationReviewError("Source binding mismatch: "+eid)
    sha = source.get("source_pdf_sha256", "not supplied") if source else "not supplied"
    if sha != "not supplied" and (not isinstance(sha, str) or len(sha) != 64):
        raise NarrationReviewError("Source SHA-256 invalid")
    lines = [
        "# Offline scientific narration review packet",
        "",
        "**UNREVIEWED / NOT APPROVED.** Generated prompts cannot certify mathematics.",
        "Part: "+str(storyboard.get("part_id"))+". Source PDF SHA256: "+sha+".",
        "Human specialist review and actual spoken-word listening remain mandatory.",
        "",
    ]
    seen, used = set(), set()
    for idx, seg in enumerate(segments, 1):
        sid, nid = seg["slide_id"], seg["segment_id"]
        words = seg["spoken_text"]
        eids = seg["element_ids"]
        if (nid in seen or sid not in by_slide or not isinstance(words, str)
                or not words.strip() or not eids or len(eids) != len(set(eids))):
            raise NarrationReviewError("Invalid narration segment")
        seen.add(nid)
        sl = by_slide[sid]
        linked = {e["element_id"]:e["source_page"] for e in sl["elements"]}
        if not set(eids).issubset(linked):
            raise NarrationReviewError("Cross-slide narration link")
        used.update(eids)
        pages = sorted({linked[eid] for eid in eids})
        lines.extend([
            "## "+str(idx)+" / "+nid+" — "+sl["title"], "",
            "Source PDF page(s): "+", ".join(map(str,pages)),
            "Element(s): "+", ".join(eids), "",
            "Proposed spoken text:", "> "+words.replace("\n", "\n> "), "",
        ])
        for title, triggers in CATEGORIES.items():
            if any(k in words.casefold() for k in triggers):
                lines.append("- [ ] "+title+": confirm the exact mathematical scope against typeset source.")
        if bindings is not None:
            for eid in eids:
                ref = bindings[eid]
                if ref.get("source_figure_id"):
                    lines.append("- [ ] Source figure "+str(ref["source_figure_id"])+
                                 ": verify all source panels and labels; SHA256 "+
                                 str(ref.get("reference_sha256", "not supplied")))
        lines.extend([
            "- [ ] Verify formula, signs, variables, source evidence and excluded domains.",
            "- [ ] Review spoken grouping; listen to the actual WAV after synthesis.",
            "",
        ])
    if used != known:
        raise NarrationReviewError("Visual elements lack corresponding speech")
    lines.extend([
        "## Release barrier", "",
        "No source outline, expert approval, exact storyboard approval receipt, TTS,",
        "MP4 or student publication is authorized by this advisory report.",
        "",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser(description="Offline advisory pre-TTS review")
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--source-bindings", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    a=parser.parse_args(argv)
    st=json.loads(a.storyboard.read_text(encoding="utf-8"))
    binding=(json.loads(a.source_bindings.read_text(encoding="utf-8"))
             if a.source_bindings else None)
    packet=build_review(st,binding)
    with a.out.open("x",encoding="utf-8") as f:f.write(packet)
    print("Advisory review packet saved (NOT APPROVED):",a.out)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
