"""Reconcile two independently staged original WAV multipart technical preview batches."""
from pathlib import Path
from .figure_source_identity import require
from .original_multipart_stage_audit import audit_whole_slide_staging
from .original_wav_multipart_plan import inspect_original_slide_wav_plan

def audit_two_part_preview_sets(*,root:Path,first_stage:Path,
                                 second_stage:Path,names:tuple[str,...])->dict:
    root=Path(root).absolute()
    first_stage,second_stage=Path(first_stage).absolute(),Path(second_stage).absolute()
    require(first_stage!=second_stage
            and not first_stage.is_relative_to(second_stage)
            and not second_stage.is_relative_to(first_stage),
            "Independent part stage must not reuse another review output")
    first=audit_whole_slide_staging(root=root,staged=first_stage,
                                    names=names,start_part=1)
    second=audit_whole_slide_staging(root=root,staged=second_stage,
                                     names=names,start_part=2)
    items=[]
    for a,b in zip(first["items"],second["items"]):
        require(a["name"]==b["name"],"Subchapter reordering")
        expected=inspect_original_slide_wav_plan(root/a["name"])["proposed_parts"]
        combined=(a["verified_original_whole_slide_review_parts"]
                  + b["verified_original_whole_slide_review_parts"])
        ids=[x["part_id"] for x in combined]
        require(len(ids)==len(set(ids))
                and ids==[x["part_id"] for x in expected],
                "Missing, repeated or reordered complete original WAV video parts")
        items.append({"subchapter":a["name"],
                      "verified_original_pcm_preview_part_count":len(combined),
                      "actual_encoded_part_seconds":[x["actual_encoded_duration_s"]
                                                     for x in combined],
                      "all_parts_strictly_under_600":all(
                          0<x["actual_encoded_duration_s"]<600 for x in combined),
                      "spoken_to_element_highlight_timing_verified":False})
    return {"status":"COMPLETE_GENUINE_ORIGINAL_PCM_PREVIEWS_REVIEW_ONLY",
            "items":items,
            "verified_review_mp4_part_count":sum(
                x["verified_original_pcm_preview_part_count"] for x in items),
            "actual_element_tts_jobs_generated":0,
            "source_math_and_visual_semantic_approval":False,
            "real_spoken_element_highlight_sync_verified":False,
            "human_academic_listening_qa_verified":False,
            "student_publication_authorized":False}
