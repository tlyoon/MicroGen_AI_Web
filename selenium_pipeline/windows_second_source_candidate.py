"""Independent second-original lecture *technical candidate* comparison.

Input must come from the existing strictly SHA-verified historic scoped source
and newly verified PR507 reviewed-MP4 source, not an asserted grade or a new
publisher model call. A different PDF hash proves distinctness only, never
academic quality, faithful speech, human listening, or release authorization.
"""
from __future__ import annotations

import re

_HISTORICAL = "ONE_SCOPED_HISTORICAL_ORIGINAL_FULL_MEDIA_ACCEPTANCE_REUSED"
_MEDIA = "EXACT_SOURCEBOUND_MP4_TECHNICAL_EVIDENCE_VERIFIED_ONLY"


def compare_source_provenance(*, historic: dict | None,
                              candidate: dict | None) -> dict:
    result = {
        "schema_version": 1,
        "status": "SECOND_SOURCE_PROVENANCE_INCOMPLETE",
        "historical_accepted_reference": False,
        "candidate_technical_media_verified": False,
        "distinct_original_source_sha256_verified": False,
        "technical_second_source_candidate_ready_for_academic_review": False,
        "second_distinct_original_academic_acceptance_verified": False,
        "independent_human_math_figure_audio_signoff": False,
        "release_authorized": False,
        "new_model_or_tts_calls": False,
        "student_publication_authorized": False,
        "outstanding_requirements": [
            "Existing independent historic accepted source reference",
            "Different SHA-bound original source and verified decoded MP4",
            "Source-cited independent AI mathematics and figure-semantic review",
            "Independent AI speech/phonetic checks plus timing, voice and MP4 verification",
            "Complete autonomous academic evidence and separately authorize publication",
        ],
    }
    sha = re.compile(r"[a-f0-9]{64}\Z")
    if type(historic) is not dict or type(candidate) is not dict:
        return result
    a, b = historic.get("source_sha256"), candidate.get("source_sha256")
    hist_ok = (
        historic.get("status") == _HISTORICAL
        and historic.get("accepted_scoped_original_source_count") == 1
        and historic.get("new_independent_second_source_accepted") is False
        and historic.get("student_publication_authorized") is False
        and isinstance(a, str) and sha.fullmatch(a) is not None
    )
    media_ok = (
        candidate.get("status") == _MEDIA
        and candidate.get("technical_sourcebound_mp4_verified") is True
        and type(candidate.get("decoded_mp4_parts_verified")) is int
        and candidate["decoded_mp4_parts_verified"] > 0
        and candidate.get("full_lecture_release_authorized") is False
        and candidate.get("student_publication_authorized") is False
        and candidate.get("new_model_or_tts_calls") is False
        and isinstance(b, str) and sha.fullmatch(b) is not None
    )
    result["historical_accepted_reference"] = hist_ok
    result["candidate_technical_media_verified"] = media_ok
    if not (hist_ok and media_ok):
        return result
    result["historical_source_sha256"] = a
    result["candidate_source_sha256"] = b
    if a == b:
        result["status"] = "SAME_ORIGINAL_SOURCE_CANNOT_BE_SECOND_CANDIDATE"
        return result
    result.update({
        "status": "DISTINCT_SECOND_SOURCE_TECHNICAL_MEDIA_FOR_INDEPENDENT_REVIEW",
        "distinct_original_source_sha256_verified": True,
        "technical_second_source_candidate_ready_for_academic_review": True,
        "outstanding_requirements": [
            "Run source-cited independent two-pass AI mathematics QA",
            "Run AI-assisted original figure, diagram and slide semantic checks",
            "Run independent Gemini audio transcription, phonetic and voice QA",
            "Reverify decoded synchronized MP4s for full coverage and visual meaning",
            "Recompute autonomous original lecture evidence before release",
            "Review stacked code and final Windows release prior to publishing",
        ],
    })
    return result
