"""Real slide PDF vector candidates for text-unmatched narration, never semantic approval."""
from __future__ import annotations
from pathlib import Path
import math
import pymupdf
from .figure_source_identity import require,_sha
from .original_packet_evidence_audit import audit_original_review_packet

def inventory_unmatched_pdf_visual_regions(*,folder:Path,packet:dict)->dict:
    folder=Path(folder).absolute()
    baseline=audit_original_review_packet(folder=folder,packet=packet)
    rows=[]
    with pymupdf.open(folder/"slides.pdf") as deck:
        for row in packet["review_items"]:
            if row["candidate_targets"]:continue
            uid=row["utterance_id"]
            slide=int(uid[1:4])
            pg=deck[slide-1]
            regions=[]
            for i,d in enumerate(pg.get_drawings()):
                rect=d.get("rect")
                if not rect:continue
                box=[round(float(v),3) for v in rect]
                if not all(math.isfinite(v) for v in box):continue
                if box[2]-box[0]<6 or box[3]-box[1]<6:continue
                if not (0<=box[0]<box[2]<=pg.rect.width+.002 and
                        0<=box[1]<box[3]<=pg.rect.height+.002):continue
                regions.append({"drawing_index":i,"actual_pdf_bbox_pt":box,
                                "suggestion_is_a_semantic_math_match":False})
            rows.append({"utterance_id":uid,"slide":slide,
                         "source_pdf_sha256":_sha(folder/"slides.pdf"),
                         "actual_pdf_vector_regions":regions[:40],
                         "regions_truncated":len(regions)>40,
                         "selected_region":None,"math_review_approved":False})
    require(len(rows)==len(baseline["zero_candidate_ids"]) and
            all(r["utterance_id"] in baseline["zero_candidate_ids"] for r in rows),
            "Missing all original narration gaps")
    return {"status":"ORIGINAL_PDF_DRAWING_REGIONS_FOR_UNMATCHED_UTTERANCES_ONLY",
            "unmatched_utterance_count":len(rows),"rows":rows,
            "original_source_verified":True,"semantic_matching_verified":False,
            "tts_authorized":False,"publication_authorized":False}
