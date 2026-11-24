"""Physically witness original textbook context for untouched G3 slides.

This is an immutable, source-only queue for later *independent* visual and
scientific reviewers, not a source-science verdict. Recheck the original
preflight SHA and actual source/slides/script/mapping on every restart.
No model request, old Send replay, paid API, acceptance or publication.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf

from .g3_unreviewed_source_preflight_v1 import ROOT as PRE_ROOT, pinned
from .g3_original_visual_question_source_audit_v1 import _questions
from .g3_semantic_source_repair_v1 import _read, _sha, _canon, _write_once, need
from .g3_source_rejected_offline_repair_v1 import _terms
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .rich_element_model_alignment import request_for_slide
from .recovery_registry import lookup_mechanism

KIND="g3_untouched_source_witness"
SIGNATURE="G3_PREPARED_UNREVIEWED_ORIGINAL_SLIDES_LACK_PAGE_WITNESSED_SCIENCE_WORKLIST"
MECHANISM="PIN_ALL_ORIGINAL_TEXT_AND_PHYSICAL_PDF_QUOTES_WITHOUT_MODEL_SEND"
ROOT="g3_untouched_source_witness_v2"
STATUS="G3_UNTOUCHED_ORIGINAL_SLIDE_PUBLISHER_VISUAL_WITNESSES_UNAPPROVED"
MAX_SLIDES=6
MAX_PAGES=24
MAX_PAGE_CHARS=25000
MAX_PAGE_LINES=900
MAX_QUOTES_PER_UTTERANCE=2
MAX_QUOTE=360


def _sha_text(value: str)->str:
    return hashlib.sha256(value.encode("utf8")).hexdigest()


def _pages(folder:Path,source_sha:str)->list[dict]:
    source=folder/"source.pdf"
    need(source.is_file() and not source.is_symlink()
         and _sha(source)==source_sha,
         "Original publisher PDF changed before untouched witness")
    pages=[]
    with pymupdf.open(source) as pdf:
        need(1<=len(pdf)<=MAX_PAGES,
             "Unbounded original publisher subsection")
        for number,page in enumerate(pdf,1):
            text=page.get_text(sort=True)
            lines=text.splitlines(keepends=True)
            need(len(text)<=MAX_PAGE_CHARS and len(lines)<=MAX_PAGE_LINES,
                 "Original publisher page is too large for bounded evidence")
            candidates=[]
            seen=set()
            for index in range(len(lines)):
                for width in (1,2,3):
                    quote="".join(lines[index:index+width]).strip()
                    if not 25<=len(quote)<=MAX_QUOTE or (
                            "\x00" in quote or "\r" in quote):
                        continue
                    terms=_terms(quote)
                    digest=_sha_text(quote)
                    if not terms or digest in seen:
                        continue
                    seen.add(digest)
                    candidates.append((quote,terms,digest))
            pages.append({"page":number,"candidates":candidates})
    need(_sha(source)==source_sha,
         "Original publisher PDF changed during text extraction")
    return pages


def _witness(*,folder:Path,source_sha:str,pages:list,
             spoken:str,visible_terms:set[str])->list[dict]:
    spoken_terms=_terms(spoken)
    if len(spoken_terms)<2 or not visible_terms:
        return []
    ranked=[]
    for page in pages:
        for quote,terms,digest in page["candidates"]:
            in_spoken=sorted(spoken_terms&terms)
            in_visible=sorted(visible_terms&terms)
            if len(in_spoken)<2 or not in_visible:
                continue
            ranked.append((
                -len(in_spoken)-len(in_visible),
                -len(in_spoken),page["page"],digest,quote,
                in_spoken,in_visible))
    results=[]
    seen_pages=set()
    for _,_,page,digest,quote,in_spoken,in_visible in sorted(ranked):
        if page in seen_pages:
            continue
        try:
            proof=prove_source_quote_occurrence(
                source_pdf=folder/"source.pdf",
                expected_sha256=source_sha,
                page_number=page,verbatim_quote=quote)
        except (ValueError,RuntimeError,KeyError,TypeError):
            # Overlapping columns, discontinuous lines or ambiguous extracts
            # are NEVER accepted as a genuine original publisher witness.
            continue
        need(proof["math_semantics_author_verified"] is False
             and proof["publication_authorized"] is False,
             "Physical PDF excerpt must not grant scientific approval")
        results.append({
            "original_publisher_pdf_page":page,
            "verbatim_textbook_quote":quote,
            "literal_quote_sha256":digest,
            "physically_verified_quote_sha256":proof["quote_sha256"],
            "narration_token_overlap":in_spoken[:20],
            "rendered_visible_token_overlap":in_visible[:20],
            "physically_witnessed_source":True,
            "scientific_semantic_support_verified":False,
        })
        seen_pages.add(page)
        if len(results)==MAX_QUOTES_PER_UTTERANCE:
            break
    return results


def _packet(*,spec:dict,state_root:Path,preflight_file:Path,
            pages:list)->dict:
    prepared=pinned(spec=spec,state_root=state_root,
                    task_file=preflight_file)
    need(prepared["status"]==
         "G3_UNTOUCHED_ORIGINAL_SLIDE_SOURCE_PREPARED_NO_SEND"
         and prepared["new_browser_sends"]==0
         and prepared["independent_scientific_QA_complete"] is False,
         "Only genuinely untouched source-prepared slides are eligible")
    folder=Path(spec["source_folder"]).absolute()
    request=request_for_slide(
        source_folder=folder,checkpoint=Path(spec["checkpoint"]).absolute(),
        slide_number=prepared["original_slide"])
    shas=request["source_inputs_sha256"]
    need(request["request_sha256"]==
         prepared["original_mapping_request_sha256"]
         and shas==prepared["source_inputs_sha256"]
         and shas["source.pdf"]==_sha(folder/"source.pdf"),
         "Untouched source/slides/script identity changed")
    units=request["original_utterances"]
    targets=request["visible_targets"]
    need(len(units)==prepared["original_utterance_count"]
         and len(targets)==prepared["original_visual_target_count"],
         "Original slide narration or visual element count changed")
    expected_units=[
        {"original_utterance_id":x["utterance_id"],
         "original_spoken_text_sha256":_sha_text(x["verbatim_text"])}
        for x in units]
    expected_targets=[
        {"original_target_id":x["target_id"],
         "original_target_kind":x["kind"],
         "original_visible_text_sha256":_sha_text(x["visible_text"])}
        for x in targets]
    need(expected_units==prepared["original_utterances"]
         and expected_targets==prepared["original_visible_targets"],
         "Original slide rendered text and narration SHA changed")
    visible_terms=set().union(*(_terms(x["visible_text"])
                                 for x in targets))
    narrations=[]
    for unit in units:
        quote_rows=_witness(
            folder=folder,source_sha=shas["source.pdf"],
            pages=pages,spoken=unit["verbatim_text"],
            visible_terms=visible_terms)
        narrations.append({
            "original_utterance_id":unit["utterance_id"],
            "exact_original_narration":unit["verbatim_text"],
            "original_narration_sha256":_sha_text(unit["verbatim_text"]),
            "physical_publisher_quote_candidates":quote_rows,
            "source_excerpt_alone_proves_physics":False,
            "independent_source_science_QA_required":True,
        })
    original_targets=[{
        "original_target_id":t["target_id"],
        "original_target_kind":t["kind"],
        "exact_original_rendered_text":t["visible_text"],
        "original_rendered_text_sha256":_sha_text(t["visible_text"]),
        "independent_rendered_visual_QA_required":True,
    } for t in targets]
    # A navigation-only narrator can introduce substantive numbered
    # questions that are visibly present but never spoken. Their source
    # science QA must remain explicit and independent of narration.
    visual_questions=[]
    for target in targets:
        if (target["kind"]!="text_group" or not
                target["visible_text"].lstrip().startswith("1 ")):
            continue
        for question_number,text in enumerate(
                _questions(target["visible_text"]),1):
            candidates=_witness(
                folder=folder,source_sha=shas["source.pdf"],
                pages=pages,spoken=text,visible_terms=_terms(text))
            visual_questions.append({
                "original_group_target_id":target["target_id"],
                "original_question_number":question_number,
                "exact_rendered_physics_question":text,
                "rendered_question_sha256":_sha_text(text),
                "physical_publisher_quote_candidates":candidates,
                "source_excerpt_alone_proves_answer":False,
                "independent_scientific_and_visual_QA_required":True,
            })
    need(len(visual_questions)<=8,
         "Unbounded original slide rendered scientific questions")
    scope=_sha_text(_canon({
        "evidence_schema_version":2,
        "preflight_scope":prepared["scope_sha256"],
        "preflight_file_sha256":_sha(preflight_file),
        "original_utterance_ids":[r["original_utterance_id"]
                                  for r in narrations],
        "original_target_ids":[r["original_target_id"]
                               for r in original_targets]}).decode("utf8"))
    return {
        "schema_version":2,"status":STATUS,"scope_sha256":scope,
        "section":spec["section"],
        "original_slide":prepared["original_slide"],
        "original_preflight_scope_sha256":prepared["scope_sha256"],
        "original_preflight_file_sha256":_sha(preflight_file),
        "original_source_inputs_sha256":shas,
        "original_mapping_request_sha256":request["request_sha256"],
        "original_narrations":narrations,
        "original_rendered_visual_targets":original_targets,
        "original_rendered_scientific_questions":visual_questions,
        "rendered_scientific_question_count":len(visual_questions),
        "total_physically_witnessed_quote_candidates":sum(
            len(x["physical_publisher_quote_candidates"])
            for x in [*narrations,*visual_questions]),
        "source_text_extracted_without_ocr":True,
        "source_quote_is_semantic_approval":False,
        "independent_scientific_QA_complete":False,
        "independent_visual_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_QA_complete":False,
        "original_browser_claim_replayed":False,
        "new_browser_sends":0,"paid_gemini_API_calls":0,
        "student_publication_authorized":False,
    }


def materialize(*,specs:list,state_root:Path)->dict:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "Missing executable original publisher witness recovery")
    root=Path(state_root).absolute()
    need(root.is_dir() and not root.is_symlink()
         and type(specs) is list and 1<=len(specs)<=6,
         "Original G3 source-only evidence root missing")
    items=[]
    for spec in specs:
        need(type(spec) is dict
             and all(k in spec for k in (
                 "section","source_folder","checkpoint","review_root")),
             "Original G3 subsection mapping required")
        prehome=root/PRE_ROOT/spec["section"]
        if not prehome.exists():
            continue
        need(prehome.is_dir() and not prehome.is_symlink(),
             "Redirected original untouched review tasks")
        tasks=sorted(prehome.glob("*.json"))
        need(len(tasks)<=MAX_SLIDES and all(
            x.is_file() and not x.is_symlink() for x in tasks),
            "Original untouched review task inventory unbounded")
        if not tasks:
            continue
        folder=Path(spec["source_folder"]).absolute()
        first=_read(tasks[0])
        pages=_pages(folder,first["source_inputs_sha256"]["source.pdf"])
        for file in tasks:
            task=_packet(spec=spec,state_root=root,preflight_file=file,
                         pages=pages)
            out=root/ROOT/spec["section"]
            need(not out.is_symlink(),
                 "Redirected publisher source evidence checkpoint")
            out.mkdir(parents=True,exist_ok=True)
            _write_once(out/(task["scope_sha256"]+".json"),task)
            items.append(task)
    need(len(items)<=MAX_SLIDES,
         "Unexpected original untouched slide evidence inventory")
    return {
        "schema_version":2,
        "status":"G3_UNTOUCHED_PUBLISHER_VISUAL_WITNESSES_STAGED_UNAPPROVED",
        "prepared_original_slides":len(items),
        "original_narrations":sum(len(x["original_narrations"])
                                  for x in items),
        "original_rendered_targets":sum(len(x["original_rendered_visual_targets"])
                                       for x in items),
        "unspoken_rendered_scientific_questions":sum(
            len(x["original_rendered_scientific_questions"])
            for x in items),
        "physically_witnessed_quote_candidates":sum(
            x["total_physically_witnessed_quote_candidates"]
            for x in items),
        "original_slides_without_any_textbook_quote":sum(
            x["total_physically_witnessed_quote_candidates"]==0
            for x in items),
        "tasks":[{"section":x["section"],
                  "slide":x["original_slide"],
                  "scope_sha256":x["scope_sha256"],
                  "quote_candidates":x["total_physically_witnessed_quote_candidates"]}
                 for x in items],
        "independent_scientific_QA_accepted":0,
        "independent_visual_QA_accepted":0,
        "new_browser_sends":0,"paid_gemini_API_calls":0,
        "student_publication_authorized":False,
    }
