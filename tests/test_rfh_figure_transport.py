"""No-network tests of the *actual* vendored figure mapper's retry decisions.

The production vendor has a command-line entrypoint at module import time.
We isolate its run_mapping function from its AST so that tests execute its
real orchestration but never attach a browser or call Gemini.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from selenium_pipeline.runner import _needs_api_python_for_stages, _needs_browser

REPO = Path(__file__).resolve().parents[1]
VENDOR = REPO / "selenium_pipeline/vendor_template_v2/map_and_rename_selenium_v8.py"


class FakeChrome:
    def __init__(self, *args, **kwargs):
        self.start_calls = 0
        self.shutdown_calls = 0
        self._map_prompt_cache = None

    def start(self, **kwargs):
        self.start_calls += 1

    def shutdown(self):
        self.shutdown_calls += 1


def make_runner(tmp_path: Path, monkeypatch, fake_mapper):
    page = tmp_path / "pages" / "page_1"
    crop = tmp_path / "crops" / "page_1"
    page.mkdir(parents=True)
    crop.mkdir(parents=True)
    (page / "page_1.png").write_bytes(b"PNG")
    (crop / "fig_1.png").write_bytes(b"PNG")

    source = ast.parse(VENDOR.read_text(encoding="utf-8-sig"))
    node = next(n for n in source.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == "run_mapping")
    code = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                   str(VENDOR), "exec")
    created = []

    class TrackChrome(FakeChrome):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            created.append(self)

    cfg = SimpleNamespace(
        root=tmp_path, pages_dir="pages", crops_dir="crops",
        gemini_url="https://gemini.google.com", debug_port=9222,
        wait_mapping_max=30, chrome_exe=None,
        user_data_dir=None, profile_directory=None,
        fallback_user_data_dir=None, fallback_profile_directory=None,
        use_persistent_chrome=False, force_kill_chrome_to_free_port=False,
    )
    monkeypatch.setenv("MICROGEN_PACKAGE_ROOT", str(REPO))
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr("selenium_pipeline.gemini_model.ensure_mode",
                        lambda *args, **kwargs: "flash")
    namespace = {
        "Path": Path, "sys": sys, "os": os, "time": time,
        "subprocess": subprocess, "shutil": shutil,
        "CFG": cfg,
        "gemsel": SimpleNamespace(Config=lambda **kwargs: SimpleNamespace(**kwargs),
                                  GeminiSeleniumClient=TrackChrome),
        "natural_sort_key": lambda x: x,
        "log": lambda *args, **kwargs: None,
        "stop_generation_if_present": lambda c: False,
        "GeminiGenerationStalled": type("GeminiGenerationStalled", (RuntimeError,), {}),
        "map_and_rename_single_step": fake_mapper,
    }
    exec(code, namespace)
    return namespace["run_mapping"], created, crop


@pytest.mark.parametrize(
    "mode,fail_selenium,expected",
    [
        ("selenium", 0, ["browser"]),
        ("selenium", 2, ["browser", "browser", "browser"]),
        ("api", 0, ["api"]),
        ("fallback", 0, ["browser"]),
        ("fallback", 2, ["browser", "browser", "browser"]),
        ("fallback", 3, ["browser", "browser", "browser", "api"]),
    ],
)
def test_stage_figure_transport_is_task_local_and_stops_on_valid_result(
    monkeypatch, tmp_path, mode, fail_selenium, expected
):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", mode)
    monkeypatch.setenv("MICROGEN_SELENIUM_ATTEMPTS", "3")
    monkeypatch.setenv("MICROGEN_API_ATTEMPTS", "2")
    calls = []

    def fake_mapper(client, page, folder, **kwargs):
        backend = kwargs["backend_override"]
        calls.append(backend)
        assert kwargs["single_attempt"] is True
        if backend == "browser" and calls.count("browser") <= fail_selenium:
            raise RuntimeError("Gemini Selenium response invalid or stalled")
        return page.with_name("mapping_verified.txt"), [folder / "Figure 1.1.png"]

    run, clients, crops = make_runner(tmp_path, monkeypatch, fake_mapper)
    run("pages", "crops", 1, 1, 30, False, False)
    assert calls == expected
    if mode == "api":
        assert not clients, "Pure API figure mapping must never attach Chrome"
    else:
        assert clients and clients[0].start_calls == 1
        assert clients[0].shutdown_calls == 1
    import json
    trace = json.loads((crops / "gemini_transport_attempts.json").read_text())
    assert trace["mode"] == mode
    assert trace["completed"] is True
    assert [x["backend"] for x in trace["attempts"]] == [
        "selenium" if x == "browser" else x for x in expected
    ]


def test_fallback_does_not_escalate_on_one_recoverable_selenium_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "fallback")
    seen = []

    def mapper(client, page, folder, **kwargs):
        seen.append(kwargs["backend_override"])
        if len(seen) == 1:
            raise TimeoutError("Gemini still pending past deadline")
        return page.with_name("mapping.txt"), []

    run, _clients, _crops = make_runner(tmp_path, monkeypatch, mapper)
    run("pages", "crops", 1, 1, 30, False, False)
    assert seen == ["browser", "browser"]


def test_fallback_exhaustion_never_marks_page_success(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "fallback")
    calls = []

    def mapper(client, page, folder, **kwargs):
        calls.append(kwargs["backend_override"])
        raise RuntimeError("Gemini refuses or returns incomplete mapping")

    run, _clients, crops = make_runner(tmp_path, monkeypatch, mapper)
    with pytest.raises(RuntimeError, match="no completion claim"):
        run("pages", "crops", 1, 1, 30, False, False)
    assert calls == ["browser"] * 3 + ["api"] * 2
    import json
    trace = json.loads((crops / "gemini_transport_attempts.json").read_text())
    assert trace["completed"] is False
    assert len(trace["attempts"]) == 5


def test_permission_error_never_triggers_api_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "fallback")
    calls = []

    def mapper(client, page, folder, **kwargs):
        calls.append(kwargs["backend_override"])
        raise PermissionError("Read-only teaching root")

    run, _clients, crops = make_runner(tmp_path, monkeypatch, mapper)
    with pytest.raises(RuntimeError, match="no completion claim"):
        run("pages", "crops", 1, 1, 30, False, False)
    assert calls == ["browser"], "A permission error is permanent, not retryable"
    assert not (crops / "gemini_transport_attempts.json").exists()


def test_figure_preflight_eager_chrome_only_in_pure_selenium(monkeypatch):
    for mode, browser, sdk in [
        ("selenium", True, False),
        ("api", False, True),
        ("fallback", False, True),
    ]:
        monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", mode)
        assert _needs_browser("figures") is browser
        assert _needs_api_python_for_stages(["figures"]) is sdk


def test_old_per_stage_api_override_cannot_force_api_under_selenium(monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "selenium")
    monkeypatch.setenv("MICROGEN_FIGURE_MAPPING_BACKEND", "api")
    calls = []
    def mapper(client, page, folder, **kwargs):
        calls.append(kwargs["backend_override"])
        return page.with_name("mapping.txt"), []

    run, _, _ = make_runner(tmp_path:=Path(__import__("tempfile").mkdtemp()), monkeypatch, mapper)
    try:
        run("pages", "crops", 1, 1, 30, False, False)
        assert calls == ["browser"]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_chrome_startup_failure_is_bounded_and_can_use_api_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "fallback")
    monkeypatch.setattr(FakeChrome, "start",
                        lambda self, **kwargs: (_ for _ in ()).throw(
                            RuntimeError("Chrome port / authenticated session unavailable")))
    backends = []

    def mapper(client, page, folder, **kwargs):
        backends.append(kwargs["backend_override"])
        assert kwargs["backend_override"] == "api"
        return page.with_name("verified.txt"), []

    run, clients, crops = make_runner(tmp_path, monkeypatch, mapper)
    run("pages", "crops", 1, 1, 30, False, False)
    assert len(clients) == 3
    assert all(client.shutdown_calls == 1 for client in clients)
    assert backends == ["api"]
    import json
    statuses = json.loads((crops / "gemini_transport_attempts.json").read_text())
    assert [item["status"] for item in statuses["attempts"]] == [
        "rejected", "rejected", "rejected", "validated"
    ]


def test_invalid_mode_fails_before_gemini_or_file_processing(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "hybrid")
    calls = []
    run, clients, crop = make_runner(
        tmp_path, monkeypatch,
        lambda *args, **kwargs: calls.append(1)
    )
    with pytest.raises(ValueError, match="must be selenium, api, or fallback"):
        run("pages", "crops", 1, 1, 30, False, False)
    assert not calls and not clients
    assert not (crop / "gemini_transport_attempts.json").exists()
