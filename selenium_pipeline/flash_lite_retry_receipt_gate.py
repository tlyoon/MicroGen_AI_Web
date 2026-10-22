"""Verify actual Flash-Lite/Kore attempt receipts before proposing Cloud fallback.

Do not invent attempts or infer same speaker voice from provider label.
"""
from __future__ import annotations
import re
from .figure_source_identity import require
from .incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE

def inspect_primary_tts_attempts(*,job:dict,attempts:list[dict])->dict:
    require(type(job) is dict and type(attempts) is list
            and 0<=len(attempts)<=3
            and type(job.get("job_id")) is str and job["job_id"]
            and type(job.get("spoken_text_sha256")) is str
            and re.fullmatch("[a-f0-9]{64}",job["spoken_text_sha256"]),
            "Actual original spoken job identity and bounded attempt evidence required")
    encountered=set();failed=0;succeeded=0
    for i,e in enumerate(attempts,1):
        require(type(e) is dict and e.get("job_id")==job["job_id"]
                and e.get("spoken_text_sha256")==job["spoken_text_sha256"]
                and e.get("model")==DEFAULT_MODEL and e.get("voice")==DEFAULT_VOICE
                and e.get("attempt_number")==i
                and type(e.get("execution_id")) is str
                and re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}",e["execution_id"])
                and e["execution_id"] not in encountered
                and e.get("result") in ("OBSERVED_FAILURE","OBSERVED_SUCCESS")
                and e.get("provider_receipt_attached") is True
                and (succeeded==0),
                "Cannot count duplicate, invented, mixed-voice or post-success attempts")
        encountered.add(e["execution_id"])
        failed+=(e["result"]=="OBSERVED_FAILURE")
        succeeded+=(e["result"]=="OBSERVED_SUCCESS")
    return {"status":"ACTUAL_PRIMARY_FLASH_LITE_RETRY_RECEIPTS_RECONCILED",
            "primary_model":DEFAULT_MODEL,"primary_voice":DEFAULT_VOICE,
            "observed_failure_count":failed,"observed_success_count":succeeded,
            "may_consider_cloud_fallback":failed==3 and succeeded==0,
            "cloud_fallback_execution_authorized":False,
            "same_voice_across_providers_independently_proven":False,
            "student_publication_authorized":False}
