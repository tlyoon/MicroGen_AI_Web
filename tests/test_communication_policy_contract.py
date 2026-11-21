"""No network: all content stages must use Gemini Selenium without API fallback."""
from __future__ import annotations
import pytest

from selenium_pipeline.communication_policy import (
    CommunicationBackend, CommunicationMode, CommunicationPolicy,
    GEMINI_CONTENT_STAGES, policy_from_configuration, resolve_mode,
)


def test_no_mode_is_selenium_by_default():
    assert resolve_mode(environment={}) is CommunicationMode.SELENIUM
    assert policy_from_configuration(environment={}).mode is CommunicationMode.SELENIUM


@pytest.mark.parametrize("stage", sorted(GEMINI_CONTENT_STAGES))
def test_every_content_and_scientific_review_stage_selenium_only(stage):
    p=CommunicationPolicy().plan(stage)
    assert len(p)==3
    assert all(x.backend is CommunicationBackend.SELENIUM for x in p)
    assert [x.number for x in p]==[1,2,3]


@pytest.mark.parametrize("mode", [CommunicationMode.API,CommunicationMode.FALLBACK])
def test_explicit_legacy_modes_are_refused_before_stage_dispatch(mode):
    with pytest.raises(ValueError,match="SELENIUM_ONLY_CONTENT_POLICY"):
        CommunicationPolicy(mode=mode)


@pytest.mark.parametrize("mode", [
    "api","fallback","API"," FALLBACK ","hybrid","browser","auto",
    "none","gemini","api-if-slow",
])
def test_environment_and_launcher_cannot_force_paid_content(mode):
    with pytest.raises(ValueError,match="SELENIUM_ONLY_CONTENT_POLICY"):
        resolve_mode(environment={"MICROGEN_COMMUNICATION_MODE":mode})
    with pytest.raises(ValueError,match="SELENIUM_ONLY_CONTENT_POLICY"):
        resolve_mode(mode,environment={})


def test_only_selenium_override_is_allowed():
    assert resolve_mode("selenium",environment={
        "MICROGEN_COMMUNICATION_MODE":"api"}) is CommunicationMode.SELENIUM
    assert resolve_mode(" SELENIUM ",environment={}) is CommunicationMode.SELENIUM


@pytest.mark.parametrize("stage",["tts","tts_qa","video","script_qa","latex",""])
def test_text_transport_policy_not_used_for_speech_or_local_stages(stage):
    with pytest.raises(ValueError,match="Gemini content stages"):
        CommunicationPolicy().plan(stage)


@pytest.mark.parametrize("budget",[0,-1,11,1.5,True,"3"])
def test_invalid_budget_fails_closed(budget):
    with pytest.raises(ValueError,match="attempts"):
        CommunicationPolicy(selenium_attempts=budget)
    with pytest.raises(ValueError,match="attempts"):
        CommunicationPolicy(api_attempts=budget)


def test_valid_selenium_retry_budget_never_adds_paid_fallback():
    p=CommunicationPolicy(selenium_attempts=2,api_attempts=3)
    assert [(t.backend.value,t.number) for t in p.plan("slides")]==[
        ("selenium",1),("selenium",2)]


def test_legacy_environment_must_not_activate_paid_adapter():
    assert resolve_mode(environment={
        "MICROGEN_NARRATION_BACKEND":"api",
        "MICROGEN_FIGURE_MAPPING_BACKEND":"api"}) is CommunicationMode.SELENIUM
