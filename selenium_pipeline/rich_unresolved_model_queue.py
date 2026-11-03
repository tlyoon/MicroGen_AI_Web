"""Incremental sourcebound rich-element model queue: ask ONLY unresolved text.

An independent SHA-bound fallback already accepted exact publisher + rendered
author PDF PROSE spans; those links are immutable and do not need to be sent
again to Gemini/ChatGPT. Queue only the remaining original utterances, allow a
single model answer for those IDs, and merge them without modifying accepted
old links, original PDF/script or source-reviewed mapping evidence.

The output remains TECHNICAL REVIEW ONLY. All returned math/figures and weak
semantic claims remain unaccepted until independent mathematical/visual proof.
No model, paid TTS, media, retry or student publication is executed here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .rich_element_model_alignment import (
    RichMappingError, require, stable_hash, request_for_slide,
    assess_response, load_accepted_checkpoint, parse_response,
)
from .rich_element_mapping_checkpoint import _sha


STATUS="ORIGINAL_UNRESOLVED_ONLY_SOURCEBOUND_SEMANTIC_MODEL_QUEUE_REVIEW"
MERGED_STATUS="SOURCEBOUND_INCREMENTAL_MODEL_MERGE_REVIEW_ONLY"


def _read_json(path:Path)->dict:
    require(path.is_file() and not path.is_symlink(), "Missing unsafe source-bound record")
    try:
        raw=json.loads(path.read_text("utf8"))
    except (ValueError,OSError) as exc:
        raise RichMappingError("Original source-bound record JSON incomplete") from exc
    require(type(raw) is dict,"Expected source-bounded JSON object")
    return raw


def verified_fallback(*,source_folder:Path,checkpoint:Path,
                      fallback_dir:Path)->tuple[dict,list[tuple[dict,dict]]]:
    meta,_=load_accepted_checkpoint(folder=source_folder,checkpoint=checkpoint)
    fallback_dir=Path(fallback_dir).absolute()
    require(fallback_dir.is_dir() and not fallback_dir.is_symlink()
            and not fallback_dir.is_relative_to(Path(source_folder).absolute()),
            "Fallback original-source receipts must remain external")
    manifest=_read_json(fallback_dir/"SAFE_PROSE_FALLBACK_MANIFEST.json")
    require(manifest.get("status")==
               "DETERMINISTIC_SOURCE_GROUNDED_SAFE_PROSE_CANDIDATES_REVIEW_ONLY"
            and manifest.get("source_inputs_sha256")==meta["source_inputs_sha256"]
            and manifest.get("original_slide_count")==meta["slide_count"]
            and manifest.get("model_provider_invoked") is False
            and manifest.get("paid_tts_authorized") is False
            and manifest.get("student_publication_authorized") is False,
            "Original accepted fallback misidentified or falsely authorized")
    refs=manifest.get("each_slide_response_stable_sha256")
    require(type(refs) is dict and len(refs)==meta["slide_count"],
            "Accepted fallback response set is incomplete")
    original=[]
    n_safe=n_unresolved=0
    for slide in range(1,meta["slide_count"]+1):
        name=f"slide_{slide:03d}.json"
        path=fallback_dir/name
        row=_read_json(path)
        require(row.get("producer")==
               "DETERMINISTIC_SOURCE_PDF_SAFE_PROSE_FALLBACK_V1"
               and row.get("slide")==slide
               and row.get("audio_generation_authorized") is False
               and row.get("student_publication_authorized") is False
               and stable_hash(row)==refs.get(name),
               "Prior verified source-prose link record was changed or forged")
        audit=assess_response(source_folder=source_folder,
            checkpoint=checkpoint,slide_number=slide,proposed=row)
        for decision,review in zip(row["associations"],audit["entries"]):
            verified=review["source_and_visible_text_anchors_independently_verified"]
            require((decision["target_id"] is not None)==verified,
                    "Previously accepted prose link or held ambiguity changed")
            if verified:
                n_safe+=1
                require(decision["needs_review"] is False
                        and review["author_visual_kind"]=="text_block",
                        "Only independently proven old prose text can be reused")
            else:
                n_unresolved+=1
                require(decision["target_id"] is None
                        and decision["source_page"] is None
                        and decision["source_quote"] is None
                        and decision["needs_review"] is True,
                        "Unverified old mathematical claims must remain null")
        original.append((row,audit))
    require(n_safe==manifest.get("machine_verified_safe_prose_links")
            and n_unresolved==manifest.get(
                "unresolved_original_math_figure_or_ambiguous_utterances")
            and n_safe+n_unresolved==manifest.get("original_utterances"),
            "Original fallback coverage or source-bound counts have changed")
    return manifest,original


def _partial_request(*,request:dict,accepted_row:dict,accepted_audit:dict)->dict:
    by_id={row["utterance_id"]:row for row in
           request["original_utterances"]}
    original_choices=accepted_row["associations"]
    unresolved=[]
    kept=[]
    for choice,validation in zip(original_choices,accepted_audit["entries"]):
        uid=choice["utterance_id"]
        require(uid in by_id,"Accepted fallback contains extra utterance")
        if validation["source_and_visible_text_anchors_independently_verified"]:
            kept.append({"utterance_id":uid,
                         "target_id":choice["target_id"],
                         "source_page":choice["source_page"],
                         "source_quote":choice["source_quote"],
                         "original_verbatim_text_sha256":
                            validation["original_verbatim_spoken_text_sha256"]})
        else:
            unresolved.append(by_id[uid])
    partial={
        "schema_version":1,
        "status":STATUS,
        "slide":request["slide"],
        "source_inputs_sha256":request["source_inputs_sha256"],
        "full_original_request_sha256":request["request_sha256"],
        "immutable_accepted_fallback_full_sha256":stable_hash(accepted_row),
        "source_page_excerpts":request["source_page_excerpts"],
        "visible_targets":request["visible_targets"],
        "only_unresolved_original_utterances":unresolved,
        "accepted_prose_links_already_sha_verified_do_not_resend":kept,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }
    partial["partial_request_sha256"]=stable_hash(partial)
    return partial


def prompt_partial(request:dict)->str:
    require(request.get("status")==STATUS
            and request.get("paid_tts_authorized") is False,
            "Only original source-bound unresolved review requests may be sent")
    task={
        "slide":request["slide"],
        "partial_request_sha256":request["partial_request_sha256"],
        "only_unresolved_original_utterances":
            request["only_unresolved_original_utterances"],
        "visible_targets":request["visible_targets"],
        "source_page_excerpts":request["source_page_excerpts"],
    }
    return (
        "You are proposing SOURCE-GROUNDED visual targets only for the "
        "UNRESOLVED narration units. Earlier independently verified "
        "prose associations have already been accepted, may NOT be "
        "resubmitted or changed, and ARE NOT included here. Return one "
        "JSON object ONLY: slide, partial_request_sha256 (unchanged), "
        "associations (exactly one per listed unresolved utterance, "
        "in supplied order); each association must have utterance_id, "
        "target_id (one exact listed ID or null), source_page "
        "(one supplied textbook page or null), source_quote (12-240 "
        "literal consecutive chars from that page or null), reason "
        "(short string), needs_review (bool). Do not invent mathematical "
        "symbols, signs, domains or source-figure identities. If the "
        "evidence is ambiguous choose null. Do NOT authorize TTS, "
        "academic approval, or student release. Source to equations and "
        "figure panels requires independent post-model verification. "
        "No guesses to inflate completion counts.\n\n"
        +json.dumps(task,ensure_ascii=False,separators=(",",":"))
    )


def prepare_queue(*,source_folder:Path,checkpoint:Path,
                  fallback_dir:Path,destination:Path)->dict:
    destination=Path(destination).absolute()
    source_folder=Path(source_folder).absolute()
    require(destination.parent.is_dir() and not destination.exists()
            and not destination.is_relative_to(source_folder)
            and not source_folder.is_relative_to(destination),
            "Only NEW independent source-external incremental model queue")
    original_manifest,old=verified_fallback(
        source_folder=source_folder,checkpoint=checkpoint,
        fallback_dir=fallback_dir)
    pairs=[]
    for slide,(baseline,audit) in enumerate(old,1):
        request=request_for_slide(source_folder=source_folder,
            checkpoint=checkpoint,slide_number=slide)
        partial=_partial_request(request=request,accepted_row=baseline,
                                 accepted_audit=audit)
        pairs.append(partial)
    require(sum(len(r["only_unresolved_original_utterances"]) for r in pairs)
            ==original_manifest[
                "unresolved_original_math_figure_or_ambiguous_utterances"],
            "Unresolved-only queue attempted to repeat accepted work")
    # Reconfirm input source and original accepted receipts before writing.
    verified_fallback(source_folder=source_folder,checkpoint=checkpoint,
                      fallback_dir=fallback_dir)
    destination.mkdir()
    entries=[]
    for partial in pairs:
        slide=partial["slide"]
        request_file=destination/f"slide_{slide:03d}.unresolved_request.json"
        with request_file.open("x",encoding="utf8") as stream:
            json.dump(partial,stream,indent=2,ensure_ascii=False)
            stream.write("\n")
        filename=None
        if partial["only_unresolved_original_utterances"]:
            filename=f"slide_{slide:03d}.prompt.txt"
            (destination/filename).write_text(
                prompt_partial(partial)+"\n",encoding="utf8")
        entries.append({
            "slide":slide,
            "status":("READY_UNRESOLVED_ONLY_MODEL_PROPOSAL"
                      if filename else
                      "ALREADY_SOURCE_VERIFIED_NO_MODEL_SUBMISSION"),
            "partial_request_sha256":partial["partial_request_sha256"],
            "request_file":request_file.name,
            "model_prompt_file":filename,
            "already_independently_proven_prose":len(
                partial["accepted_prose_links_already_sha_verified_do_not_resend"]),
            "remaining_model_proposal_utterances":len(
                partial["only_unresolved_original_utterances"]),
        })
    result={
        "schema_version":1,
        "status":"SOURCEBOUND_UNRESOLVED_ONLY_MODEL_JOB_QUEUE_NO_AUTO_SUBMIT",
        "source_inputs_sha256":original_manifest["source_inputs_sha256"],
        "fallback_manifest_sha256":stable_hash(original_manifest),
        "accepted_fallback_original_file_sha256":{
            f"slide_{slide:03d}.json":_sha(
                Path(fallback_dir).absolute()/f"slide_{slide:03d}.json")
            for slide in range(1,original_manifest["original_slide_count"]+1)},
        "original_slides":original_manifest["original_slide_count"],
        "already_accepted_prose_links_reused_not_sent":sum(
            e["already_independently_proven_prose"] for e in entries),
        "only_unresolved_utterances_requested":sum(
            e["remaining_model_proposal_utterances"] for e in entries),
        "jobs":entries,
        "automated_model_submission_permitted":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    }
    with (destination/"UNRESOLVED_ONLY_MODEL_QUEUE_MANIFEST.json").open(
            "x",encoding="utf8") as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    return result


def verify_queue(*,source_folder:Path,checkpoint:Path,
                 fallback_dir:Path,queue_folder:Path)->tuple[dict,dict,list]:
    oldmeta,old=verified_fallback(
        source_folder=source_folder,checkpoint=checkpoint,
        fallback_dir=fallback_dir)
    queue_folder=Path(queue_folder).absolute()
    require(queue_folder.is_dir() and not queue_folder.is_symlink()
            and not queue_folder.is_relative_to(Path(source_folder).absolute()),
            "Unknown or unsafe unresolved model queue folder")
    manifest=_read_json(queue_folder/"UNRESOLVED_ONLY_MODEL_QUEUE_MANIFEST.json")
    require(manifest.get("schema_version")==1
            and manifest.get("status")==
                "SOURCEBOUND_UNRESOLVED_ONLY_MODEL_JOB_QUEUE_NO_AUTO_SUBMIT"
            and manifest.get("source_inputs_sha256")==oldmeta["source_inputs_sha256"]
            and manifest.get("fallback_manifest_sha256")==stable_hash(oldmeta)
            and manifest.get("automated_model_submission_permitted") is False
            and manifest.get("paid_tts_authorized") is False
            and manifest.get("student_publication_authorized") is False
            and len(manifest.get("jobs",[]))==len(old),
            "Queue is incomplete or refers to a different original lecture")
    physical=manifest.get("accepted_fallback_original_file_sha256")
    require(type(physical) is dict and len(physical)==len(old)
            and all(physical.get(f"slide_{i:03d}.json")==_sha(
                Path(fallback_dir).absolute()/f"slide_{i:03d}.json")
                for i in range(1,len(old)+1)),
            "Previously accepted original prose reply physical bytes changed")
    rows=[]
    for slide,(entry,(baseline,audit)) in enumerate(
            zip(manifest["jobs"],old),1):
        recomputed=_partial_request(
            request=request_for_slide(source_folder=source_folder,
                checkpoint=checkpoint,slide_number=slide),
            accepted_row=baseline,accepted_audit=audit)
        filename=f"slide_{slide:03d}.unresolved_request.json"
        require(entry.get("slide")==slide and
                entry.get("request_file")==filename and
                entry.get("partial_request_sha256")==
                    recomputed["partial_request_sha256"]
                and _read_json(queue_folder/filename)==recomputed,
                "Incremental model queue was altered or resent accepted text")
        prompt_name=(f"slide_{slide:03d}.prompt.txt"
                     if recomputed["only_unresolved_original_utterances"]
                     else None)
        require(entry.get("model_prompt_file")==prompt_name
                and (queue_folder/prompt_name).read_text("utf8")==
                      prompt_partial(recomputed)+"\n" if prompt_name else
                entry.get("model_prompt_file") is None,
                "Incremental original source prompt changed")
        rows.append(recomputed)
    require(sum(len(x["only_unresolved_original_utterances"]) for x in rows)
            ==manifest["only_unresolved_utterances_requested"]
            and sum(len(x["accepted_prose_links_already_sha_verified_do_not_resend"])
                    for x in rows)==manifest[
                        "already_accepted_prose_links_reused_not_sent"],
            "Original approved links or pending utterance counts changed")
    return manifest,oldmeta,rows


def merge_response(*,source_folder:Path,checkpoint:Path,
                   fallback_dir:Path,queue_folder:Path,slide:int,
                   partial_response:dict)->tuple[dict,dict]:
    manifest,_,request_rows=verify_queue(
        source_folder=source_folder,checkpoint=checkpoint,
        fallback_dir=fallback_dir,queue_folder=queue_folder)
    require(type(slide) is int and 1<=slide<=len(request_rows),
            "Unknown original slide number in model reply")
    partial=request_rows[slide-1]
    require(type(partial_response) is dict
            and partial_response.get("slide")==slide
            and partial_response.get("partial_request_sha256")==
                partial["partial_request_sha256"]
            and partial_response.get("paid_tts_authorized") in (None,False)
            and partial_response.get("student_publication_authorized") in (None,False),
            "Model result is not this exact unresolved source job")
    choices=partial_response.get("associations")
    expected=partial["only_unresolved_original_utterances"]
    require(type(choices) is list and len(choices)==len(expected),
            "Model answer must cover only and ALL unresolved utterances")
    for answer,old in zip(choices,expected):
        require(type(answer) is dict and
                answer.get("utterance_id")==old["utterance_id"],
                "Model illegally repeated, dropped or reordered accepted old utterance")
    baseline=_read_json(Path(fallback_dir).absolute()/f"slide_{slide:03d}.json")
    oldchoices=baseline["associations"]
    replacements={x["utterance_id"]:x for x in choices}
    merged=[]
    for item in oldchoices:
        # Precise immutable accepted answer copied without editing one field.
        merged.append(replacements[item["utterance_id"]]
                      if item["target_id"] is None else dict(item))
    require(len(merged)==len(oldchoices) and
            all((v["utterance_id"]==x["utterance_id"])
                for v,x in zip(merged,oldchoices)),
            "Original ordered narration was altered")
    combined={
        "slide":slide,
        "request_sha256":baseline["request_sha256"],
        "producer":MERGED_STATUS,
        "sourcebound_unresolved_job_sha256":partial["partial_request_sha256"],
        "prior_verified_safe_prose_sha256":stable_hash(baseline),
        "associations":merged,
        "audio_generation_authorized":False,
        "student_publication_authorized":False,
    }
    reviewed=assess_response(source_folder=source_folder,
                checkpoint=checkpoint,slide_number=slide,proposed=combined)
    old_audit=assess_response(source_folder=source_folder,
                checkpoint=checkpoint,slide_number=slide,proposed=baseline)
    for base,new,x,y in zip(oldchoices,merged,
                             old_audit["entries"],reviewed["entries"]):
        if base["target_id"] is not None:
            require(base==new
                    and x["source_and_visible_text_anchors_independently_verified"]
                    and y["source_and_visible_text_anchors_independently_verified"],
                    "Model tried to replace previously accepted source-based text")
    require(reviewed["utterances_total"]==len(merged)
            and reviewed["text_source_and_author_anchors_passed"]>=sum(
                x["target_id"] is not None for x in oldchoices),
            "Merged reply erased an independently verified original mapping")
    return combined,reviewed


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    a=sub.add_parser("prepare")
    for option in ("source-folder","checkpoint","fallback-dir","out-dir"):
        a.add_argument("--"+option,type=Path,required=True)
    b=sub.add_parser("merge")
    for option in ("source-folder","checkpoint","fallback-dir","queue-folder",
                   "partial-response","out"):
        b.add_argument("--"+option,type=Path,required=True)
    b.add_argument("--slide",type=int,required=True)
    args=p.parse_args(argv)
    if args.action=="prepare":
        value=prepare_queue(source_folder=args.source_folder,
            checkpoint=args.checkpoint,fallback_dir=args.fallback_dir,
            destination=args.out_dir)
        print(json.dumps({"status":value["status"],
            "original_slides":value["original_slides"],
            "already_reused":value["already_accepted_prose_links_reused_not_sent"],
            "unresolved_jobs":value["only_unresolved_utterances_requested"],
            "paid_tts_authorized":False}))
    else:
        require(args.partial_response.is_file()
                and not args.partial_response.is_symlink()
                and args.out.parent.is_dir() and not args.out.exists()
                and not args.out.is_relative_to(args.source_folder.absolute()),
                "Untrusted source/response paths or output conflicts")
        result=parse_response(args.partial_response.read_text("utf8"))
        merged,audit=merge_response(
            source_folder=args.source_folder,checkpoint=args.checkpoint,
            fallback_dir=args.fallback_dir,queue_folder=args.queue_folder,
            slide=args.slide,partial_response=result)
        with args.out.open("x",encoding="utf8") as stream:
            json.dump(merged,stream,indent=2,ensure_ascii=False)
            stream.write("\n")
        print(json.dumps({"status":audit["status"],
            "source_verified_links":audit["text_source_and_author_anchors_passed"],
            "unresolved_review_items":audit["remaining_review_items"],
            "paid_tts_authorized":False}))
if __name__=="__main__":
    main()
