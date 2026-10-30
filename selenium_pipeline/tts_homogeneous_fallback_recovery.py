"""Offline Flash-Lite/Kore 3-attempt recovery and homogeneous-voice fallback.

No TTS provider is called; this is NOT paid-service authorization. Crucially,
one voice/model must cover the whole output; never mix primary Kore WAVs with
Cloud Chirp/Kore WAVs in one lecture, and unknown provider outcomes cannot be
silently treated as failures.
"""
from __future__ import annotations
import re
from .incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE
from .tts_effective_identity import CHIRP,CLOUD_KORE

class TTSFallbackRecoveryError(ValueError):pass
HEX=re.compile(r"[0-9a-f]{64}\Z")

def plan_full_batch_tts_recovery(*,jobs:dict,history:list[dict])->dict:
    if (type(jobs) is not dict
        or jobs.get("status")!="REVIEWED_ELEMENT_CHUNK_REQUESTS_NOT_YET_DISPATCHED"
        or jobs.get("model")!=DEFAULT_MODEL or jobs.get("voice")!=DEFAULT_VOICE
        or jobs.get("paid_tts_execution_authorized") is not False
        or jobs.get("student_publication_authorized") is not False
        or type(jobs.get("chunk_jobs")) is not list
        or jobs.get("job_count")!=len(jobs["chunk_jobs"])
        or not 1<=len(jobs["chunk_jobs"])<=500
        or type(history) is not list):
        raise TTSFallbackRecoveryError("Unapproved, oversized or paid original TTS job scope")
    expected=[x.get("job_id") for x in jobs["chunk_jobs"] if type(x) is dict]
    if (len(expected)!=len(jobs["chunk_jobs"])
        or len(set(expected))!=len(expected)
        or any(type(x) is not str or not x for x in expected)):
        raise TTSFallbackRecoveryError("Unsafe or duplicated original utterance IDs")
    if len(history)>3*len(expected):
        raise TTSFallbackRecoveryError("Unbounded TTS attempt journal")
    per_job={k:[] for k in expected}
    for row in history:
        if type(row) is not dict or row.get("job_id") not in per_job:
            raise TTSFallbackRecoveryError("Unexpected job evidence")
        for field,value in (("model",DEFAULT_MODEL),("voice",DEFAULT_VOICE)):
            if row.get(field)!=value:
                raise TTSFallbackRecoveryError("Mixed primary TTS models or voices prohibited")
        if (type(row.get("attempt")) is not int or
            row["attempt"]!=len(per_job[row["job_id"]])+1 or
            row["attempt"]>3):
            raise TTSFallbackRecoveryError("Attempt sequence missing, duplicated or over three")
        if row.get("result") not in ("VERIFIED_TERMINAL_FAILURE","UNKNOWN_OUTCOME","CONFIRMED_SUCCESS"):
            raise TTSFallbackRecoveryError("Unverified model failure category")
        if row["result"]=="VERIFIED_TERMINAL_FAILURE":
            if (row.get("same_owned_provider_request") is not True
                or type(row.get("evidence_sha256")) is not str
                or not HEX.fullmatch(row["evidence_sha256"])):
                raise TTSFallbackRecoveryError("Terminal failure needs provider-specific actual evidence")
        per_job[row["job_id"]].append(row)
    if any(any(row["result"]=="UNKNOWN_OUTCOME" for row in rows)
           for rows in per_job.values()):
        status="HALTED_UNKNOWN_PROVIDER_OUTCOME_NO_RETRY"
    elif any(any(row["result"]=="CONFIRMED_SUCCESS" for row in rows)
             for rows in per_job.values()):
        status="PARTIAL_PRIMARY_SUCCESS_REQUIRES_NEW_HOMOGENEOUS_BATCH"
    elif all(len(rows)==3 and all(row["result"]=="VERIFIED_TERMINAL_FAILURE"
                                 for row in rows)
             for rows in per_job.values()):
        status="ELIGIBLE_TO_PLAN_FULL_CLOUD_KORE_REGENERATION_NOT_DISPATCHED"
    else:
        status="FLASH_LITE_KORE_ATTEMPTS_PENDING_WITHIN_3"
    ready=status=="ELIGIBLE_TO_PLAN_FULL_CLOUD_KORE_REGENERATION_NOT_DISPATCHED"
    return {"status":status,"original_utterances":len(expected),
            "verified_failures_per_job":{key:sum(x["result"]=="VERIFIED_TERMINAL_FAILURE"
                                                 for x in rows)
                                         for key,rows in per_job.items()},
            "all_elements_must_be_regenerated_as_one_voice":ready,
            "full_batch_regeneration_jobs":expected if ready else [],
            "fallback_candidate_model":CHIRP if ready else None,
            "fallback_candidate_voice":CLOUD_KORE if ready else None,
            "existing_primary_wavs_may_be_mixed_into_fallback":False,
            "voice_acoustic_equivalence_independently_verified":False,
            "human_listening_QA_required":True,
            "provider_request_authorized_by_this_plan":False,
            "paid_service_authorized_by_this_plan":False,
            "student_publication_authorized":False}
