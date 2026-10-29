"""Fail-closed original Thomas narrated-element production readiness accounting.

Blanket review permission never substitutes for validated per-utterance
math/correct pronunciation; whole-slide PCM preview is not element sync.
"""
from __future__ import annotations
from pathlib import Path
from .figure_source_identity import require
from .original_packet_evidence_audit import audit_original_review_packet
from .pdf_drawing_fallback_inventory import inventory_unmatched_pdf_visual_regions

def audit_series_element_production_readiness(*,folders:dict[str,Path],
                                               packets:dict[str,dict],
                                               owner_allows_manual_review:bool)->dict:
    require(owner_allows_manual_review is True
            and type(folders) is dict and type(packets) is dict
            and set(folders)==set(packets)=={"8.4","8.5","8.6"},
            "Owner authorization and exact real original subchapters required")
    topics=[];total=0;candidate_missing=0;pending=0
    for name in ("8.4","8.5","8.6"):
        base=audit_original_review_packet(folder=folders[name],packet=packets[name])
        extra=inventory_unmatched_pdf_visual_regions(folder=folders[name],
                                                      packet=packets[name])
        require(extra["unmatched_utterance_count"]==len(base["zero_candidate_ids"]),
                "Original PDF target coverage divergence")
        total+=base["utterance_count"]
        candidate_missing+=len(base["zero_candidate_ids"])
        pending+=base["pending_review_count"]
        topics.append({"subchapter":name,
                       "original_utterance_count":base["utterance_count"],
                       "unreviewed_math_utterances":base["pending_review_count"],
                       "missing_text_element_candidates":len(base["zero_candidate_ids"]),
                       "possible_pdf_vector_regions_unattested":sum(
                           len(x["actual_pdf_vector_regions"]) for x in extra["rows"]),
                       "source_math_semantics_approved":False,
                       "real_per_element_audio_approved":False,
                       "student_ready":False})
    require(total==218,"Original baseline narration has changed; rerun source audit")
    return {"status":"REAL_THOMAS_SOURCE_ASSETS_REAUDITED_RELEASE_BLOCKED",
            "source_utterance_count":total,
            "text_candidate_gaps":candidate_missing,
            "human_review_decisions_pending":pending,
            "owner_authorized_continuation_of_checks":True,
            "all_math_checks_independently_completed":False,
            "actual_individual_element_voice_PCM_verified":False,
            "strict_encoded_element_video_acceptance_verified":False,
            "academic_listening_qa_verified":False,
            "student_publication_authorized":False,
            "topics":topics}
