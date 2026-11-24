"""New separate G2 ranked visual source-review input, never model Send."""
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
import pytest

from selenium_pipeline import g2_ranked_source_review_candidate_v3 as v2
from selenium_pipeline import g2_focused_source_target_preflight_v1 as pre
from selenium_pipeline import g2_distinct_focused_source_review_v1 as focused
from selenium_pipeline import autonomous_recovery_continuation_v1 as ctl
from selenium_pipeline.recovery_registry import lookup_mechanism
from selenium_pipeline.ai_academic_web_review import review_instructions
from tests.test_g2_distinct_focused_source_review_v1 import real_source_fixture
from tests.test_autonomous_recovery_continuation_v1 import campaign_fixture


def _mismatch_fixture(real_source_fixture,monkeypatch):
    folder,queue,job,quote,claim=real_source_fixture
    title=copy.deepcopy(job["slides"][0]["visual_targets"][0])
    title["id"]="s003.text.000"
    title["visible_text"]="Unrelated Title Heading"
    job["slides"][0]["visual_targets"]=[
        title,job["slides"][0]["visual_targets"][0]]
    for unit in job["slides"][0]["utterances"]:
        unit["ranked_candidates"]=["s003.text.001","s003.text.000"]
    for mod in (focused,pre,v2):
        monkeypatch.setattr(mod,"build_review_job",
                            lambda **kw:copy.deepcopy(job))
    return folder,queue,job,claim


def test_registry_new_ranked_candidate_is_executable():
    assert lookup_mechanism(v2.KIND,v2.SIGNATURE)==v2.MECHANISM


def test_mismatch_generates_distinct_physical_source_review_job_without_sends(
        real_source_fixture,monkeypatch):
    folder,queue,job,claim=_mismatch_fixture(
        real_source_fixture,monkeypatch)
    original=focused.plan(folder=folder,queue_root=queue,slide=3,
                          utterance_id="s003.utterance.001")
    prior=pre.stage(folder=folder,queue_root=queue,item=original)
    assert prior["status"]==pre.STATUS_MISMATCH
    old_claim=(claim/"dispatch_attempted.claim").read_bytes()
    good=v2.stage(folder=folder,queue_root=queue,item=original,
                  source_preflight=prior)
    assert good["status"]==v2.STATUS
    assert good["new_review_send_authorized"] is False
    assert good["new_browser_sends"]==0
    assert good["paid_gemini_API_calls"]==0
    assert good["student_publication_authorized"] is False
    payload=json.loads(Path(good["receipt"]).read_text("utf8"))
    assert payload["scope_sha256"]!=original["scope_sha256"]
    assert payload["original_focused_wrong_target_scope_sha256"]==(
        original["scope_sha256"])
    assert payload["schema_version"]==3
    assert payload["new_initial_prompt_sha256"]!=payload[
        "new_challenge_prompt_sha256"]
    # The prompts must rehash from the EXACT persisted JSON job. The prior
    # V2 packet silently changed its prompt when sorted JSON was reloaded.
    reloaded_job=payload["source_science_review_job"]
    assert hashlib.sha256(review_instructions(
        reloaded_job,mode="INITIAL_REVIEW").encode()).hexdigest()==(
            payload["new_initial_prompt_sha256"])
    assert hashlib.sha256(review_instructions(
        reloaded_job,mode="INDEPENDENT_CHALLENGE").encode()).hexdigest()==(
            payload["new_challenge_prompt_sha256"])
    assert payload["original_legacy_rendered_target_id"]=="s003.text.000"
    assert payload["corrected_ranked_physical_target_id"]=="s003.text.001"
    job_v2=payload["source_science_review_job"]
    assert job_v2["slides"][0]["visual_targets"][0]["id"]=="s003.text.001"
    assert job_v2["slides"][0]["visual_targets"][0]["visible_text"]==(
        real_source_fixture[3])
    assert "focused_source_review_v1" not in job_v2
    assert job_v2["focused_source_review_v3"]["independent_scientific_two_pass_QA_required"] is True
    assert payload["source_only_ranking_is_scientific_proof"] is False
    assert payload["independent_academic_QA_complete"] is False
    assert not (queue.parent/focused.REVIEW_ROOT_NAME).exists()
    assert (claim/"dispatch_attempted.claim").read_bytes()==old_claim
    saved=Path(good["receipt"]).read_bytes()
    assert v2.stage(folder=folder,queue_root=queue,item=original,
                    source_preflight=prior)==good
    assert Path(good["receipt"]).read_bytes()==saved


def test_ranked_candidate_never_promotes_an_aligned_legacy_source(
        real_source_fixture,monkeypatch):
    folder,queue,job,quote,claim=real_source_fixture
    monkeypatch.setattr(pre,"build_review_job",lambda **kw:copy.deepcopy(job))
    item=focused.plan(folder=folder,queue_root=queue,slide=3,
                      utterance_id="s003.utterance.001")
    preflight=pre.stage(folder=folder,queue_root=queue,item=item)
    assert preflight["status"]==pre.STATUS_READY
    with pytest.raises(ValueError,match="aligned or unverified"):
        v2.stage(folder=folder,queue_root=queue,item=item,
                 source_preflight=preflight)


def test_changed_original_pdf_blocks_stale_ranked_candidate(
        real_source_fixture,monkeypatch):
    folder,queue,job,claim=_mismatch_fixture(
        real_source_fixture,monkeypatch)
    item=focused.plan(folder=folder,queue_root=queue,slide=3,
                      utterance_id="s003.utterance.001")
    preflight=pre.stage(folder=folder,queue_root=queue,item=item)
    with (folder/"source.pdf").open("ab") as f:
        f.write(b"source changed")
    with pytest.raises(ValueError):
        v2.stage(folder=folder,queue_root=queue,item=item,
                 source_preflight=preflight)


def test_immutable_preflight_tampering_blocks_ranked_candidate(
        real_source_fixture,monkeypatch):
    folder,queue,job,claim=_mismatch_fixture(
        real_source_fixture,monkeypatch)
    item=focused.plan(folder=folder,queue_root=queue,slide=3,
                      utterance_id="s003.utterance.001")
    old=pre.stage(folder=folder,queue_root=queue,item=item)
    path=Path(old["receipt"])
    value=json.loads(path.read_text("utf8"))
    value["student_publication_authorized"]=True
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        v2.stage(folder=folder,queue_root=queue,item=item,
                 source_preflight=old)


def test_controller_autonomously_stages_separate_review_v2_without_send(
        campaign_fixture,monkeypatch):
    folder,queue,job,calls,run=campaign_fixture
    old=copy.deepcopy(job["slides"][0]["visual_targets"][0])
    old["id"]="s003.text.000"
    old["visible_text"]="Unrelated Title Heading"
    job["slides"][0]["visual_targets"]=[
        old,job["slides"][0]["visual_targets"][0]]
    for x in job["slides"][0]["utterances"]:
        x["ranked_candidates"]=["s003.text.001","s003.text.000"]
    monkeypatch.setattr(ctl,"build_review_job",
                        lambda **kw:copy.deepcopy(job))
    for mod in (focused,pre,v2):
        monkeypatch.setattr(mod,"build_review_job",
                            lambda **kw:copy.deepcopy(job))
    receipt=run("stage_ranked_review_v2_20261124",
                max_sends=0,execute=False,stage_source_only=True,
                max_actions=3)
    assert len(receipt["stages"])==3
    assert all(x["ranked_source_review_candidate"]["status"]==v2.STATUS
               for x in receipt["stages"])
    assert len(list((queue.parent/v2.ROOT).glob("*.json")))==3
    assert not calls
    assert receipt["possible_provider_sends_reserved"]==0
    assert receipt["new_paid_gemini_api_calls"]==0
    assert receipt["student_publication_authorized"] is False
