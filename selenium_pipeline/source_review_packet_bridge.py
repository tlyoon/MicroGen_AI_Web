"""Independent complete reviewer-worklist bridge; no synthetic approvals.

Exports every original utterance as an individually reviewable PDF-evidence row.
Imports only explicitly attested choices through the existing exact-page
source quote validator; no missing assignment becomes a silent approval.
"""
from __future__ import annotations
import json
from pathlib import Path
from .figure_source_identity import require,_sha
from .source_grounded_element_hints import source_evidence_worklist
from .incremental_nonliteral_selection import validate_explicit_element_choices
from .incremental_element_candidate_map import candidate_map

def export_review_packet(*,folder:Path,output:Path)->dict:
    folder,output=Path(folder).absolute(),Path(output).absolute()
    require(output.suffix==".json" and output.parent.is_dir()
            and not output.exists() and not output.is_relative_to(folder),
            "Only export into a new independent external review file")
    evidence=source_evidence_worklist(folder=folder)
    choices=[{"utterance_id":u["utterance_id"],
              "spoken_text_sha256":u["spoken_text_sha256"],
              "source_page_suggestions":sorted({n for t in u["candidate_source_hints"]
                                                      for n in t["source_pages_with_lexical_overlap"]}),
              "candidate_targets":u["candidate_source_hints"],
              "review_target_id":None,
              "source_page":None,"verbatim_source_quote":None,
              "reviewer_attestation":False,"reviewer_id":None}
             for u in evidence["entries"]]
    result={"status":"UNSIGNED_EXPLICIT_ELEMENT_REVIEW_PACKET",
            "original_source_sha256":evidence["source_sha256"],
            "original_slides_sha256":evidence["slides_sha256"],
            "original_script_sha256":evidence["script_sha256"],
            "utterance_count":evidence["utterance_count"],
            "review_items":choices,
            "all_math_semantics_approved":False,
            "tts_billing_authorized":False,"student_publication_authorized":False}
    with output.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    return result

def validate_signed_review_packet(*,folder:Path,packet:dict)->dict:
    folder=Path(folder).absolute()
    base=source_evidence_worklist(folder=folder)
    require(type(packet) is dict and packet.get("status")=="UNSIGNED_EXPLICIT_ELEMENT_REVIEW_PACKET"
            and packet.get("utterance_count")==base["utterance_count"]
            and packet.get("original_source_sha256")==base["source_sha256"]
            and packet.get("original_slides_sha256")==base["slides_sha256"]
            and packet.get("original_script_sha256")==base["script_sha256"]
            and packet.get("tts_billing_authorized") is False
            and packet.get("student_publication_authorized") is False
            and type(packet.get("review_items")) is list
            and len(packet["review_items"])==base["utterance_count"],
            "Missing or stale full-original reviewed packet")
    decisions=[]
    for given,actual in zip(packet["review_items"],base["entries"]):
        require(type(given) is dict
                and given.get("utterance_id")==actual["utterance_id"]
                and given.get("spoken_text_sha256")==actual["spoken_text_sha256"]
                and given.get("candidate_targets")==actual["candidate_source_hints"]
                and given.get("source_page_suggestions")==sorted({
                    n for t in actual["candidate_source_hints"]
                    for n in t["source_pages_with_lexical_overlap"]}),
                "Packet target geometry, evidence or utterance order was changed")
        selected=given.get("review_target_id")
        if selected is None:
            require(given.get("reviewer_attestation") is False
                    and given.get("source_page") is None
                    and given.get("verbatim_source_quote") is None
                    and given.get("reviewer_id") is None,
                    "Unreviewed entries must not carry forged approval signals")
            continue
        require(type(selected) is str
                and selected in [t["target_id"] for t in actual["candidate_source_hints"]],
                "Explicit selected target must be a real slide element")
        decisions.append({
            "utterance_id":given["utterance_id"],
            "spoken_text_sha256":given["spoken_text_sha256"],
            "target_id":selected,
            "source_page":given.get("source_page"),
            "verbatim_source_quote":given.get("verbatim_source_quote"),
            "reviewer_attestation":given.get("reviewer_attestation"),
            "reviewer_id":given.get("reviewer_id")})
    verified=validate_explicit_element_choices(
        folder=folder,choices=decisions,candidates=candidate_map(folder=folder))
    require(verified["reviewed_utterance_count"]==len(decisions),
            "Reviewer choice reconciliation mismatch")
    return {"status":"RECONCILED_SOURCE_REVIEW_PACKET_PARTIAL_APPROVAL",
            "source_bound_validated_choices":verified,
            "reviewed_utterances":len(decisions),
            "unreviewed_utterances":base["utterance_count"]-len(decisions),
            "all_utterance_math_semantics_machine_proven":False,
            "tts_billing_authorized":False,
            "student_publication_authorized":False}
