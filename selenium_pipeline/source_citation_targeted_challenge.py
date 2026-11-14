"""One new evidence-changed source review, not a replay of an old Gemini Send.

Only original UNRESOLVED utterances with newly witnessed source quotes are
eligible. A previous claimed model reply, original job, original source PDFs,
and supplemental quote packet are independently SHA-verified. The saved old
request and results stay immutable. New challenge execution MUST use the
existing crash-persistent academic_review_checkpoint.submit_once mechanism.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .academic_review_checkpoint import fingerprint
from .ai_academic_web_review import review_instructions
from .figure_source_identity import _sha, require
from .pdf_text_source_span_witness import prove_source_quote_occurrence


def _read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(),
            "Missing original source review evidence")
    result = json.loads(path.read_text("utf8"))
    require(type(result) is dict, "Original model/source receipt must be JSON object")
    return result


def _new_quotes_only(*, old: dict, supplemented: dict, unit: dict,
                     source: Path) -> bool:
    old_pairs = {(p["source_page"], p["verbatim_source_quote"])
                 for p in old["allowed_citations"]}
    current = supplemented["allowed_citations"]
    require(supplemented.get("spoken_sha256") == unit["spoken_sha256"],
            "New source quotes no longer match original narration bytes")
    pairs = [(p["source_page"], p["verbatim_source_quote"]) for p in current]
    require(len(pairs) == len(set(pairs)) and len(pairs) <= 2,
            "Unbounded or duplicated verified source quote packet")
    for item in current:
        checked = prove_source_quote_occurrence(
            source_pdf=source, expected_sha256=_sha(source),
            page_number=item["source_page"],
            verbatim_quote=item["verbatim_source_quote"])
        require(item["quote_sha256"] == checked["quote_sha256"],
                "Supplemental source quote was not physically witnessed")
    return bool(set(pairs) - old_pairs)


def prepare_targeted_challenge(*, original_job: Path, original_checkpoint: Path,
                               new_source_quotes: Path) -> dict:
    original_job = Path(original_job).absolute()
    original_checkpoint = Path(original_checkpoint).absolute()
    new_source_quotes = Path(new_source_quotes).absolute()
    job = _read(original_job)
    require(job.get("status") == "SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED"
            and job.get("academic_approval") is False
            and job.get("student_publication_authorized") is False,
            "Original academic job is not a frozen unapproved review")
    folder = Path(job["original_folder"]).absolute()
    require(folder.is_dir() and not folder.is_symlink()
            and not original_checkpoint.is_relative_to(folder)
            and not new_source_quotes.is_relative_to(folder),
            "Review receipts and supplemental quotes must be source-external")
    names = (("source.pdf", "source_sha256"),
             ("slides.pdf", "slides_sha256"),
             ("script.txt", "script_sha256"))
    require(all(_sha(folder/name) == job[field] for name, field in names),
            "Original textbook / slide / spoken source has changed")
    old_reply = original_checkpoint/"model_response_untrusted.txt"
    state = _read(original_checkpoint/"request_state.json")
    identity = _read(original_checkpoint/"model_response_identity.json")
    require((original_checkpoint/"dispatch_attempted.claim").is_file(),
            "Previous academic challenge never had a durable Send claim")
    prompt = review_instructions(job, mode="INITIAL_REVIEW")
    expected = fingerprint(
        request_text=prompt,
        source_hashes={name:job[field] for name,field in names},
        review_mode="INITIAL_REVIEW")
    raw = old_reply.read_bytes()
    require(0 < len(raw) < 1_800_000*4
            and identity.get("request_fingerprint") == expected
            and state.get("request_fingerprint") == expected
            and identity.get("response_sha256")
            == state.get("response_sha256")
            == hashlib.sha256(raw).hexdigest()
            and identity.get("kind") == "SAVED_POST_CLAIM_MODEL_REPLY_V1"
            and identity.get("approved") is False
            and identity.get("new_model_requests") is False
            and all(state.get(field)==identity.get(field)==job[field]
                    for _name,field in names),
            "Original Gemini Send/response identity is not independently verifiable")
    old_response = json.loads(raw.decode("utf8"))
    units = [u for slide in job["slides"] for u in slide["utterances"]]
    rows = old_response.get("rows")
    require(old_response.get("status") == "ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE"
            and type(rows) is list and len(rows) == len(units)
            and job["utterance_count"] == len(units),
            "Missing or truncated original academic review")
    latest = _read(new_source_quotes)
    require(latest.get("status") == "PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1"
            and all(latest.get(field)==job[field] for _,field in names),
            "Supplemental source-citation packet no longer matches source")
    old_candidates = job["verified_source_quote_candidates_v1"]["utterances"]
    current_candidates = latest["utterances"]
    require(len(units)==len(old_candidates)==len(current_candidates)
            and [x["utterance_id"] for x in old_candidates]
            ==[x["utterance_id"] for x in current_candidates]
            ==[x["id"] for x in units],
            "Cross-utterance quote reassignment or source-candidate drift")
    selected=[];excluded=[]
    for unit, old, fresh, response in zip(
            units,old_candidates,current_candidates,rows):
        uid=unit["id"]
        require(old["spoken_sha256"]==fresh["spoken_sha256"]==unit["spoken_sha256"]
                and response.get("utterance_id")==uid
                and response.get("spoken_sha256")==unit["spoken_sha256"],
                "Original Gemini answer or source quote identity was changed")
        revised=_new_quotes_only(old=old,supplemented=fresh,
                                 unit=unit,source=folder/"source.pdf")
        if response.get("verdict")=="UNRESOLVED" and revised:
            selected.append(uid)
        else:
            excluded.append(uid)
    require(selected and len(selected) <= 30,
            "No bounded unresolved units gained materially new exact source evidence")
    keep=set(selected)
    target_slides=[]
    for slide in job["slides"]:
        narrowed=[u for u in slide["utterances"] if u["id"] in keep]
        if narrowed:
            target_slides.append({**slide,"utterances":narrowed})
    target_packet={**latest,
                   "utterances":[row for row in current_candidates
                                 if row["utterance_id"] in keep]}
    challenge={**job,
        "status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
        "selected_original_slides":[x["slide"] for x in target_slides],
        "utterance_count":len(selected),
        "slides":target_slides,
        "verified_source_quote_candidates_v1":target_packet,
        "targeted_independent_challenge_no_original_replay":True,
        "prior_original_job_sha256":_sha(original_job),
        "prior_original_response_sha256":hashlib.sha256(raw).hexdigest(),
        "supplemental_source_quote_sha256":_sha(new_source_quotes),
        "original_unresolved_utterance_ids":selected,
        "old_model_verdicts_not_reclassified":True,
        "academic_approval":False,"student_publication_authorized":False}
    # The model will receive only changed evidence and unresolved original
    # utterances. This differs materially from the already claimed request.
    require(review_instructions(challenge,mode="INDEPENDENT_CHALLENGE")
            != prompt, "Never replay an old academic-review browser prompt")
    require(all(_sha(folder/name)==job[field] for name,field in names),
            "Original source changed during the independent challenge preflight")
    return {"status":"NEW_SOURCE_EVIDENCE_TARGETED_CHALLENGE_NOT_SENT",
            "source_job":challenge,
            "included_original_unresolved_units":len(selected),
            "excluded_original_units":excluded,
            "original_source_and_model_response_untouched":True,
            "new_model_request_attempted":False,
            "academic_mathematics_independently_verified":False,
            "student_publication_authorized":False}


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-job",type=Path,required=True)
    p.add_argument("--original-checkpoint",type=Path,required=True)
    p.add_argument("--new-source-quotes",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    obj=prepare_targeted_challenge(
        original_job=a.original_job,original_checkpoint=a.original_checkpoint,
        new_source_quotes=a.new_source_quotes)
    require(a.out.parent.is_dir() and not a.out.exists()
            and not a.out.is_relative_to(Path(obj["source_job"]["original_folder"])),
            "Targeted challenge must be a new source-external JSON checkpoint")
    with a.out.open("x",encoding="utf8") as h:
        json.dump(obj,h,indent=2,ensure_ascii=False)
        h.write("\n")
    print(json.dumps({k:v for k,v in obj.items() if k != "source_job"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
