"""Evidence-first prioritization from actual source-hashed review rows.

Owner approval permits doing checks, not fabrication of finished checks.
"""
from __future__ import annotations
from pathlib import Path
from .original_packet_evidence_audit import audit_original_review_packet
from .pdf_drawing_fallback_inventory import inventory_unmatched_pdf_visual_regions
from .figure_source_identity import require

def build_manual_review_triage(*,folder:Path,packet:dict,
                               owner_allows_review:bool)->dict:
    require(owner_allows_review is True,"Explicit owner permission required")
    base=audit_original_review_packet(folder=folder,packet=packet)
    drawings=inventory_unmatched_pdf_visual_regions(folder=folder,packet=packet)
    vector={x["utterance_id"]:x for x in drawings["rows"]}
    queue=[]
    for row in packet["review_items"]:
        uid=row["utterance_id"]
        n=len(row["candidate_targets"])
        extra=vector.get(uid,{})
        npaths=len(extra.get("actual_pdf_vector_regions",[]))
        queue.append({"utterance_id":uid,
                      "original_spoken_text_sha256":row["spoken_text_sha256"],
                      "priority":"MISSING_TEXT_TARGET" if n==0 else (
                          "AMBIGUOUS_TARGETS" if n>1 else "SOURCE_SEMANTICS_REVIEW"),
                      "verified_visible_text_candidate_count":n,
                      "unassigned_vector_candidate_count":npaths,
                      "source_page_hints_are_proof":False,
                      "manual_mathematical_review_completed":False})
    queue.sort(key=lambda q:({"MISSING_TEXT_TARGET":0,"AMBIGUOUS_TARGETS":1,
                              "SOURCE_SEMANTICS_REVIEW":2}[q["priority"]],
                             q["utterance_id"]))
    return {"status":"OWNER_AUTHORIZED_INDEPENDENT_MATH_REVIEW_TRIAGE",
            "utterance_count":base["utterance_count"],
            "candidate_free_count":len(base["zero_candidate_ids"]),
            "review_queue":queue,"signed_source_review_decision_count":0,
            "owner_approval_is_math_evidence":False,"tts_authorized":False,
            "student_publication_authorized":False}
