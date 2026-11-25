"""Continuation regression: bounded loops, no fake progress or publication."""
import pytest
from selenium_pipeline.g3_source_quote_bounded_continuation_v1 import continue_quotes


def fake(steps,seen):
    def run(**kw):
        seen.append(kw["section"])
        count,next_remaining=steps.pop(0)
        return dict(status="G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL",
            new_source_quote_tasks_staged=count,
            remaining_unprocessed_ambiguous_tasks=next_remaining,
            new_physically_witnessed_publisher_quotes=2*count,
            new_task_receipts=[str(i) for i in range(count)],
            source_scientific_QA_complete=False,
            student_publication_authorized=False,new_browser_sends=0,
            new_paid_gemini_API_calls=0)
    return run


def invoke(remaining,steps,max_batches=8):
    seen=[]
    out=continue_quotes(source_folder="source",state_root="state",
        section="Serway_8_2",draft_receipt="draft.json",
        source_hashes={},expected_remaining=remaining,
        max_batches=max_batches,advance_one=fake(steps,seen))
    return out,seen


def test_repeated_source_only_work_until_closed():
    out,seen=invoke(5,[(2,3),(2,1),(1,0)])
    assert out["new_source_quote_tasks_staged"]==5
    assert out["new_physically_witnessed_publisher_quotes"]==10
    assert out["batches_executed"]==3
    assert len(seen)==3
    assert out["student_publication_authorized"] is False


def test_bounded_eight_batches_16_tasks():
    out,seen=invoke(100,[(2,100-2*(i+1)) for i in range(8)])
    assert out["new_source_quote_tasks_staged"]==16
    assert out["remaining_unprocessed_ambiguous_tasks"]==84
    assert len(seen)==8


def test_idempotent_stall_stops_without_retrying():
    out,seen=invoke(9,[(0,9)])
    assert out["new_source_quote_tasks_staged"]==0
    assert len(seen)==1


def test_no_start_when_all_done():
    out,seen=invoke(0,[])
    assert out["batches_executed"]==0 and not seen


def test_forged_new_tasks_or_remaining_rejected():
    with pytest.raises(ValueError,match="invented progress"):
        invoke(7,[(2,6)])


def test_oversized_batch_rejected():
    with pytest.raises(ValueError,match="invented progress"):
        invoke(9,[(3,6)])


def test_no_unbounded_runs():
    with pytest.raises(ValueError,match="Unbounded"):
        invoke(20,[],max_batches=50)


def test_new_browser_send_is_never_admitted():
    def bad(**kw):
        x=fake([(1,1)],[])(**kw)
        x["new_browser_sends"]=1
        return x
    with pytest.raises(ValueError):
        continue_quotes(source_folder="source",state_root="state",
            section="Serway_8_3",draft_receipt="draft.json",
            source_hashes={},expected_remaining=2,advance_one=bad)



def test_recover_interrupted_scopes_before_forward_batch():
    calls=[]
    def replay(**kwargs):
        calls.append(kwargs.get("max_new_tasks",2))
        if kwargs.get("max_new_tasks")==0:
            return dict(status="G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL",
                original_ambiguous_utterance_count=47,reused_source_quote_tasks=26,
                remaining_unprocessed_ambiguous_tasks=21,
                new_source_quote_tasks_staged=0,
                new_physically_witnessed_publisher_quotes=0,
                student_publication_authorized=False,
                source_scientific_QA_complete=False,new_browser_sends=0,
                new_paid_gemini_API_calls=0)
        return fake([(2,19)],[])(**kwargs)
    result=continue_quotes(source_folder="original",state_root="state",
        section="Serway_8_2",draft_receipt="draft.json",source_hashes={},
        expected_remaining=37,max_batches=1,resume_from_saved=True,
        advance_one=replay)
    assert result["prior_unfinalized_scopes_recovered"]==16
    assert result["new_source_quote_tasks_staged"]==2
    assert result["remaining_unprocessed_ambiguous_tasks"]==19
    assert calls==[0,2]


def test_unsafe_mismatched_checkpoint_receipt_fails_closed():
    def unsafe(**kw):
        return dict(status="G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL",
            original_ambiguous_utterance_count=47,reused_source_quote_tasks=99,
            remaining_unprocessed_ambiguous_tasks=0,new_source_quote_tasks_staged=0,
            new_physically_witnessed_publisher_quotes=0,student_publication_authorized=False,
            source_scientific_QA_complete=False,new_browser_sends=0,
            new_paid_gemini_API_calls=0)
    with pytest.raises(ValueError,match="inventory inconsistent"):
        continue_quotes(source_folder="original",state_root="state",
            section="Serway_8_2",draft_receipt="draft.json",source_hashes={},
            expected_remaining=37,resume_from_saved=True,advance_one=unsafe)


def test_previous_source_drift_cannot_resume_as_success():
    def corrupted(**kw):
        raise ValueError("Original textbook SHA mismatch")
    with pytest.raises(ValueError,match="SHA mismatch"):
        continue_quotes(source_folder="original",state_root="state",
            section="Serway_8_3",draft_receipt="draft.json",source_hashes={},
            expected_remaining=50,resume_from_saved=True,advance_one=corrupted)


def test_restarted_completed_source_inventory_returns_no_new_sends():
    seen=[]
    def only_reconcile(**kw):
        seen.append(kw.get("max_new_tasks"))
        return dict(status="G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL",
            original_ambiguous_utterance_count=47,reused_source_quote_tasks=47,
            remaining_unprocessed_ambiguous_tasks=0,new_source_quote_tasks_staged=0,
            new_physically_witnessed_publisher_quotes=0,student_publication_authorized=False,
            source_scientific_QA_complete=False,new_browser_sends=0,
            new_paid_gemini_API_calls=0)
    r=continue_quotes(source_folder="original",state_root="state",
        section="Serway_8_2",draft_receipt="draft.json",source_hashes={},
        expected_remaining=21,resume_from_saved=True,advance_one=only_reconcile)
    assert r["prior_unfinalized_scopes_recovered"]==21
    assert r["batches_executed"]==0 and seen==[0]
