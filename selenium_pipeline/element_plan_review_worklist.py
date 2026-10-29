"""Human-readable review worklist from a deliberately unapproved auto draft."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .element_plan_autodraft import AutoDraftError


def safe(value: object, limit: int = 110) -> str:
    text=" ".join(str(value or "").split())
    text=text.replace("|","\\|").replace("`","'")
    return text[:limit]+("…" if len(text)>limit else "")


def worklist(draft: dict) -> str:
    if draft.get("status")!="REVIEW_REQUIRED_NOT_TTS_READY" or        draft.get("can_stage_or_synthesize_audio") is not False:
        raise AutoDraftError("Only unapproved source-bound auto drafts are reviewable")
    lines=[
        "# Element-highlight plan: mandatory review worklist",
        "",
        "**REVIEW-ONLY — not authorized for TTS or student publication.**",
        "",
        f"Slides: **{draft['slide_count']}**; proposed PDF targets: "
        f"**{draft['candidate_target_count']}**; existing narration fragments: "
        f"**{draft['utterance_count']}**; ambiguous matches: "
        f"**{draft['ambiguous_utterance_count']}**; "
        f"slides with suspected multipart figures: "
        f"**{draft['figure_panel_slide_count']}**.",
        "",
        "Every excerpt is from the original script. Source-page candidates and "
        "visual-word similarity are hints, **not** verified mathematical mapping. "
        "Check the original textbook figures, exact labels, source pages, "
        "all equations, narration and final audio.",
        "",
    ]
    for slide in draft["slides"]:
        lines.extend([
            f"## Slide {slide['slide_number']}",
            "",
            f"Title: {safe(slide['title_hint']) or '(no title extracted)'}",
            "",
            "Unverified textbook-page candidates: "+(
                ", ".join(f"p.{c['source_page']} ({c['word_overlap']:.2f})"
                    for c in slide["source_page_candidates_unverified"]) or "none"),
            "",
            f"Visual targets: {len(slide['auto_candidate_targets'])}; "
            f"excluded fragments: {len(slide['excluded_visual_fragments'])}; "
            f"suspected multipart figure: "
            f"{'YES — inspect all panels' if slide['figure_panel_review_required'] else 'none detected'}.",
            "",
            "| Script fragment | Exact existing narration (excerpt) | Candidate target hints, UNVERIFIED |",
            "| --- | --- | --- |",
        ])
        for utterance in slide["proposed_utterances"]:
            options=utterance["candidate_target_rankings_unverified"]
            labels=", ".join(f"{x['draft_element_id']} ({x['overlap_hint']:.2f})"
                              for x in options) or "NO LEXICAL MATCH"
            if utterance["mapping_ambiguous"]:
                labels="**REVIEW AMBIGUITY**: "+labels
            lines.append(f"| {utterance['proposal_id']} | "
                         f"{safe(utterance['verbatim_script_fragment'],140)} | "
                         f"{safe(labels,180)} |")
        lines.extend(["",
            "Reviewer must confirm the correct source page and literal source "
            "quotation; choose full rendered elements or review each figure "
            "panel; combine consecutive original utterances without rewriting "
            "their words; assign matching real individual PCM WAVs. "
            "Never infer figure meaning solely from aspect ratio.",
            "",
        ])
    lines.extend(["---",
                  "This worklist is not a staging plan. A separately reviewed "
                  "JSON selection, exact original WAV hashes and independent "
                  "source/geometry verification are required before producing "
                  "any review-only MP4. Academic approval remains separate.",
                  ""])
    return "\n".join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--draft",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args(argv)
    if a.out.exists() or not a.out.parent.is_dir():
        raise FileExistsError("Worklist output must be a new file")
    source=json.loads(a.draft.read_text(encoding="utf8"))
    data=worklist(source)
    with a.out.open("x",encoding="utf8") as f:f.write(data)
    print("Wrote review-only worklist:",a.out)

if __name__=="__main__":
    main()
