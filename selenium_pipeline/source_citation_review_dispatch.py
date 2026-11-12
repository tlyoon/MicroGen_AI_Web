"""One-shot Gemini Selenium academic review of a SHA-locked bounded batch.

No batch retry, no prompt/quote trimming and no release approval. Recovers only
existing durable evidence after uncertain/failed Send; never resends it.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

from .evidence_reuse_contract import file_sha256
from .ai_academic_web_review import run_web_review

class SourceReviewDispatchError(ValueError):
    pass

def require(ok,msg):
    if not ok:
        raise SourceReviewDispatchError(msg)

def inspect_batch(*,manifest_path:Path,job_path:Path,out:Path,
                  checkpoint_dir:Path):
    manifest_path=Path(manifest_path).absolute()
    job_path=Path(job_path).absolute()
    out=Path(out).absolute()
    checkpoint_dir=Path(checkpoint_dir).absolute()
    root=manifest_path.parent
    require(manifest_path.name=="source_citation_batch_manifest.json"
            and manifest_path.is_file() and not manifest_path.is_symlink()
            and job_path.parent==root and job_path.is_file()
            and not job_path.is_symlink() and job_path.stat().st_size<1_000_000,
            "Unsafe source-bound batch request")
    manifest=json.loads(manifest_path.read_text(encoding="utf8"))
    job=json.loads(job_path.read_text(encoding="utf8"))
    entry=next((x for x in manifest.get("jobs",[])
                if x.get("job_filename")==job_path.name),None)
    require(manifest.get("schema_version")==1
            and manifest.get("status") in (
                "ALL_SOURCE_CITED_REVIEW_JOBS_READY_NOT_DISPATCHED",
                "PARTIAL_SOURCE_CITED_REVIEW_JOBS_UNRESOLVED_NO_SEND")
            and entry is not None
            and entry.get("job_sha256")==file_sha256(job_path)
            and entry.get("slides")==job.get("selected_original_slides")
            and entry.get("source_quote_evidence_complete") is True
            and entry.get("AI_review_submitted") is False
            and job.get("utterance_count")==entry.get("utterance_count")
            and job.get("student_publication_authorized") is False,
            "Batch SHA or prior Send claim changed")
    folder=Path(manifest.get("source_folder","")).absolute()
    require(folder.is_dir() and not folder.is_symlink()
            and not root.is_relative_to(folder)
            and not folder.is_relative_to(root)
            and all((folder/name).is_file() and
                    file_sha256(folder/name)==manifest[field]
                    ==job[field] for name,field in (
                        ("source.pdf","source_sha256"),
                        ("slides.pdf","slides_sha256"),
                        ("script.txt","script_sha256"))),
            "Original source/slides/script or batch identity changed")
    require(out.parent.is_dir() and not out.exists()
            and checkpoint_dir.parent.is_dir()
            and not out.is_relative_to(folder)
            and not checkpoint_dir.is_relative_to(folder),
            "New external result and request checkpoint required")
    quotes=job.get("verified_source_quote_candidates_v1")
    require(isinstance(quotes,dict) and
            quotes.get("status")=="PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1"
            and quotes.get("source_sha256")==manifest["source_sha256"]
            and len(json.dumps(quotes,ensure_ascii=False))<=13000,
            "Citation whitelist absent/oversized")
    return folder,job

def dispatch(*,manifest_path:Path,job_path:Path,out:Path,
             checkpoint_dir:Path,wait_cap_s=240,recover_only=False):
    folder,job=inspect_batch(
        manifest_path=manifest_path,job_path=job_path,out=out,
        checkpoint_dir=checkpoint_dir)
    if recover_only:
        # Revalidate the exact already-SUBMITTED and SHA-bound owned reply.
        # This route can NEVER contact Gemini or prepare a fresh Send.
        from .academic_review_checkpoint import validate_saved,fingerprint
        from .ai_academic_web_review import (
            review_instructions,validate_model_review)
        from .series_gemini import decode_storyboard_response
        request_text=review_instructions(job,mode="INITIAL_REVIEW")
        request_sha=fingerprint(
            request_text=request_text,
            source_hashes={
                "source.pdf":job["source_sha256"],
                "slides.pdf":job["slides_sha256"],
                "script.txt":job["script_sha256"]},
            review_mode="INITIAL_REVIEW")
        def validate(raw):
            data=decode_storyboard_response(raw)
            return validate_model_review(
                folder=folder,job=job,response=data,mode="INITIAL_REVIEW")
        result=validate_saved(
            checkpoint=checkpoint_dir,expected_fingerprint=request_sha,
            validator=validate)
    else:
        result=run_web_review(
            folder=folder,job=job,mode="INITIAL_REVIEW",
            wait_cap_s=wait_cap_s,checkpoint_dir=Path(checkpoint_dir))
    require(result.get("status")=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
            and result.get("review_count")==job["utterance_count"]
            and result.get("student_publication_authorized") is False,
            "Model review did not provide full source-witnessed batch")
    out=Path(out).absolute()
    with out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    return {"status":"AI_ONE_PASS_SOURCE_WITNESSED_NOT_RELEASE_APPROVED",
            "slides":job["selected_original_slides"],
            "utterances_reviewed":result["review_count"],
            "supported":sum(row["verdict"]=="SUPPORTED" for row in result["rows"]),
            "unresolved":sum(row["verdict"]=="UNRESOLVED" for row in result["rows"]),
            "incorrect":sum(row["verdict"]=="INCORRECT" for row in result["rows"]),
            "raw_gemini_request_count_maximum":1,
            "student_publication_authorized":False,
            "result_sha256":file_sha256(out)}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--job",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--wait-cap-seconds",type=int,default=240)
    p.add_argument("--recover-only",action="store_true",
                   help="Validate the same already-claimed model response; no Gemini Send")
    args=p.parse_args(argv)
    try:
        result=dispatch(manifest_path=args.manifest,job_path=args.job,
                        out=args.out,checkpoint_dir=args.checkpoint_dir,
                        wait_cap_s=args.wait_cap_seconds,
                        recover_only=args.recover_only)
    except Exception as exc:
        result={"status":"AI_REVIEW_NOT_ACCEPTED_NO_RESEND",
                "error_type":type(exc).__name__,
                "reason":str(exc)[:400],
                "new_tts_requests":0,
                "student_publication_authorized":False}
    print(json.dumps(result,indent=2))
    return 0 if result.get("status")=="AI_ONE_PASS_SOURCE_WITNESSED_NOT_RELEASE_APPROVED" else 2

if __name__=="__main__":
    raise SystemExit(main())
