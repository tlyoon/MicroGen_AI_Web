"""Long-horizon source work remains useful while an unrelated G2 Send is HELD."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from selenium_pipeline import long_horizon_g3_source_worker_v1 as worker
from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.recovery_registry import lookup_mechanism


def prepare(tmp_path):
    archive=tmp_path/"original_inputs"
    state=tmp_path/"G3_state"
    root=tmp_path/"receipts"
    rows=[]
    for section,name in (("Serway_8_2","8_2"),("Serway_8_3","8_3")):
        src=archive/name
        src.mkdir(parents=True)
        for file in ("source.pdf","slides.pdf","script.txt"):
            (src/file).write_bytes((section+"/"+file).encode())
        draft=state/"g3_original_element_review_drafts_v1"/section/("a"*64+".json")
        draft.parent.mkdir(parents=True)
        draft.write_text("{}")
        row={
            "section":section,
            "element_mapping_source_review":{
                "status":"G3_ORIGINAL_SOURCE_ELEMENT_MAPPING_REVIEW_STAGED_NO_TTS",
                "draft_receipt":str(draft),
                "source_sha256":_sha(src/"source.pdf"),
                "slides_sha256":_sha(src/"slides.pdf"),
                "script_sha256":_sha(src/"script.txt")},
            "publisher_quote_mapping_recovery":{
                "status":"G3_SOURCE_PHYSICAL_CONTEXT_INCREMENTALLY_STAGED_NO_APPROVAL",
                "original_ambiguous_utterance_count":3,
                "source_scientific_QA_complete":False,
                "student_publication_authorized":False}}
        rows.append(row)
    report=tmp_path/"original_report.json"
    report.write_text(json.dumps({
        "source_bound_actual_highlight_recovery":rows}))
    state.mkdir(exist_ok=True)
    return dict(original_report=report,archive_root=archive,
                state_root=state,report_root=root)


def fake_progress(previous=None,override=None):
    already=previous or {}
    calls=[]
    def advance(**kwargs):
        section=kwargs["section"]
        calls.append(section)
        cur=already.get(section,0)
        new=min(2,3-cur)
        already[section]=cur+new
        result={
          "status":"G3_BOUNDED_SOURCE_PHYSICAL_QUOTE_CONTINUATION_NO_APPROVAL",
          "prior_unfinalized_scopes_recovered":cur,
          "new_source_quote_tasks_staged":new,
          "remaining_unprocessed_ambiguous_tasks":3-cur-new,
          "source_scientific_QA_complete":False,
          "new_browser_sends":0,"new_paid_gemini_API_calls":0,
          "student_publication_authorized":False}
        if override:return override(section,result)
        return result
    return advance,calls,already


def test_registry_executable_handler():
    assert lookup_mechanism(worker.KIND,worker.SIGNATURE)==worker.MECHANISM


def test_advance_unrelated_sections_until_complete(tmp_path):
    params=prepare(tmp_path)
    advance,calls,saved=fake_progress()
    out=worker.run(**params,continuation_fn=advance)
    assert out["status"]==worker.DONE
    assert out["source_only_completed"]
    assert out["new_source_scopes_in_this_run"]=={"Serway_8_2":3,"Serway_8_3":3}
    assert len(calls)==4
    assert out["rounds_completed"]==2
    assert not out["student_publication_authorized"]


def test_one_source_drift_is_held_other_continues(tmp_path):
    params=prepare(tmp_path)
    (params["archive_root"]/"8_3"/"script.txt").write_bytes(b"changed!")
    advance,calls,saved=fake_progress()
    out=worker.run(**params,continuation_fn=advance)
    assert out["source_sections"]["Serway_8_3"]["status"]=="SOURCE_SCOPE_HELD"
    assert out["source_sections"]["Serway_8_2"]["status"]=="SOURCE_SCOPE_COMPLETE"
    assert saved=={"Serway_8_2":3}
    assert len(calls)==2
    assert not out["source_only_completed"]


def test_interruption_restores_scoped_progress_without_replay(tmp_path):
    params=prepare(tmp_path)
    advance,calls,saved=fake_progress()
    first=worker.run(**params,max_rounds=1,continuation_fn=advance)
    assert first["source_sections"]["Serway_8_2"]["remaining"]==1
    assert first["rounds_completed"]==1
    second=worker.run(**params,continuation_fn=advance)
    assert second["status"]==worker.DONE
    assert second["new_source_scopes_in_this_run"]=={
        "Serway_8_2":1,"Serway_8_3":1}
    assert saved=={"Serway_8_2":3,"Serway_8_3":3}
    assert worker._read(params["report_root"]/"g3_long_horizon_progress.json")["status"]==worker.DONE


def test_zero_new_progress_hold_does_not_block_other_source(tmp_path):
    params=prepare(tmp_path)
    advance,calls,saved=fake_progress()
    def never_add_other(section,row):
        if section=="Serway_8_2":
            row.update(new_source_quote_tasks_staged=0,
                       remaining_unprocessed_ambiguous_tasks=3)
        return row
    out=worker.run(**params,continuation_fn=fake_progress(override=never_add_other)[0])
    assert "Serway_8_2" in out["held_sections"]
    assert out["source_sections"]["Serway_8_3"]["status"]=="SOURCE_SCOPE_COMPLETE"


def test_fabricated_model_send_or_acceptance_is_rejected(tmp_path):
    params=prepare(tmp_path)
    def fake(section,row):
        if section=="Serway_8_2":
            row["new_browser_sends"]=1
        return row
    out=worker.run(**params,continuation_fn=fake_progress(override=fake)[0])
    assert out["source_sections"]["Serway_8_2"]["status"]=="SOURCE_SCOPE_HELD"
    assert out["source_sections"]["Serway_8_3"]["status"]=="SOURCE_SCOPE_COMPLETE"
    assert out["new_browser_sends"]==0


def test_overreported_tasks_cannot_be_claimed_as_complete(tmp_path):
    params=prepare(tmp_path)
    def corrupted(section,row):
        if section=="Serway_8_2":
            row["remaining_unprocessed_ambiguous_tasks"]=0
        return row
    out=worker.run(**params,continuation_fn=fake_progress(override=corrupted)[0])
    assert out["source_sections"]["Serway_8_2"]["status"]=="SOURCE_SCOPE_HELD"
    assert not out["source_only_completed"]


def test_invalid_manifest_or_unbounded_loop_fails_closed(tmp_path):
    params=prepare(tmp_path)
    with pytest.raises(ValueError,match="Unbounded"):
        worker.run(**params,max_rounds=1000)
    obj=json.loads(params["original_report"].read_text())
    obj["source_bound_actual_highlight_recovery"][1]["section"]="Serway_8_2"
    params["original_report"].write_text(json.dumps(obj))
    with pytest.raises(ValueError,match="section set changed"):
        worker.run(**params)


def test_receipt_is_source_only(tmp_path):
    params=prepare(tmp_path)
    fn,calls,saved=fake_progress()
    report=worker.run(**params,continuation_fn=fn)
    raw=(params["report_root"]/"g3_long_horizon_progress.json").read_text()
    assert "source_scientific_QA_complete" in raw
    assert report["source_scientific_QA_complete"] is False
    assert report["independent_acoustic_QA_complete"] is False
    assert report["independent_video_highlight_QA_complete"] is False
    assert report["student_publication_authorized"] is False

