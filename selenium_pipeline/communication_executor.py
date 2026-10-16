"""Task-local, validation-gated Gemini transport attempts.

This is Phase 1's transport-independent execution core. It does not choose
Chrome sessions, submit live Gemini requests, or change production defaults.
Each stage adapter supplies backend-specific callables and a validator.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, TypeVar

from .communication_policy import CommunicationBackend, CommunicationPolicy, GEMINI_CONTENT_STAGES

T = TypeVar("T")


class FailureKind(str, Enum):
    STALLED = "stalled"
    REFUSAL = "refusal"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TRANSPORT_ERROR = "transport_error"
    INVALID_OUTPUT = "invalid_output"
    PERMANENT_INPUT_ERROR = "permanent_input_error"


class AttemptFailure(Exception):
    def __init__(self, kind: FailureKind, detail: str):
        super().__init__(detail)
        self.kind = kind


class TaskFailed(Exception):
    def __init__(self, stage: str, outcomes: tuple["AttemptOutcome", ...]):
        super().__init__(f"{stage}: no validated Gemini response after {len(outcomes)} attempt(s)")
        self.stage = stage
        self.outcomes = outcomes


@dataclass(frozen=True)
class AttemptOutcome:
    backend: CommunicationBackend
    number: int
    status: str
    failure: FailureKind | None = None


@dataclass(frozen=True)
class ValidatedResult(Generic[T]):
    result: T
    backend: CommunicationBackend
    attempt: int
    outcomes: tuple[AttemptOutcome, ...]


def execute_content_request(
    stage: str,
    policy: CommunicationPolicy,
    *,
    selenium: Callable[[], T],
    api: Callable[[], T],
    validate: Callable[[T], bool],
    on_outcome: Callable[[AttemptOutcome], None] | None = None,
) -> ValidatedResult[T]:
    """Return only a validated response; no unvalidated output is published.

    Caller owns retry delays and transport shutdown between attempts.
    Permanent input errors abort without using more attempts or falling back.
    Unexpected exceptions are *not* swallowed or reclassified as transport
    failures. This prevents programming bugs being hidden as Gemini stalls.
    """
    if stage not in GEMINI_CONTENT_STAGES:
        raise ValueError(f"Unsupported Gemini content stage: {stage!r}")
    actions = {CommunicationBackend.SELENIUM: selenium, CommunicationBackend.API: api}
    outcomes: list[AttemptOutcome] = []

    def record(outcome: AttemptOutcome) -> None:
        outcomes.append(outcome)
        if on_outcome is not None:
            on_outcome(outcome)

    for attempt in policy.plan(stage):
        try:
            response = actions[attempt.backend]()
            if not validate(response):
                raise AttemptFailure(FailureKind.INVALID_OUTPUT, "Response did not satisfy stage validation")
        except AttemptFailure as error:
            record(AttemptOutcome(attempt.backend, attempt.number, "failed", error.kind))
            if error.kind == FailureKind.PERMANENT_INPUT_ERROR:
                raise TaskFailed(stage, tuple(outcomes)) from error
            continue
        record(AttemptOutcome(attempt.backend, attempt.number, "passed"))
        return ValidatedResult(response, attempt.backend, attempt.number, tuple(outcomes))
    raise TaskFailed(stage, tuple(outcomes))
