"""Read-only original-source mathematical claim triage for an exact lecture folder.

Heuristics are cues for what to REVIEW, never academic source consensus.
No user requests, no model calls, no source edits, no TTS or publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pymupdf

from .incremental_element_candidate_map import candidate_map
from .figure_source_identity import require, _sha


_EXPLICIT_FORMULA_PHRASE = re.compile(
    r"\b(?:x\s+(?:equals?|equal\s+to)|a[- ]squared|x[- ]squared|"
    r"one\s+plus\s+tangent\s+squared|"
    r"one\s+minus\s+sine\s+squared|"
    r"(?:secant|sine|tangent)\s+squared)\b", re.I
)

_SIGNALS = (
    ("SUBSTITUTION_OR_IDENTITY_CANDIDATE",
     re.compile(r"\b(?:tangent|tan|sine|sin|cosine|cos|secant|sec|pythagorean|identity|identities|substitution|substituting)\b", re.I)),
    ("INTEGRATION_OR_DERIVATION_CANDIDATE",
     re.compile(r"\b(?:integral|integrate|integrand|derivative|differential|antiderivative|factor|simplif|cancel|logarithm)\w*", re.I)),
    ("GEOMETRY_OR_RADICAL_CANDIDATE",
     re.compile(r"\b(?:triangle|hypotenuse|adjacent|opposite|radical|square root|quadratic|domain|angle|interval|inverse)\b", re.I)),
)


def triage_unit(spoken: str, slide: int) -> dict:
    require(type(spoken) is str and bool(spoken.strip()), "Original spoken unit missing")
    raw = " ".join(spoken.split())
    if slide == 1 and re.fullmatch(r"\d+(?:\.\d+)+\s+[^\n]{3,120}", raw):
        kind = "SECTION_TITLE_METADATA_CANDIDATE"
        signals = []
    else:
        signals = [name for name, detector in _SIGNALS if detector.search(raw)]
        kind = signals[0] if signals else "GENERAL_PROSE_OR_UNKNOWN_CANDIDATE"
    return {"triage_kind": kind, "matching_review_cues": signals,
            "explicit_formula_phrase_candidate": bool(_EXPLICIT_FORMULA_PHRASE.search(raw)),
            "semantic_mathematics_verified": False,
            "original_source_quote_verified": False,
            "figure_semantics_verified": False}


def inventory_original_mathematics(*, folder: Path) -> dict:
    root = Path(folder).absolute()
    require(root.is_dir() and not root.is_symlink(), "Immutable original folder required")
    sources = (root / "source.pdf", root / "slides.pdf", root / "script.txt")
    require(all(p.is_file() and not p.is_symlink() for p in sources),
            "Original source, slides and script required")
    hashes = tuple(_sha(p) for p in sources)
    inventory = candidate_map(folder=root)
    require((inventory["source_sha256"], inventory["slides_sha256"],
             inventory["script_sha256"]) == hashes,
            "Source candidate identity differs from original input")
    with pymupdf.open(sources[0]) as textbook:
        source_pages = len(textbook)
    require(source_pages > 0 and inventory["slide_count"] > 0,
            "Missing physical original source or slide pages")
    slides = []
    counts: dict[str, int] = {}
    for s in inventory["slides"]:
        sid = s["slide"]
        rows = []
        for u in s["original_utterance_candidates"]:
            if not re.fullmatch(rf"s{sid:03d}\.utterance\.\d{{3}}", u["utterance_id"]):
                raise ValueError("Original narration source identity does not match slide")
            hint = triage_unit(u["original_text"], sid)
            counts[hint["triage_kind"]] = counts.get(hint["triage_kind"], 0) + 1
            rows.append({
                "utterance_id": u["utterance_id"],
                "original_spoken_sha256": u["original_text_sha256"],
                "original_spoken_characters": len(u["original_text"]),
                "candidate_visible_element_ids": [
                    t["target_id"] for t in u["candidate_visual_targets"]],
                **hint,
                "prior_source_review_status": "NOT_ASSESSED_IN_THIS_INVENTORY",
                "model_request_sent": False,
                "human_academic_approval": False,
            })
        slides.append({
            "slide": sid,
            "utterance_count": len(rows),
            "visible_text_candidate_count": len(s["candidate_visual_targets"]),
            "figure_semantics_review_required": True,
            "utterances": rows,
        })
    require(sum(s["utterance_count"] for s in slides) == inventory["utterance_count"],
            "Original utterance count mismatch in source inventory")
    require(tuple(_sha(p) for p in sources) == hashes,
            "Original assets changed during inventory")
    math_candidates = [
        {"slide": s["slide"], "utterance_id": u["utterance_id"],
         "triage_kind": u["triage_kind"],
         "original_spoken_sha256": u["original_spoken_sha256"]}
        for s in slides for u in s["utterances"]
        if u["triage_kind"] in (
            "SUBSTITUTION_OR_IDENTITY_CANDIDATE",
            "INTEGRATION_OR_DERIVATION_CANDIDATE",
            "GEOMETRY_OR_RADICAL_CANDIDATE")
    ]
    return {
        "status": "SOURCE_BOUND_REVIEW_PRIORITY_INVENTORY_NOT_ACADEMIC_APPROVAL",
        "original_source_sha256": hashes[0],
        "original_slides_sha256": hashes[1],
        "original_script_sha256": hashes[2],
        "physical_textbook_pdf_pages": source_pages,
        "original_slide_count": len(slides),
        "original_utterance_count": inventory["utterance_count"],
        "triage_counts": counts,
        "potential_substantive_review_units": len(math_candidates),
        "suggested_first_substantive_slide": next(
            (s["slide"] for s in slides if s["slide"] > 1
             and sum(u["explicit_formula_phrase_candidate"]
                     for u in s["utterances"]) >= 2), None),
        "candidate_units": math_candidates,
        "slides": slides,
        "all_original_units_accounted_for": True,
        "heuristic_cues_are_mathematical_proof": False,
        "individual_claim_source_quote_verified": False,
        "independent_math_consensus_verified": False,
        "new_academic_scope_authorized": False,
        "model_request_sent": False,
        "paid_tts_authorized": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", required=True, type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    result = inventory_original_mathematics(folder=args.folder)
    if args.out:
        target = args.out.absolute()
        if (target.exists() or not target.parent.is_dir()
            or target.is_relative_to(args.folder.absolute())):
            raise ValueError("New evidence may only be written outside originals")
        with target.open("x", encoding="utf8") as out:
            json.dump(result, out, indent=2, sort_keys=True)
            out.write("\n")
    print(json.dumps({
        "status": result["status"],
        "source_sha256": result["original_source_sha256"],
        "source_pages": result["physical_textbook_pdf_pages"],
        "slides": result["original_slide_count"],
        "original_utterances": result["original_utterance_count"],
        "triage_counts": result["triage_counts"],
        "first_substantive_slide": result["suggested_first_substantive_slide"],
        "semantic_math_approved": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
