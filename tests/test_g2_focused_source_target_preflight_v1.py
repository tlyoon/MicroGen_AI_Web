"""Source-backed G2 target-choice preflight: real PDF and no-Send faults."""
import copy
import json
import hashlib
from pathlib import Path
import pytest

from selenium_pipeline import g2_focused_source_target_preflight_v1 as pre
from selenium_pipeline import g2_ranked_source_review_candidate_v3 as v2
from selenium_pipeline import g2_distinct_focused_source_review_v1 as focused
from selenium_pipeline import autonomous_recovery_continuation_v1 as ctl
from selenium_pipeline.recovery_registry import lookup_mechanism
from tests.test_g2_distinct_focused_source_review_v1 import real_source_fixture
from tests.test_autonomous_recovery_continuation_v1 import campaign_fixture


def _fixture(real_source_fixture,monkeypatch,*,mismatch=False):
    folder,queue,job,quote,claim=real_source_fixture
    if mismatch:
        wrong=copy.deepcopy(job["slides"][0]["visual_targets"][0])
        wrong["id"]="s003.text.000"
        wrong["visible_text"]="Unrelated Title Heading"
        job["slides"][0]["visual_targets"]=[
            wrong,job["slides"][0]["visual_targets"][0]]
        for u in job["slides"][0]["utterances"]:
            u["ranked_candidates"]=["s003.text.001","s003.text.000"]
    monkeypatch.setattr(focused,"build_review_job",
                        lambda **kw:copy.deepcopy(job))
    monkeypatch.setattr(pre,"build_review_job",
                        lambda **kw:copy.deepcopy(job))
    return folder,queue,job,claim


def test_registry_has_executable_g2_target_audit():
    assert lookup_mechanism(pre.KIND,pre.SIGNATURE)==pre.MECHANISM


def test_real_pdf_quote_and_target_staged_without_sends(
        real_source_fixture,monkeypatch):
    folder,queue,job,claim=_fixture(real_source_fixture,monkeypatch)
    item=focused.plan(folder=folder,queue_root=queue,slide=3,
                      utterance_id="s003.utterance.001")
    before=(claim/"dispatch_attempted.claim").read_bytes()
    got=pre.stage(folder=folder,queue_root=queue,item=item)
    assert got["status"]==pre.STATUS_READY
    assert got["new_browser_sends"]==0
    assert got["independent_academic_QA_complete"] is False
    path=Path(got["receipt"])
    packet=json.loads(path.read_text("utf8"))
    assert packet["original_utterance_id"]=="s003.utterance.001"
    assert packet["physically_witnessed_quote_sha256"]==hashlib.sha256(
        real_source_fixture[3].encode()).hexdigest()
    assert packet["publisher_quote_is_scientific_proof"] is False
    assert packet["best_ranked_target_is_academically_verified"] is False
    assert packet["student_publication_authorized"] is False
    saved=path.read_bytes()
    assert pre.stage(folder=folder,queue_root=queue,item=item)==got
    assert path.read_bytes()==saved
    assert (claim/"dispatch_attempted.claim").read_bytes()==before
    assert not (queue.parent/focused.REVIEW_ROOT_NAME).exists()


def test_legacy_wrong_title_flagged_without_changing_old_claim(
        real_source_fixture,monkeypatch):
    folder,queue,job,claim=_fixture(
        real_source_fixture,monkeypatch,mismatch=True)
    item=focused.plan(folder=folder,queue_root=queue,slide=3,
                      utterance_id="s003.utterance.001")
    got=pre.stage(folder=folder,queue_root=queue,item=item)
    assert got["status"]==pre.STATUS_MISMATCH
    assert got["legacy_target_id"]=="s003.text.000"
    assert got["first_physically_backed_ranked_target_id"]=="s003.text.001"
    assert got["new_paid_gemini_API_calls"]==0
    packet=json.loads(Path(got["receipt"]).read_text("utf8"))
    assert packet["original_focused_selected_target_text"]==(
        "Unrelated Title Heading")
    assert packet["focused_target_is_first_ranked_physical_candidate"] is False
    assert packet["independent_academic_QA_complete"] is False
    assert not (queue.parent/focused.REVIEW_ROOT_NAME).exists()


def test_source_drift_fails_closed_before_audit(
        real_source_fixture,monkeypatch):
    folder,queue,job,claim=_fixture(real_source_fixture,monkeypatch)
    item=focused.plan(folder=folder,queue_root=queue,slide=3,
                      utterance_id="s003.utterance.001")
    with (folder/"source.pdf").open("ab") as f:
        f.write(b"tampered source")
    with pytest.raises(ValueError,match="fingerprint drift"):
        pre.stage(folder=folder,queue_root=queue,item=item)


def test_dry_run_automatically_stages_all_independent_source_choices(
        campaign_fixture,monkeypatch):
    # Fixture provided by existing central G2 campaign tests.
    folder,queue,job,calls,run=campaign_fixture
    monkeypatch.setattr(pre,"build_review_job",
                        lambda **kw:copy.deepcopy(job))
    def staged(**kw):
        return pre.stage(**kw)
    report=run("g2_multi_source_stage_20261124",
               max_sends=0,execute=False,
               stage_source_only=True,max_actions=3)
    assert len(report["stages"])==3
    assert [x["unit"] for x in report["stages"]]==[
        f"s003.utterance.{i:03d}" for i in (1,2,3)]
    assert all(x["source_target_audit"]["status"]==pre.STATUS_READY
               for x in report["stages"])
    assert not calls
    assert report["possible_provider_sends_reserved"]==0
    assert report["student_publication_authorized"] is False
    assert len(list((queue.parent/pre.ROOT).glob("*.json")))==3


def test_new_send_must_stop_when_rendered_source_target_rank_mismatch(
        campaign_fixture,monkeypatch):
    folder,queue,job,calls,run=campaign_fixture
    wrong=copy.deepcopy(job["slides"][0]["visual_targets"][0])
    wrong["id"]="s003.text.000"
    wrong["visible_text"]="Unrelated Title Heading"
    job["slides"][0]["visual_targets"]=[wrong,job["slides"][0]["visual_targets"][0]]
    for u in job["slides"][0]["utterances"]:
        u["ranked_candidates"]=["s003.text.001","s003.text.000"]
    monkeypatch.setattr(ctl,"build_review_job",
                        lambda **kw:copy.deepcopy(job))
    monkeypatch.setattr(focused,"build_review_job",
                        lambda **kw:copy.deepcopy(job))
    monkeypatch.setattr(pre,"build_review_job",
                        lambda **kw:copy.deepcopy(job))
    monkeypatch.setattr(v2,"build_review_job",
                        lambda **kw:copy.deepcopy(job))
    receipt=run("g2_mismatch_no_send_20261124",
                max_sends=2,execute=True,max_actions=3)
    assert not calls
    assert receipt["possible_provider_sends_reserved"]==0
    assert len(receipt["stages"])==3
    assert all(x["source_target_audit"]["status"]==pre.STATUS_MISMATCH
               for x in receipt["stages"])
    assert receipt["new_paid_gemini_api_calls"]==0
    assert receipt["student_publication_authorized"] is False
