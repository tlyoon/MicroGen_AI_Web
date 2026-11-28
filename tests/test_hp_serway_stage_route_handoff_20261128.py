"""HP route handoff and revision-gated pre-Send rearm regression tests."""
import json
import os
import pytest
from selenium_pipeline.stage_route_env_v1 import (
    sync_stage_route_env,StageRouteHandoffError)
from selenium_pipeline.safe_presend_retry_v1 import (
    verified_new_code_stage_handoff_retry)

OLD="0"*40
NEW="1"*40
def route(stage,family="hydrogen"):
    return json.dumps(dict(schema_version=1,stage=stage,
                           family=family,catalog_sha256="a"*64,
                           reason="PREVIOUS_VERIFIED_TASK_DEFAULT_REOBSERVED"))

def test_runner_clears_stale_figures_route_before_slides():
    parent={"MICROGEN_DYNAMIC_ROUTE_PENDING":route("figures"),
            "MICROGEN_MODEL_ROUTE_REASON":"figures_only",
            "MICROGEN_MODEL_ROUTE_OFFERED":"hydrogen"}
    child=dict(parent)
    assert not sync_stage_route_env("slides",child,parent)
    assert "MICROGEN_DYNAMIC_ROUTE_PENDING" not in parent
    assert "MICROGEN_DYNAMIC_ROUTE_PENDING" not in child
    assert "MICROGEN_MODEL_ROUTE_REASON" not in child
    assert "MICROGEN_MODEL_ROUTE_OFFERED" not in child

def test_runner_passes_fresh_narration_route_after_selection():
    parent={"MICROGEN_DYNAMIC_ROUTE_PENDING":route("slides","neon"),
            "MICROGEN_MODEL_ROUTE_REASON":"slides"}
    child=dict(parent)
    assert not sync_stage_route_env("narration",child,parent)
    # ensure_mode() runs in parent, observes the exact owned Hydrogen route,
    # and creates a new narration-specific pending verification identity.
    parent["MICROGEN_DYNAMIC_ROUTE_PENDING"]=route("narration","hydrogen")
    parent["MICROGEN_MODEL_ROUTE_REASON"]="narration_verified"
    parent["MICROGEN_MODEL_ROUTE_OFFERED"]="hydrogen,neon"
    assert sync_stage_route_env("narration",child,parent)
    assert json.loads(child["MICROGEN_DYNAMIC_ROUTE_PENDING"])["stage"]=="narration"
    assert child["MICROGEN_MODEL_ROUTE_REASON"]=="narration_verified"

def test_same_stage_pending_preserved_for_initial_browser_launch():
    parent={"MICROGEN_DYNAMIC_ROUTE_PENDING":route("slides","neon"),
            "MICROGEN_MODEL_ROUTE_REASON":"preflight"}
    child={}
    assert sync_stage_route_env("slides",child,parent)
    assert child["MICROGEN_DYNAMIC_ROUTE_PENDING"]==parent["MICROGEN_DYNAMIC_ROUTE_PENDING"]
    assert child["MICROGEN_MODEL_ROUTE_REASON"]=="preflight"

@pytest.mark.parametrize("bad",["{bad",json.dumps({"schema_version":1,"stage":"slides"}),
                                  json.dumps({"schema_version":2,"stage":"slides",
                                              "family":"neon","catalog_sha256":"a"*64})])
def test_malformed_or_unknown_stage_pending_fails_closed(bad):
    with pytest.raises(StageRouteHandoffError):
        sync_stage_route_env("narration",{},{"MICROGEN_DYNAMIC_ROUTE_PENDING":bad})

def make_entry(tmp_path,body,status="QUARANTINED_MANUAL_RECONCILIATION"):
    p=tmp_path/"1.4_v2_attempt4.log";p.write_text(body,encoding="utf8")
    return {"status":status,"source_sha256":"f"*64,
            "attempts":[{"code_sha":OLD,"source_sha256":"f"*64,
                         "returncode":1,"log":str(p)}]}

ROUTE_LOG=("gen_script_selenium_v15.py\n"
           "[GEMINI-MODE] OWNED_FAMILY_VERIFIED_AFTER_NEW_CHAT Open mode picker, currently Hydrogen Medium\n"
           "[GEMINI-THINKING] OWNED_LEVEL_VERIFIED_AFTER_NEW_CHAT medium\n"
           "DynamicGeminiRouteError: Pending dynamic route identity changed\n"
           "DynamicGeminiRouteError: Dynamic task route could not be persisted; do not Send")

THINKING_LOG=("gen_slides_selenium_v11.py\n"
    + ("owned Gemini pre-send stage failure: OWNED_MEDIUM_THINKING_SELECTION\n"
       "VERIFIED_PRE_SEND_FAILURE\n")*3
    + "RuntimeError: Failed to produce a valid Beamer slide stack after all attempts")

def test_stage_handoff_no_send_rearmed_on_new_sha(tmp_path):
    e=make_entry(tmp_path,ROUTE_LOG)
    assert verified_new_code_stage_handoff_retry(e,NEW,tmp_path)
    assert not verified_new_code_stage_handoff_retry(e,OLD,tmp_path)
    e["attempts"][-1]["code_sha"]=NEW
    assert not verified_new_code_stage_handoff_retry(e,NEW,tmp_path)

def test_three_pre_send_thinking_failures_are_safely_rearmed(tmp_path):
    e=make_entry(tmp_path,THINKING_LOG)
    assert verified_new_code_stage_handoff_retry(e,NEW,tmp_path)

@pytest.mark.parametrize("extra",[
    "UNCERTAIN_SEND","Gemini wait: elapsed=20",
    "Gemini submission registered","[SEND-VERIFY] narration prompt typed",
    "Gemini response received"
])
def test_ever_possible_provider_send_cannot_rearm(tmp_path,extra):
    e=make_entry(tmp_path,ROUTE_LOG+"\n"+extra)
    assert not verified_new_code_stage_handoff_retry(e,NEW,tmp_path)

def test_historical_unknown_status_and_missing_proof_never_rearm(tmp_path):
    for status in ("QUARANTINED_EXTERNAL_OUTCOME_UNCERTAIN",
                   "VIDEO_VERIFIED","BLOCKED_SOURCE"):
        e=make_entry(tmp_path,ROUTE_LOG,status)
        assert not verified_new_code_stage_handoff_retry(e,NEW,tmp_path)
    e=make_entry(tmp_path,"Gemini wait: elapsed=400; response_chars=53\nUNCERTAIN_SEND")
    assert not verified_new_code_stage_handoff_retry(e,NEW,tmp_path)


def test_exact_pending_narration_identity_can_commit_after_owned_proofs(monkeypatch):
    """The failing commit path sees narration, never stale slides."""
    from selenium_pipeline import gemini_dynamic_task_router as router
    parent={"MICROGEN_DYNAMIC_ROUTE_PENDING":route("slides","neon")}
    child=dict(parent)
    assert not sync_stage_route_env("narration",child,parent)
    parent["MICROGEN_DYNAMIC_ROUTE_PENDING"]=route("narration","hydrogen")
    assert sync_stage_route_env("narration",child,parent)
    with monkeypatch.context() as patch:
        patch.setenv("MICROGEN_DYNAMIC_ROUTE_PENDING",
                     child["MICROGEN_DYNAMIC_ROUTE_PENDING"])
        patch.setattr(router,"save_verified_task_default",
                      lambda **kwargs: {"family":kwargs["family"],
                                         "thinking_level":kwargs["thinking_level"],
                                         "stage":kwargs["stage"]})
        result=router.commit_verified_pending_route(
            stage="narration",
            owned_selected_label="Open mode picker, currently Hydrogen Medium",
            thinking_level="medium",port=9222,
            model_ui_checked=True,thinking_radio_checked=True)
        assert result=={"family":"hydrogen","thinking_level":"medium",
                        "stage":"narration"}
        assert not os.getenv("MICROGEN_DYNAMIC_ROUTE_PENDING")
