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
    # A completed mocked mapping must produce the same files a real
    # source-verified Gemini mapper produces, not just return a filename.
    (tmp_path / "source.pdf").write_bytes(b"unchanged synthetic PDF")

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
    def materializing_mapper(client, original_page, original_folder, **kwargs):
        result = fake_mapper(client, original_page, original_folder, **kwargs)
        if result is None:
            return None
        returned_mapping, targets = result
        if targets:
            expected = original_page.with_name(original_page.stem + "_mapping.txt")
            originals = sorted(original_folder.glob("fig_[0-9]*.png"))
            assert len(originals) == len(targets), "Fixture must map every original crop"
            for orig, target in zip(originals, targets):
                target.write_bytes(orig.read_bytes())
            expected.write_text("\n".join(
                f'{orig.name} : "{target.stem}" : {target.name}'
                for orig, target in zip(originals, targets)
            ) + "\n", encoding="utf-8")
        return returned_mapping, targets

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
        "map_and_rename_single_step": materializing_mapper,
    }
    exec(code, namespace)
    return namespace["run_mapping"], created, crop



@pytest.mark.parametrize("failures,count",[(0,1),(2,3)])
def test_figure_mapping_selenium_recovery_only(monkeypatch,tmp_path,failures,count):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    calls=[]
    def mapper(client,page,folder,**kwargs):
        calls.append(kwargs["backend_override"])
        if len(calls)<=failures:
            raise RuntimeError("Selenium browser preparation incomplete")
        return page.with_name("mapping_verified.txt"),[folder/"Figure 1.1.png"]
    run,clients,crop=make_runner(tmp_path,monkeypatch,mapper)
    run("pages","crops",1,1,30,False,False)
    assert calls==["browser"]*count
    assert len(clients)==1 and clients[0].shutdown_calls==1
    import json
    trace=json.loads((crop/"gemini_transport_attempts.json").read_text())
    assert trace["completed"] is True
    assert all(x["backend"]=="selenium" for x in trace["attempts"])


def test_all_figure_selenium_failures_no_api_or_completed_mapping(monkeypatch,tmp_path):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    calls=[]
    def mapper(client,page,folder,**kwargs):
        calls.append(kwargs["backend_override"])
        raise RuntimeError("Gemini Selenium exhausted")
    run,_,crop=make_runner(tmp_path,monkeypatch,mapper)
    with pytest.raises(RuntimeError):
        run("pages","crops",1,1,30,False,False)
    assert calls==["browser"]*3
    import json
    trace=json.loads((crop/"gemini_transport_attempts.json").read_text())
    assert trace["completed"] is False


def test_invalid_modes_fail_before_browser_model_or_mapping(monkeypatch,tmp_path):
    for mode in ("api","fallback","hybrid"):
        monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE",mode)
        calls=[]
        run,clients,crop=make_runner(tmp_path/mode,monkeypatch,
            lambda *a,**k:calls.append(1))
        with pytest.raises(ValueError,match="SELENIUM_ONLY"):
            run("pages","crops",1,1,30,False,False)
        assert not calls and not clients


def test_per_stage_api_backend_override_not_used(monkeypatch,tmp_path):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    monkeypatch.setenv("MICROGEN_FIGURE_MAPPING_BACKEND","api")
    calls=[]
    def mapper(client,page,folder,**kwargs):
        calls.append(kwargs["backend_override"])
        return page.with_name("mapping.txt"),[folder/"Figure 1.1.png"]
    run,_,_=make_runner(tmp_path,monkeypatch,mapper)
    run("pages","crops",1,1,30,False,False)
    assert calls==["browser"]


def test_figure_chrome_unavailable_stays_bounded_without_paid_fallback(monkeypatch,tmp_path):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    monkeypatch.setattr(FakeChrome,"start",
        lambda self,**kw:(_ for _ in ()).throw(RuntimeError("Chrome unavailable")))
    seen=[]
    run,clients,crops=make_runner(tmp_path,monkeypatch,
        lambda client,page,folder,**kw:seen.append(kw))
    with pytest.raises(RuntimeError):
        run("pages","crops",1,1,30,False,False)
    assert not seen
    assert len(clients)==3


def test_figure_browser_never_needs_paid_sdk_python(monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    assert _needs_browser("figures")
    assert not _needs_api_python_for_stages(["figures","slides","narration"])
