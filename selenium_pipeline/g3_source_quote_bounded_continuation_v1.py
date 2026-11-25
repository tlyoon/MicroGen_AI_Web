"""Bounded, idempotent continuation of genuine G3 textbook-quote recovery.

This only repeatedly invokes the previously registered physical PDF witness.
No model reviewer, TTS, paid API, student publication or semantic acceptance.
A single run has a strict finite cap; restarted runs reuse scoped receipts.
"""
from __future__ import annotations

from pathlib import Path
from .figure_source_identity import require
from .g3_element_publisher_quote_autoforward_v1 import advance as source_quotes

MAX_BATCHES=8


def continue_quotes(*, source_folder:Path, state_root:Path, section:str,
                    draft_receipt:Path,source_hashes:dict,
                    expected_remaining:int,max_batches:int=MAX_BATCHES,
                    advance_one=None,resume_from_saved:bool=False)->dict:
    require(type(max_batches) is int and 1<=max_batches<=MAX_BATCHES
            and type(expected_remaining) is int and expected_remaining>=0,
            "Unbounded or unverified G3 source continuation")
    advance=advance_one or source_quotes
    remaining=expected_remaining
    recovered=0
    if resume_from_saved:
        # Re-read the physically source-proven immutable unit receipts rather
        # than trusting an interrupted summary. max_new_tasks=0 is essential.
        saved=advance(source_folder=source_folder,state_root=state_root,
            section=section,draft_receipt=draft_receipt,
            source_hashes=source_hashes,max_new_tasks=0)
        require(saved["status"]=="G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL"
                and saved["source_scientific_QA_complete"] is False
                and saved["student_publication_authorized"] is False
                and saved["new_browser_sends"]==0
                and saved["new_paid_gemini_API_calls"]==0
                and saved["new_source_quote_tasks_staged"]==0
                and saved["new_physically_witnessed_publisher_quotes"]==0,
                "Resume preflight must be an exact zero-Send source-only recheck")
        old=saved["reused_source_quote_tasks"]
        total=saved["original_ambiguous_utterance_count"]
        observed=saved["remaining_unprocessed_ambiguous_tasks"]
        require(type(old) is int and type(total) is int
                and type(observed) is int and 0<=old<=total
                and observed==total-old
                and 0<=observed<=expected_remaining<=total,
                "Interrupted source-scope inventory inconsistent with pinned baseline")
        recovered=expected_remaining-observed
        remaining=observed
    new_tasks=0;new_quotes=0;rounds=0;receipts=[]
    for _ in range(max_batches):
        if remaining==0:break
        row=advance(source_folder=source_folder,state_root=state_root,
            section=section,draft_receipt=draft_receipt,
            source_hashes=source_hashes)
        require(row["status"]=="G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL", "Source continuation returned unexpected status")
        require(row["source_scientific_QA_complete"] is False, "Source continuation falsely approved science")
        require(row["student_publication_authorized"] is False, "Source continuation cannot authorize release")
        require(row["new_browser_sends"]==0, "Source continuation cannot make browser Sends")
        require(row["new_paid_gemini_API_calls"]==0, "Source continuation cannot make paid API calls")
        count=row["new_source_quote_tasks_staged"]
        nxt=row["remaining_unprocessed_ambiguous_tasks"]
        quotes=row["new_physically_witnessed_publisher_quotes"]
        require(type(count) is int and 0<=count<=2
                and type(nxt) is int and nxt>=0
                and nxt==remaining-count
                and type(quotes) is int and 0<=quotes<=4*count,
                "G3 physical quote batch invented progress or changed scope")
        rounds+=1
        new_tasks+=count;new_quotes+=quotes
        receipts+=row["new_task_receipts"]
        remaining=nxt
        if count==0:break
    return {
        "status":"G3_BOUNDED_SOURCE_PHYSICAL_QUOTE_CONTINUATION_NO_APPROVAL",
        "section":section,"batches_executed":rounds,
        "prior_unfinalized_scopes_recovered":recovered,
        "source_receipts_reconciled_before_new_work":resume_from_saved,
        "new_source_quote_tasks_staged":new_tasks,
        "new_physically_witnessed_publisher_quotes":new_quotes,
        "remaining_unprocessed_ambiguous_tasks":remaining,
        "new_task_receipts":receipts,
        "source_scientific_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "student_publication_authorized":False,
        "new_browser_sends":0,
        "new_paid_gemini_API_calls":0,
    }

