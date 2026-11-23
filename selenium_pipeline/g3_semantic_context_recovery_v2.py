"""G3 scientific reviewer failure -> distinct physically witnessed textbook context.

This is not a third model retry. Two saved original one-Send reviews are
revalidated as immutable input; consistent UNRESOLVED model verdicts trigger
read-only original textbook example retrieval. Candidate paragraphs must
overlap actual narration AND independently verified rendered slide content.
No model verdict, source semantic acceptance, audio or publication is added.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pymupdf

from .g3_source_rejected_offline_repair_v1 import _canon,_sha,_terms,need
from .g3_semantic_source_repair_v1 import _write_once
from .pdf_text_source_span_witness import prove_source_quote_occurrence
from .series_gemini import decode_storyboard_response
from .academic_review_checkpoint import _neon_model_witness, fingerprint
from .ai_academic_web_review import review_instructions
from .recovery_registry import lookup_mechanism

KIND="g3_semantic_context_recovery"
SIGNATURE="G3_TWO_SOURCE_REVIEWERS_FOUND_AN_EXACT_BUT_IRRELEVANT_QUOTE"
MECHANISM="RECLASSIFY_TWO_UNRESOLVED_VERDICTS_AND_RETRIEVE_DISTINCT_PDF_CONTEXT"
STATUS="G3_BOTH_INDEPENDENT_SCIENCE_REVIEWERS_UNRESOLVED_SOURCE_REPAIR_V3"
MAX_PAGES=24
MAX_QUOTES=8
MAX_QUOTES_PER_PAGE=2
MAX_WINDOW=400


def _original_review_rows(root:Path,report:dict,job:dict)->tuple[dict,dict]:
    rows=[]
    for folder,key,mode in (
        ("initial_request","first_owned_source_review_sha256","INITIAL_REVIEW"),
        ("challenge_request","independent_challenge_owned_response_sha256",
         "INDEPENDENT_CHALLENGE")):
        path=root/folder/"model_response_untrusted.txt"
        state=root/folder/"request_state.json"
        need(path.is_file() and not path.is_symlink()
             and state.is_file() and not state.is_symlink()
             and _sha(path)==report[key],
             "Original two-pass source model response SHA changed")
        status=json.loads(state.read_text("utf8"))
        expected=fingerprint(
            request_text=review_instructions(job,mode=mode),
            source_hashes={
                "source.pdf":job["source_sha256"],
                "slides.pdf":job["slides_sha256"],
                "script.txt":job["script_sha256"]},
            review_mode=mode)
        need(status.get("status")=="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"
             and status.get("request_fingerprint")==expected
             and status.get("review_mode")==mode
             and status.get("response_sha256")==report[key],
             "Source AI response was not original, accepted or source-pinned")
        _neon_model_witness(
            root/folder,expected,
            expected_response_sha256=report[key])
        response=decode_storyboard_response(path.read_text("utf8"))
        need(response.get("status")=="ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE"
             and type(response.get("rows")) is list
             and len(response["rows"])==1
             and response["rows"][0].get("verdict") in (
                 "SUPPORTED","INCORRECT","UNRESOLVED"),
             "Original model sentence cannot be independently classified")
        rows.append(response["rows"][0])
    return rows[0],rows[1]


def _context(*,folder:Path,job:dict,
             previous_quotes:set[tuple[int,str]])->list[dict]:
    unit=job["slides"][0]["utterances"][0]
    target=job["slides"][0]["visual_targets"][0]
    original_terms=_terms(unit["spoken_text"])
    target_terms=_terms(target["visible_text"])
    eligible=[]
    source=folder/"source.pdf"
    with pymupdf.open(source) as pdf:
        need(1<=len(pdf)<=MAX_PAGES,"Unbounded original textbook subsection")
        for i,page in enumerate(pdf):
            text=page.get_text(sort=True)
            need(len(text)<=25_000,
                 "Large publisher PDF page requires explicit subdivision")
            # Preserve exact adjacent PDF text lines as a CONTIGUOUS
            # quotation; never concatenate distant positions or OCR guesses.
            lines=text.splitlines(keepends=True)
            for index in range(len(lines)):
                for window in (1,2,3,4):
                    quote="".join(lines[index:index+window]).strip()
                    if not 25<=len(quote)<=MAX_WINDOW:
                        continue
                    overlaps=sorted(_terms(quote)&original_terms)
                    target_anchor=sorted(_terms(quote)&target_terms)
                    if len(overlaps)<2 or not target_anchor:
                        continue
                    key=(i+1,hashlib.sha256(quote.encode("utf8")).hexdigest())
                    if key in previous_quotes:
                        continue
                    try:
                        witness=prove_source_quote_occurrence(
                            source_pdf=source,
                            expected_sha256=job["source_sha256"],
                            page_number=i+1,verbatim_quote=quote)
                    except (ValueError,RuntimeError,KeyError,TypeError):
                        continue
                    need(witness["math_semantics_author_verified"] is False,
                         "PDF snippet cannot self-verify scientific meaning")
                    score=len(overlaps)+len(target_anchor)
                    eligible.append({
                        "source_page":i+1,
                        "verbatim_source_quote":quote,
                        "original_source_quote_sha256":key[1],
                        "witnessed_quote_sha256":witness["quote_sha256"],
                        "original_spoken_overlap":overlaps[:20],
                        "rendered_target_overlap":target_anchor[:20],
                        "source_lexical_score":score,
                        "physically_witnessed_original_PDF":True,
                        "source_semantic_support_verified":False,
                    })
    # Keep independent PDF-page evidence, not eight near-duplicates
    # from a single narrative paragraph. This lets a final derivation on
    # the next original page compete with earlier introductory language.
    chosen=[]
    page_counts={}
    normalized_seen=set()
    for row in sorted(eligible,key=lambda x:(
        -x["source_lexical_score"],x["source_page"],
        x["original_source_quote_sha256"])):
        page=row["source_page"]
        collapsed=" ".join(row["verbatim_source_quote"].split())
        if (page_counts.get(page,0)>=MAX_QUOTES_PER_PAGE
                or (page,collapsed) in normalized_seen):
            continue
        chosen.append(row)
        normalized_seen.add((page,collapsed))
        page_counts[page]=page_counts.get(page,0)+1
        if len(chosen)>=MAX_QUOTES:
            break
    return chosen


def recover(*,folder:Path,task:dict,review_root:Path)->dict:
    """Classify saved independent reviewers; stage source-context repair only."""
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "New G3 semantic-context recovery mechanism not registered")
    folder=Path(folder).absolute()
    review_root=Path(review_root).absolute()
    need(folder.is_dir() and not folder.is_symlink()
         and review_root.is_dir() and not review_root.is_symlink()
         and not review_root.is_relative_to(folder)
         and task.get("status")=="G3_DISTINCT_SOURCE_SEMANTIC_QA_READY_NO_SEND"
         and task.get("old_whole_slide_request_replayed") is False
         and task.get("student_publication_authorized") is False,
         "Source-identified, unapproved distinct G3 task required")
    job=task["science_review_job"]
    need(_sha(folder/"source.pdf")==job["source_sha256"]
         and _sha(folder/"slides.pdf")==job["slides_sha256"]
         and _sha(folder/"script.txt")==job["script_sha256"]
         and job["g3_distinct_source_science_v1"]["scope_sha256"]==
             task["scope_sha256"],
         "Original G3 source or one-claim semantics altered")
    original=review_root/"two_pass_science_evidence.json"
    need(original.is_file() and not original.is_symlink(),
         "Two independent source reviews required before context repair")
    report=json.loads(original.read_text("utf8"))
    need(report.get("source_sha256")==job["source_sha256"]
         and report.get("scope_sha256")==task["scope_sha256"]
         and report.get("two_actual_model_scientific_reviews") is True
         and report.get("original_G3_semantic_mappings_promoted")==0
         and report.get("student_publication_authorized") is False,
         "Original G3 scientific-repair evidence was not independently reviewed")
    first,second=_original_review_rows(review_root,report,job)
    uid=task["original_utterance_id"]
    need(first["utterance_id"]==second["utterance_id"]==uid,
         "Model reviewer changed original narrated statement")
    verdicts=[first["verdict"],second["verdict"]]
    if verdicts==["UNRESOLVED","UNRESOLVED"]:
        status=STATUS
        previous={
            (c["source_page"],c["publisher_raw_quote_sha256"])
            for c in task["exact_original_source_quote_candidates"]}
        alternatives=_context(folder=folder,job=job,previous_quotes=previous)
        recommendation=(
            "NEW_DISTINCT_EXAMPLE_CONTEXT_REVIEW_TASK_REQUIRED"
            if alternatives else
            "NO_ALTERNATIVE_PHYSICAL_SOURCE_CONTEXT_FOUND_HOLD")
    elif verdicts==["SUPPORTED","SUPPORTED"] and report.get(
            "science_AI_source_agreed") is True:
        status="G3_TWO_SOURCE_AI_REVIEWERS_SUPPORTED_NO_HUMAN_APPROVAL"
        alternatives=[]
        recommendation="PENDING_SEPARATE_ORIGINAL_G3_SEMANTIC_QA"
    else:
        status="G3_TWO_SOURCE_AI_REVIEWERS_DISAGREE_OR_IDENTIFY_ERROR"
        alternatives=[]
        recommendation="SCIENTIFIC_REVIEW_OR_TEXT_CORRECTION_REQUIRED"
    output={
        "schema_version":3,"status":status,
        "original_source_task_scope_sha256":task["scope_sha256"],
        "original_two_pass_receipt_sha256":_sha(original),
        "original_source_sha256":job["source_sha256"],
        "original_utterance_id":uid,
        "original_two_model_verdicts":verdicts,
        "source_context_alternative_candidates":alternatives,
        "new_distinct_recovery_action":recommendation,
        "additional_context_snippets_are_semantic_proof":False,
        "previous_original_model_claims_replayed":False,
        "new_gemini_browser_sends":0,
        "new_gemini_paid_API_calls":0,
        "original_G3_semantic_mappings_promoted":0,
        "independent_scientific_QA_human_attestation":False,
        "acoustic_QA_accepted":False,
        "video_QA_accepted":False,
        "student_publication_authorized":False,
    }
    # Preserve the first v2 source navigation receipt and original 2-pass
    # model evidence. Better paragraph-window ranking is a NEW version.
    _write_once(review_root/"semantic_context_recovery_v3.json",output)
    return output
