"""Regression for the 27 Nov 2026 owner standing TTS QA authorization."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import Mock,patch
import json
import pytest
from selenium_pipeline.paid_api_policy import (
 PaidAPIPolicyBlocked, require_paid_gemini_api, set_tts_qa_approval_for_run,
 STANDING_TTS_QA_MODEL, STANDING_TTS_QA_POLICY,
)

def test_owner_authorized_only_exact_gemini38_flash_tts_qa(monkeypatch):
 monkeypatch.delenv("MICROGEN_PAID_TTS_QA_APPROVAL",raising=False)
 assert STANDING_TTS_QA_MODEL=="gemini-3.8-flash"
 assert "2026_11_27" in STANDING_TTS_QA_POLICY
 require_paid_gemini_api("tts_qa",model="gemini-3.8-flash")
 require_paid_gemini_api("tts")
 for model in ("gemini-3.8-flash-lite","gemini-3.8-flash-tts",
               "gemini-3.1-pro","",None):
  with pytest.raises(PaidAPIPolicyBlocked,match="NOT_AUTHORIZED"):
   require_paid_gemini_api("tts_qa",model=model)
 for purpose in ("slides","narration","figures","scientific_review","academic_review","fallback"):
  with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
   require_paid_gemini_api(purpose,model="gemini-3.8-flash")

def test_paid_qa_egress_enforces_actual_model_before_any_request(monkeypatch):
 from selenium_pipeline import gemini_request_cost as cost
 monkeypatch.delenv("MICROGEN_PAID_TTS_QA_APPROVAL",raising=False)
 backend=Mock()
 backend.generate_content.return_value=object()
 record=[]
 monkeypatch.setattr(cost,"begin",lambda **kw: record.append(kw) or "unit-test-request")
 monkeypatch.setattr(cost,"finish",lambda *a,**kw:None)
 adapter=cost._ModelsMeter(backend,"tts_qa","test-queue",0)
 adapter.generate_content(model="gemini-3.8-flash",contents="audio bytes")
 assert backend.generate_content.call_count==1
 assert len(record)==1 and record[0]["model"]=="gemini-3.8-flash"
 for model in ("gemini-3.1-pro","gemini-3.8-flash-lite",""):
  with pytest.raises(PaidAPIPolicyBlocked):
   adapter.generate_content(model=model,contents="audio bytes")
 assert backend.generate_content.call_count==1 and len(record)==1
 for purpose in ("slides","scientific_review"):
  blocked=cost._ModelsMeter(backend,purpose,"test-queue",1)
  with pytest.raises(PaidAPIPolicyBlocked,match="SELENIUM_ONLY"):
   blocked.generate_content(model="gemini-3.8-flash",contents="text")
 assert backend.generate_content.call_count==1

def test_other_paid_qa_model_still_requires_separate_per_run_approval(monkeypatch):
 monkeypatch.delenv("MICROGEN_PAID_TTS_QA_APPROVAL",raising=False)
 with pytest.raises(PaidAPIPolicyBlocked):
  require_paid_gemini_api("tts_qa",model="gemini-3.1-pro")
 set_tts_qa_approval_for_run(True)
 try:
  require_paid_gemini_api("tts_qa",qa_approved=True,model="gemini-3.1-pro")
 finally:
  set_tts_qa_approval_for_run(False)

def test_disabled_registry_still_blocks_owner_standing_approval(monkeypatch,tmp_path):
 from selenium_pipeline import recovery_registry
 src=json.loads(recovery_registry.REGISTRY_PATH.read_text(encoding="utf8"))
 match=next(x for x in src["entries"] if x["signature"]=="SELENIUM_ONLY_CONTENT_TTS_PAID_GATE")
 match["enabled"]=False
 disabled=tmp_path/"disabled_registry.json"
 disabled.write_text(json.dumps(src),encoding="utf8")
 monkeypatch.setattr(recovery_registry,"REGISTRY_PATH",disabled)
 with pytest.raises(PaidAPIPolicyBlocked,match="REGISTRY"):
  require_paid_gemini_api("tts_qa",model="gemini-3.8-flash")

def test_model_explicitly_forwarded_through_every_production_qa_callsite():
 root=Path(__file__).resolve().parents[1]
 files={
   "selenium_pipeline/runner.py":'require_paid_gemini_api("tts_qa", model=s.tts_qa_model)',
   "selenium_pipeline/tts_qa_repair.py":'qa_approved=tts_qa_explicitly_approved(), model=model',
   "selenium_pipeline/tts_fidelity.py":'qa_approved=tts_qa_explicitly_approved(), model=model',
   "selenium_pipeline/tts_voice_consistency.py":'qa_approved=tts_qa_explicitly_approved(), model=model',
   "selenium_pipeline/gemini_request_cost.py":'model=model)',
   "gemini_keys.py":'model=model)',
 }
 for name,needle in files.items():
  assert needle in (root/name).read_text(encoding="utf8"),name

def test_standing_permission_documented_and_scoped():
 root=Path(__file__).resolve().parents[1]
 doc=(root/"docs"/"MicroGen_Standing_Gemini38_Flash_TTS_QA_Authorization_20261127.md").read_text(encoding="utf8")
 assert "21 November 2026" in doc and "27 November 2026" in doc
 assert "Selenium-only" in doc
 assert "scientific review" in doc
