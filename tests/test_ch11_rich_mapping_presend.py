"""Rich mapping source-bound browser routing: no-Send failure recovery."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from selenium_pipeline.gemini_model import ensure_mode,GeminiModelError
from selenium_pipeline.recovery_registry import lookup_mechanism

class _Driver:
    window_handles=["owned"]
    current_url="https://gemini.google.com/app"
    current_window_handle="owned"
    def __init__(self):
        self.switch_to=SimpleNamespace(window=lambda handle:None)
        self.closed=False
    def quit(self):self.closed=True

def test_rich_mapping_browser_route_registry_bound():
    assert lookup_mechanism(
        "presend_capability_repair",
        "RICH_MAPPING_SOURCE_BOUND_UI_PREFLIGHT_BEFORE_SEND"
    )=="TASK_SCOPED_REGISTERED_OWNED_UI_MODEL_FALLBACK_NO_SEND"

def test_rich_mapping_scope_uses_verified_model_family_not_legacy_exact_flash():
    from selenium import webdriver
    d=_Driver()
    with patch.object(webdriver,"Chrome",return_value=d), \
         patch("selenium_pipeline.gemini_model._owned_picker",return_value=object()), \
         patch("selenium_pipeline.gemini_model.select_owned_gemini_with_recovery",
               return_value="Open mode picker, currently Neon High") as recovery, \
         patch("selenium_pipeline.gemini_model.select_owned_gemini_mode") as legacy:
        actual=ensure_mode(port=9222,mode="flash",timeout=2,stage="rich_mapping")
    assert "Neon" in actual
    recovery.assert_called_once()
    assert recovery.call_args.kwargs["stage"]=="rich_mapping"
    assert recovery.call_args.kwargs["allow_fallback"] is True
    legacy.assert_not_called()
    assert d.closed

def test_disabled_rich_mapping_registry_blocks_before_selector_or_send():
    from selenium import webdriver
    d=_Driver()
    with patch.object(webdriver,"Chrome",return_value=d), \
         patch("selenium_pipeline.gemini_model._owned_picker",return_value=object()), \
         patch("selenium_pipeline.recovery_registry.lookup_mechanism",return_value=None), \
         patch("selenium_pipeline.gemini_model.select_owned_gemini_with_recovery") as recovery, \
         pytest.raises(GeminiModelError,match="NOT_REGISTERED_NO_SEND"):
        ensure_mode(port=9222,mode="flash",timeout=1,stage="rich_mapping")
    recovery.assert_not_called()
    assert d.closed

def test_direct_cli_preflight_failure_never_claims_ambiguous_send(tmp_path):
    from selenium_pipeline.rich_element_model_alignment import main
    target=tmp_path/"test_audit.json"
    source_folder=tmp_path/"source";source_folder.mkdir()
    with patch("selenium_pipeline.rich_element_model_alignment.request_for_slide",
               return_value={"request_sha256":"sha","source_inputs_sha256":{}}), \
         patch("selenium_pipeline.gemini_model.ensure_mode",
               side_effect=GeminiModelError("EXACT_UI_ROUTE_NOT_ESTABLISHED_NO_SEND")) as preflight, \
         patch("selenium_pipeline.series_gemini._browser_request") as send, \
         pytest.raises(GeminiModelError,match="NO_SEND"):
        main(["--source-folder",str(source_folder),
              "--checkpoint",str(tmp_path),
              "--slide","1","--out",str(target),
              "--gemini-web","--browser-port","9222","--wait-s","10"])
    preflight.assert_called_once()
    assert preflight.call_args.kwargs["stage"]=="rich_mapping"
    assert not target.with_suffix(".submission_held.json").exists()
    assert not target.exists()
    send.assert_not_called()
