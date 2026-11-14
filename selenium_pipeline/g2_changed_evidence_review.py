"""Third evidence CHANGED (not repeated) source+visual academic challenge planner.

The old model's unsupported/invalid statements cannot be silently approved,
but a missing real PDF figure/mathematical target or an independently new
physical source passage can justify exactly one *different* bounded challenge.
The planner sends NO model request, synthesizes NO audio, never reclassifies an
old claim, and preserves all previously claimed source review checkpoints.
Use existing academic_review_checkpoint.submit_once for any future dispatch.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .ai_academic_web_review import build_review_job, review_instructions
from .figure_source_identity import _sha, require
from .source_citation_challenge_reconciler import reconcile


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(),
            "Missing immutable academic source evidence")
    obj=json.loads(path.read_text(encoding="utf8"))
    require(type(obj) is dict,"Invalid academic evidence object")
    return obj


def changed_evidence_jobs(*, baseline_ledger: Path,
                          challenge_manifest: Path) -> dict:
    """Revalidate true prior Gemini replies before constructing fresh evidence."""
    ledger=Path(baseline_ledger).absolute()
    manifest=_read(Path(challenge_manifest).absolute())
    entries=manifest.get("entries")
    require(type(entries) is list and 1 <= len(entries) <= 24,
            "Bounded six-style source challenge manifest required")
    already=reconcile(baseline_ledger=ledger,entries=entries,
                      allow_partial=False)
    require(already.get("G2_approved") is False
            and already.get("student_publication_authorized") is False,
            "Already approved source is not eligible for change-based retries")
    out=[];selected=set();all_original=set();counts={
        "original_unresolved":0,
        "second_round_supported_excluded":0,
        "third_challenge_changed_citation_or_visual":0,
        "unchanged_evidence_not_resubmitted":0,
    }
    for entry in entries:
        orig_path=Path(entry["original_job"]).absolute()
        old=_read(orig_path)
        folder=Path(old["original_folder"]).absolute()
        frozen=_read(Path(entry["original_checkpoint"])/
                     "model_response_identity.json")
        raw_path=Path(entry["original_checkpoint"])/"model_response_untrusted.txt"
        raw=raw_path.read_bytes()
        require(sha(raw)==frozen.get("response_sha256"),
                "Original model response SHA changed")
        original_reply=json.loads(raw.decode("utf8"))
        second_result=_read(Path(entry["new_result"]))
        second_reply_identity=_read(Path(entry["new_checkpoint"])/
                                   "model_response_identity.json")
        require(_sha(Path(entry["new_checkpoint"])/
                     "model_response_untrusted.txt")
                ==second_reply_identity.get("response_sha256"),
                "Changed source second-pass model reply missing or altered")
        original_rows=original_reply.get("rows")
        require(type(original_rows) is list
                and len(original_rows)==old["utterance_count"],
                "Original utterance set changed")
        existing={x["utterance_id"]:x for x in second_result["rows"]}
        old_source=_read(Path(entry["new_source_quotes"]))
        old_candidate={x["utterance_id"]:x for x in old_source["utterances"]}
        fresh=build_review_job(folder=folder,
                  slide_numbers=old["selected_original_slides"])
        require(all(fresh.get(field)==old.get(field)
                    for field in ("source_sha256","slides_sha256","script_sha256"))
                and fresh["utterance_count"]==old["utterance_count"],
                "Fresh academic job changed the original lecture material")
        physical={x["utterance_id"]:x for x in
                  fresh["verified_source_quote_candidates_v1"]["utterances"]}
        old_targets={s["slide"]:{v["id"] for v in s["visual_targets"]}
                     for s in old["slides"]}
        extra_targets={
            s["slide"]:[v["id"] for v in s["visual_targets"]
                        if v["id"] not in old_targets[s["slide"]]]
            for s in fresh["slides"]
        }
        unchanged=[];eligible=[];per_reason={}
        for unit in original_rows:
            uid=unit["utterance_id"]
            require(uid not in all_original and uid in physical,
                    "Wrong original unit or duplicate original source row")
            all_original.add(uid)
            if unit["verdict"] != "UNRESOLVED":
                continue  # Never replay supported or disputed old claims.
            counts["original_unresolved"]+=1
            later=existing.get(uid)
            if later:
                require(later["verdict"] in ("SUPPORTED","UNRESOLVED","INCORRECT"),
                        "Invalid second-model verdict")
                if later["verdict"]=="SUPPORTED":
                    counts["second_round_supported_excluded"]+=1
                    continue
                # A prior INCORRECT judgement is not fixed by a new quote.
                if later["verdict"]=="INCORRECT":
                    unchanged.append(uid)
                    continue
            slide=int(uid[1:4])
            oldc=old_candidate[uid]["allowed_citations"]
            now=physical[uid]["allowed_citations"]
            old_pairs={(x["source_page"],x["verbatim_source_quote"])
                       for x in oldc}
            new_pairs={(x["source_page"],x["verbatim_source_quote"])
                       for x in now}
            new_quote=bool(new_pairs-old_pairs)
            new_visual=bool(extra_targets.get(slide))
            if not (new_quote or new_visual):
                unchanged.append(uid)
                counts["unchanged_evidence_not_resubmitted"]+=1
                continue
            require(uid not in selected,"Source unit selected twice")
            selected.add(uid)
            eligible.append(uid)
            per_reason[uid]={"new_exact_quote":new_quote,
                             "new_physical_visual_target_choices":
                                 extra_targets.get(slide,[])}
        if not eligible:
            continue
        keep=set(eligible)
        slides=[]
        for s in fresh["slides"]:
            subset=[u for u in s["utterances"] if u["id"] in keep]
            if subset:
                slides.append({**s,"utterances":subset})
        packet={**fresh["verified_source_quote_candidates_v1"],
                "utterances":[x for x in
                    fresh["verified_source_quote_candidates_v1"]["utterances"]
                    if x["utterance_id"] in keep]}
        new_job={**fresh,"slides":slides,
                 "utterance_count":len(eligible),
                 "selected_original_slides":[s["slide"] for s in slides],
                 "verified_source_quote_candidates_v1":packet,
                 "original_source_review_response_sha256":sha(raw),
                 "previous_changed_evidence_reply_sha256":
                     second_reply_identity["response_sha256"],
                 "source_research_is_new_evidence_only":True,
                 "prior_model_verdicts_not_reclassified":True,
                 "academic_approval":False,
                 "student_publication_authorized":False}
        new_prompt=review_instructions(new_job,mode="INDEPENDENT_CHALLENGE")
        require(new_prompt != review_instructions(
                    old,mode="INITIAL_REVIEW")
                and all(_sha(folder/name)==old[field]
                        for name,field in (("source.pdf","source_sha256"),
                                           ("slides.pdf","slides_sha256"),
                                           ("script.txt","script_sha256"))),
                "Repeated source review prompt or mutated original files")
        out.append({
            "source_job":new_job,
            "source_job_request_sha256":sha(new_prompt.encode("utf8")),
            "original_job":str(orig_path),
            "verified_original_reply_sha256":sha(raw),
            "verified_second_reply_sha256":
                second_reply_identity["response_sha256"],
            "eligible_original_unresolved_units":eligible,
            "change_reasons":per_reason,
            "unmodified_existing_verdicts":True,
            "actual_model_request_submitted":False,
            "student_publication_authorized":False,
        })
        counts["third_challenge_changed_citation_or_visual"]+=len(eligible)
    require(counts["original_unresolved"]==
            already["original_source_unresolved_unchanged"],
            "Original unresolved count changed")
    require(counts["second_round_supported_excluded"]==
            already["new_independently_source_witnessed_model_supported"],
            "Do not repeat already model-supported second-pass source units")
    require(counts["third_challenge_changed_citation_or_visual"]<=
            already["source_unresolved_with_new_challenges"],
            "Third challenge cannot include new or already-supported narration")
    return {"schema_version":1,
            "status":"UNSENT_PHYSICALLY_CHANGED_G2_SOURCE_AND_VISUAL_EVIDENCE",
            "source_sha256":already["source_sha256"],
            "original_utterances":already["original_utterance_count"],
            "previous_academic_ledger_status":already["status"],
            "previous_unresolved_unchanged":
                already["source_unresolved_with_new_challenges"],
            "previous_invalid_citations_unchanged":
                already["untrusted_original_utterances"],
            "totals":counts,
            "jobs":out,
            "new_Gemini_or_TTS_requests":0,
            "independent_scientific_validation":False,
            "G2_approved":False,
            "student_publication_authorized":False}


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("baseline-ledger","challenge-manifest","out"):
        p.add_argument("--"+k,required=True,type=Path)
    a=p.parse_args(argv)
    result=changed_evidence_jobs(baseline_ledger=a.baseline_ledger,
                                 challenge_manifest=a.challenge_manifest)
    out=a.out.absolute()
    require(not out.exists() and out.parent.is_dir()
            and not out.is_relative_to(Path(result["jobs"][0]
                    ["source_job"]["original_folder"])),
            "Third challenge plan must be new, outside original source tree")
    with out.open("x",encoding="utf8") as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({"status":result["status"],
                      "jobs":len(result["jobs"]),
                      **result["totals"]},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
