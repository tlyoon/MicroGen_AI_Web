"""Exact Neon source-science response wall prevents 30-minute no-text stalls."""
from __future__ import annotations
import os
import pytest

from selenium_pipeline.g3_bounded_owned_browser_window_v1 import (
    bounded_science_response,ENV,KIND,SIGNATURE,MECHANISM)
from selenium_pipeline.recovery_registry import lookup_mechanism


def test_registered_real_no_text_generation_recovery():
    assert lookup_mechanism(KIND,SIGNATURE)==MECHANISM


def test_exact_scoped_hard_wall_restored_after_success_or_error(monkeypatch):
    monkeypatch.setenv(ENV,"1800")
    with bounded_science_response(absolute_max_seconds=180):
        assert os.getenv(ENV)=="180"
    assert os.getenv(ENV)=="1800"
    with pytest.raises(RuntimeError):
        with bounded_science_response(absolute_max_seconds=180):
            assert os.getenv(ENV)=="180"
            raise RuntimeError("Recorded browser attempt may have been sent")
    assert os.getenv(ENV)=="1800"


def test_absent_initial_wall_restored_when_source_task_finishes(monkeypatch):
    monkeypatch.delenv(ENV,raising=False)
    with bounded_science_response():
        assert os.getenv(ENV)=="180"
    assert ENV not in os.environ


@pytest.mark.parametrize("bad",[0,30,119,241,500,180.0,"180",None])
def test_unbounded_or_ambiguous_browser_wall_rejected(bad):
    with pytest.raises(ValueError):
        with bounded_science_response(absolute_max_seconds=bad):
            pass
