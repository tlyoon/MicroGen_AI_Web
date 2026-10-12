"""Deterministic tests for the RFH task-local transport executor."""
import pytest

from selenium_pipeline.communication_policy import CommunicationBackend, CommunicationMode, CommunicationPolicy
from selenium_pipeline.communication_executor import (
    AttemptFailure, FailureKind, TaskFailed, execute_content_request,
)


@pytest.mark.parametrize("stage", ["figures", "slides", "narration"])
def test_default_is_exclusively_selenium_even_after_retries(stage):
    calls = []
    def selenium():
        calls.append("selenium")
        raise AttemptFailure(FailureKind.STALLED, "no useful Gemini response")
    def api():
        calls.append("api")
        return "valid"
    with pytest.raises(TaskFailed) as error:
        execute_content_request(stage, CommunicationPolicy(), selenium=selenium, api=api,
                                validate=lambda x: x == "valid")
    assert calls == ["selenium"] * 3
    assert len(error.value.outcomes) == 3


@pytest.mark.parametrize("stage", ["figures", "slides", "narration"])
def test_api_mode_never_calls_selenium(stage):
    calls = []
    result = execute_content_request(
        stage, CommunicationPolicy(mode=CommunicationMode.API),
        selenium=lambda: (_ for _ in ()).throw(AssertionError("selenium was invoked")),
        api=lambda: calls.append("api") or "content",
        validate=lambda x: x == "content",
    )
    assert calls == ["api"]
    assert result.backend == CommunicationBackend.API


@pytest.mark.parametrize("stage", ["figures", "slides", "narration"])
def test_fallback_requires_three_failed_selenium_attempts(stage):
    calls = []
    def selenium():
        calls.append("selenium")
        raise AttemptFailure(FailureKind.TRANSPORT_ERROR, "composer failure")
    def api():
        calls.append("api")
        return "valid"
    r = execute_content_request(
        stage, CommunicationPolicy(mode=CommunicationMode.FALLBACK),
        selenium=selenium, api=api, validate=lambda x: x == "valid",
    )
    assert calls == ["selenium"] * 3 + ["api"]
    assert r.backend == CommunicationBackend.API
    assert len(r.outcomes) == 4
    assert r.outcomes[-1].status == "passed"


def test_validation_rejection_causes_retry_without_publishing():
    values = iter(["I cannot do this", "Complete content"])
    r = execute_content_request(
        "slides", CommunicationPolicy(mode=CommunicationMode.FALLBACK),
        selenium=lambda: next(values),
        api=lambda: (_ for _ in ()).throw(AssertionError("premature fallback")),
        validate=lambda s: s.startswith("Complete"),
    )
    assert r.result == "Complete content"
    assert r.outcomes[0].failure == FailureKind.INVALID_OUTPUT


def test_permanent_input_error_aborts_without_fallback():
    calls = []
    def selenium():
        calls.append("selenium")
        raise AttemptFailure(FailureKind.PERMANENT_INPUT_ERROR, "missing source PDF")
    with pytest.raises(TaskFailed) as error:
        execute_content_request(
            "figures", CommunicationPolicy(mode=CommunicationMode.FALLBACK),
            selenium=selenium,
            api=lambda: calls.append("api") or "invalid",
            validate=bool,
        )
    assert calls == ["selenium"]
    assert error.value.outcomes[0].failure == FailureKind.PERMANENT_INPUT_ERROR


def test_new_task_starts_at_selenium_after_prior_api_fallback():
    policy = CommunicationPolicy(mode=CommunicationMode.FALLBACK, selenium_attempts=2)
    calls = []
    def selenium():
        calls.append("selenium")
        raise AttemptFailure(FailureKind.REFUSAL, "not generated")
    def api():
        calls.append("api")
        return "good"
    for stage in ("figures", "narration"):
        execute_content_request(stage, policy, selenium=selenium, api=api, validate=lambda x: x == "good")
    assert calls == ["selenium", "selenium", "api"] * 2


def test_unexpected_programming_errors_not_hidden():
    with pytest.raises(ZeroDivisionError):
        execute_content_request(
            "narration", CommunicationPolicy(mode=CommunicationMode.FALLBACK),
            selenium=lambda: 1 / 0, api=lambda: "valid", validate=bool,
        )


def test_outcome_callback_traces_each_attempt():
    traces = []
    r = execute_content_request(
        "narration", CommunicationPolicy(),
        selenium=lambda: "correct", api=lambda: "unused", validate=lambda x: x == "correct",
        on_outcome=traces.append,
    )
    assert list(r.outcomes) == traces
    assert len(traces) == 1
    assert traces[0].status == "passed"
