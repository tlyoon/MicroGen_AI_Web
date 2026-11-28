"""Scoped user-authorized G2 capacity: historical cap never reset or replayed."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from selenium_pipeline import g2_v3_explicit_scoped_capacity_v1 as grant
from selenium_pipeline import g2_ranked_v3_owned_selenium_handoff_v1 as handoff
from selenium_pipeline import g2_distinct_focused_source_review_v1 as focused
from selenium_pipeline.autonomous_recovery_continuation_v1 import _campaign,_append
from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.recovery_registry import lookup_mechanism
from tests.test_g2_ranked_v3_owned_selenium_handoff_v1 import eligible as historical_eligible
from tests.test_g2_distinct_focused_source_review_v1 import real_source_fixture


@pytest.fixture()
def eligible(real_source_fixture,monkeypatch):
    return historical_eligible.__wrapped__(real_source_fixture,monkeypatch)


def initial_parent(eligible,*,complete=True):
    folder,queue,candidate,old_claim=eligible
    home,head,events=_campaign(
        root=queue/"autonomous_recovery_continuation_v1",
        campaign_id=grant.PARENT,source_sha=_sha(folder/"source.pdf"),
        queue_sha=_sha(queue/"queue.json"),max_sends=2)
    events=_append(home,head,events,"RESERVE",
                   scope="old_one",phase="INITIAL",detail="old")
    events=_append(home,head,events,"RESULT" if complete else "HOLD",
                   scope="old_one",phase="INITIAL",detail="old")
    events=_append(home,head,events,"RESERVE",
                   scope="old_one",phase="CHALLENGE",detail="old")
    _append(home,head,events,"RESULT",
                   scope="old_one",phase="CHALLENGE",detail="old")
    return home


def test_registry_contains_one_explicit_new_capacity_recovery():
    assert lookup_mechanism(grant.KIND,grant.SIGNATURE)==grant.MECHANISM


def test_missing_explicit_consent_must_not_create_campaign(eligible):
    folder,queue,candidate,_=eligible
    with pytest.raises(ValueError,match="explicit authorization"):
        grant.provision(folder=folder,queue_root=queue,candidate_file=candidate,
                        health_result=queue/"health.json")
    assert not (queue.parent/grant.ROOT).exists()


def test_distinct_one_scope_two_pass_grant_is_immutable_and_idempotent(eligible,monkeypatch):
    folder,queue,candidate,_=eligible
    original=initial_parent(eligible)
    parent_sha=_sha(original/"campaign.json")
    monkeypatch.setattr(focused,"_health_ok",lambda **kw:{"verified":True})
    a=grant.provision(folder=folder,queue_root=queue,candidate_file=candidate,
                     health_result=queue/"health.json",explicit_user_consent=True)
    assert a["new_cap"]==2
    assert a["new_model_requests"]==0
    assert a["old_cap_unchanged"]
    assert _sha(original/"campaign.json")==parent_sha
    b=grant.provision(folder=folder,queue_root=queue,candidate_file=candidate,
                     health_result=queue/"health.json",explicit_user_consent=True)
    assert a==b
    result=handoff.inspect(folder=folder,queue_root=queue,candidate_file=candidate,
                           campaign_id=a["new_campaign_id"],execute=False)
    assert result["status"]=="G2_V3_NEW_DISTINCT_MODEL_INPUT_READY_NO_SEND"
    assert result["original_campaign_cap"]==2
    assert result["new_browser_sends_reserved"]==0
    assert result["student_publication_authorized"] is False


def test_old_uncertain_HOLD_disallows_new_capacity(eligible,monkeypatch):
    folder,queue,candidate,_=eligible
    initial_parent(eligible,complete=False)
    monkeypatch.setattr(focused,"_health_ok",lambda **kw:{})
    with pytest.raises(ValueError,match="unresolved"):
        grant.provision(folder=folder,queue_root=queue,candidate_file=candidate,
                        health_result=queue/"health.json",explicit_user_consent=True)
    assert not (queue.parent/grant.ROOT).exists()


def test_health_missing_or_unverified_cannot_create_grant(eligible):
    folder,queue,candidate,_=eligible
    initial_parent(eligible)
    with pytest.raises(Exception):
        grant.provision(folder=folder,queue_root=queue,candidate_file=candidate,
                        health_result=queue/"missing.json",explicit_user_consent=True)
    assert not (queue.parent/grant.ROOT).exists()


def test_mismatched_old_claim_journal_fails_closed(eligible,monkeypatch):
    folder,queue,candidate,_=eligible
    home=initial_parent(eligible)
    monkeypatch.setattr(focused,"_health_ok",lambda **kw:{})
    a=grant.provision(folder=folder,queue_root=queue,candidate_file=candidate,
                     health_result=queue/"health.json",explicit_user_consent=True)
    path=home/"event_004.json"
    raw=json.loads(path.read_text("utf8"));raw["detail"]="tampered"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError):
        grant.verify_grant(queue_root=queue,source_sha=_sha(folder/"source.pdf"),
          scope_sha=a["scope_sha256"],candidate_sha=_sha(candidate),
          campaign_id=a["new_campaign_id"],cap=2)


def test_grant_cannot_change_selected_source_scope_or_budget(eligible,monkeypatch):
    folder,queue,candidate,_=eligible
    initial_parent(eligible)
    monkeypatch.setattr(focused,"_health_ok",lambda **kw:{})
    a=grant.provision(folder=folder,queue_root=queue,candidate_file=candidate,
                     health_result=queue/"health.json",explicit_user_consent=True)
    sha=_sha(folder/"source.pdf")
    with pytest.raises(ValueError):
        grant.verify_grant(queue_root=queue,source_sha=sha,
                           scope_sha="0"*64,candidate_sha=_sha(candidate),
                           campaign_id=a["new_campaign_id"],cap=2)
    with pytest.raises(ValueError):
        grant.verify_grant(queue_root=queue,source_sha=sha,
                           scope_sha=a["scope_sha256"],candidate_sha=_sha(candidate),
                           campaign_id=a["new_campaign_id"],cap=3)



def test_new_campaign_with_no_explicit_grant_cannot_use_reviewer(eligible):
    folder,queue,candidate,_=eligible
    from datetime import datetime,timezone
    row=json.loads(candidate.read_text("utf8"))
    name=grant.PREFIX+datetime.now(timezone.utc).strftime("%Y%m%d")+"_"+row["scope_sha256"][:12]
    _campaign(root=queue/"autonomous_recovery_continuation_v1",
        campaign_id=name,source_sha=_sha(folder/"source.pdf"),
        queue_sha=_sha(queue/"queue.json"),max_sends=2)
    with pytest.raises(ValueError,match="explicit grant"):
        handoff.inspect(folder=folder,queue_root=queue,candidate_file=candidate,
                       campaign_id=name,execute=False)


def _with_yesterday_then_today(eligible, monkeypatch):
    """Make a genuine prior-date grant, then restore UTC today.

    Does not mutate or reset the original immutable G2 campaign.
    """
    from datetime import datetime as real_datetime, timedelta
    class Yesterday:
        @staticmethod
        def now(tz):
            return real_datetime.now(tz) - timedelta(days=1)
    folder, queue, candidate, _ = eligible
    initial_parent(eligible)
    monkeypatch.setattr(focused, "_health_ok", lambda **kw: {"verified": True})
    monkeypatch.setattr(grant, "datetime", Yesterday)
    yesterday = grant.provision(
        folder=folder, queue_root=queue, candidate_file=candidate,
        health_result=queue/"health.json", explicit_user_consent=True)
    historical = (queue.parent/grant.ROOT/_sha(folder/"source.pdf")/
                  (real_datetime.now(grant.timezone.utc) -
                   timedelta(days=1)).strftime("%Y%m%d"))
    saved = (historical.with_suffix(".json")).read_bytes()
    monkeypatch.setattr(grant, "datetime", real_datetime)
    return yesterday, historical.with_suffix(".json"), saved


def _pretend_new_independent_ranked_scope(eligible, monkeypatch):
    """Inject a separately bound source scope for the grant-only unit test.

    The real V3 source inspector independently verifies such scopes; this
    mock never invokes Gemini and cannot qualify a forged model request.
    """
    original = handoff._verify
    def select(*, folder, queue_root, candidate_file):
        row, job = original(folder=folder, queue_root=queue_root,
                            candidate_file=candidate_file)
        return {**row, "scope_sha256": "f" * 64}, job
    monkeypatch.setattr(handoff, "_verify", select)


def test_new_utc_day_allows_distinct_scope_without_old_send_replay(eligible, monkeypatch):
    folder, queue, candidate, _ = eligible
    parent = queue/"autonomous_recovery_continuation_v1"/grant.PARENT
    old_original=parent
    # same source and parent, prior daily grant has no new-review Send
    yesterday, prior_file, prior_bytes = _with_yesterday_then_today(
        eligible,monkeypatch)
    historical_sha=_sha(old_original/"campaign.json")
    _pretend_new_independent_ranked_scope(eligible,monkeypatch)
    today = grant.provision(folder=folder,queue_root=queue,
        candidate_file=candidate,health_result=queue/"health.json",
        explicit_user_consent=True)
    assert yesterday["scope_sha256"] != today["scope_sha256"]
    assert yesterday["new_campaign_id"] != today["new_campaign_id"]
    assert yesterday["new_model_requests"] == today["new_model_requests"] == 0
    assert prior_file.read_bytes() == prior_bytes
    assert _sha(old_original/"campaign.json") == historical_sha
    assert today["old_cap_unchanged"]
    assert today["student_publication_authorized"] is False
    assert grant.verify_grant(
        queue_root=queue,source_sha=_sha(folder/"source.pdf"),
        scope_sha=today["scope_sha256"],
        candidate_sha=_sha(candidate),campaign_id=today["new_campaign_id"],
        cap=2)["original_request_replay_authorized"] is False


def test_yesterday_reserved_same_scope_cannot_be_replayed_today(eligible, monkeypatch):
    folder,queue,candidate,_ = eligible
    _, prior_file, saved = _with_yesterday_then_today(eligible,monkeypatch)
    with pytest.raises(ValueError, match="cannot be replayed"):
        grant.provision(folder=folder,queue_root=queue,
            candidate_file=candidate,health_result=queue/"health.json",
            explicit_user_consent=True)
    assert prior_file.read_bytes() == saved


def test_same_utc_day_cannot_allocate_second_different_scope(eligible, monkeypatch):
    folder,queue,candidate,_ = eligible
    initial_parent(eligible)
    monkeypatch.setattr(focused,"_health_ok",lambda **kw:{})
    first=grant.provision(folder=folder,queue_root=queue,
        candidate_file=candidate,health_result=queue/"health.json",
        explicit_user_consent=True)
    _pretend_new_independent_ranked_scope(eligible,monkeypatch)
    with pytest.raises(ValueError, match="Only one distinct G2"):
        grant.provision(folder=folder,queue_root=queue,
            candidate_file=candidate,health_result=queue/"health.json",
            explicit_user_consent=True)


def test_prior_grant_modified_or_removed_source_identity_fails_closed(eligible,monkeypatch):
    folder,queue,candidate,_ = eligible
    _, prior_file, _ = _with_yesterday_then_today(eligible,monkeypatch)
    previous=json.loads(prior_file.read_text("utf8"))
    previous["source_sha256"]="0"*64
    prior_file.write_text(json.dumps(previous),encoding="utf8")
    _pretend_new_independent_ranked_scope(eligible,monkeypatch)
    with pytest.raises(ValueError,match="Prior distinct G2 grant identity changed"):
        grant.provision(folder=folder,queue_root=queue,
            candidate_file=candidate,health_result=queue/"health.json",
            explicit_user_consent=True)


def test_new_day_recovery_is_executable_registry_entry():
    assert lookup_mechanism(grant.KIND,grant.RENEW_SIGNATURE)==grant.MECHANISM
