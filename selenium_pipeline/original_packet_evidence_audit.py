"""Fail-closed original-asset review-packet completeness and geometry audit.

This audits evidence candidates, never accepts scientific interpretation.
"""
from __future__ import annotations
import json,math,re
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha

def audit_original_review_packet(*,folder:Path,packet:dict)->dict:
    folder=Path(folder).absolute()
    require(folder.is_dir() and not folder.is_symlink() and type(packet) is dict
            and packet.get("status")=="UNSIGNED_EXPLICIT_ELEMENT_REVIEW_PACKET"
            and packet.get("tts_billing_authorized") is False
            and packet.get("student_publication_authorized") is False,
            "A source-bound unsigned review packet is required")
    for file,key in (("source.pdf","original_source_sha256"),
                     ("slides.pdf","original_slides_sha256"),
                     ("script.txt","original_script_sha256")):
        require(_sha(folder/file)==packet.get(key),"Source identity changed")
    rows=packet.get("review_items")
    require(type(rows) is list and len(rows)==packet.get("utterance_count")
            and len(rows)>0,"Incomplete original narration review packet")
    seen=set();with_candidate=0;unreviewed=0;zero_candidate=[]
    with pymupdf.open(folder/"slides.pdf") as deck:
        for row in rows:
            uid=row.get("utterance_id")
            require(type(uid) is str and re.fullmatch(
                r"s\d{3}\.utterance\.\d{3}",uid)
                and uid not in seen and type(row.get("spoken_text_sha256")) is str
                and re.fullmatch("[a-f0-9]{64}",row["spoken_text_sha256"]),
                "Duplicate/unidentified original utterance")
            seen.add(uid)
            index=int(uid[1:4])
            require(1<=index<=len(deck),"Narration slide index out of bounds")
            options=row.get("candidate_targets")
            require(type(options) is list,"Missing target candidate inventory")
            if options:with_candidate+=1
            else:zero_candidate.append(uid)
            target_ids=set()
            for c in options:
                box=c.get("actual_visible_pdf_bbox_pt")
                target=c.get("target_id")
                require(type(target) is str and target not in target_ids
                        and type(box) is list and len(box)==4
                        and all(type(z) in (int,float) and math.isfinite(z) for z in box),
                        "Target identity/geometry invalid")
                target_ids.add(target)
                w,h=deck[index-1].rect.width,deck[index-1].rect.height
                require(0<=box[0]<box[2]<=w+.002
                        and 0<=box[1]<box[3]<=h+.002,
                        "Target is outside actual slide")
            if row.get("review_target_id") is None:
                unreviewed+=1
                require(row.get("reviewer_attestation") is False,
                        "Missing target cannot be attested as verified")
    return {"status":"ALL_ORIGINAL_PACKET_IDENTITIES_AND_BBOXES_AUDITED",
            "utterance_count":len(rows),"with_visible_candidates":with_candidate,
            "zero_candidate_ids":zero_candidate,"pending_review_count":unreviewed,
            "human_math_semantics_verified":False,
            "audio_to_element_timing_verified":False,
            "student_publication_authorized":False}
