"""Phase 1C: fault-inject the actual narration main, no Gemini or Chrome calls."""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from selenium_pipeline.runner import _needs_api_python_for_stages, _needs_browser, _may_use_browser

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
        def __init__(self, *args, **kwargs):
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
        request_script_api_once=lambda instr, pages, **kwargs:
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



@pytest.mark.parametrize("answers,expected",[
    (["VALID"],["selenium"]),
    ([None,None,"VALID"],["selenium"]*3),
    (["INVALID","VALID"],["selenium"]*2),
])
def test_narration_uses_only_selenium(tmp_path,monkeypatch,answers,expected):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    run,calls,clients,script=_main(tmp_path,monkeypatch,answers,["NEVER_API"])
    assert run()==0
    assert calls==expected
    assert script.read_text()=="VALID"
    assert clients and clients[0].shutdown_count==1
    trace=json.loads((tmp_path/"gemini_narration_transport_attempts.json").read_text())
    assert trace["mode"]=="selenium"
    assert all(v["backend"]=="selenium" for v in trace["attempts"])


def test_invalid_narration_never_falls_back_or_publishes(tmp_path,monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    run,calls,_,script=_main(tmp_path,monkeypatch,
        ["INVALID"]*3,["WOULD_BE_CHARGEABLE"])
    assert run()==1
    assert not script.exists()
    assert calls==["selenium"]*3
    trace=json.loads((tmp_path/"gemini_narration_transport_attempts.json").read_text())
    assert trace["completed"] is False


def test_missing_source_no_browser_or_api(tmp_path,monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    run,calls,_,_=_main(tmp_path,monkeypatch,["VALID"],["NEVER"])
    (tmp_path/"source.pdf").unlink()
    assert run()==1 and calls==[]


def test_legacy_mode_denied_before_browser_or_api(tmp_path,monkeypatch):
    for mode in ("api","fallback"):
        monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE",mode)
        run,calls,_,script=_main(tmp_path,monkeypatch,["VALID"],["NEVER"])
        with pytest.raises(ValueError,match="SELENIUM_ONLY"):
            run()
        assert calls==[] and not script.exists()


def test_browser_stage_and_lock_require_selenium(monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    for stage in ("figures","slides","narration"):
        assert _needs_browser(stage)
        assert _may_use_browser(stage)
    assert not _needs_api_python_for_stages(["narration"])
    for stage in ("script_qa","tts","tts_qa","video"):
        assert not _may_use_browser(stage)
    for mode in ("api","fallback"):
        monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE",mode)
        with pytest.raises(ValueError,match="SELENIUM_ONLY"):
            _needs_browser("narration")


def test_launcher_never_forces_api_default():
    root=VENDOR.parents[2]
    script=(root/"operations/Start-MicroGen_AI_Web.ps1").read_text(encoding="utf-8-sig")
    assert "$env:MICROGEN_COMMUNICATION_MODE = 'selenium'" in script
    assert "$env:MICROGEN_NARRATION_BACKEND = 'api'" not in script
