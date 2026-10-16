"""Deterministic, source-bound element-to-narration drafting (NEVER TTS ready).

Matches exact utterance spans from existing slide narration to PDF-rendered
text/whole-figure candidate anchors. No words, source pages, figure panels
or WAVs are invented; all ambiguous candidates remain review-required.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf
from .scene_candidate_authoring import draft as scene_draft, terms
from .element_narration_stage import rectangle, ElementStageError
from .runner import blocks


class AutoDraftError(ValueError):
    """Cannot safely propose or promote a rendered content/audio match."""


def require(ok: bool, reason: str):
    if not ok:
        raise AutoDraftError(reason)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda: f.read(1048576), b""):
            h.update(piece)
    return h.hexdigest()


def utterances(text: str) -> list[str]:
    """Split at actual sentence boundaries without splitting decimal 8.4.

    Original whitespace is preserved through concatenation, so source text
    cannot be paraphrased, added to or normalized into new TTS content.
    """
    require(isinstance(text, str) and bool(text.strip()), "Empty narration")
    raw = re.split(r"(?<=[.!?])(?=\s+[A-Z\"“])", text)
    units = []
    for line in raw:
        if not line.strip():
            continue
        # Preserve original exact characters, including whitespace at boundary.
        units.append(line)
    require("".join(units) == text, "Sentence partition changed original script")
    return units


def similarity(a: str, b: str) -> float:
    """Lexical evidence is a *hint*, not academic or semantic approval."""
    left, right = Counter(terms(a)), Counter(terms(b))
    if not left or not right:
        return 0.0
    matched = sum(min(n, right.get(k, 0)) for k, n in left.items())
    return round(matched / max(1, sum(left.values())), 4)


def stable_recommendations(speech: str, candidates: list[dict]) -> list[dict]:
    ranked=[]
    for target in candidates:
        if target.get("kind") == "text_block":
            score=similarity(speech,target.get("visible_text",""))
        else:
            score=0.0  # Never infer figure meaning from file/position alone.
        if score > 0:
            ranked.append({"draft_element_id":target["draft_element_id"],
                           "overlap_hint":score,
                           "anchor":target["anchor"]})
    return sorted(ranked,key=lambda x:(-x["overlap_hint"],x["draft_element_id"]))[:3]


def propose(*, source_pdf: Path, slides_pdf: Path, script_txt: Path) -> dict:
    source, slides, script = (Path(p).resolve() for p in
                             (source_pdf,slides_pdf,script_txt))
    require(all(p.is_file() and not p.is_symlink() for p in (source,slides,script)),
            "Original source/slides/script files required")
    candidate=scene_draft(source,slides)
    raw=script.read_text(encoding="utf-8-sig")
    try:
        paragraphs=blocks(raw)
    except ValueError as e:
        raise AutoDraftError("Narration headers are absent, repeated or unordered") from e
    require(len(paragraphs)==candidate["slide_count"],
            "Narration slide count is not the rendered slide count")
    with pymupdf.open(slides) as rendered:
        proposals=[]
        for row, (number, text) in zip(candidate["slides"],paragraphs):
            require(number == row["slide_number"],
                    "Slide narration out of order")
            pg=rendered[number-1]
            targets=[]
            excluded=[]
            for item in row["targets"]:
                anchor=item["anchor"]
                try:
                    rect,kind=rectangle(pg,anchor)
                    # A wide composite figure needs *manual panel*
                    # identification; never silently highlight only (a).
                    requires_panel=(item["type"]=="image_whole" and
                                   item.get("suspected_multipart") is True)
                    targets.append({
                        "draft_element_id":item["draft_element_id"],
                        "kind":anchor["type"],
                        "anchor":anchor,
                        "rendered_rect_pt":[round(x,2) for x in rect],
                        "visible_text":item.get("visible_text"),
                        "suspected_multipart":requires_panel,
                        "panel_identity_review_required":requires_panel,
                        "source_page_candidate_unverified":
                            row["source_page_candidates_unverified"],
                        "source_evidence_verified":False,
                        "author_reviewed":False})
                except ElementStageError as exc:
                    excluded.append({"draft_element_id":item["draft_element_id"],
                                     "reason":str(exc)})
            spoken=[]
            for j,unit in enumerate(utterances(text),1):
                matches=stable_recommendations(unit,targets)
                best=matches[0]["overlap_hint"] if matches else 0.0
                runner_up=matches[1]["overlap_hint"] if len(matches)>1 else 0.0
                # A high lexical overlap is still not evidence of mathematical
                # meaning; never set a reviewer/semantic approval bit here.
                ambiguous=(best<0.3 or best-runner_up<0.15)
                spoken.append({
                    "proposal_id":f"s{number:03d}.utterance.{j:03d}",
                    "verbatim_script_fragment":unit,
                    "candidate_target_rankings_unverified":matches,
                    "mapping_ambiguous":ambiguous,
                    "manual_target_selection_required":True,
                    "spoken_word_fidelity_verified":False,
                    "approved_for_tts":False})
            require("".join(x["verbatim_script_fragment"] for x in spoken)==text,
                    "Draft does not exactly preserve original narration")
            proposals.append({
                "slide_number":number,
                "original_script_block_sha256":hashlib.sha256(
                    text.encode("utf8")).hexdigest(),
                "title_hint":row["title_hint"],
                "verbatim_slide_narration":text,
                "source_page_candidates_unverified":
                    row["source_page_candidates_unverified"],
                "source_page_approved":False,
                "source_quote_approved":False,
                "auto_candidate_targets":targets,
                "excluded_visual_fragments":excluded,
                "figure_panel_review_required":any(
                    t["panel_identity_review_required"] for t in targets),
                "proposed_utterances":spoken,
                "review_required":True,
                "approved_for_stage":False})
    n_targets=sum(len(p["auto_candidate_targets"]) for p in proposals)
    n_utterances=sum(len(p["proposed_utterances"]) for p in proposals)
    n_ambiguous=sum(x["mapping_ambiguous"] for p in proposals
                    for x in p["proposed_utterances"])
    return {
        "schema_version":1,"status":"REVIEW_REQUIRED_NOT_TTS_READY",
        "draft_kind":"PDF_GEOMETRY_PLUS_EXISTING_VERBATIM_SLIDE_SCRIPT",
        "source_sha256":file_hash(source),
        "slides_sha256":file_hash(slides),
        "script_sha256":file_hash(script),
        "slide_count":len(proposals),
        "candidate_target_count":n_targets,
        "utterance_count":n_utterances,
        "ambiguous_utterance_count":n_ambiguous,
        "figure_panel_slide_count":sum(p["figure_panel_review_required"]
                                         for p in proposals),
        "no_new_narration_words":True,
        "all_audio_generated":False,
        "source_meaning_reviewed":False,
        "manual_mapping_reviewed":False,
        "automatic_author_approval":False,
        "academic_approval":False,"student_publication":False,
        "can_stage_or_synthesize_audio":False,
        "cannot_be_used_as_authored_element_plan":True,
        "slides":proposals}


def main(argv=None)->int:
    ap=argparse.ArgumentParser(description="Unapproved element/narration proposals")
    ap.add_argument("--source-pdf",required=True,type=Path)
    ap.add_argument("--slides-pdf",required=True,type=Path)
    ap.add_argument("--script",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    args=ap.parse_args(argv)
    out=args.out.resolve()
    require(not out.exists() and out.parent.is_dir(),
            "Review-only draft path must be new")
    for original in (args.source_pdf,args.slides_pdf,args.script):
        require(not out.is_relative_to(original.resolve().parent),
                "Do not place tentative draft beside original source")
    result=propose(source_pdf=args.source_pdf,slides_pdf=args.slides_pdf,
                   script_txt=args.script)
    with out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({k:v for k,v in result.items() if k in (
        "status","slide_count","candidate_target_count",
        "utterance_count","ambiguous_utterance_count","figure_panel_slide_count",
        "can_stage_or_synthesize_audio")},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
