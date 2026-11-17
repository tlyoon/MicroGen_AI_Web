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


# This is a deterministic *review aid* (never a mathematical semantic
# verifier). Spoken names and PDF-extracted glyphs have different spelling.
MATH_PATTERNS={
    "sine": r"(?<![a-z])(?:sine|sin)(?![a-z])",
    "cosine": r"(?<![a-z])(?:cosine|cos)(?![a-z])",
    "tangent": r"(?<![a-z])(?:tangent|tan)(?![a-z])",
    "secant": r"(?<![a-z])(?:secant|sec)(?![a-z])",
    "pi": r"(?:\bpi\b|π)",
    "squared": r"(?:\bsquared\b|\bsquare\b|[²]|\^\s*2\b)",
    "cubed": r"(?:\bcubed\b|[³]|\^\s*3\b)",
    "square_root": r"(?:\bsquare\s+root\b|√|\bsqrt\b)",
    "integral": r"(?:\bintegral\b|∫)",
    "logarithm": r"(?:\blogarithm\b|\blog\b|\bln\b)",
    "infinity": r"(?:\binfinity\b|∞)",
}
TRIG_TERMS={"sine","cosine","tangent","secant"}


def math_markers(text: str) -> set[str]:
    text=unicodedata.normalize("NFKC",text).casefold()
    return {key for key,pattern in MATH_PATTERNS.items()
            if re.search(pattern,text)}


def _exact_spoken_math_operator_hint(speech: str, visible: str) -> float:
    """Strict literal notation equivalents for *ranking only*.

    Never infer mathematical truth, equivalence of arbitrary expressions,
    figure semantics or timing. A recognized spoken operator must match
    the IDENTICAL physical PDF operands and result. Incomplete glyphs,
    missing denominators or a conflicting equation yield zero hint.
    """
    spoken=speech.casefold()
    rendered=visible.casefold()
    number={"zero":"0","one":"1","two":"2","three":"3"}
    equation=re.search(
        r"\b([a-z])\s+plus\s+([a-z])\s+equals\s+"
        r"(zero|one|two|three|[0-9])\b",spoken)
    if equation:
        left,right,value=equation.groups()
        value=number.get(value,value)
        actual=(r"(?<![a-z0-9])"+re.escape(left)+r"\s*\+\s*"+
                re.escape(right)+r"\s*=\s*"+re.escape(value)+r"(?![0-9])")
        if re.search(actual,rendered):
            return .92
    # When speech discusses where the exponents come from, it may name
    # the exact printed equation in an *opposite verbal order*. Propose
    # that physical equation for independent review without asserting
    # left/right interpretation or mathematical correctness.
    partial=re.search(r"\b([a-z])\s+plus\s+([a-z])\b",spoken)
    if (partial and re.search(r"\bexponents?\b",spoken)
            and re.search(r"\b(?:left|right)\b",spoken)
            and not re.search(r"\b(?:not|never|unequal|incorrect|wrong)\b",
                              spoken)):
        a,b=partial.groups()
        for word,value in number.items():
            if re.search(r"\b"+word+r"\b",spoken):
                expression=(r"(?<![a-z0-9])"+re.escape(a)+r"\s*\+\s*"+
                            re.escape(b)+r"\s*=\s*"+value+r"(?![0-9])")
                if re.search(expression,rendered):
                    return .68
    proportional=re.search(
        r"\b([a-z])\s+is\s+proportional\s+to\b"
        r".{0,90}?\b([a-z])\s+times\b"
        r".{0,90}?\b([a-z])\s+squared\b",spoken)
    if proportional:
        x,a,t=proportional.groups()
        compact=re.sub(r"\s+","",rendered)
        exact=re.escape(x)+r"∝"+re.escape(a)+re.escape(t)+r"(?:2|²)"
        if re.search(exact,compact):
            return .90
    # An *explicit* literal unit ratio can provide a textual focus hint.
    # Never infer a divisor from stacked PDF glyphs or conflate T with T².
    if (re.search(r"\blength\s+divided\s+by\s+time\b",spoken)
            and not re.search(r"\b(?:time\s+)?squared\b",spoken)
            and re.search(r"(?<![a-z0-9])l\s*/\s*t(?![a-z0-9²])",
                          rendered)):
        return .63
    return 0.0


def stable_recommendations(speech: str, candidates: list[dict]) -> list[dict]:
    spoken_math=math_markers(speech)
    # Only SOURCE-WITNESSED caption panels may have a deterministic
    # author-label match. A vague 'panel b' is never used to guess a
    # rectangular image region, and the hint never approves science/TTS.
    named=re.search(r"(?i)\b(?:panel|diagram)\s*\(?([a-f])\)?\b",speech)
    requested_panel=named.group(1).lower() if named else None
    ranked=[]
    for target in candidates:
        kind=target.get("kind")
        if kind not in ("text_block","image_caption_panel","math_row_group"):
            continue
        if kind=="math_row_group":
            # Recycle physically reconstructed 2-8 glyph-fragment equations
            # as review targets, never claims of mathematical equivalence.
            anchor=target.get("anchor") or {}
            if (anchor.get("type")!="math_row_group"
                    or target.get("original_math_block_hashes_verified") is not True
                    or target.get("mathematical_semantics_verified") is not False):
                continue
        if kind=="image_caption_panel":
            anchor=target.get("anchor") or {}
            if (anchor.get("type")!="original_pdf_panel_visual_provenance"
                    or target.get("source_caption_panel_meaning_verified") is not True
                    or target.get("independent_visual_registration_verified") is not True
                    or target.get("mathematical_semantics_verified") is not False):
                continue
            if requested_panel and anchor.get("panel")!=requested_panel:
                continue
        visible=target.get("visible_text","") or ""
        lexical=similarity(speech,visible)
        target_math=math_markers(visible)
        math_coverage=(len(spoken_math & target_math)/len(spoken_math)
                       if spoken_math else 0.0)
        speech_trig=spoken_math & TRIG_TERMS
        visible_trig=target_math & TRIG_TERMS
        trig_conflict=bool(speech_trig and visible_trig
                           and speech_trig.isdisjoint(visible_trig))
        # Math keywords provide a separate visible hint; they cannot
        # approve figure meaning, equation equivalence, or narration.
        score=(.65*lexical+.35*math_coverage
               if spoken_math and target_math else lexical)
        if trig_conflict:
            # A named incompatible function is never a safe focus suggestion.
            # Do not merely down-rank it: candidates may otherwise outrank
            # all correct expressions in the same rendered slide.
            continue
        if kind in ("text_block","math_row_group"):
            # This supplies a *physical literal notation hint* only, not an
            # equation-equivalence or scientific-acceptance conclusion.
            literal=_exact_spoken_math_operator_hint(speech,visible)
            if literal:
                from .recovery_registry import lookup_mechanism
                try:
                    registered=lookup_mechanism(
                        "source_mapping_repair",
                        "SPOKEN_LITERAL_OPERATOR_VS_RENDERED_MATH_SYMBOL")
                except (ValueError,OSError):
                    registered=None
                if registered=="EXACT_PHYSICAL_PDF_OPERATOR_ALIAS_RANKING_HINT_ONLY":
                    score=max(score,literal)
                # A retired/missing/tampered historical repair cannot
                # silently make extra PDF targets eligible for review.
        if kind=="image_caption_panel" and requested_panel:
            # Original textbook's unique visible (a)/(b)/(c) anchors
            # independently match source caption meanings to actual image
            # pixels. This is a robust *ranking hint* only, not academic QA.
            score=max(score,.99)
        score=round(score,4)
        if score>0:
            ranked.append({"draft_element_id":target["draft_element_id"],
                           "overlap_hint":score,
                           "lexical_hint":lexical,
                           "mathematical_term_coverage_hint":round(math_coverage,4),
                           "math_terms_in_both_unverified":
                               sorted(spoken_math & target_math),
                           "possible_trig_mismatch_review":trig_conflict,
                           "anchor":target["anchor"]})
    # A physically contiguous equation row may include a heading/text block
    # already offered separately. Never manufacture a new 'close second'
    # ambiguity by ranking duplicate evidence as two independent choices.
    # Retain all source-verified groups in the visual inventory for review,
    # but rank a group only when its additional fragments provide material
    # lexical or mathematical-term coverage over constituent text blocks.
    deduplicated=[]
    for candidate in ranked:
        anchor=candidate["anchor"]
        if anchor.get("type")=="math_row_group":
            members=set(anchor.get("indices",[]))
            constituent=[r for r in ranked
                if r["anchor"].get("type")=="text_block"
                and r["anchor"].get("index") in members]
            if constituent:
                best=max(constituent,key=lambda x:x["overlap_hint"])
                if (candidate["overlap_hint"]<=best["overlap_hint"]+.07
                        and candidate["mathematical_term_coverage_hint"]
                            <=best["mathematical_term_coverage_hint"]+.1):
                    continue
        deduplicated.append(candidate)
    return sorted(deduplicated,
                  key=lambda x:(-x["overlap_hint"],x["draft_element_id"]))[:3]


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
                    requires_panel=(item["type"] in
                                   {"image_whole","inline_image_whole"} and
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
            # The historical rich-lecture mapper listed only the WHOLE
            # multi-panel bitmap, even after an independent source-caption
            # and cross-detector physical panel proof became available. Add
            # these safe, distinctly selectable captioned panel candidates
            # to the *ordinary* source-grounded rich mapping request too.
            # Their source-visible caption proves panel meaning/provenance,
            # not a narrated claim's mathematical correctness or TTS timing.
            from .captioned_panel_target_router import panel_targets_for_slide
            for panel in panel_targets_for_slide(
                    source=source,slides=slides,slide_number=number,
                    rendered_text=pg.get_text()):
                targets.append({
                    "draft_element_id":panel["draft_element_id"],
                    "kind":panel["kind"],
                    "anchor":panel["anchor"],
                    "rendered_rect_pt":panel["bbox_pdf_pt"],
                    "visible_text":panel["visible_text"],
                    "suspected_multipart":False,
                    "panel_identity_review_required":False,
                    "source_caption_panel_meaning_verified":True,
                    "independent_visual_registration_verified":True,
                    "mathematical_semantics_verified":False,
                    "source_page_candidate_unverified":
                        [panel["anchor"]["source_page"]],
                    "source_evidence_verified":False,
                    "author_reviewed":False,
                })
            # Existing rich drafts ALREADY contain grouped mathematical
            # regions. The previously fixed independent source verifier must
            # ENRICH those same physical IDs, not append duplicate shapes.
            # Unwitnessed math-row geometry stays visible for review only;
            # it may never receive a trusted ranking or speech cue.
            from .verified_slide_visual_candidates import composite_math_targets
            verified_math={formula["draft_element_id"]:formula
                for formula in composite_math_targets(pg,number,[])}
            for target in targets:
                if target["kind"]!="math_row_group":
                    continue
                witness=verified_math.get(target["draft_element_id"])
                source_matched=bool(
                    witness and target["anchor"]==witness["anchor"]
                    and target["visible_text"]==witness["visible_text"])
                target["original_math_block_hashes_verified"]=source_matched
                target["mathematical_semantics_verified"]=False
            require(len({t["draft_element_id"] for t in targets})==len(targets),
                    "Repeated physical element IDs in rich review candidate inventory")
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
