"""Source-grounded Selenium slide generation; no API fallback after a failure."""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch
import pytest

from selenium_pipeline import slides_api
from selenium_pipeline.slide_transport_guard import PreSendFailure
from selenium_pipeline.communication_policy import CommunicationPolicy,CommunicationMode
from selenium_pipeline.paid_api_policy import PaidAPIPolicyBlocked
from selenium_pipeline.runner import _needs_browser,_needs_api_python_for_stages

ROOT=Path(__file__).resolve().parents[1]
VENDOR=ROOT/"selenium_pipeline/vendor_template_v2/gen_slides_selenium_v11.py"
LATEX=r"\documentclass{beamer}\begin{document}\begin{frame}Test\end{frame}\end{document}"


def source_inputs(tmp_path):
    src=tmp_path/"source.pdf";src.write_bytes(b"%PDF-1.7\noriginal")
    p=tmp_path/"prompt.txt";p.write_text("Use source only")
    meta=tmp_path/"dimensions.json";meta.write_text("{}")
    return src,p,meta


def _vendor_slide_function():
    tree=ast.parse(VENDOR.read_text(encoding="utf-8-sig"))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
              and n.name=="generate_slides_tex")
    import os
    ns={
        "Path":Path,"os":os,"log":lambda *a,**k:None,
        "find_citation_artifacts":lambda _:[],
        "sanitize_gemini_latex_response":lambda x:x,
        "normalize_unicode_to_latex":lambda x:x,
        "beamer_stack_sanity_check":lambda text,folder,**k:
            (text.startswith(r"\documentclass"),["Invalid"])}
    exec(compile(ast.fix_missing_locations(ast.Module(
        body=[node],type_ignores=[])),str(VENDOR),"exec"),ns)
    return ns["generate_slides_tex"]


def test_paid_slide_adapter_denied_before_any_sdk_call(tmp_path):
    src,p,meta=source_inputs(tmp_path)
    with patch("gemini_keys.call_with_client_failover") as send:
        with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
            slides_api.request_slides(src,p,meta,"Use Beamer")
        send.assert_not_called()


def test_paid_slide_cli_does_not_create_raw_output(tmp_path):
    src,p,meta=source_inputs(tmp_path)
    instr=tmp_path/"request.txt";instr.write_text("Beamer")
    output=tmp_path/"api.txt"
    with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
        slides_api.main(["--source",str(src),"--prompt",str(p),
            "--dimensions",str(meta),"--instruction-file",str(instr),
            "--output",str(output)])
    assert not output.exists()


@pytest.mark.parametrize("failures,expected",[(0,1),(2,3)])
def test_selenium_only_slide_success_after_bounded_presend_recovery(
        tmp_path,failures,expected):
    src,p,meta=source_inputs(tmp_path)
    calls=[]
    def browser(backend,instruction):
        calls.append(backend)
        if len(calls)<=failures:
            raise PreSendFailure("Composer not hydrated pre-send")
        return LATEX
    output=tmp_path/"slides.tex"
    result=_vendor_slide_function()(
        None,src,p,meta,output,30,response_provider=browser,
        communication_plan=CommunicationPolicy().plan("slides"))
    assert result==output
    assert calls==["selenium"]*expected
    assert output.read_text().strip()==LATEX


def test_failed_selenium_never_switches_to_api_or_publishes(tmp_path):
    src,p,meta=source_inputs(tmp_path)
    calls=[]
    def broken(backend,instruction):
        calls.append(backend)
        raise PreSendFailure("Browser unavailable")
    output=tmp_path/"slides.tex"
    with pytest.raises(RuntimeError):
        _vendor_slide_function()(
            None,src,p,meta,output,30,response_provider=broken,
            communication_plan=CommunicationPolicy().plan("slides"))
    assert calls==["selenium"]*3
    assert not output.exists()


@pytest.mark.parametrize("mode",[CommunicationMode.API,CommunicationMode.FALLBACK])
def test_legacy_slide_api_modes_not_constructible(mode):
    with pytest.raises(ValueError,match="SELENIUM_ONLY"):
        CommunicationPolicy(mode)


def test_runner_always_needs_chrome_for_content_never_sdk(monkeypatch):
    monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE","selenium")
    assert _needs_browser("slides")
    assert not _needs_api_python_for_stages(["slides"])
    for invalid in ("api","fallback"):
        monkeypatch.setenv("MICROGEN_COMMUNICATION_MODE",invalid)
        with pytest.raises(ValueError,match="SELENIUM_ONLY"):
            _needs_browser("slides")


def test_vendor_has_pre_claim_api_denial():
    text=VENDOR.read_text(encoding="utf-8-sig")
    assert 'if backend != "selenium":' in text
    assert 'require_paid_gemini_api("slides")' in text
    assert 'policy.plan("slides")' in text
