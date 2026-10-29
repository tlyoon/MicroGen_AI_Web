"""Exact PCM-sample, per-element grouping with strict output-duration margin.

This plans separately generated and verified PCM chunks; it is not a speech
alignment algorithm and does not claim final encoded MP4 acceptance.
"""
from __future__ import annotations
from .figure_source_identity import require

def plan_verified_element_pcm_parts(*,clips:list[dict],maximum_pcm_s:float=540)->dict:
    require(type(clips) is list and 1<=len(clips)<=500
            and type(maximum_pcm_s) in (float,int) and 1<=maximum_pcm_s<=540,
            "Bounded original-voice external PCM segments and duration limit required")
    seen=set();rate=None;groups=[];part=[];running=0;start=0
    for c in clips:
        require(type(c) is dict and type(c.get("job_id")) is str
                and c["job_id"] and c["job_id"] not in seen
                and type(c.get("sample_frames")) is int and c["sample_frames"]>0
                and type(c.get("sample_rate")) is int
                and 8000<=c["sample_rate"]<=96000,
                "Duplicate original utterance or unverifiable sample counter")
        seen.add(c["job_id"])
        if rate is None:rate=c["sample_rate"]
        require(c["sample_rate"]==rate and
                0.15<=c["sample_frames"]/rate<120
                and c["sample_frames"]/rate<maximum_pcm_s,
                "Original PCM audio sample rate or individual chunk duration incompatible")
        frames=c["sample_frames"]
        if part and (running+frames)/rate>=maximum_pcm_s:
            groups.append({"part_number":len(groups)+1,"sample_rate":rate,
                           "total_pcm_frames":running,
                           "exact_pcm_seconds":running/rate,
                           "events":part})
            part=[];running=0
        part.append({"job_id":c["job_id"],
                     "part_pcm_start_frame":running,
                     "part_pcm_end_frame":running+frames,
                     "exact_part_pcm_start_seconds":running/rate,
                     "exact_part_pcm_end_seconds":(running+frames)/rate})
        running+=frames
    groups.append({"part_number":len(groups)+1,"sample_rate":rate,
                   "total_pcm_frames":running,"exact_pcm_seconds":running/rate,
                   "events":part})
    require(all(0<p["exact_pcm_seconds"]<maximum_pcm_s and
                p["exact_pcm_seconds"]<600 for p in groups)
            and sum(len(p["events"]) for p in groups)==len(clips),
            "Part splitting must preserve every exact original utterance once")
    return {"status":"EXACT_EXTERNAL_ELEMENT_PCM_MULTIPART_TIMELINE_REVIEW_ONLY",
            "total_original_element_chunks":len(clips),"proposed_part_count":len(groups),
            "parts":groups,
            "actual_encoded_MP4_duration_verified":False,
            "spoken_text_fidelity_verified":False,
            "student_publication_authorized":False}
