"""PDF-vector aware Gemini review work, then conservative two-pass AI consensus.

Independent MODEL agreement is never presumed. The two response artifacts
are separate passes; independently verified source geometry/quotes remain
hard gates. Does not forge a human signature or student release.
"""
from __future__ import annotations
import json
from pathlib import Path
from .figure_source_identity import require,_sha
from .ai_academic_web_review import build_review_job,validate_model_review
from .pdf_drawing_fallback_inventory import inventory_unmatched_pdf_visual_regions
from .original_packet_evidence_audit import audit_original_review_packet

def add_real_pdf_vector_options(*,folder:Path,job:dict,packet:dict)->dict:
    folder=Path(folder).absolute()
    require(job["source_sha256"]==_sha(folder/"source.pdf")
            and job["slides_sha256"]==_sha(folder/"slides.pdf")
            and job["script_sha256"]==_sha(folder/"script.txt"),
            "Original PDF identity must remain exact for vector options")
    audit_original_review_packet(folder=folder,packet=packet)
    vector=inventory_unmatched_pdf_visual_regions(folder=folder,packet=packet)
    entries={x["utterance_id"]:x for x in vector["rows"]}
    extended=json.loads(json.dumps(job))
    for slide in extended["slides"]:
        existing={x["id"] for x in slide["visual_targets"]}
        for utterance in slide["utterances"]:
            if utterance["ranked_candidates"]:continue
            entry=entries.get(utterance["id"])
            if entry is None:continue
            for v in entry["actual_pdf_vector_regions"]:
                key=f"s{slide['slide']:03}.vector.{v['drawing_index']:03}"
                if key not in existing:
                    slide["visual_targets"].append({
                        "id":key,"kind":"pdf_vector_drawing_unreviewed",
                        "bbox_pdf_pt":v["actual_pdf_bbox_pt"],
                        "visible_text":"[Original slide PDF drawing; visually inspect the attached slide]",
                        "independent_visual_semantics_proven":False})
                    existing.add(key)
                utterance["ranked_candidates"].append(key)
    extended["status"]="ORIGINAL_PDF_MULTIMODAL_AI_REVIEW_REQUEST_NOT_DISPATCHED"
    extended["vector_options_are_academic_approval"]=False
    return extended

def reconcile_dual_ai_reviews(*,folder:Path,job:dict,
                              initial:dict,challenge:dict,
                              distinct_review_sessions:bool)->dict:
    require(distinct_review_sessions is True,"Independent separately recorded review sessions required")
    require(initial.get("mode")=="INITIAL_REVIEW"
            and challenge.get("mode")=="INDEPENDENT_CHALLENGE"
            and initial.get("review_count")==challenge.get("review_count")==job["utterance_count"],
            "Distinct complete initial and challenge review receipts required")
    expected=[u for s in job["slides"] for u in s["utterances"]]
    results=[];accepted=0
    for a,b,original in zip(initial["rows"],challenge["rows"],expected):
        require(a["utterance_id"]==b["utterance_id"]==original["id"]
                and a["spoken_sha256"]==b["spoken_sha256"]==original["spoken_sha256"],
                "Cannot reconcile a different original spoken utterance")
        agreed=(a["verdict"]==b["verdict"]=="SUPPORTED"
                and a["target_id"] is not None and a["target_id"]==b["target_id"]
                and a["source_page"]==b["source_page"]
                and a["verbatim_source_quote"]==b["verbatim_source_quote"]
                and a["exact_textbook_quote_verified"] is True
                and b["exact_textbook_quote_verified"] is True
                and a["text_target_pdf_bbox_pt"]==b["text_target_pdf_bbox_pt"]
                and a["math_explanation"].strip()!=b["math_explanation"].strip())
        if agreed:accepted+=1
        results.append({"utterance_id":original["id"],
                        "spoken_sha256":original["spoken_sha256"],
                        "target_id":a["target_id"] if agreed else None,
                        "target_bbox_pdf_pt":a["text_target_pdf_bbox_pt"] if agreed else None,
                        "source_page":a["source_page"] if agreed else None,
                        "source_quote":a["verbatim_source_quote"] if agreed else None,
                        "review_disagreement":not agreed,
                        "ai_double_pass_source_witnessed":agreed,
                        "automatic_scientific_proof":False,
                        "human_reviewer_attested":False})
    require(all(_sha(Path(folder)/filename)==job[key] for filename,key in
                (("source.pdf","source_sha256"),("slides.pdf","slides_sha256"),
                 ("script.txt","script_sha256"))),"Underlying mathematics source changed")
    return {"status":"AI_DOUBLE_PASS_SOURCE_WITNESSED_ELEMENT_REVIEW",
            "original_utterance_count":len(results),
            "ai_two_pass_agreement_count":accepted,
            "unresolved_or_disputed_count":len(results)-accepted,
            "items":results,"source_sha256":job["source_sha256"],
            "slides_sha256":job["slides_sha256"],
            "script_sha256":job["script_sha256"],
            "human_academic_review_completed":False,
            "ai_consensus_is_formal_proof":False,
            "student_publication_authorized":False}
