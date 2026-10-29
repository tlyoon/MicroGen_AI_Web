"""Independently witness attested source page, quote, visual target and spoken SHA.

An owner's global approval is not an utterance-specific scientific review.
"""
from __future__ import annotations
import re
from pathlib import Path
from .figure_source_identity import require
from .original_packet_evidence_audit import audit_original_review_packet
from .pdf_text_source_span_witness import prove_source_quote_occurrence

def audit_attested_math_target_records(*,folder:Path,packet:dict)->dict:
    folder=Path(folder).absolute()
    audit_original_review_packet(folder=folder,packet=packet)
    approved=[];pending=[]
    for row in packet["review_items"]:
        target=row.get("review_target_id")
        if target is None:
            require(row.get("reviewer_attestation") is False
                    and row.get("reviewer_id") is None
                    and row.get("source_page") is None
                    and row.get("verbatim_source_quote") is None,
                    "Unsigned narration cannot masquerade as reviewed")
            pending.append(row["utterance_id"])
            continue
        require(type(target) is str
                and target in [x["target_id"] for x in row["candidate_targets"]]
                and row.get("reviewer_attestation") is True
                and type(row.get("reviewer_id")) is str
                and re.fullmatch(r"[A-Za-z0-9_.-]{3,80}",row["reviewer_id"]),
                "Each mathematical target needs an individually attested original anchor")
        witness=prove_source_quote_occurrence(
            source_pdf=folder/"source.pdf",
            expected_sha256=packet["original_source_sha256"],
            page_number=row.get("source_page"),
            verbatim_quote=row.get("verbatim_source_quote"),
            occurrence_index=row.get("source_occurrence_index"))
        approved.append({"utterance_id":row["utterance_id"],
                         "original_spoken_text_sha256":row["spoken_text_sha256"],
                         "selected_visible_element":target,
                         "textbook_source_witness":witness,
                         "reviewer_id":row["reviewer_id"],
                         "attestation_is_independently_mathematically_proven":False})
    return {"status":"TEXTBOOK_QUOTE_AND_SELECTED_VISIBLE_ELEMENT_WITNESSES",
            "specific_attestations_with_valid_source_evidence":len(approved),
            "unreviewed_count":len(pending),"attested_witnesses":approved,
            "pending_utterances":pending,
            "owner_permission_is_not_scientific_evidence":True,
            "source_math_semantics_independently_verified":False,
            "student_publication_authorized":False}
