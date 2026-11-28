"""Regression proof for HP stale Gemini menu and no-replay revision retries."""
from unittest.mock import patch
from selenium_pipeline import gemini_model
from selenium_pipeline.safe_presend_retry_v1 import verified_new_code_presend_retry

class Driver:
    current_window_handle = "owned"
    current_url = "https://gemini.google.com/app"

class Picker:
    expanded = "true"
    clicks = 0
    def get_attribute(self, name):
        return self.expanded if name == "aria-expanded" else None
    def click(self):
        self.clicks += 1
        self.expanded = "false"

def test_stale_owned_model_menu_recovers_by_one_close_reopen(monkeypatch):
    driver, picker = Driver(), Picker()
    reopened = []
    monkeypatch.setattr(gemini_model, "_owned_picker", lambda *_: picker)
    monkeypatch.setattr(gemini_model, "_visible_model_options",
                        lambda *_: ["Neon"] if reopened else [])
    monkeypatch.setattr(gemini_model.time,"sleep",lambda *_: None)
    def verified_open(_driver, _handle, _picker, *, allow_model_switch):
        assert (_driver, _handle, _picker) == (driver, "owned", picker)
        assert allow_model_switch is True
        assert picker.expanded == "false"
        picker.expanded = "true"
        reopened.append(True)
    with patch("selenium_pipeline.gemini_thinking."
               "_open_owned_mode_picker_with_verified_fallback",
               side_effect=verified_open):
        assert gemini_model._reopen_owned_model_menu_if_empty(driver,"owned")
    assert picker.clicks == 1
    assert picker.expanded == "true"
    assert reopened == [True]

def test_menu_already_has_options_never_toggles(monkeypatch):
    p=Picker()
    monkeypatch.setattr(gemini_model,"_owned_picker",lambda *_:p)
    monkeypatch.setattr(gemini_model,"_visible_model_options",
                        lambda *_:["hydrogen","neon","carbon"])
    assert not gemini_model._reopen_owned_model_menu_if_empty(Driver(),"owned")
    assert p.clicks==0

def test_foreign_tab_never_toggles(monkeypatch):
    p=Picker()
    monkeypatch.setattr(gemini_model,"_owned_picker",lambda *_:p)
    try:
        gemini_model._reopen_owned_model_menu_if_empty(Driver(),"foreign")
    except gemini_model.GeminiModelError as e:
        assert "TAB_CHANGED" in str(e)
    else: raise AssertionError("Foreign tab was not refused")
    assert p.clicks==0

def _entry(path):
    return {"status":"BLOCKED_PRE_SEND","source_sha256":"a"*64,
            "attempts":[{"source_sha256":"a"*64,"code_sha":"0"*40,
                         "returncode":1,"log":str(path)}]}

def test_new_verified_revision_may_retry_one_presend_model_menu_failure(tmp_path):
    p=tmp_path/"1.4_v2_attempt3.log"
    p.write_text("PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND\n"
                 "selenium_pipeline.gemini_model.GeminiModelError: "
                 "PRE_SEND_MODEL_FALLBACK_NOT_AUTHORIZED_WITHOUT_EXACT_MENU_EVIDENCE")
    e=_entry(p)
    assert verified_new_code_presend_retry(e,"1"*40,tmp_path)
    assert not verified_new_code_presend_retry(e,"0"*40,tmp_path)
    e["attempts"][-1]["code_sha"]="1"*40
    assert not verified_new_code_presend_retry(e,"1"*40,tmp_path)

def test_uncertain_send_and_quarantine_never_retry(tmp_path):
    p=tmp_path/"1.2_v2_attempt3.log"
    p.write_text("PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND\n"
                 "GeminiModelError: PRE_SEND_MODEL_FALLBACK_NOT_AUTHORIZED_WITHOUT_EXACT_MENU_EVIDENCE\n"
                 "UNCERTAIN_SEND")
    e=_entry(p)
    assert not verified_new_code_presend_retry(e,"1"*40,tmp_path)
    p.write_text(p.read_text().replace("UNCERTAIN_SEND",""))
    e["status"]="QUARANTINED_MANUAL_RECONCILIATION"
    assert not verified_new_code_presend_retry(e,"1"*40,tmp_path)
    e["status"]="BLOCKED_PRE_SEND"
    e["source_sha256"]="b"*64
    assert not verified_new_code_presend_retry(e,"1"*40,tmp_path)

def test_outside_log_dir_never_admitted(tmp_path):
    outside=tmp_path.parent/"outside_1_4.log"
    outside.write_text("PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND\n"
                       "GeminiModelError: PRE_SEND_MODEL_FALLBACK_NOT_AUTHORIZED_WITHOUT_EXACT_MENU_EVIDENCE")
    try:
        assert not verified_new_code_presend_retry(_entry(outside),"1"*40,tmp_path)
    finally:
        outside.unlink()
