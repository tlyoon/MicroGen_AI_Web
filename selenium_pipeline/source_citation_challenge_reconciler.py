"""Read-only reconciliation of original G2 source-review ledger and new one-shot challenges.

Independent source-citation and immutable Gemini reply verification are
mandatory. A model-supported row NEVER becomes scientific/academic approval,
an accepted mathematical proof, release authorization, or an audio cue.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .academic_review_checkpoint import fingerprint
from .ai_academic_web_review import review_instructions, validate_model_review
from .figure_source_identity import _sha, require
from .source_citation_targeted_challenge import prepare_targeted_challenge


def _read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(),
            "Missing source review or owned response evidence")
    value=json.loads(path.read_text("utf8"))
    require(type(value) is dict, "Malformed source review or owned response")
    return value


def reconcile(*, baseline_ledger: Path, entries: list[dict],
              allow_partial: bool = True) -> dict:
    """Revalidate saved row evidence, no new provider/network/model calls.

    Explicit source/job/reply manifest, with no hardcoded source, user or PC.
    """
    baseline=_read(Path(baseline_ledger))
    require(type(entries) is list and bool(entries)
            and len(entries)<=24
            and all(type(entry) is dict for entry in entries),
            "Only bounded explicit academic review entries may reconcile")
    require(baseline.get("status") in (
                "PARTIAL_ONE_PASS_SOURCE_REVIEW_WITH_GAPS",
                "ALL_ORIGINAL_ONE_PASS_ROWS_RECHECKED_NOT_ACADEMIC_APPROVAL")
            and baseline.get("academic_science_independently_verified") is False
            and baseline.get("release_approved") is False
            and baseline.get("original_utterance_count") > 0,
            "Original academic ledger is not approved/valid")
    expected_names=[row["job"] for row in baseline["jobs"]]
    require(len(entries)==len(expected_names)==baseline["review_batch_count"]
            and len(set(expected_names))==len(expected_names),
            "Original academic review ledger/manifest coverage mismatch")
    names=[]
    completed=[];blocked=[];seen=set();eligible_all=set()
    original_units=set()
    for idx,entry in enumerate(entries):
        required=("original_job","original_checkpoint","new_source_quotes",
                  "new_plan","new_result","new_checkpoint")
        require(all(type(entry.get(k)) is str and bool(entry[k])
                    for k in required),
                "Missing physically owned original/new academic review paths")
        paths={k:Path(entry[k]).absolute() for k in required}
        require(len(set(paths.values()))==len(paths),
                "Original or new review paths are aliased/reused")
        job_path=paths["original_job"]
        name=job_path.stem
        require(job_path.name==expected_names[idx]
                and name not in names,
                "Academic original jobs omitted, swapped or duplicated")
        names.append(name)
        cp=paths["original_checkpoint"]
        new_quote=paths["new_source_quotes"]
        # The identical deterministic preflight rechecks original Gemini
        # response SHA, original job/script/slides/source, all new original-PDF
        # quote witnesses, and the unchanged original source review identity.
        original=_read(job_path)
        require(all(original.get(field)==baseline[key] for field,key in (
            ("source_sha256","source_sha256"),
            ("slides_sha256","slides_sha256"),
            ("script_sha256","script_sha256"))),
            "Original job and first-pass ledger use different source bytes")
        prior_units=[u["id"] for s in original["slides"] for u in s["utterances"]]
        require(len(prior_units)==baseline["jobs"][idx]["original_utterances"]
                and set(prior_units).isdisjoint(original_units),
                "Original unit was removed or reused in another job")
        original_units.update(prior_units)
        prepared=prepare_targeted_challenge(
            original_job=job_path,original_checkpoint=cp,
            new_source_quotes=new_quote)
        expected_job=prepared["source_job"]
        eligible={u["id"] for s in expected_job["slides"] for u in s["utterances"]}
        require(not eligible.intersection(eligible_all),
                "Original unresolved source unit is present in multiple challenges")
        eligible_all.update(eligible)
        new_plan=paths["new_plan"]
        result_file=paths["new_result"]
        own=paths["new_checkpoint"]
        if not result_file.exists():
            if new_plan.exists() or own.exists():
                blocked.append({"original_job":name,
                                "eligible_utterances":len(eligible),
                                "state":"ATTEMPT_UNRESOLVED_NO_RETRY"})
            else:
                blocked.append({"original_job":name,
                                "eligible_utterances":len(eligible),
                                "state":"NOT_ATTEMPTED"})
            continue
        require(new_plan.is_file() and not new_plan.is_symlink()
                and own.is_dir() and not own.is_symlink(),
                "New Gemini result must have original planned job and real Send")
        saved=_read(new_plan)
        require(saved.get("status")=="NEW_SOURCE_EVIDENCE_TARGETED_CHALLENGE_NOT_SENT"
                and saved.get("source_job")==expected_job
                and saved.get("new_model_request_attempted") is False
                and saved.get("included_original_unresolved_units")==len(eligible),
                "Review job request differs from verified original evidence")
        actual=_read(result_file)
        state=_read(own/"request_state.json")
        identity=_read(own/"model_response_identity.json")
        response_file=own/"model_response_untrusted.txt"
        require((own/"dispatch_attempted.claim").is_file()
                and not (own/"dispatch_attempted.claim").is_symlink()
                and response_file.is_file() and not response_file.is_symlink(),
                "New source-research reply not claimed by a real Gemini Send")
        raw=response_file.read_bytes()
        require(0<len(raw)<1_800_000*4
                and hashlib.sha256(raw).hexdigest()==state.get("response_sha256")
                ==identity.get("response_sha256")
                and identity.get("approved") is False
                and identity.get("new_model_requests") is False
                and state.get("status")=="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"
                and state.get("review_mode")==identity.get("review_mode")
                =="INDEPENDENT_CHALLENGE",
                "Original new Gemini response bytes or claimed identity invalid")
        folder=Path(expected_job["original_folder"]).absolute()
        paths={"source.pdf":expected_job["source_sha256"],
               "slides.pdf":expected_job["slides_sha256"],
               "script.txt":expected_job["script_sha256"]}
        require(all(_sha(folder/key)==digest for key,digest in paths.items()),
                "Original source/author material changed since challenge")
        request=review_instructions(expected_job,mode="INDEPENDENT_CHALLENGE")
        fp=fingerprint(request_text=request,source_hashes=paths,
                       review_mode="INDEPENDENT_CHALLENGE")
        require(state.get("request_fingerprint")==identity.get("request_fingerprint")==fp
                and state.get("prompt_sha256")==identity.get("prompt_sha256")
                ==hashlib.sha256(request.encode("utf8")).hexdigest(),
                "Saved browser reply belongs to another source/review prompt")
        reply=json.loads(raw.decode("utf8"))
        audited=validate_model_review(
            folder=folder,job=expected_job,response=reply,
            mode="INDEPENDENT_CHALLENGE")
        require(actual==audited and actual.get("academic_mathematics_independently_verified") is False
                and actual.get("student_publication_authorized") is False
                and actual.get("tts_authorized") is False
                and actual.get("review_count")==len(eligible),
                "Claimed new verdict was not source-witnessed or silently approved")
        reviewed_ids={r["utterance_id"] for r in actual["rows"]}
        require(reviewed_ids==eligible and reviewed_ids.isdisjoint(seen),
                "Original source review has missing, foreign or duplicate units")
        seen.update(reviewed_ids)
        types={key:sum(r["verdict"]==key for r in actual["rows"])
               for key in ("SUPPORTED","UNRESOLVED","INCORRECT")}
        require(sum(types.values())==len(eligible),
                "Gemini result discarded an original unresolved unit")
        completed.append({"original_job":name,
                          "source_witnessed_original_units":len(eligible),
                          "result_sha256":_sha(result_file),
                          "provider_reply_sha256":_sha(response_file),
                          **types})
    require(len(original_units)==baseline["original_utterance_count"],
            "Original 74-unit source review was not preserved")
    if not allow_partial:
        require(not blocked,"A targeted academic challenge is still unconfirmed")
    new_supported=sum(x["SUPPORTED"] for x in completed)
    new_incorrect=sum(x["INCORRECT"] for x in completed)
    reviewed=sum(x["source_witnessed_original_units"] for x in completed)
    remain=baseline["source_unresolved"]-new_supported-new_incorrect
    require(remain>=0 and (baseline["source_supported"]+new_supported
            +baseline["source_incorrect"]+new_incorrect+remain
            +baseline["untrusted_utterances"]
            +baseline["not_yet_reviewed_utterances"])
            ==baseline["original_utterance_count"],
            "Original source review arithmetic or challenge reconciliation invalid")
    return {"schema_version":1,
            "status":"SOURCE_WITNESSED_G2_UPDATED_EVIDENCE_NOT_ACADEMIC_APPROVAL",
            "source_sha256":baseline["source_sha256"],
            "slides_sha256":baseline["slides_sha256"],
            "script_sha256":baseline["script_sha256"],
            "original_utterance_count":baseline["original_utterance_count"],
            "original_source_supported_unchanged":baseline["source_supported"],
            "original_source_unresolved_unchanged":baseline["source_unresolved"],
            "original_invalid_citations_untouched":baseline["untrusted_utterances"],
            "new_independently_source_witnessed_model_supported":new_supported,
            "new_independently_source_witnessed_model_incorrect":new_incorrect,
            "source_supported_with_new_challenges":baseline["source_supported"]+new_supported,
            "source_unresolved_with_new_challenges":remain,
            "source_incorrect_with_new_challenges":baseline["source_incorrect"]+new_incorrect,
            "untrusted_original_utterances":baseline["untrusted_utterances"],
            "new_challenge_utterances_reviewed":reviewed,
            "new_challenge_utterances_not_confirmed":sum(
                 x["eligible_utterances"] for x in blocked),
            "completed_challenges":completed,
            "blocked_or_unattempted_challenges":blocked,
            "academic_science_independently_verified":False,
            "full_element_narration_synchronization_verified":False,
            "independent_acoustic_approval":False,
            "G2_approved":False,"student_publication_authorized":False,
            "new_model_or_tts_requests":0}


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("baseline-ledger","challenge-manifest","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args(argv)
    manifest=_read(a.challenge_manifest)
    require(manifest.get("status")==
            "ORIGINAL_SOURCE_BOUND_G2_CHALLENGE_RECONCILIATION_MANIFEST_V1"
            and manifest.get("new_model_or_tts_requests")==0
            and type(manifest.get("entries")) is list,
            "Only explicit no-request source-bound challenge manifests qualify")
    result=reconcile(baseline_ledger=a.baseline_ledger,
                     entries=manifest["entries"])
    require(a.out.parent.is_dir() and not a.out.exists(),
            "G2 reconciliation is new external evidence, not an overwrite")
    with a.out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ("completed_challenges",
                                   "blocked_or_unattempted_challenges")},
                     indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
