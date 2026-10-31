import unittest
from selenium_pipeline.tts_homogeneous_fallback_recovery import (
    plan_full_batch_tts_recovery,TTSFallbackRecoveryError)
from selenium_pipeline.incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE
def fixture():
 return {"status":"REVIEWED_ELEMENT_CHUNK_REQUESTS_NOT_YET_DISPATCHED",
         "model":DEFAULT_MODEL,"voice":DEFAULT_VOICE,"job_count":2,
         "chunk_jobs":[{"job_id":"s001.utterance.001"},{"job_id":"s001.utterance.002"}],
         "paid_tts_execution_authorized":False,
         "student_publication_authorized":False}
def failure(job,index):
 return {"job_id":job,"attempt":index,"model":DEFAULT_MODEL,"voice":DEFAULT_VOICE,
         "result":"VERIFIED_TERMINAL_FAILURE",
         "same_owned_provider_request":True,
         "evidence_sha256":hex(index)[2:]*64 if index==1 else "a"*64}
class Fallback(unittest.TestCase):
 def test_three_independent_actual_failures_for_all_jobs_only(self):
  jobs=fixture()
  rows=[failure(k,n) for k in [x["job_id"] for x in jobs["chunk_jobs"]]
        for n in (1,2,3)]
  r=plan_full_batch_tts_recovery(jobs=jobs,history=rows)
  self.assertEqual(r["status"],"ELIGIBLE_TO_PLAN_FULL_CLOUD_KORE_REGENERATION_NOT_DISPATCHED")
  self.assertEqual(len(r["full_batch_regeneration_jobs"]),2)
  self.assertFalse(r["existing_primary_wavs_may_be_mixed_into_fallback"])
  self.assertFalse(r["paid_service_authorized_by_this_plan"])
 def test_two_failures_do_not_authorize_fallback(self):
  jobs=fixture()
  r=plan_full_batch_tts_recovery(jobs=jobs,
       history=[failure(k,n) for k in [x["job_id"] for x in jobs["chunk_jobs"]]
                for n in (1,2)])
  self.assertEqual(r["status"],"FLASH_LITE_KORE_ATTEMPTS_PENDING_WITHIN_3")
  self.assertEqual(r["full_batch_regeneration_jobs"],[])
 def test_ambiguous_provider_response_and_mixed_model_fail_closed(self):
  jobs=fixture();rows=[failure("s001.utterance.001",1)]
  rows[0]["result"]="UNKNOWN_OUTCOME"
  self.assertEqual(plan_full_batch_tts_recovery(jobs=jobs,history=rows)
       ["status"],"HALTED_UNKNOWN_PROVIDER_OUTCOME_NO_RETRY")
  rows[0]["model"]="chirp3-hd"
  with self.assertRaises(TTSFallbackRecoveryError):
   plan_full_batch_tts_recovery(jobs=jobs,history=rows)
 def test_duplicate_or_unverified_failure_cannot_advance_counter(self):
  jobs=fixture();row=failure("s001.utterance.001",1)
  for records in ([row,row], [{**row,"evidence_sha256":"0"}]):
   with self.assertRaises(TTSFallbackRecoveryError):
    plan_full_batch_tts_recovery(jobs=jobs,history=records)
 def test_partial_success_must_not_mix_kore_corey(self):
  jobs=fixture()
  row=failure("s001.utterance.001",1)
  row["result"]="CONFIRMED_SUCCESS"
  r=plan_full_batch_tts_recovery(jobs=jobs,history=[row])
  self.assertEqual(r["status"],"PARTIAL_PRIMARY_SUCCESS_REQUIRES_NEW_HOMOGENEOUS_BATCH")
  self.assertFalse(r["existing_primary_wavs_may_be_mixed_into_fallback"])
