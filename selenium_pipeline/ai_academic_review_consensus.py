"""Recheck saved two-pass Gemini scientific source evidence independently.

This is evidence-based AI agreement, not mathematical proof, spoken audio QA,
an invented human review signature, or permission for student publication.
"""
from __future__ import annotations
import json,hashlib
from pathlib import Path
from .figure_source_identity import require,_sha
from .ai_academic_review_queue import _check_queue,_receipt_name
from .ai_academic_web_review import build_review_job
from .pdf_text_source_span_witness import prove_source_quote_occurrence

def _independently_check_saved_pass(*,folder:Path,job:dict,record:dict,mode:str)->list[dict]:
    require(record.get("status")=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
            and record.get("mode")==mode
            and record.get("review_count")==job["utterance_count"]
            and record.get("student_publication_authorized") is False
            and type(record.get("rows")) is list
            and len(record["rows"])==job["utterance_count"],
            "Saved AI review cannot be promoted without original scope")
    goals=[u for s in job["slides"] for u in s["utterances"]]
    targets={s["slide"]:{t["id"]:t for t in s["visual_targets"]} for s in job["slides"]}
    rows=[]
    for original,guess in zip(goals,record["rows"]):
        require(guess.get("utterance_id")==original["id"]
                and guess.get("spoken_sha256")==original["spoken_sha256"]
                and guess.get("verdict") in ("SUPPORTED","INCORRECT","UNRESOLVED")
                and type(guess.get("math_explanation")) is str
                and len(guess["math_explanation"].strip())>=25,
                "Source-bound utterance or distinct academic explanation missing")
        slide=int(original["id"][1:4])
        tid=guess.get("target_id")
        if tid is not None:
            require(tid in targets[slide]
                    and guess.get("text_target_pdf_bbox_pt")==targets[slide][tid]["bbox_pdf_pt"],
                    "Original visible target is not identical to the real PDF")
        citation=guess.get("exact_textbook_quote_verified") is True
        if citation:
            prove_source_quote_occurrence(
                source_pdf=folder/"source.pdf",expected_sha256=job["source_sha256"],
                page_number=guess.get("source_page"),
                verbatim_quote=guess.get("verbatim_source_quote"))
        if guess["verdict"]=="SUPPORTED":
            require(tid is not None and citation,
                    "Supported scientific claim must cite original book and actual slide")
        rows.append(guess)
    return rows

def reconcile_actual_review_queue(*,queue_root:Path,folder:Path)->dict:
    queue_root,folder=Path(queue_root).absolute(),Path(folder).absolute()
    plan=json.loads((queue_root/"queue.json").read_text(encoding="utf8"))
    require(plan.get("status")=="IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE"
            and plan.get("original_source_folder")==str(folder),"Untrusted queue identity")
    accepted=[];unresolved=[];total=0;first_completed=0;challenge_completed=0
    for row in plan["slide_jobs"]:
        slide=row["slide"]
        _check_queue(queue_root=queue_root,folder=folder,slide=slide,mode="INITIAL_REVIEW")
        job=build_review_job(folder=folder,slide_numbers=[slide])
        total+=job["utterance_count"]
        first=queue_root/_receipt_name(slide,"INITIAL_REVIEW")
        second=queue_root/_receipt_name(slide,"INDEPENDENT_CHALLENGE")
        if not first.is_file():
            unresolved.extend({"utterance_id":u["id"],"reason":"NO_INITIAL_SOURCE_REVIEW"}
                              for s in job["slides"] for u in s["utterances"])
            require(not second.exists(),"Challenge cannot precede initial")
            continue
        primary=json.loads(first.read_text(encoding="utf8"))
        a=_independently_check_saved_pass(folder=folder,job=job,record=primary,mode="INITIAL_REVIEW")
        first_completed+=len(a)
        if not second.is_file():
            unresolved.extend({"utterance_id":u["id"],"reason":"MISSING_SECOND_INDEPENDENT_AI_PASS"}
                              for s in job["slides"] for u in s["utterances"])
            continue
        challenging=json.loads(second.read_text(encoding="utf8"))
        b=_independently_check_saved_pass(folder=folder,job=job,record=challenging,mode="INDEPENDENT_CHALLENGE")
        challenge_completed+=len(b)
        require(_sha(first)!=_sha(second),"Identical AI response receipts cannot prove independence")
        for original,x,y in zip(job["slides"][0]["utterances"],a,b):
            agreed=(x["verdict"]==y["verdict"]=="SUPPORTED"
                    and x["target_id"]==y["target_id"] and x["target_id"] is not None
                    and x["source_page"]==y["source_page"]
                    and x["exact_textbook_quote_verified"] is True
                    and y["exact_textbook_quote_verified"] is True
                    and x["math_explanation"].strip()!=y["math_explanation"].strip())
            if not agreed:
                unresolved.append({"utterance_id":original["id"],"reason":"UNRESOLVED_SOURCE_MATH_AI_DISAGREEMENT"})
                continue
            accepted.append({"utterance_id":original["id"],
                             "original_spoken_sha256":original["spoken_sha256"],
                             "selected_target_id":x["target_id"],
                             "selected_bbox_pdf_pt":x["text_target_pdf_bbox_pt"],
                             "source_pdf_page":x["source_page"],
                             "independent_citations":[x["verbatim_source_quote"],y["verbatim_source_quote"]],
                             "two_different_original_source_explanations":True,
                             "author_human_attestation":False})
    require(total==plan["expected_utterances"]
            and len(accepted)+len(unresolved)==total,
            "Original review queue silently omitted an utterance")
    return {"status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
            "original_utterances":total,"initial_ai_reviewed":first_completed,
            "challenge_ai_reviewed":challenge_completed,
            "agreed_source_witnessed_segments":len(accepted),
            "pending_or_disputed":len(unresolved),
            "accepted_ai_evidence":accepted,"unresolved":unresolved,
            "AI_consensus_is_formal_math_proof":False,
            "authentic_human_academic_approval":False,
            "real_tts_speech_generated":False,
            "student_publication_authorized":False}
