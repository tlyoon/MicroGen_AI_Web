"""Physically verify all source PDF review rectangles; triage visible math risks.

This is a SOURCE GEOMETRY / TYPOGRAPHY AUDIT, not proof of spoken
mathematics, a source-locked academic review or permission to publish.
"""
from __future__ import annotations
import argparse
import json
import math
import re
from pathlib import Path

import pymupdf
from .element_plan_autodraft import file_hash
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_semantic_mapping_review import (
    EXPECTED_SOURCE_SHA, require,
)

def physical_matches(page, candidate: dict) -> bool:
    rect = candidate.get("source_pdf_rect_pt")
    text = candidate.get("actual_visible_original_pdf_text")
    require(type(rect) is list and len(rect) == 4
            and all(type(n) in (int, float) and math.isfinite(n) for n in rect)
            and 0 <= rect[0] < rect[2] <= page.rect.width
            and 0 <= rect[1] < rect[3] <= page.rect.height
            and isinstance(text, str) and bool(text.strip()),
            "PDF text rectangle escaped original raster or missing content")
    normalized = " ".join(text.split())
    blocks = page.get_text("blocks")
    found = [block for block in blocks if len(block) > 4
             and all(abs(float(block[k]) - rect[k]) <= .15 for k in range(4))
             and " ".join(str(block[4]).split()) == normalized]
    return len(found) == 1

def triage_flags(narration: str, visible: str, score: float) -> list[str]:
    """Cautious *review flags*, never semantic rejections or author approvals."""
    flags = []
    if score < .35:
        flags.append("LOW_MATCH_STRENGTH")
    if "\x01" in visible or "\ufffd" in visible:
        flags.append("PDF_EXTRACTION_CONTROL_GLYPH")
    if re.match(r"^\s*(?:\d+\s*[<≤≥>]|[<≤≥>])", visible):
        flags.append("POSSIBLE_SPLIT_EQUATION_OR_FRACTION")
    if len(visible.strip()) < 20 and not re.search(
        r"(?i)\b(correct answer|option|integrate|substitute)\b", visible):
        flags.append("VERY_SHORT_VISUAL_BLOCK")
    lower = narration.casefold()
    v = visible.casefold()
    # The text contains math polarity; a mismatched strict/non-strict
    # statement must be investigated, not silently promoted.
    polarity = ("negative", "positive", "nonnegative", "non-negative",
                "nonpositive", "strictly", "at least", "at most")
    if any(p in lower for p in polarity) and any(p in v for p in polarity):
        if (("strictly" in lower) != ("strictly" in v)
                or ("nonnegative" in lower) != ("nonnegative" in v)):
            flags.append("POLARITY_OR_DOMAIN_SCOPE_REVIEW")
    if len(re.findall(r"(?:\d+|[a-z])\s*[≤≥<>]", v)) > 0:
        flags.append("VISIBLE_DOMAIN_OR_SIGN_INEQUALITY")
    return sorted(set(flags))

def audit_original_pdf_review(*, original: Path, candidate_receipt: Path,
                              output: Path) -> dict:
    root = Path(original).resolve()
    receipt = Path(candidate_receipt).resolve()
    out = Path(output).absolute()
    require(root.is_dir() and receipt.is_file() and out.parent.is_dir()
            and not out.exists() and not out.is_relative_to(root.parent)
            and not Path(original).is_symlink()
            and not Path(candidate_receipt).is_symlink(),
            "Source/receipt absent or output would touch protected originals")
    ledger = json.loads(receipt.read_text(encoding="utf8"))
    require(ledger.get("status") ==
            "REAL_SOURCE_PDF_ACOUSTIC_VISUAL_WORKLIST_NOT_SEMANTICALLY_APPROVED"
            and ledger.get("schema_version") == 1
            and ledger.get("student_publication_authorized") is False
            and ledger.get("complete_element_synchronization_approved") is False
            and ledger.get("academic_source_math_approved") is False
            and ledger.get("source_pdf_sha256") == EXPECTED_SOURCE_SHA
            and ledger.get("historical_slides_covered") == 16,
            "Untrusted candidate worklist or false release status")
    require(file_hash(root/"source.pdf") == EXPECTED_SOURCE_SHA,
            "Original textbook source identity drift")
    tts = json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    rows = tts["slides"]
    require([s["slide"] for s in rows] == list(range(1,18)),
            "Original actual TTS slide ordering drift")
    results = []
    physically_verified = 0
    uncertain = 0
    with pymupdf.open(root/"slides.pdf") as deck:
        require(len(deck) == 17, "Wrong original-slide PDF page count")
        for slide in ledger["slides"]:
            idx = slide["slide"]
            require(isinstance(idx, int) and 1 <= idx <= 17 and idx != 4,
                    "Unexpected protected source slide in review worklist")
            sentences, _ = tokenize_reference_sentences(
                rows[idx-1]["tts_text"])
            for segment in slide["candidate_segments"]:
                if not segment["unique_target_review_priority"]:
                    continue
                num = segment["sentence_index"]
                require(1 <= num <= len(sentences)
                        and segment["spoken_original_fragment_sha256"] ==
                        sentences[num-1]["narration_fragment_sha256"]
                        and segment["actual_recorded_word_start_second"] is not None
                        and segment["actual_recorded_word_end_second"] is not None
                        and segment["speech_to_visible_math_semantics_approved"] is False
                        and segment["eligible_for_final_student_highlight"] is False,
                        "Original narration acoustic identity absent")
                candidate = segment["candidate_targets"][0]
                require(physical_matches(deck[idx-1], candidate),
                        "Candidate bbox/text not physically present in protected PDF")
                score = candidate["review_priority_score_not_probability"]
                require(isinstance(score, (int, float)) and math.isfinite(score),
                        "Bad priority score")
                flags = triage_flags(sentences[num-1]["narration_fragment"],
                                     candidate["actual_visible_original_pdf_text"],
                                     score)
                results.append({
                    "slide": idx, "sentence_index": num,
                    "element_id": candidate["original_pdf_element_id"],
                    "pdf_rect_pt": candidate["source_pdf_rect_pt"],
                    "measured_word_interval_s": [
                        segment["actual_recorded_word_start_second"],
                        segment["actual_recorded_word_end_second"]],
                    "physical_pdf_geometry_and_text_verified": True,
                    "review_risk_flags": flags,
                    "review_risk_flagged": bool(flags),
                    "semantic_math_approved": False,
                    "release_highlight_allowed": False,
                })
                physically_verified += 1
                uncertain += bool(flags)
    require(physically_verified ==
            ledger["uniquely_prioritized_pdf_review_targets"] and
            physically_verified > 0,
            "Real original-PDF review inventory incomplete")
    require(file_hash(root/"source.pdf") == EXPECTED_SOURCE_SHA,
            "Protected textbook changed during geometry review")
    outcome = {
        "schema_version": 1,
        "status": "PHYSICALLY_REVERIFIED_PDF_TARGETS_SEMANTICALLY_UNAPPROVED",
        "source_pdf_sha256": EXPECTED_SOURCE_SHA,
        "candidate_receipt_sha256": file_hash(receipt),
        "actual_pdf_blocks_verified": physically_verified,
        "risk_flagged_candidate_blocks": uncertain,
        "mathematical_semantics_approved": False,
        "full_spoken_element_synchronization_approved": False,
        "student_publication_authorized": False,
        "candidates": results,
    }
    with out.open("x", encoding="utf8") as handle:
        json.dump(outcome, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return outcome

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a=p.parse_args()
    out=audit_original_pdf_review(original=a.original,
                                  candidate_receipt=a.candidates,
                                  output=a.out)
    print(json.dumps({k:v for k,v in out.items() if k!="candidates"},indent=2))

if __name__ == "__main__":
    main()
