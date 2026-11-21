"""Selenium-only lecture-content transport, enforced BEFORE any model request.

Legacy 'api'/'fallback' names are recognized only to reject them. No
environment variable, launcher override or temporary browser outage may
reintroduce a chargeable Gemini API content request. TTS and explicitly
approved paid audio QA have a separate, narrow paid_api_policy gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from typing import Mapping


class CommunicationMode(str, Enum):
    SELENIUM = "selenium"
    API = "api"          # REJECTED legacy input; kept for clear diagnostics
    FALLBACK = "fallback"  # REJECTED legacy input; kept for compatibility


class CommunicationBackend(str, Enum):
    SELENIUM = "selenium"
    API = "api"          # Never emitted by an admissible plan


GEMINI_CONTENT_STAGES = frozenset({
    "figures", "slides", "narration", "academic_review", "scientific_review",
    "pedagogy_review", "script_review",
})
DEFAULT_COMMUNICATION_MODE = CommunicationMode.SELENIUM
MODE_ENV_VAR = "MICROGEN_COMMUNICATION_MODE"


@dataclass(frozen=True)
class Attempt:
    backend: CommunicationBackend
    number: int


@dataclass(frozen=True)
class CommunicationPolicy:
    mode: CommunicationMode = CommunicationMode.SELENIUM
    selenium_attempts: int = 3
    api_attempts: int = 2  # legacy config; never produces an API attempt

    def __post_init__(self) -> None:
        if self.mode is not CommunicationMode.SELENIUM:
            raise ValueError(
                "SELENIUM_ONLY_CONTENT_POLICY: API and fallback modes are "
                "forbidden for lecture generation and scientific review")
        if type(self.selenium_attempts) is not int or not 1 <= self.selenium_attempts <= 10:
            raise ValueError("selenium_attempts must be an integer from 1 to 10")
        if type(self.api_attempts) is not int or not 1 <= self.api_attempts <= 10:
            raise ValueError("api_attempts must be an integer from 1 to 10")

    def plan(self, stage: str) -> tuple[Attempt, ...]:
        if stage not in GEMINI_CONTENT_STAGES:
            raise ValueError(f"Mode selection is only for Gemini content stages, not {stage!r}")
        return tuple(
            Attempt(CommunicationBackend.SELENIUM, i)
            for i in range(1, self.selenium_attempts + 1)
        )


def resolve_mode(
    override: str | None = None,
    *, environment: Mapping[str, str] | None = None,
) -> CommunicationMode:
    """Reject API/fallback even if selected through environment or CLI.

    Explicit Selenium overrides a legacy environment setting only when the
    actual launcher invokes it; no silent API mode normalization.
    """
    env = os.environ if environment is None else environment
    value = (override if override is not None and override.strip()
             else env.get(MODE_ENV_VAR, "selenium"))
    if str(value).strip().lower() != "selenium":
        raise ValueError(
            "SELENIUM_ONLY_CONTENT_POLICY: "
            f"{MODE_ENV_VAR}={str(value)!r} forbidden; "
            "only selenium is permitted (no API fallback)")
    return CommunicationMode.SELENIUM


def policy_from_configuration(
    *, override: str | None = None,
    environment: Mapping[str, str] | None = None,
    selenium_attempts: int = 3,
    api_attempts: int = 2,
) -> CommunicationPolicy:
    return CommunicationPolicy(
        mode=resolve_mode(override, environment=environment),
        selenium_attempts=selenium_attempts, api_attempts=api_attempts)
