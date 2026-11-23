"""Safe automatic OFFLINE continuation when G3 model reply is source-rejected.

Reuses the real original request, rejected model capture, source PDF and
existing rejection verifier. Creates candidate *publisher quotations* by
exact substring of the original PDF text ONLY. Scores are lexical navigation
hints, NOT support for scientific/diagram or audio acceptance. Does not retry
any uncertain or rejected Gemini Send, and never edits original source or QA.

This path is eligible even when the two-uncertain-Send G3 circuit breaker
forbids all additional model use. It is intentionally NOT a model fallback.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

from . import g3_rich_mapping_auto_continuation_v71 as reviewer
from .recovery_registry import lookup_mechanism
from .rich_element_model_alignment import request_for_slide, parse_response

KIND="g3_rejected_source_quote_offline_repair"
SIGNATURE="G3_CAPTURED_SOURCE_QUOTE_REJECTION_WITH_BROWSER_CIRCUIT_OPEN"
MECHANISM="REVERIFY_REJECTED_MODEL_AND_MATERIALIZE_EXACT_PUBLISHER_SNIPPETS"
STATUS="G3_REJECTED_CAPTURE_SOURCE_QUOTE_WORKLIST_NO_SEND_V2"
MAX_SECTIONS=8
MAX_SLIDES_PER_SECTION=120
MAX_CANDIDATES_PER_UTTERANCE=3
MAX_SOURCE_CHARS=180_000
_WORDS=re.compile(r"[A-Za-z0-9]{4,}",re.UNICODE)
_SECTION=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}\Z")
_STOP=frozenset((
    "that","this","with","from","which","these","those","into","through",
    "about","during","system","model","energy","slide","chapter","section",
    "what","when","have","there","will","would","could","should","some",
    "such","your","their","them","both","only","then","more","each",
))


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _sha(path:Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canon(value:dict) -> bytes:
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)
            +"\n").encode("utf8")


def _write_once(path:Path, data:dict) -> None:
    content=_canon(data)
    need(not path.is_symlink() and path.parent.is_dir()
         and not path.parent.is_symlink(),
         "Offline source-repair output redirected")
    staged=path.with_suffix(".stage")
    need(not staged.is_symlink(),"Redirected temporary worklist")
    if path.exists():
        need(path.is_file() and path.read_bytes()==content,
             "Previously issued source-repair evidence changed")
        if staged.exists():
            need(staged.is_file() and staged.read_bytes()==content,
                 "Staged source worklist differs from the immutable result")
            staged.unlink()
        return
    if staged.exists():
        need(staged.is_file() and staged.read_bytes()==content,
             "Interrupted worklist content changed")
    else:
        with staged.open("xb") as writer:
            writer.write(content)
            writer.flush()
            os.fsync(writer.fileno())
    os.replace(staged,path)


def _terms(text:str) -> set[str]:
    return {v.lower() for v in _WORDS.findall(text)
            if v.lower() not in _STOP}


def _source_spans(*,utterance:str,target_text:str,pages:list) -> list[dict]:
    """Physical PDF source snippets; no semantic assertion or model inference."""
    need(len(pages)<=4,"Unexpected unbounded original page evidence")
    want=_terms(utterance)|_terms(target_text)
    unique={}
    for page in pages:
        number=page["source_page"]
        literal=page["original_page_text"]
        need(type(number) is int and type(literal) is str
             and len(literal)<=MAX_SOURCE_CHARS,
             "Invalid publisher page excerpt")
        for match in re.finditer(r"[^\r\n]{12,240}",literal):
            quote=match.group()
            overlap=sorted(_terms(quote)&want)
            if len(overlap)<2:
                continue
            # A single generic shared token is not strong enough to
            # justify a source repair even as a lexical candidate.
            key=(number,hashlib.sha256(quote.encode("utf8")).hexdigest())
            candidate={
                "source_page":number,
                "publisher_quote_verbatim":quote,
                "publisher_quote_sha256":key[1],
                "publisher_page_text_sha256":hashlib.sha256(
                    literal.encode("utf8")).hexdigest(),
                "source_offset_start":match.start(),
                "source_offset_end":match.end(),
                "overlapping_terms":overlap[:20],
                "lexical_overlap_count":len(overlap),
                "quote_physically_present":True,
                "meaning_or_target_mapping_verified":False,
                "independent_scientific_QA_approved":False,
            }
            need(literal[match.start():match.end()]==quote,
                 "Source candidate did not match physical PDF text")
            unique[key]=candidate
    return sorted(unique.values(),key=lambda x:(
        -x["lexical_overlap_count"],x["source_page"],
        x["source_offset_start"]))[:MAX_CANDIDATES_PER_UTTERANCE]


def rejected_packet(*,source_folder:Path,checkpoint:Path,review_root:Path,
                    slide:int) -> dict:
    """Revalidate original rejection before proposing a separate, new task."""
    source_folder,checkpoint,review_root=(
        Path(source_folder).absolute(),Path(checkpoint).absolute(),
        Path(review_root).absolute())
    reviewer.prepare(source_folder=source_folder,checkpoint=checkpoint,
                     review_root=review_root)
    files=reviewer._files(review_root,slide)
    observed=reviewer._verified_source_rejection(
        source_folder=source_folder,checkpoint=checkpoint,
        n=slide,files=files)
    need(observed["status"]=="SOURCE_QUOTE_REJECTED_NO_REPLAY",
         "No independently reproduced historical scientific source rejection")
    claim=reviewer._read(files["claim"])
    response=reviewer._read(files["response"])
    need(parse_response(files["capture"].read_text("utf8"))==response,
         "Captured original model bytes changed from parsed original")
    request=request_for_slide(
        source_folder=source_folder,checkpoint=checkpoint,
        slide_number=slide)
    need(request.get("request_sha256")==claim.get("request_sha256")
         and request.get("source_inputs_sha256")==claim.get("source_inputs_sha256")
         and response.get("slide")==slide
         and len(response["associations"])==len(request["original_utterances"]),
         "Source-backed rejected model and request identity changed")
    target_map={v["target_id"]:v for v in request["visible_targets"]}
    missing=[]
    rows=[]
    for utterance,original in zip(
        request["original_utterances"],response["associations"]):
        need(original["utterance_id"]==utterance["utterance_id"],
             "Original model reordered or changed narration units")
        target_id=original.get("target_id")
        quote=original.get("source_quote")
        if target_id is None or quote is not None:
            continue
        need(target_id in target_map,
             "Rejected original model referenced a nonexistent slide target")
        target=target_map[target_id]
        spans=_source_spans(
            utterance=utterance["verbatim_text"],
            target_text=target.get("visible_text",""),
            pages=request["source_page_excerpts"])
        row={
            "utterance_id":utterance["utterance_id"],
            "verbatim_utterance_sha256":hashlib.sha256(
                utterance["verbatim_text"].encode("utf8")).hexdigest(),
            "original_selected_target_id":target_id,
            "original_selected_target_kind":target["kind"],
            "original_visible_text_sha256":hashlib.sha256(
                target.get("visible_text","").encode("utf8")).hexdigest(),
            "original_model_source_quote_was_missing":True,
            "original_model_source_selection_rejected":True,
            "source_excerpt_candidates":spans,
            "status":("PHYSICALLY_WITNESSED_LEXICAL_CANDIDATES_NOT_SEMANTIC_REPAIR"
                      if spans else
                      "NO_LEXICALLY_MATCHED_SOURCE_SNIPPETS_UNRESOLVED"),
            "human_or_independent_semantic_review_required":True,
        }
        rows.append(row)
        missing.append(utterance["utterance_id"])
    need(bool(missing),"Original rejection is not missing publisher quote")
    packet={
        "schema_version":2,
        "status":STATUS,
        "source_folder":str(source_folder),
        "source_inputs_sha256":claim["source_inputs_sha256"],
        "original_mapping_checkpoint_sha256":_sha(
            checkpoint/"mapping_checkpoint.json"),
        "original_slide_number":slide,
        "original_request_sha256":request["request_sha256"],
        "original_rejected_claim_sha256":_sha(files["claim"]),
        "original_rejected_raw_model_capture_sha256":_sha(files["capture"]),
        "original_rejected_parsed_response_sha256":_sha(files["response"]),
        "source_rejection_reason":claim["source_rejection_reason"],
        "original_rejected_utterances_missing_source_quote":missing,
        "publisher_quote_worklist":rows,
        "quote_candidates_are_scientific_proof":False,
        "original_rejected_source_review_accepted":False,
        "repaired_source_to_target_mapping_accepted":False,
        "author_source_PDF_modified":False,
        "original_historical_model_request_replayed":False,
        "new_browser_sends":0,
        "new_paid_gemini_API_requests":0,
        "independent_acoustic_review_complete":False,
        "highlighted_video_accepted":False,
        "student_publication_authorized":False,
    }
    return packet


def materialize(*,specs:list,output_root:Path) -> dict:
    """Auto-forward across all G3 source-rejected slides, without model Sends."""
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "G3 source rejection offline repair not registered")
    output_root=Path(output_root).absolute()
    need(type(specs) is list and 1<=len(specs)<=MAX_SECTIONS
         and output_root.parent.is_dir() and not output_root.is_symlink(),
         "Bounded detached G3 offline repair root required")
    require_sections=set()
    for spec in specs:
        need(type(spec) is dict
             and _SECTION.fullmatch(spec.get("section","")) is not None
             and spec["section"] not in require_sections,
             "G3 source sections not unique")
        require_sections.add(spec["section"])
        for key in ("source_folder","checkpoint","review_root"):
            need(isinstance(spec.get(key),Path)
                 and spec[key].is_dir() and not spec[key].is_symlink()
                 and not output_root.is_relative_to(spec[key])
                 and not spec[key].is_relative_to(output_root),
                 "Source review and output directories must be independent")
        reviewer.prepare(
            source_folder=spec["source_folder"],
            checkpoint=spec["checkpoint"],review_root=spec["review_root"])
    output_root.mkdir(exist_ok=True)
    need(output_root.is_dir() and not output_root.is_symlink(),
         "Offline source repair root redirected after creation")
    issued=[]
    unreviewed=0
    uncertain=0
    retained=0
    for spec in specs:
        meta=reviewer._read(spec["review_root"]/"g3_auto_mapping_identity.json")
        count=meta["original_slides"]
        need(type(count) is int and 1<=count<=MAX_SLIDES_PER_SECTION,
             "Unbounded original G3 slide inventory")
        for n in range(1,count+1):
            files=reviewer._files(spec["review_root"],n)
            # Existing owner can restore saved claims but must never submit.
            observed=reviewer._inspect_one(
                source_folder=spec["source_folder"],
                checkpoint=spec["checkpoint"],root=spec["review_root"],
                n=n)
            status=observed["status"]
            if status=="ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET":
                unreviewed+=1
            elif status in ("CLAIMED_OR_UNKNOWN_SEND_NO_REPLAY",
                          "SAVED_SOURCE_REPLY_UNTRUSTED_NO_REPLAY",
                          "QUARANTINED_MODEL_EVIDENCE_WITHOUT_SEND_CLAIM"):
                uncertain+=1
            if status!="SOURCE_QUOTE_REJECTED_NO_REPLAY":
                continue
            retained+=1
            packet=rejected_packet(
                source_folder=spec["source_folder"],
                checkpoint=spec["checkpoint"],
                review_root=spec["review_root"],slide=n)
            section_root=output_root/spec["section"]
            section_root.mkdir(exist_ok=True)
            need(section_root.is_dir() and not section_root.is_symlink(),
                 "Unsafe section-specific offline source-repair output")
            name=f"slide_{n:03d}_{hashlib.sha256(_canon(packet)).hexdigest()[:24]}.json"
            path=section_root/name
            _write_once(path,packet)
            issued.append({
                "section":spec["section"],"slide":n,
                "worklist_path":str(path),
                "worklist_sha256":_sha(path),
                "missing_source_quote_units":len(
                    packet["original_rejected_utterances_missing_source_quote"]),
                "lexical_candidate_units":sum(bool(row["source_excerpt_candidates"])
                    for row in packet["publisher_quote_worklist"]),
                "original_scientific_rejection_preserved":True,
            })
    return {
        "schema_version":1,
        "status":"G3_REJECTED_SOURCE_OFFLINE_WORKLIST_PERSISTED_NO_MODEL_SEND",
        "rejected_original_slides_retained":retained,
        "offline_quote_worklists":issued,
        "untouched_original_slides":unreviewed,
        "uncertain_original_browser_sends_retained":uncertain,
        "new_browser_sends":0,
        "new_paid_gemini_API_requests":0,
        "new_original_source_review_acceptances":0,
        "independent_scientific_QA_complete":False,
        "independent_acoustic_review_complete":False,
        "highlighted_video_accepted":False,
        "student_publication_authorized":False,
    }
