"""Phase 1C: fault-inject the actual narration main, no Gemini or Chrome calls."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from selenium_pipeline.runner import _needs_api_python_for_stages, _needs_browser

VENDOR = (Path(__file__).resolve().parents[1] /
          "selenium_pipeline/vendor_template_v2/gen_script_selenium_v15.py")


def _main(tmp_path, monkeypatch, selenium_responses, api_responses):
    tmp_path.mkdir(exist_ok=True, parents=True)
    source = tmp_path / "source.pdf"
    slides = tmp_path / "slides.pdf"
    prompt = tmp_path / "gen_script_prompt_v10.txt"
    for p in (source, slides):
        p.write_bytes(b"%PDF-1.7\nsynthetic")
    prompt.write_text("Narrate the source safely.")
    script = tmp_path / "script.txt"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MICROGEN_PACKAGE_ROOT", str(VENDOR.parents[2]))

    tree = ast.parse(VENDOR.read_text(encoding="utf-8-sig"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    code = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                   str(VENDOR), "exec")
    calls = []
    made = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.start_count = 0
            self.shutdown_count = 0
            made.append(self)

        def start(self, **kwargs):
            self.start_count += 1

        def shutdown(self):
            self.shutdown_count += 1

    def next_result(backend, results):
        calls.append(backend)
        idx = calls.count(backend) - 1
        answer = results[idx] if idx < len(results) else None
        if isinstance(answer, Exception):
            raise answer
        return answer

    def save_script(txt):
        script.write_text(txt, encoding="utf-8")

    def archive(p):
        if p.exists():
            p.unlink()

    from selenium_pipeline.communication_policy import policy_from_configuration
    ns = dict(
        os=os, sys=sys, Path=Path, json=json,
        policy_from_configuration=policy_from_configuration,
        CommunicationBackend=__import__("selenium_pipeline.communication_policy", fromlist=["CommunicationBackend"]).CommunicationBackend,
        SLIDES_PDF=slides, SOURCE_PDF=source, PROMPT_FILE=prompt,
        OUT_SCRIPT=script, RENDERED_PROMPT_FILE=tmp_path / "rendered.txt",
        log=lambda *args, **kwargs: None,
        count_pdf_pages=lambda f: 2,
        extract_exact_slide_titles=lambda f: ["Physics A", "Physics B"],
        render_prompt_template=lambda *a: "Check both PDF files.",
        save_rendered_prompt=lambda x: None,
        save_exact_titles_json=lambda *a: None,
        build_instruction=lambda *a: "Generate complete narration.",
        retry_instruction=lambda instr, warnings: instr,
        _load_local_gemini_selenium_module=lambda:
            SimpleNamespace(Config=lambda **kwargs: SimpleNamespace(**kwargs),
                            GeminiSeleniumClient=FakeClient),
        request_script_once=lambda client, gemsel, instr, pages:
            next_result("selenium", selenium_responses),
        request_script_api_once=lambda instr, pages:
            next_result("api", api_responses),
        sanitize_and_rebuild_script=lambda text, titles: text,
        save_script_text=save_script,
        run_post_processors=lambda: None,
        force_exact_titles_after_postprocessing=lambda titles: None,
        collect_all_warnings=lambda path, pdf, titles:
            ["Unacceptable narration"] if path.read_text().startswith("INVALID") else [],
        backup_existing=archive,
    )
    exec(code, ns)
    return ns["main"], calls, made, script


@pytest.mark.parametrize("mode,selenium_answers,api_answers,expected", [
    ("selenium", ["VALID"], [], ["selenium"]),
    ("selenium", [None, None, "VALID"], [], ["selenium"] * 3),
    ("api", [], ["VALID"], ["api"]),
    ("fallback", ["VALID"], [], ["selenium"]),
    ("fallback", [None, RuntimeError("stalled"), None], ["VALID"],
     ["selenium"] * 3 + ["api"]),
])
def test_task_local_modes_retry_and_stop_on_valid_narration(
    tmp_path, monkeypatch, mode, selenium_answers, api_answers, expected
):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", mode)
    run, calls, clients, script = _main(tmp_path, monkeypatch,
                                         selenium_answers, api_answers)
    assert run() == 0
    assert calls == expected
    assert script.read_text() == "VALID"
    trace = json.loads((tmp_path / "gemini_narration_transport_attempts.json").read_text())
    assert trace["completed"] is True
    assert trace["mode"] == mode
    if mode == "api":
        assert not clients
    else:
        assert clients and clients[0].start_count == 1
        assert clients[0].shutdown_count == 1


def test_rejected_narration_never_published_as_valid(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "fallback")
    run, calls, _, script = _main(tmp_path, monkeypatch,
                                   ["INVALID" for _ in range(3)],
                                   ["INVALID" for _ in range(2)])
    assert run() == 1
    assert not script.exists()
    assert calls == ["selenium"] * 3 + ["api"] * 2
    assert len(list(tmp_path.glob("script.rejected_*_attempt_*.txt"))) == 5
    trace = json.loads((tmp_path / "gemini_narration_transport_attempts.json").read_text())
    assert trace["completed"] is False


def test_narration_fallback_only_after_all_selenium_validation_failures(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "fallback")
    run, calls, _, script = _main(tmp_path, monkeypatch,
                                  ["INVALID", "VALID"], ["SHOULD_NOT_RUN"])
    assert run() == 0
    assert calls == ["selenium", "selenium"]
    assert script.read_text() == "VALID"


def test_local_missing_source_fails_without_consulting_gemini(tmp_path, monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", "fallback")
    run, calls, _, _ = _main(tmp_path, monkeypatch, ["VALID"], ["VALID"])
    (tmp_path / "source.pdf").unlink()
    assert run() == 1
    assert calls == []


def test_narration_browser_and_sdk_preflight_honor_central_setting(monkeypatch):
    for mode, browser, sdk in (
        ("selenium", True, False),
        ("api", False, True),
        ("fallback", False, True),
    ):
        monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE", mode)
        assert _needs_browser("narration") is browser
        assert _needs_api_python_for_stages(["narration"]) is sdk


def test_production_launcher_has_override_and_no_forced_api_default():
    root = VENDOR.parents[2]
    script = (root / "operations/Start-MicroGen_AI_Web.ps1").read_text(encoding="utf-8-sig")
    runner = (root / "selenium_pipeline/runner.py").read_text(encoding="utf-8-sig")
    assert "[string]$CommunicationMode = ''" in script
    assert "$env:MICROGEN_COMMUNICATION_MODE = 'selenium'" in script
    assert "$env:MICROGEN_NARRATION_BACKEND = 'api'" not in script
    assert "--communication-mode" in runner
