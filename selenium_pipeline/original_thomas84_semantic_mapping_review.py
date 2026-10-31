"""Conservative PDF-element worklist from real §8.4 acoustic word anchors.

Source and timing evidence are independently rechecked; all inferred mathematical
links stay UNAPPROVED, with no TTS, PDF, source, or student-media mutation.
The ledger improves *reviewable* coverage, never claims semantic certification.
"""
from __future__ import annotations

import argparse
import json
import re
import math
from pathlib import Path

from .element_plan_autodraft import file_hash, math_markers, propose, similarity
from .original_thomas84_offline_word_pdf_timing import (
    HISTORIC_SLIDES, tokenize_reference_sentences,
)
from .production_video_contract import VideoContractError

EXPECTED_SOURCE_SHA = "b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
RECEIPT_STATUS = "REAL_HISTORICAL_16_SLIDES_ASR_TO_ORIGINAL_PDF_ELEMENT_CANDIDATES_REVIEW_ONLY"
TRIG = {"sine", "cosine", "tangent", "secant"}
STEPS = {"first": "1", "second": "2", "third": "3", "fourth": "4"}
ROLES = {
    "substitute": r"\b(?:substitut(?:e|ion|ing)|substituting)\b",
    "transform": r"\b(?:transform|simplif(?:y|ication)|algebraic)\b",
    "integrate": r"\b(?:integrat(?:e|ion|ing)|antiderivative|evaluate)\b",
    "reverse": r"\b(?:reverse|reversib(?:le|ility)|back.substitut)\b",
    "triangle": r"\b(?:triangle|hypotenuse|opposite|adjacent)\b",
    "domain": r"\b(?:domain|interval|restrict(?:ed|ion|ing)?|inverse)\b",
    "factor": r"\b(?:factor(?:ed|ing)?|coefficient)\b",
    "answer": r"\b(?:answer|option|correct)\b",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VideoContractError(message)


def _roles(text: str) -> set[str]:
    lowered = text.casefold()
    return {key for key, pattern in ROLES.items() if re.search(pattern, lowered)}


def _step(text: str) -> str | None:
    lowered = text.casefold()
    match = re.search(r"\b(first|second|third|fourth)\b", lowered)
    return STEPS[match.group(1)] if match else None


def ranked_pdf_candidates(sentence: str, targets: list[dict]) -> list[dict]:
    """Rank visible original-PDF text, never approve a mathematical mapping."""
    speech_math = math_markers(sentence)
    speech_roles = _roles(sentence)
    speech_step = _step(sentence)
    ranked = []
    for target in targets:
        if target.get("kind") != "text_block" or target.get("panel_identity_review_required"):
            continue
        visible = target.get("visible_text") or ""
        if not visible.strip():
            continue
        visual_math = math_markers(visible)
        visual_roles = _roles(visible)
        # Conflicting explicitly named trigonometric functions cannot be
        # reconciled by generic semantic/role overlap. Keep missing trig
        # evidence as a review candidate, never infer that a function matches.
        s_trig, v_trig = speech_math & TRIG, visual_math & TRIG
        if s_trig and v_trig and not (s_trig & v_trig):
            continue
        overlap = similarity(sentence, visible)
        shared_math = speech_math & visual_math
        shared_roles = speech_roles & visual_roles
        ordinal = bool(speech_step and re.match(
            r"\s*" + re.escape(speech_step) + r"\s", visible))
        # All signals are observational; score is only for prioritizing review.
        score = round(.45 * overlap +
                      .32 * (len(shared_math) / max(1, len(speech_math))) +
                      .18 * (len(shared_roles) / max(1, len(speech_roles))) +
                      .25 * ordinal, 4)
        if score <= .15 or not (shared_math or shared_roles or ordinal):
            continue
        rect = target.get("rendered_rect_pt")
        require(isinstance(rect, list) and len(rect) == 4 and
                all(isinstance(x, (float, int)) and not isinstance(x, bool)
                    and math.isfinite(x) for x in rect) and
                rect[0] >= 0 and rect[1] >= 0 and
                rect[0] < rect[2] and rect[1] < rect[3],
                "PDF rendered element has invalid or nonfinite geometry")
        ranked.append({
            "original_pdf_element_id": target["draft_element_id"],
            "source_pdf_rect_pt": rect,
            "actual_visible_original_pdf_text": visible,
            "lexical_overlap": overlap,
            "shared_math_markers": sorted(shared_math),
            "shared_procedure_markers": sorted(shared_roles),
            "matching_numbered_step": ordinal,
            "review_priority_score_not_probability": score,
            "math_semantics_verified": False,
            "safe_for_student_highlight": False,
        })
    return sorted(ranked, key=lambda r: (-r["review_priority_score_not_probability"],
                                         r["original_pdf_element_id"]))[:3]


def build_real_pdf_mapping_worklist(*, original: Path, timing_receipt: Path,
                                    output: Path) -> dict:
    root = Path(original).resolve()
    timeline = Path(timing_receipt).resolve()
    out = Path(output).absolute()
    require(root.is_dir() and timeline.is_file() and
            not Path(original).is_symlink() and
            not Path(timing_receipt).is_symlink() and
            out.parent.is_dir() and not out.exists() and
            not out.is_relative_to(root.parent) and not out.is_symlink(),
            "Use a fresh outside-source receipt, never touch protected originals")
    report = json.loads(timeline.read_text(encoding="utf8"))
    require(type(report) is dict and report.get("schema_version") == 1 and
            report.get("status") == RECEIPT_STATUS and
            report.get("actual_historical_slides_inspected") == 16 and
            report.get("student_publication_authorized") is False and
            report.get("complete_video_spoken_element_synchronization_certified") is False and
            report.get("academic_source_math_two_pass_approved") is False and
            report.get("whisper_used") is False and
            report.get("network_asr_used") is False and
            report.get("provider_synthesis_requests_sent") == 0,
            "Untrusted, incomplete, or falsely approved acoustic receipt")
    hashes = report.get("source_original_hashes", {})
    require(type(hashes) is dict and hashes.get("source.pdf") == EXPECTED_SOURCE_SHA,
            "Original Thomas source identity is unproven")
    saved_wavs = report.get("original_historical_WAV_hashes", {})
    require(type(saved_wavs) is dict and
            set(saved_wavs) == {f"slide{i}.wav" for i in HISTORIC_SLIDES},
            "Acoustic WAV inventory missing/altered")
    for name, sha in {**hashes, **saved_wavs}.items():
        require(re.fullmatch(r"[a-f0-9]{64}", str(sha)) is not None and
                file_hash(root / name) == sha,
                f"Protected original source/PCM hash mismatch: {name}")
    draft = propose(source_pdf=root / "source.pdf",
                    slides_pdf=root / "slides.pdf", script_txt=root / "script.txt")
    require(draft["source_sha256"] == EXPECTED_SOURCE_SHA and
            draft["slides_sha256"] == hashes["slides.pdf"] and
            draft["script_sha256"] == hashes["script.txt"] and
            draft["slide_count"] == 17,
            "Actual PDF draft does not match protected source hashes")
    tts = json.loads((root / "script_tts.json").read_text(encoding="utf8"))
    slides_tts = tts.get("slides")
    require(type(slides_tts) is list and
            [x.get("slide") for x in slides_tts] == list(range(1, 18)),
            "Changed original TTS slide ordering")
    rows = report.get("slides")
    require(type(rows) is list and
            [r.get("slide") for r in rows] == list(HISTORIC_SLIDES),
            "Real acoustic worklist slide ordering missing")
    output_slides = []
    total_timed = total_prioritized = 0
    for original_row in rows:
        index = original_row["slide"]
        sentences, _ = tokenize_reference_sentences(slides_tts[index-1]["tts_text"])
        timed = original_row.get("candidate_elements")
        require(type(timed) is list and len(timed) == len(sentences),
                "Acoustic sentence count no longer matches original saved narration")
        targets = draft["slides"][index-1]["auto_candidate_targets"]
        units = []
        for evidence, sentence in zip(timed, sentences):
            require(evidence.get("sentence_index") == sentence["sentence_index"] and
                    evidence.get("narration_fragment_sha256") ==
                    sentence["narration_fragment_sha256"] and
                    evidence.get("original_actual_slide_narration_fragment") ==
                    sentence["narration_fragment"] and
                    evidence.get("real_speech_to_source_element_semantics_verified") is False and
                    evidence.get("eligible_for_final_student_highlight") is False and
                    evidence.get("original_script_tts_matches_draft_fragment") is True,
                    "Acoustic receipt narration/source integrity failed")
            measured = evidence.get("word_timing_hypothesis_available") is True
            first = evidence.get("first_matched_real_audio_second")
            last = evidence.get("last_matched_real_audio_second")
            if measured:
                require(type(first) in (int, float) and
                        type(last) in (int, float) and
                        0 <= first < last <= original_row["actual_original_PCM_duration_s"] + .02 and
                        evidence.get("actual_ASR_aligned_anchor_count", 0) >= 2,
                        "Acoustic time cannot be proved from measured words")
                total_timed += 1
            else:
                require(first is None and last is None,
                        "Acoustically unanchored sentence has invented time")
            candidates = ranked_pdf_candidates(sentence["narration_fragment"], targets)
            prioritized = measured and len(candidates) >= 1 and (
                len(candidates) == 1 or
                candidates[0]["review_priority_score_not_probability"] -
                candidates[1]["review_priority_score_not_probability"] >= .12)
            total_prioritized += int(prioritized)
            units.append({
                "sentence_index": sentence["sentence_index"],
                "spoken_original_fragment_sha256": sentence["narration_fragment_sha256"],
                "actual_recorded_word_start_second": first,
                "actual_recorded_word_end_second": last,
                "unprompted_acoustic_word_anchor_count":
                    evidence["actual_ASR_aligned_anchor_count"],
                "source_pdf_geometry_recomputed": True,
                "candidate_targets": candidates,
                "unique_target_review_priority": bool(prioritized),
                "spoken_words_complete_verified": False,
                "speech_to_visible_math_semantics_approved": False,
                "eligible_for_final_student_highlight": False,
            })
        output_slides.append({"slide": index, "source_wav_sha256":
                             saved_wavs[f"slide{index}.wav"],
                             "candidate_segments": units,
                             "complete_element_sync_approved": False})
    result = {
        "schema_version": 1,
        "status": "REAL_SOURCE_PDF_ACOUSTIC_VISUAL_WORKLIST_NOT_SEMANTICALLY_APPROVED",
        "source_pdf_sha256": EXPECTED_SOURCE_SHA,
        "pr332_timing_receipt_sha256": file_hash(timeline),
        "historical_slides_covered": 16,
        "measured_acoustic_sentence_time_hypotheses": total_timed,
        "uniquely_prioritized_pdf_review_targets": total_prioritized,
        "academic_source_math_approved": False,
        "complete_element_synchronization_approved": False,
        "student_publication_authorized": False,
        "paid_service_requests": 0,
        "slides": output_slides,
    }
    # Recheck unchanged before committing an exclusive external receipt.
    for name, sha in {**hashes, **saved_wavs}.items():
        require(file_hash(root / name) == sha, "Source changed during PDF mapping")
    with out.open("x", encoding="utf8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--timing-receipt", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    outcome = build_real_pdf_mapping_worklist(
        original=args.original, timing_receipt=args.timing_receipt, output=args.out)
    print(json.dumps({key: value for key, value in outcome.items()
                      if key != "slides"}, indent=2))


if __name__ == "__main__":
    main()
