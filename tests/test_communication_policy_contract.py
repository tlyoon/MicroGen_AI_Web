"""Phase 0 contract tests: no network, Selenium session, audio, or file writes."""
from __future__ import annotations

import pytest

from selenium_pipeline.communication_policy import (
    Attempt,
    CommunicationBackend,
    CommunicationMode,
    CommunicationPolicy,
    GEMINI_CONTENT_STAGES,
    policy_from_configuration,
    resolve_mode,
)


def test_default_is_pure_selenium_when_no_variable_is_present():
    assert resolve_mode(environment={}) is CommunicationMode.SELENIUM
    assert policy_from_configuration(environment={}).mode is CommunicationMode.SELENIUM


@pytest.mark.parametrize("stage", sorted(GEMINI_CONTENT_STAGES))
def test_default_uses_only_selenium_for_every_gemini_content_stage(stage):
    plan = CommunicationPolicy().plan(stage)
    assert len(plan) == 3
    assert all(item.backend is CommunicationBackend.SELENIUM for item in plan)
    assert [item.number for item in plan] == [1, 2, 3]


@pytest.mark.parametrize("stage", sorted(GEMINI_CONTENT_STAGES))
def test_pure_api_never_attempts_selenium(stage):
    plan = CommunicationPolicy(CommunicationMode.API).plan(stage)
    assert plan == (Attempt(CommunicationBackend.API, 1),
                    Attempt(CommunicationBackend.API, 2))


@pytest.mark.parametrize("stage", sorted(GEMINI_CONTENT_STAGES))
def test_fallback_attempts_selenium_three_times_before_api(stage):
    plan = CommunicationPolicy(CommunicationMode.FALLBACK).plan(stage)
    assert [(x.backend.value, x.number) for x in plan] == [
        ("selenium", 1), ("selenium", 2), ("selenium", 3),
        ("api", 1), ("api", 2),
    ]


def test_fallback_is_task_local_not_sticky_across_calls():
    policy = CommunicationPolicy(CommunicationMode.FALLBACK)
    first_task = policy.plan("figures")
    new_task = policy.plan("narration")
    assert first_task[0].backend == new_task[0].backend == CommunicationBackend.SELENIUM
    assert first_task is not new_task
    assert policy.mode is CommunicationMode.FALLBACK


def test_cli_override_takes_precedence_over_environment():
    env = {"MICROGEN_COMMUNICATION_MODE": "api"}
    assert resolve_mode(environment=env) is CommunicationMode.API
    assert resolve_mode("fallback", environment=env) is CommunicationMode.FALLBACK
    assert resolve_mode("selenium", environment=env) is CommunicationMode.SELENIUM


@pytest.mark.parametrize("mode", ["selenium", "api", "fallback", "SELENIUM", " API "])
def test_only_three_modes_are_accepted_case_insensitively(mode):
    assert resolve_mode(mode, environment={}).value == mode.strip().lower()


@pytest.mark.parametrize("bad", ["hybrid", "browser", "auto", "none", "gemini", "api-if-slow"])
def test_unknown_modes_fail_closed(bad):
    with pytest.raises(ValueError, match="must be selenium, api, or fallback"):
        resolve_mode(bad, environment={})


@pytest.mark.parametrize("stage", ["tts", "tts_qa", "video", "script_qa", "latex", ""])
def test_communication_modes_do_not_control_tts_or_local_stages(stage):
    with pytest.raises(ValueError, match="Gemini content stages"):
        CommunicationPolicy().plan(stage)


@pytest.mark.parametrize("attempts", [0, -1, 11, 1.5, True, "3"])
def test_invalid_retry_budgets_are_rejected(attempts):
    with pytest.raises(ValueError, match="attempts"):
        CommunicationPolicy(selenium_attempts=attempts)
    with pytest.raises(ValueError, match="attempts"):
        CommunicationPolicy(api_attempts=attempts)


def test_attempt_budgets_are_configurable_without_reordering_backends():
    policy = CommunicationPolicy(
        mode=CommunicationMode.FALLBACK, selenium_attempts=2, api_attempts=1
    )
    assert [(item.backend.value, item.number) for item in policy.plan("slides")] == [
        ("selenium", 1), ("selenium", 2), ("api", 1)
    ]


def test_no_legacy_environment_variables_override_new_mode_setting():
    env = {
        "MICROGEN_NARRATION_BACKEND": "api",
        "MICROGEN_FIGURE_MAPPING_BACKEND": "api",
    }
    # The production runner still uses these older variables today. Phase 1
    # integration must explicitly remove or reject conflicting overrides.
    assert resolve_mode(environment=env) is CommunicationMode.SELENIUM
