"""Fault injection for restart-safe, source-bound slide Gemini requests."""
from pathlib import Path
import ast
from unittest.mock import patch

import pytest

from selenium_pipeline.slide_transport_guard import (
    SlideAttemptClaim, PreSendFailure, IndeterminateSend)
from selenium_pipeline.communication_policy import CommunicationPolicy, CommunicationMode


def _fixtures(tmp_path):
    src = tmp_path / "source.pdf"
    prompt = tmp_path / "prompt.txt"
    src.write_bytes(b"%PDF-1.7\noriginal source")
    prompt.write_text("Source-only slide instructions", encoding="utf-8")
    return src, prompt


def test_prior_unknown_send_never_repeated(tmp_path):
    source, prompt = _fixtures(tmp_path)
    claim = SlideAttemptClaim(source, prompt, "A", backend="selenium",
                              ordinal=1, root=tmp_path / "claims")
    assert claim.read_existing() is None
    claim.mark_send_may_have_occurred()
    with pytest.raises(IndeterminateSend, match="unresolved"):
        claim.read_existing()
    with pytest.raises(IndeterminateSend, match="already claimed"):
        claim.mark_send_may_have_occurred()


def test_response_recovered_without_new_send_and_tamper_rejected(tmp_path):
    src, prompt = _fixtures(tmp_path)
    claim = SlideAttemptClaim(src, prompt, "A", backend="api", ordinal=1,
                              root=tmp_path / "claims")
    claim.mark_send_may_have_occurred()
    claim.capture(r"\documentclass{beamer}\end{document}")
    assert "documentclass" in claim.read_existing()
    same = SlideAttemptClaim(src, prompt, "A", backend="api", ordinal=1,
                             root=tmp_path / "claims")
    assert same.read_existing() == claim.read_existing()
    same.raw_path.write_text("corruption")
    with pytest.raises(IndeterminateSend, match="checksum"):
        same.read_existing()


def test_attempts_and_source_versions_are_separate(tmp_path):
    src, prompt = _fixtures(tmp_path)
    root = tmp_path / "claims"
    one = SlideAttemptClaim(src, prompt, "A", backend="api", ordinal=1, root=root)
    two = SlideAttemptClaim(src, prompt, "A", backend="api", ordinal=2, root=root)
    one.mark_send_may_have_occurred()
    assert two.read_existing() is None
    src.write_bytes(b"%PDF-1.7\nchanged source")
    changed = SlideAttemptClaim(src, prompt, "A", backend="api", ordinal=1, root=root)
    assert changed.read_existing() is None


def _vendor_function():
    vendor = Path(__file__).resolve().parents[1] / (
        "selenium_pipeline/vendor_template_v2/gen_slides_selenium_v11.py")
    tree = ast.parse(vendor.read_text(encoding="utf-8-sig"))
    fn = next(x for x in tree.body
              if isinstance(x, ast.FunctionDef) and x.name == "generate_slides_tex")
    import os
    ns = {
        "Path": Path, "os": os, "log": lambda *a, **k: None,
        "find_citation_artifacts": lambda *a: [],
        "sanitize_gemini_latex_response": lambda s: s,
        "normalize_unicode_to_latex": lambda s: s,
        "beamer_stack_sanity_check": lambda text, folder, **kwargs:
            (text.startswith(r"\documentclass"), []),
    }
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(vendor), "exec"), ns)
    return ns["generate_slides_tex"]


LATEX = r"\documentclass{beamer}\begin{document}\begin{frame}Test\end{frame}\end{document}"


def test_safe_presend_failure_can_use_api_fallback(tmp_path):
    src, prompt = _fixtures(tmp_path)
    png = tmp_path / "dimensions.json"
    png.write_text("{}")
    calls = []
    def transport(backend, instruction):
        calls.append(backend)
        if backend == "selenium":
            raise PreSendFailure("owned picker not hydrated")
        return LATEX
    _vendor_function()(None, src, prompt, png, tmp_path / "slides.tex", 20,
                       response_provider=transport,
                       communication_plan=CommunicationPolicy(
                           CommunicationMode.FALLBACK,
                           selenium_attempts=1, api_attempts=1).plan("slides"))
    assert calls == ["selenium", "api"]


def test_unknown_or_uncertain_send_never_triggers_fallback(tmp_path):
    src, prompt = _fixtures(tmp_path)
    png = tmp_path / "dimensions.json"
    png.write_text("{}")
    for failure in (IndeterminateSend("claimed send"), RuntimeError("unclassified")):
        calls = []
        def transport(backend, instruction):
            calls.append(backend)
            raise failure
        with pytest.raises(type(failure)):
            _vendor_function()(None, src, prompt, png, tmp_path / "slides.tex", 20,
                               response_provider=transport,
                               communication_plan=CommunicationPolicy(
                                   CommunicationMode.FALLBACK,
                                   selenium_attempts=1, api_attempts=1).plan("slides"))
        assert calls == ["selenium"]


def test_model_identity_is_recorded_and_mismatch_is_not_reused(tmp_path, monkeypatch):
    src, prompt = _fixtures(tmp_path)
    monkeypatch.setenv("MICROGEN_GEMINI_UI_MODE", "flash")
    a = SlideAttemptClaim(src, prompt, "A", backend="selenium",
                          ordinal=1, root=tmp_path / "claims")
    a.mark_send_may_have_occurred()
    a.capture(LATEX)
    monkeypatch.setenv("MICROGEN_GEMINI_UI_MODE", "pro")
    b = SlideAttemptClaim(src, prompt, "A", backend="selenium",
                          ordinal=1, root=tmp_path / "claims")
    with pytest.raises(IndeterminateSend, match="mismatch"):
        b.read_existing()


def test_api_single_sdk_invocation_budget(tmp_path):
    src, prompt = _fixtures(tmp_path)
    metadata = tmp_path / "dimensions.json"
    metadata.write_text("{}")
    from types import SimpleNamespace
    from selenium_pipeline.slides_api import request_slides
    seen = {}
    def request(factory, operation, **kwargs):
        seen.update(kwargs)
        return operation(SimpleNamespace(models=SimpleNamespace(
            generate_content=lambda **kw: SimpleNamespace(
                candidates=[SimpleNamespace(finish_reason="STOP")],
                text=LATEX))))
    with patch("gemini_keys.call_with_client_failover", side_effect=request):
        assert request_slides(src, prompt, metadata, "Beamer") == LATEX
    assert seen["max_retries"] == 0
