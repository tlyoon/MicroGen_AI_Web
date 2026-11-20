"""Real queue reviewer consensus to original-verbatim primary Kore TTS handoff.

No paid provider dispatch, no same-speaker claim, no student release.
"""
from __future__ import annotations
import json
from pathlib import Path
from .figure_source_identity import require,_sha
from .ai_academic_review_consensus import reconcile_actual_review_queue
from .ai_academic_web_review import build_review_job
from .ai_reviewed_audio_qa import prepare_original_ai_tts_jobs
from .incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE

def prepare_real_source_ai_kore_jobs(*,folder:Path,queue_root:Path,
                                    destination:Path|None=None)->dict:
    folder=Path(folder).absolute()
    queue_root=Path(queue_root).absolute()
    check=reconcile_actual_review_queue(queue_root=queue_root,folder=folder)
    require(check.get("student_publication_authorized") is False
            and check.get("AI_consensus_is_formal_math_proof") is False,
            "Independent AI mathematical review must retain correct limitations")
    source=json.loads((queue_root/"queue.json").read_text(encoding="utf8"))
    approved={x["utterance_id"]:x for x in check["accepted_ai_evidence"]}
    requests=[]
    unresolved=[]
    for row in source["slide_jobs"]:
        job=build_review_job(folder=folder,slide_numbers=[row["slide"]])
        u=job["slides"][0]["utterances"]
        decisions=[]
        for item in u:
            accepted=approved.get(item["id"])
            decisions.append({"utterance_id":item["id"],
                              "spoken_sha256":item["spoken_sha256"],
                              "ai_double_pass_source_witnessed":bool(accepted),
                              "target_id":accepted["selected_target_id"] if accepted else None,
                              "target_bbox_pdf_pt":accepted["selected_bbox_pdf_pt"] if accepted else None})
        consensus={"status":"AI_DOUBLE_PASS_SOURCE_WITNESSED_ELEMENT_REVIEW",
            "source_sha256":job["source_sha256"],
            "slides_sha256":job["slides_sha256"],
            "script_sha256":job["script_sha256"],
            "original_utterance_count":job["utterance_count"],"items":decisions}
        partial=prepare_original_ai_tts_jobs(folder=folder,job=job,consensus=consensus)
        requests.extend(partial["jobs"])
        unresolved.extend(partial["unresolved"])
    require(len(requests)==len(approved)
            and len(requests)+len(unresolved)==check["original_utterances"]
            and len(set(x["job_id"] for x in requests))==len(requests)
            and all(x["model"]==DEFAULT_MODEL and x["voice"]==DEFAULT_VOICE for x in requests),
            "Real source reviewed utterance coverage cannot silently change")
    report={"status":"AI_SOURCE_CITED_VERBATIM_KORE_TTS_HANDOFF_NOT_DISPATCHED",
            "source_sha256":_sha(folder/"source.pdf"),
            "slides_sha256":_sha(folder/"slides.pdf"),
            "script_sha256":_sha(folder/"script.txt"),
            "narration_total":check["original_utterances"],
            "AI_source_agreed_segments":len(requests),
            "unresolved_source_segments":len(unresolved),
            "unresolved_utterance_ids":unresolved,
            "primary_model":DEFAULT_MODEL,"primary_voice":DEFAULT_VOICE,
            "actual_verbatim_jobs":requests,"real_WAV_chunks_observed":0,
            "paid_TTS_request_made":False,
            "production_release_allowed":False,
            "student_publication_authorized":False}
    if destination is not None:
        destination=Path(destination).absolute()
        require(destination.parent.is_dir() and not destination.exists()
                and destination.suffix==".json" and
                not destination.is_relative_to(folder),
                "New external, non-overwriting real-TTS handoff destination required")
        with destination.open("x",encoding="utf8") as f:
            json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    return report
