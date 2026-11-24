"""Short single-utterance source-science browser wall; no Send replay.

Gemini's vendor response watcher has a default 1800-s absolute cap even
when a caller selects a shorter idle window. For *new* G3 source-science
and source-free health, bound a registered no-text Send to a 180-s window,
then safely quarantine it and continue other independent eligible scopes.
Only the scoped environment is changed; other lecture tasks are untouched.
"""
from __future__ import annotations

from contextlib import contextmanager
import os

from .recovery_registry import lookup_mechanism

KIND="g3_owned_browser_wall_recovery"
SIGNATURE="OWNED_NEON_HIGH_REGISTERED_SEND_STALLED_NO_MODEL_TEXT_FOR_650_SECONDS"
MECHANISM="SCOPE_G3_GEMINI_RESPONSE_HARD_MAX_180_AND_QUARANTINE_UNCERTAIN"
ENV="GEMINI_RESPONSE_HARD_MAX"


@contextmanager
def bounded_science_response(*,absolute_max_seconds:int=180):
    if lookup_mechanism(KIND,SIGNATURE)!=MECHANISM:
        raise ValueError("Bounded original-source Gemini response recovery not installed")
    if type(absolute_max_seconds) is not int or not 120<=absolute_max_seconds<=240:
        raise ValueError("Only a finite source-science response cap is authorized")
    old=os.environ.get(ENV)
    try:
        os.environ[ENV]=str(absolute_max_seconds)
        yield
    finally:
        if old is None:
            os.environ.pop(ENV,None)
        else:
            os.environ[ENV]=old
