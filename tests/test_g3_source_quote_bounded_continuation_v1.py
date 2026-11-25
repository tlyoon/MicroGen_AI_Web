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

