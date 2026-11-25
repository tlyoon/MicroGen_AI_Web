"""Finite real textbook quote witness for unapproved G3 element mappings.

Reuse the historical physically checked G3 source-context retriever rather than
making an unsanctioned Gemini science request, guessing the correct diagram, or
autopromoting the authored element mapping. After a static-video repair worklist
and immutable publisher source element draft exist, incrementally stage at
most a few SOURCE-ONLY physics/context quotes. Each attempted ambiguous
utterance is an immutable scoped checkpoint, including zero-quote outcomes.
Re-entering never reissues model sends or double-counts completed review work.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .figure_source_identity import _sha, require
from .g3_semantic_context_recovery_v2 import _context
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .recovery_registry import lookup_mechanism

KIND="g3_element_publisher_quote_autoforward"
SIGNATURE="G3_AMBIGUOUS_ELEMENT_REVIEW_DRAFT_LACKS_PHYSICAL_TEXTBOOK_CONTEXT"
MECHANISM="CONTINUE_BOUNDED_SOURCE_QUOTE_WITNESSES_WITHOUT_MODEL_SEND"
ROOT="g3_element_publisher_quote_autoforward_v1"
MAX_TASKS_PER_INVOCATION=2
MAX_STAGED_QUOTES=4


def _canon(data:dict)->bytes:
    return (json.dumps(data,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf8")


def _read(path:Path,max_bytes:int=2_000_000)->dict:
    require(path.is_file() and not path.is_symlink()
            and 0<path.stat().st_size<max_bytes,
            "Missing, unsafe or oversize source-only mapping receipt")
    doc=json.loads(path.read_text("utf8"))
    require(type(doc) is dict,"Malformed publisher evidence record")
    return doc


def _source_proof(source_pdf:Path,source_sha:str,quote:dict,verifier)->dict:
    require(type(quote) is dict
            and quote.get("physically_witnessed_original_PDF") is True
            and quote.get("source_semantic_support_verified") is False
            and type(quote.get("source_page")) is int
            and type(quote.get("verbatim_source_quote")) is str
            and quote.get("source_lexical_score",0)>=0,
            "Quote candidate cannot assert academic source agreement")
    page=quote["source_page"];body=quote["verbatim_source_quote"]
    physical=verifier(source_pdf=source_pdf,
        expected_sha256=source_sha,page_number=page,verbatim_quote=body)
    require(type(physical) is dict
            and physical.get("source_sha256")==source_sha
            and physical.get("source_page")==page
            and physical.get("math_semantics_author_verified") is False
            and physical.get("publication_authorized") is False
            and quote["witnessed_quote_sha256"]==physical.get("quote_sha256")
            and quote["original_source_quote_sha256"]==
                hashlib.sha256(body.encode("utf8")).hexdigest(),
            "Physical textbook quote does not match original source")
    return {
        "source_page":page,"verbatim_source_quote":body,
        "original_source_quote_sha256":quote["original_source_quote_sha256"],
        "witnessed_quote_sha256":physical["quote_sha256"],
        "source_lexical_score":quote["source_lexical_score"],
        "original_spoken_overlap":quote.get("original_spoken_overlap",[]),
        "rendered_target_overlap":quote.get("rendered_target_overlap",[]),
        "physical_original_publisher_source_verified":True,
        "source_semantics_verified":False,
        "human_academic_approval":False}


def advance(*,source_folder:Path,state_root:Path,section:str,
            draft_receipt:Path,source_hashes:dict,
            max_new_tasks:int=MAX_TASKS_PER_INVOCATION,
            context_fetcher=None,quote_verifier=None)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Real original source quote autoforward recovery not registered")
    src=Path(source_folder).absolute()
    state=Path(state_root).absolute()
    draft_file=Path(draft_receipt).absolute()
    require(section in ("Serway_8_2","Serway_8_3")
            and src.is_dir() and state.is_dir()
            and not src.is_symlink() and not state.is_symlink()
            and not state.is_relative_to(src)
            and 0<=max_new_tasks<=MAX_TASKS_PER_INVOCATION,
            "Invalid, unsafe or unbounded original source quote work")
    names=("source.pdf","slides.pdf","script.txt")
    require(type(source_hashes) is dict
            and set(source_hashes)==set(names)
            and all((src/n).is_file() and not (src/n).is_symlink()
                    and _sha(src/n)==source_hashes[n] for n in names),
            "Original G3 publisher PDF or narration hash changed")
    require(draft_file.is_relative_to(state/
            "g3_original_element_review_drafts_v1"/section)
            and draft_file.suffix==".json"
            and len(draft_file.stem)==64,
            "Only original state-pinned PR639 source element drafts accepted")
    draft=_read(draft_file)
    draft_bytes=draft_file.read_bytes()
    draft_sha=_sha(draft_file)
    require(draft_file.stem==draft_sha
            and all(draft[n.split(".")[0]+"_sha256"]==
                    source_hashes[n] for n in names)
            and draft.get("status")=="REVIEW_REQUIRED_NOT_TTS_READY"
            and draft.get("can_stage_or_synthesize_audio") is False
            and draft.get("academic_approval") is False
            and draft.get("manual_mapping_reviewed") is False
            and draft.get("student_publication") is False,
            "Cannot evidence changed or approved element draft as original")
    root=state/ROOT/section
    require(not root.is_symlink() and not root.is_relative_to(src),
            "G3 source-only publisher quote output must be external")
    root.mkdir(parents=True,exist_ok=True)
    fetch=context_fetcher or _context
    prove=quote_verifier or prove_source_quote_occurrence
    total=0;staged=0;reused=0;quote_count=0;held_no_target=0
    files=[]
    for slide in draft["slides"]:
        candidates={t["draft_element_id"]:t for t
                    in slide["auto_candidate_targets"]}
        for utterance in slide["proposed_utterances"]:
            if utterance["mapping_ambiguous"] is not True:continue
            total+=1
            rankings=utterance["candidate_target_rankings_unverified"]
            target=(candidates.get(rankings[0]["draft_element_id"])
                    if rankings else None)
            target_text=(target or {}).get("visible_text") or ""
            identity={
                "schema":"G3_ORIGINAL_UNAPPROVED_SOURCE_QUOTE_SCOPE_V1",
                "section":section,
                "source_hashes":source_hashes,
                "original_element_draft_sha256":draft_sha,
                "original_slide":slide["slide_number"],
                "original_utterance_id":utterance["proposal_id"],
                "original_spoken_fragment_sha256":hashlib.sha256(
                    utterance["verbatim_script_fragment"].encode("utf8")
                ).hexdigest(),
                "top_ranked_visual_element_id":(
                    target["draft_element_id"] if target else None),
                "top_ranked_visual_text_sha256":(
                    hashlib.sha256(target_text.encode("utf8")).hexdigest()
                    if target else None)}
            scope=hashlib.sha256(_canon(identity)).hexdigest()
            path=root/(scope+".json")
            if path.exists() or path.is_symlink():
                saved=_read(path,max_bytes=200_000)
                require(saved["original_scope"]==identity
                        and saved["student_publication_authorized"] is False
                        and saved["source_scientific_QA_complete"] is False,
                        "Prior source-mapping review scope mismatched original")
                for quote in saved["physically_witnessed_source_context"]:
                    # Genuine original PDF bytes, not merely a saved SHA string.
                    checked=_source_proof(src/"source.pdf",
                        source_hashes["source.pdf"],{
                        "source_page":quote["source_page"],
                        "verbatim_source_quote":quote["verbatim_source_quote"],
                        "physically_witnessed_original_PDF":True,
                        "source_semantic_support_verified":False,
                        "source_lexical_score":quote["source_lexical_score"],
                        "witnessed_quote_sha256":
                            quote["witnessed_quote_sha256"],
                        "original_source_quote_sha256":
                            quote["original_source_quote_sha256"],
                        "original_spoken_overlap":
                            quote["original_spoken_overlap"],
                        "rendered_target_overlap":
                            quote["rendered_target_overlap"],
                        },prove)
                    require(checked==quote,
                            "Old physical source context altered on restart")
                reused+=1
                continue
            if staged>=max_new_tasks:continue
            if target and len(target_text.strip())>=3:
                job={"source_sha256":source_hashes["source.pdf"],
                     "slides":[{"utterances":[{
                         "spoken_text":utterance["verbatim_script_fragment"]}],
                         "visual_targets":[{"visible_text":target_text}]}]}
                proposed=fetch(folder=src,job=job,previous_quotes=set())
                require(type(proposed) is list and len(proposed)<=8,
                        "Unbounded non-attributable source context retriever")
                verified=[_source_proof(
                    src/"source.pdf",source_hashes["source.pdf"],quote,prove)
                    for quote in proposed[:MAX_STAGED_QUOTES]]
                status=("G3_PHYSICAL_PUBLISHER_CONTEXT_STAGED_NO_SEMANTIC_APPROVAL"
                        if verified else
                        "G3_NO_PHYSICAL_PUBLISHER_CONTEXT_FOUND_SOURCE_REVIEW_REQUIRED")
            else:
                verified=[]
                held_no_target+=1
                status="G3_NO_VISUAL_TEXT_TARGET_SOURCE_REVIEW_REQUIRED"
            require(all(_sha(src/n)==source_hashes[n] for n in names)
                    and draft_file.read_bytes()==draft_bytes,
                    "Source or element draft changed during publisher context")
            report={
                "schema_version":1,"status":status,
                "original_scope":identity,
                "physically_witnessed_source_context":verified,
                "publisher_quotes_do_not_prove_physics":True,
                "source_scientific_QA_complete":False,
                "source_figure_semantics_approved":False,
                "per_element_TTS_ready":False,
                "independent_acoustic_QA_complete":False,
                "independent_video_highlight_QA_complete":False,
                "student_publication_authorized":False,
                "new_browser_sends":0,
                "new_paid_gemini_API_calls":0}
            with path.open("xb") as file:
                file.write(_canon(report));file.flush();os.fsync(file.fileno())
            files.append(str(path))
            quote_count+=len(verified)
            staged+=1
    require(all(_sha(src/n)==source_hashes[n] for n in names)
            and draft_file.read_bytes()==draft_bytes,
            "Original evidence changed after bounded source-only work")
    return {
        "status":"G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL",
        "section":section,"original_ambiguous_utterance_count":total,
        "new_source_quote_tasks_staged":staged,
        "reused_source_quote_tasks":reused,
        "new_physically_witnessed_publisher_quotes":quote_count,
        "new_tasks_without_visual_text_target":held_no_target,
        "remaining_unprocessed_ambiguous_tasks":total-staged-reused,
        "new_task_receipts":files,
        "original_draft_sha256":draft_sha,
        "original_source_sha256":source_hashes["source.pdf"],
        "source_scientific_QA_complete":False,
        "per_element_TTS_ready":False,
        "independent_video_highlight_QA_complete":False,
        "student_publication_authorized":False,
        "new_browser_sends":0,
        "new_paid_gemini_API_calls":0}
