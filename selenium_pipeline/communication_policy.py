"""Communication-mode *contract* for Gemini content-generation stages.

Phase 0 establishes an immutable retry/fallback plan and configuration
precedence. This module intentionally does NOT activate transport switching
in the production runner; stage adapters and their acceptance tests are a
separate, gated Phase 1 change. In particular, installing this module must
not silently change production-generation behaviour.

The selected mode applies to Gemini figure/caption mapping, slides and
narration. TTS, TTS quality assessment and local media stages remain
independent of this setting.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os
from typing import Mapping


class CommunicationMode(str, Enum):
    SELENIUM = "selenium"
    API = "api"
    FALLBACK = "fallback"


class CommunicationBackend(str, Enum):
    SELENIUM = "selenium"
    API = "api"


GEMINI_CONTENT_STAGES = frozenset({"figures", "slides", "narration"})
DEFAULT_COMMUNICATION_MODE = CommunicationMode.SELENIUM
MODE_ENV_VAR = "MICROGEN_COMMUNICATION_MODE"


@dataclass(frozen=True)
class Attempt:
    """A *planned* request, never a completed/validated Gemini response."""

    backend: CommunicationBackend
    number: int


@dataclass(frozen=True)
class CommunicationPolicy:
    """An immutable, task-local communication plan.

    A new policy.plan(stage) is produced for every independent request.
    Fall-back on one request cannot permanently put another request into API
    mode. The future executor must validate the result after every attempt,
    stop after the first valid answer, and must not retry bad inputs or
    permission problems merely because an API fallback exists.
    """

    mode: CommunicationMode = DEFAULT_COMMUNICATION_MODE
    selenium_attempts: int = 3
    api_attempts: int = 2

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CommunicationMode):
            raise ValueError(f"Unsupported Gemini communication mode: {self.mode!r}")
        if type(self.selenium_attempts) is not int or not 1 <= self.selenium_attempts <= 10:
            raise ValueError("selenium_attempts must be an integer from 1 to 10")
        if type(self.api_attempts) is not int or not 1 <= self.api_attempts <= 10:
            raise ValueError("api_attempts must be an integer from 1 to 10")

    def plan(self, stage: str) -> tuple[Attempt, ...]:
        if stage not in GEMINI_CONTENT_STAGES:
            raise ValueError(
                f"Mode selection is only for Gemini content stages, not {stage!r}"
            )
        if self.mode == CommunicationMode.SELENIUM:
            return tuple(
                Attempt(CommunicationBackend.SELENIUM, i)
                for i in range(1, self.selenium_attempts + 1)
            )
        if self.mode == CommunicationMode.API:
            return tuple(
                Attempt(CommunicationBackend.API, i)
                for i in range(1, self.api_attempts + 1)
            )
        return (
            tuple(
                Attempt(CommunicationBackend.SELENIUM, i)
                for i in range(1, self.selenium_attempts + 1)
            )
            + tuple(
                Attempt(CommunicationBackend.API, i)
                for i in range(1, self.api_attempts + 1)
            )
        )


def resolve_mode(
    override: str | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> CommunicationMode:
    """CLI/launcher override > environment > Selenium default.

    Invalid nonempty values fail closed; an empty override means no override.
    Legacy per-stage API overrides are deliberately not read here: Phase 1
    must reject or explicitly reconcile those before integrating this mode.
    """
    env = os.environ if environment is None else environment
    value = (
        override if override is not None and override.strip()
        else env.get(MODE_ENV_VAR, DEFAULT_COMMUNICATION_MODE.value)
    )
    value = str(value).strip().lower()
    try:
        return CommunicationMode(value)
    except ValueError as exc:
        raise ValueError(
            f"{MODE_ENV_VAR} must be selenium, api, or fallback (got {value!r})"
        ) from exc


def policy_from_configuration(
    *,
    override: str | None = None,
    environment: Mapping[str, str] | None = None,
    selenium_attempts: int = 3,
    api_attempts: int = 2,
) -> CommunicationPolicy:
    return CommunicationPolicy(
        mode=resolve_mode(override, environment=environment),
        selenium_attempts=selenium_attempts,
        api_attempts=api_attempts,
    )
