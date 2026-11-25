"""Only real independently source-validated V3 first+challenge model answers count."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from selenium_pipeline import g2_ranked_v3_two_pass_consensus_bridge_v1 as bridge
from selenium_pipeline.ai_academic_web_review import run_web_review
from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.recovery_registry import lookup_mechanism
from tests.test_g2_ranked_v3_owned_selenium_handoff_v1 import eligible
from tests.test_g2_distinct_focused_source_review_v1 import real_source_fixture
from tests.test_g2_distinct_focused_challenge_v1 import reply


def base(eligible,monkeypatch,*,previous=0,previous_ids=()):
    folder,queue,candidate,claim=eligible
    count=json.loads((queue/"queue.json").read_text("utf8"))["expected_utterances"]
    prior={
        "schema_version":1,
        "status":"G2_ORIGINAL_AND_FOCUSED_SOURCE_AI_EVIDENCE_RECONCILED_NO_RELEASE",
        "source_sha256":_sha(folder/"source.pdf"),
        "original_total_utterances":count,
        "original_two_pass_source_AI_agreements":previous-len(previous_ids),
        "combined_source_AI_agreements":previous,
        "new_focused_utterance_ids":list(previous_ids),
        "new_provider_requests":0,
        "student_publication_authorized":False,
    }
    home=queue.parent/bridge.V1_ROOT
    home.mkdir(exist_ok=True)
    serialized=json.dumps(prior,indent=2,sort_keys=True)+"\n"
    file=home/(hashlib.sha256(serialized.encode()).hexdigest()[:32]+".json")
    file.write_text(serialized,encoding="utf8")
    monkeypatch.setattr(bridge,"verify_existing_v1",
                        lambda **kw:{**prior,"receipt":str(file)})
    return folder,queue,candidate,file


def run_four(eligible,monkeypatch,**options):
    folder,queue,candidate,file=base(eligible,monkeypatch,**options)
    return bridge.reconcile(folder=folder,queue_root=queue,
                            base_v1_receipt=file)


def write_genuine_reviewer_evidence(eligible,real_source_fixture,
                                    *,initial_text=None,challenge_text=None,
                                    second_verdict="SUPPORTED"):
    folder,queue,candidate,claim=eligible
    record=json.loads(candidate.read_text("utf8"))
    job=record["source_science_review_job"]
    quote=real_source_fixture[3]
    scope=queue.parent/bridge.REVIEW_ROOT/candidate.stem
    scope.mkdir(parents=True,exist_ok=True)
    initial_text=(initial_text or "The original publisher definition supports velocity as length per time.")
    challenge_text=(challenge_text or "The physically sourced dimension is L divided by T, consistent with this sentence.")
    for mode,reason,verdict,name in (
        ("INITIAL_REVIEW",initial_text,"SUPPORTED","initial_request"),
        ("INDEPENDENT_CHALLENGE",challenge_text,second_verdict,"challenge_request")):
        out=run_web_review(folder=folder,job=job,mode=mode,
             checkpoint_dir=scope/name,required_model_family="neon",
             transport=lambda *_args,r=reason,v=verdict:reply(job,quote,r,verdict=v))
        assert out["rows"][0]["exact_textbook_quote_verified"] is True
    return scope


def original_stub(real_source_fixture,accepted=()):
    folder,queue,_,_,_=real_source_fixture
    n=json.loads((queue/"queue.json").read_text("utf8"))["expected_utterances"]
    uid=[f"s003.utterance.{i:03d}" for i in range(1,n+1)]
    return {
        "original_utterances":n,"agreed_source_witnessed_segments":len(accepted),
        "accepted_ai_evidence":[{"utterance_id":x} for x in accepted],
        "unresolved":[{"utterance_id":x} for x in uid if x not in accepted],
        "AI_consensus_is_formal_math_proof":False,
        "student_publication_authorized":False,
    }


def test_registry_handler():
    assert lookup_mechanism(bridge.KIND,bridge.SIGNATURE)==bridge.MECHANISM


def test_no_v3_model_response_is_not_new_agreement(eligible,monkeypatch):
    folder,queue,candidate,file=base(eligible,monkeypatch)
    before=[_sha(folder/"source.pdf"),_sha(queue/"queue.json"),
            _sha(candidate)]
    result=bridge.reconcile(folder=folder,queue_root=queue,
                            base_v1_receipt=file)
    assert result["genuine_V3_two_pass_records"]==0
    assert result["new_V3_independent_source_AI_agreements"]==0
    assert result["combined_source_AI_agreements"]==0
    assert result["pending_or_disputed_source_AI"]==result["original_total_utterances"]
    assert result["new_provider_requests"]==0
    assert result["student_publication_authorized"] is False
    assert [_sha(folder/"source.pdf"),_sha(queue/"queue.json"),
            _sha(candidate)]==before
    assert bridge.reconcile(folder=folder,queue_root=queue,
                            base_v1_receipt=file)==result


def test_v3_one_pass_pending_not_counted(eligible,monkeypatch):
    folder,queue,candidate,file=base(eligible,monkeypatch)
    scope=queue.parent/bridge.REVIEW_ROOT/candidate.stem
    (scope/"initial_request").mkdir(parents=True)
    result=bridge.reconcile(folder=folder,queue_root=queue,
                            base_v1_receipt=file)
    assert result["saved_V3_model_scopes_seen"]==1
    assert result["genuine_V3_two_pass_records"]==0
    assert result["combined_source_AI_agreements"]==0


def test_two_real_independent_model_passes_count_one_not_student_release(
        eligible,real_source_fixture,monkeypatch):
    folder,queue,candidate,file=base(eligible,monkeypatch)
    scope=write_genuine_reviewer_evidence(eligible,real_source_fixture)
    monkeypatch.setattr(bridge,"reconcile_actual_review_queue",
        lambda **kw:original_stub(real_source_fixture))
    result=bridge.reconcile(folder=folder,queue_root=queue,
                            base_v1_receipt=file)
    assert result["genuine_V3_two_pass_records"]==1
    assert result["new_V3_independent_source_AI_agreements"]==1
    assert result["new_V3_source_AI_utterance_ids"]==["s003.utterance.001"]
    assert result["combined_source_AI_agreements"]==1
    assert result["pending_or_disputed_source_AI"]==result["original_total_utterances"]-1
    assert result["all_85_source_AI_agreements_observed"] is False
    assert result["all_independent_acoustic_QA_complete"] is False
    assert result["formal_human_math_approval"] is False
    assert result["student_publication_authorized"] is False
    assert result["new_provider_requests"]==0
    assert scope.joinpath("two_pass_evidence.json").is_file()
    assert bridge.reconcile(folder=folder,queue_root=queue,
                            base_v1_receipt=file)==result


def test_two_real_model_passes_disagree_not_admitted(
        eligible,real_source_fixture,monkeypatch):
    folder,queue,candidate,file=base(eligible,monkeypatch)
    write_genuine_reviewer_evidence(
        eligible,real_source_fixture,second_verdict="UNRESOLVED")
    monkeypatch.setattr(bridge,"reconcile_actual_review_queue",
        lambda **kw:pytest.fail("Disputed science cannot expand accepted queue"))
    result=bridge.reconcile(folder=folder,queue_root=queue,
                            base_v1_receipt=file)
    assert result["genuine_V3_two_pass_records"]==1
    assert result["new_V3_independent_source_AI_agreements"]==0
    assert result["combined_source_AI_agreements"]==0


def test_same_existing_utterance_not_double_counted(
        eligible,real_source_fixture,monkeypatch):
    folder,queue,candidate,file=base(
        eligible,monkeypatch,previous=1,
        previous_ids=("s003.utterance.001",))
    write_genuine_reviewer_evidence(eligible,real_source_fixture)
    monkeypatch.setattr(bridge,"reconcile_actual_review_queue",
        lambda **kw:original_stub(
            real_source_fixture,accepted=()))
    result=bridge.reconcile(folder=folder,queue_root=queue,
                            base_v1_receipt=file)
    assert result["new_V3_independent_source_AI_agreements"]==0
    assert result["combined_source_AI_agreements"]==1


@pytest.mark.parametrize("damage",[
    "initial_response","neon_witness","same_raw","candidate","receipt",
])
def test_corrupt_review_evidence_or_original_source_never_counts(
        eligible,real_source_fixture,monkeypatch,damage):
    folder,queue,candidate,file=base(eligible,monkeypatch)
    scope=write_genuine_reviewer_evidence(eligible,real_source_fixture)
    monkeypatch.setattr(bridge,"reconcile_actual_review_queue",
        lambda **kw:original_stub(real_source_fixture))
    if damage=="initial_response":
        (scope/"initial_request"/"model_response_untrusted.txt").write_text(
            '{"forged":"model output"}')
    elif damage=="neon_witness":
        (scope/"challenge_request"/"neon_high_owned_model_witness.json").unlink()
    elif damage=="same_raw":
        (scope/"challenge_request"/"model_response_untrusted.txt").write_bytes(
            (scope/"initial_request"/"model_response_untrusted.txt").read_bytes())
    elif damage=="candidate":
        content=json.loads(candidate.read_text("utf8"))
        content["new_initial_prompt_sha256"]="0"*64
        candidate.write_text(json.dumps(content))
    else:
        file.write_text("{}",encoding="utf8")
    with pytest.raises(Exception):
        bridge.reconcile(folder=folder,queue_root=queue,
                         base_v1_receipt=file)
    assert not (queue/"slide_003_independent_challenge.json").exists()


def test_stale_old_v1_baseline_is_rejected(eligible,monkeypatch):
    folder,queue,candidate,file=base(eligible,monkeypatch)
    monkeypatch.setattr(bridge,"verify_existing_v1",
        lambda **kw:{"receipt":str(file),
                     "combined_source_AI_agreements":1,
                     "new_focused_utterance_ids":[]})
    with pytest.raises(ValueError,match="stale or not revalidated"):
        bridge.reconcile(folder=folder,queue_root=queue,
                         base_v1_receipt=file)


def test_partial_source_api_evidence_cannot_promote_v3(
        eligible,monkeypatch):
    folder,queue,candidate,file=base(eligible,monkeypatch)
    root=queue.parent/bridge.REVIEW_ROOT/candidate.stem
    root.mkdir(parents=True)
    (root/"challenge_request").mkdir()
    got=bridge.reconcile(folder=folder,queue_root=queue,
                         base_v1_receipt=file)
    assert got["genuine_V3_two_pass_records"]==0
    assert got["student_publication_authorized"] is False
