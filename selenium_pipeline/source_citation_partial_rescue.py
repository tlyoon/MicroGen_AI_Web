"""Recover per-utterance academic evidence from one failed, saved Gemini review.

Does NOT re-send the source or promote unsupported statements, invented quotes
or a partial evidence packet to complete/scientifically accepted status.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

from .source_citation_review_dispatch import inspect_batch
from .ai_academic_web_review import (
    review_instructions,validate_model_review)
from .academic_review_checkpoint import fingerprint,CLAIM_NAME
from .evidence_reuse_contract import file_sha256

class AcademicPartialRecoveryBlocked(ValueError):
    pass

def need(value, message):
    if not value:
        raise AcademicPartialRecoveryBlocked(message)

def salvage(*,manifest_path:Path,job_path:Path,
            checkpoint_dir:Path,out:Path)->dict:
    folder,job=inspect_batch(manifest_path=manifest_path,
                             job_path=job_path,out=out,
                             checkpoint_dir=checkpoint_dir)
    root=Path(checkpoint_dir).absolute()
    claim=root/CLAIM_NAME
    state_p=root/"request_state.json"
    raw_p=root/"model_response_untrusted.txt"
    identity_p=root/"model_response_identity.json"
    need(root.is_dir() and not root.is_symlink()
         and all(p.is_file() and not p.is_symlink()
                 for p in (claim,state_p,raw_p,identity_p)),
         "Only a previously submitted, durably recorded original answer qualifies")
    state=json.loads(state_p.read_text(encoding="utf8"))
    identity=json.loads(identity_p.read_text(encoding="utf8"))
    prompt=review_instructions(job,mode="INITIAL_REVIEW")
    exact=fingerprint(
        request_text=prompt,
        source_hashes={
            "source.pdf":job["source_sha256"],
            "slides.pdf":job["slides_sha256"],
            "script.txt":job["script_sha256"]},
        review_mode="INITIAL_REVIEW")
    raw=raw_p.read_bytes()
    need(0<len(raw)<1_800_000*4
         and state.get("status") in {
             "MODEL_REPLY_OBSERVED_UNVALIDATED",
             "REJECTED_RESPONSE_UNTRUSTED",
             "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"}
         and state.get("request_fingerprint")==exact
         and identity.get("request_fingerprint")==exact
         and state.get("response_sha256")==
             identity.get("response_sha256")==hashlib.sha256(raw).hexdigest()
         and state.get("response_length_chars")==
             identity.get("response_length_chars")==len(raw.decode("utf8"))
         and identity.get("kind")=="SAVED_POST_CLAIM_MODEL_REPLY_V1"
         and identity.get("approved") is False
         and identity.get("new_model_requests") is False
         and all(state.get(k)==identity.get(k)==job.get(k)
                 for k in ("source_sha256","slides_sha256","script_sha256")),
         "Old Gemini reply/source receipt mismatch or missing original Send")
    text=raw.decode("utf8")
    try:
        from .series_gemini import decode_storyboard_response
        response=decode_storyboard_response(text)
    except (ValueError,TypeError,RuntimeError) as exc:
        raise AcademicPartialRecoveryBlocked("Model reply cannot be parsed") from exc
    need(type(response) is dict
         and response.get("status")=="ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE"
         and type(response.get("rows")) is list
         and len(response["rows"])==job["utterance_count"],
         "Original reply missing rows; no partial fabrication")
    original_units=[
        (s,u) for s in job["slides"] for u in s["utterances"]]
    need(len(original_units)==len(response["rows"]),
         "Original utterance inventory changed")
    full_list=job["verified_source_quote_candidates_v1"]["utterances"]
    accepted=[]
    rejected=[]
    for (slide,utterance),reply in zip(original_units,response["rows"]):
        name=utterance["id"]
        if type(reply) is not dict or reply.get("utterance_id")!=name:
            rejected.append({"utterance_id":name,
                             "reason":"RESPONSE_ORDER_OR_IDENTITY_INVALID"})
            continue
        matching=[x for x in full_list
                  if x.get("utterance_id")==name]
        if len(matching)!=1:
            rejected.append({"utterance_id":name,
                             "reason":"ORIGINAL_SOURCE_CANDIDATE_MISSING"})
            continue
        single={**job,
                "utterance_count":1,
                "slides":[{**slide,"utterances":[utterance]}],
                "verified_source_quote_candidates_v1":{
                    **job["verified_source_quote_candidates_v1"],
                    "utterances":matching}}
        one={"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
             "rows":[reply]}
        try:
            result=validate_model_review(
                folder=folder,job=single,response=one,
                mode="INITIAL_REVIEW")
        except (OSError,ValueError,RuntimeError) as exc:
            rejected.append({"utterance_id":name,
                             "reason":"SOURCE_OR_TARGET_EVIDENCE_NOT_PROVEN",
                             "validation_error_type":type(exc).__name__})
            continue
        need(result.get("review_count")==1
             and result.get("student_publication_authorized") is False,
             "Partial source witness cannot be elevated to approval")
        accepted.extend(result["rows"])
    need(len(accepted)+len(rejected)==len(original_units),
         "Partial output omitted an utterance")
    report={
        "schema_version":1,
        "status":"PARTIAL_SOURCE_WITNESSED_AI_REVIEW_NOT_COMPLETE",
        "source_sha256":job["source_sha256"],
        "slides_sha256":job["slides_sha256"],
        "script_sha256":job["script_sha256"],
        "source_batch_job_sha256":file_sha256(Path(job_path)),
        "source_model_response_sha256":hashlib.sha256(raw).hexdigest(),
        "original_dispatch_checkpoint":str(root),
        "original_submission_preserved_no_resend":True,
        "original_utterances":len(original_units),
        "individually_validated":len(accepted),
        "individually_untrusted":len(rejected),
        "supported":sum(r["verdict"]=="SUPPORTED" for r in accepted),
        "unresolved":sum(r["verdict"]=="UNRESOLVED" for r in accepted),
        "incorrect":sum(r["verdict"]=="INCORRECT" for r in accepted),
        "accepted_rows":accepted,
        "untrusted_rows":rejected,
        "full_source_and_math_review_accepted":False,
        "student_publication_authorized":False,
        "new_model_or_tts_requests":0,
    }
    with Path(out).absolute().open("x",encoding="utf8") as stream:
        json.dump(report,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--job",type=Path,required=True)
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        result=salvage(
            manifest_path=a.manifest,job_path=a.job,
            checkpoint_dir=a.checkpoint_dir,out=a.out)
    except (OSError,ValueError,RuntimeError,TypeError) as exc:
        result={"status":"PARTIAL_AI_REVIEW_RECOVERY_REJECTED",
                "reason":str(exc)[:500],"new_model_or_tts_requests":0}
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ("accepted_rows","untrusted_rows")},
                     indent=2))
    return 0 if result["status"]=="PARTIAL_SOURCE_WITNESSED_AI_REVIEW_NOT_COMPLETE" else 2

if __name__=="__main__":
    raise SystemExit(main())
