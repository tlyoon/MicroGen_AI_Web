"""No-Send verified family route and fail-closed registry fault injection."""
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from selenium_pipeline.gemini_model import ensure_mode,GeminiModelError
from selenium_pipeline.recovery_registry import lookup_mechanism

class _Driver:
    window_handles=["tab"]
    current_window_handle="tab"
    current_url="https://gemini.google.com/app"
    def __init__(self):
        self.switch_to=SimpleNamespace(window=lambda h:None)
        self.closed=False
    def quit(self): self.closed=True

def test_presend_task_route_is_registered():
    assert lookup_mechanism(
        "presend_capability_repair",
        "V3_CHAPTER_RUNNER_FLASH_PREFLIGHT_BLOCKS_VERIFIED_DYNAMIC_ROUTE"
    )=="TASK_SCOPED_REGISTERED_OWNED_UI_MODEL_FALLBACK_NO_SEND"

@pytest.mark.parametrize("stage",["slides","narration"])
def test_stage_route_uses_owned_verified_selector_only(stage):
    from selenium import webdriver
    driver=_Driver()
    with patch.object(webdriver,"Chrome",return_value=driver), \
         patch("selenium_pipeline.gemini_model._owned_picker",return_value=object()), \
         patch("selenium_pipeline.gemini_model.select_owned_gemini_with_recovery",
               return_value="Open mode picker, currently Hydrogen High") as fallback, \
         patch("selenium_pipeline.gemini_model.select_owned_gemini_mode") as strict:
        label=ensure_mode(port=9222,mode="flash",timeout=1,stage=stage)
    assert "Hydrogen High" in label
    fallback.assert_called_once()
    assert fallback.call_args.kwargs["stage"]==stage
    assert fallback.call_args.kwargs["allow_fallback"] is True
    strict.assert_not_called()
    assert driver.closed

def test_registry_failure_blocks_before_any_model_change():
    from selenium import webdriver
    driver=_Driver()
    with patch.object(webdriver,"Chrome",return_value=driver), \
         patch("selenium_pipeline.gemini_model._owned_picker",return_value=object()), \
         patch("selenium_pipeline.recovery_registry.lookup_mechanism",return_value=None), \
         patch("selenium_pipeline.gemini_model.select_owned_gemini_with_recovery") as fallback, \
         pytest.raises(GeminiModelError,match="NOT_REGISTERED_NO_SEND"):
        ensure_mode(port=9222,mode="flash",timeout=1,stage="slides")
    fallback.assert_not_called()
    assert driver.closed

def test_no_stage_retains_strict_requested_flash():
    from selenium import webdriver
    driver=_Driver()
    with patch.object(webdriver,"Chrome",return_value=driver), \
         patch("selenium_pipeline.gemini_model._owned_picker",return_value=object()), \
         patch("selenium_pipeline.gemini_model.select_owned_gemini_mode",
               return_value="Open mode picker, currently Flash High") as strict, \
         patch("selenium_pipeline.gemini_model.select_owned_gemini_with_recovery") as fallback:
        label=ensure_mode(port=9222,mode="flash",timeout=1)
    assert "Flash High" in label
    strict.assert_called_once()
    fallback.assert_not_called()
