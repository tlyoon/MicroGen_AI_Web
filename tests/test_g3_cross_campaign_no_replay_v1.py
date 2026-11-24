"""One-Send G3 quarantine must persist across global campaign restarts."""
from __future__ import annotations

import json
import pytest

from selenium_pipeline.g3_continuous_advance_v1 import _prior_uncertain_send


def _claim(root,scope,*,status="SUBMITTED_OR_UNCERTAIN",
           phase="initial_request",identity=False):
    home=root/scope/phase
    home.mkdir(parents=True,exist_ok=True)
    (home/"request_state.json").write_text(
        json.dumps({"schema_version":1,"status":status,
                    "request_fingerprint":"f"*64}),encoding="utf8")
    if identity:
        (home/"model_response_identity.json").write_text(
            '{"not_necessarily_validated":true}',encoding="utf8")
    return home


def test_new_source_task_is_eligible_without_old_browser_claim(tmp_path):
    assert _prior_uncertain_send(review_root=tmp_path,scope="a"*64) is False


@pytest.mark.parametrize("status",[
    "SUBMITTED_OR_UNCERTAIN",
    "NO_RESPONSE_UNRESOLVED",
    "REJECTED_RESPONSE_UNTRUSTED",
    "LEGACY_SENT_NO_RESPONSE",
])
def test_quarantined_original_send_is_not_eligible_next_day(tmp_path,status):
    _claim(tmp_path,"a"*64,status=status)
    assert _prior_uncertain_send(review_root=tmp_path,scope="a"*64) is True
    assert _prior_uncertain_send(review_root=tmp_path,scope="a"*64) is True
    assert _prior_uncertain_send(review_root=tmp_path,scope="b"*64) is False


def test_previous_accepted_first_pass_may_continue_to_distinct_challenge(tmp_path):
    _claim(tmp_path,"a"*64,status="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
    assert _prior_uncertain_send(review_root=tmp_path,scope="a"*64) is False


def test_previous_observed_claim_may_be_recovered_without_new_send(tmp_path):
    _claim(tmp_path,"a"*64,status="SUBMITTED_OR_UNCERTAIN",identity=True)
    # run_one still must verify the original source fingerprint and
    # owned-model evidence; eligibility alone is never a Send grant.
    assert _prior_uncertain_send(review_root=tmp_path,scope="a"*64) is False


def test_any_uncertain_independent_challenge_blocks_whole_scope(tmp_path):
    scope="a"*64
    _claim(tmp_path,scope,status="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
    _claim(tmp_path,scope,status="NO_RESPONSE_UNRESOLVED",
           phase="challenge_request")
    assert _prior_uncertain_send(review_root=tmp_path,scope=scope) is True


def test_missing_torn_claim_state_is_held_not_replayed(tmp_path):
    claim=tmp_path/("a"*64)/"initial_request"
    claim.mkdir(parents=True)
    (claim/"dispatch_attempted.claim").write_text("old")
    assert _prior_uncertain_send(review_root=tmp_path,scope="a"*64) is True


def test_prepared_but_dispatch_claimed_is_not_free_to_retry(tmp_path):
    claim=_claim(tmp_path,"a"*64,status="PREPARED_NOT_SENT")
    (claim/"dispatch_attempted.claim").write_text("uncertain")
    assert _prior_uncertain_send(review_root=tmp_path,scope="a"*64) is True


def test_prepared_unsubmitted_task_can_continue(tmp_path):
    _claim(tmp_path,"a"*64,status="PREPARED_NOT_SENT")
    assert _prior_uncertain_send(review_root=tmp_path,scope="a"*64) is False


def test_corrupted_checkpoint_is_explicit_blocker_not_auto_resend(tmp_path):
    p=_claim(tmp_path,"a"*64)
    (p/"request_state.json").write_text('{"status":"APPROVED"}')
    with pytest.raises(ValueError):
        _prior_uncertain_send(review_root=tmp_path,scope="a"*64)
