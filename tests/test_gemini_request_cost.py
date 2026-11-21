"""Offline fault-injection for durable per-request cost bookkeeping."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch
import pytest

from selenium_pipeline import gemini_request_cost as cost


@pytest.fixture()
def account(tmp_path, monkeypatch):
    ledger = tmp_path / "cost.sqlite3"
    monkeypatch.setenv("MICROGEN_GEMINI_COST_LEDGER_PATH",str(ledger))
    monkeypatch.setenv("MICROGEN_SUBSECTION","8.2")
    monkeypatch.setenv("MICROGEN_CHAPTER","8")
    monkeypatch.setenv("MICROGEN_ACTIVE_GENERATION_STAGE","tts")
    return ledger


def records(account):
    with sqlite3.connect(account) as con:
        con.row_factory=sqlite3.Row
        return [dict(row) for row in con.execute(
            "SELECT * FROM gemini_requests ORDER BY started_utc,request_id")]


def fake_response(input_count=100,output_count=250,thoughts=0):
    usage=SimpleNamespace(prompt_token_count=input_count,
        candidates_token_count=output_count,thoughts_token_count=thoughts)
    return SimpleNamespace(usage_metadata=usage,text="A verified reply")


def test_api_provider_usage_takes_precedence_over_heuristics(account):
    request=cost.begin(model="gemini-3.8-flash-tts",purpose="tts",
                       transport="api",input_text="Narrate this.")
    cost.finish(request,response=fake_response(100,250))
    row=records(account)[0]
    assert row["chapter"]=="8"
    assert row["subsection"]=="8.2"
    assert row["model"]=="gemini-3.8-flash-tts"
    assert row["stage"]=="tts"
    assert row["purpose"]=="tts"
    assert row["input_tokens"]==100
    assert row["output_tokens"]==250
    assert row["input_token_source"]=="provider_reported"
    assert row["output_token_source"]=="provider_reported_including_thinking"
    assert row["estimated_usd_cost"]==pytest.approx((100*.5+250*9)/1_000_000)
    assert row["status"]=="response_captured"


def test_unknown_send_survives_restart_without_optimistic_free_charge(account):
    request=cost.begin(model="gemini-3.8-flash-lite-tts",
                       purpose="tts",transport="api",input_text="A" * 400)
    row=records(account)[0]
    assert row["status"]=="possible_send"
    assert row["input_tokens"]==100
    assert row["output_tokens"] is None
    assert "partial" in row["billing_note"]
    # Separate database connection has committed the unconfirmed send.
    assert sqlite3.connect(account).execute("SELECT COUNT(*) FROM gemini_requests").fetchone()[0]==1
    cost.finish(request,failure=TimeoutError("network dropped"))
    row=records(account)[0]
    assert row["status"]=="send_uncertain"
    assert row["failure_class"]=="TimeoutError"
    assert cost.summary()["uncertain_api_attempts_excluded_from_captured_total"]==1


def test_browser_tokens_not_mistaken_for_billed_api_cost(account,monkeypatch):
    monkeypatch.setenv("MICROGEN_ACTIVE_GENERATION_STAGE","slides")
    monkeypatch.setenv("MICROGEN_LLM_MODEL","gemini-3.8-flash")
    client=SimpleNamespace(_microgen_cost_prompt_text="Make a verified Beamer deck")
    request=cost.browser_begin(client)
    cost.browser_finish(client,status="registered_response_pending")
    assert records(account)[0]["output_tokens"] is None
    cost.browser_finish(client,response_text=r"\documentclass{beamer}\begin{frame}A\end{frame}")
    row=records(account)[0]
    assert row["request_id"]==request
    assert row["output_tokens"]>0
    assert row["output_token_source"]=="heuristic_text"
    assert row["input_token_source"]=="heuristic_text_partial_multimodal"
    assert row["estimated_usd_cost"]==0.0
    assert "subscription" in row["billing_note"]
    assert row["status"]=="response_captured"


def test_browser_no_response_does_not_invent_output_or_duplicate_request(account):
    client=SimpleNamespace(_microgen_cost_prompt_text="What is x?")
    cost.browser_begin(client)
    cost.browser_finish(client,status="send_uncertain")
    assert len(records(account))==1
    assert records(account)[0]["output_tokens"] is None
    assert records(account)[0]["status"]=="send_uncertain"


def test_fallback_retry_grouping_is_idempotent_and_counts_requests(account):
    logical="safe-group"
    first=cost.begin(model="gemini-3.8-flash-lite-tts",purpose="tts",
                     transport="api",input_text="A",logical_id=logical,retry_count=0)
    cost.finish(first,failure=TimeoutError("uncertain"))
    second=cost.begin(model="gemini-3.8-flash-lite-tts",purpose="tts",
                      transport="api",input_text="A",logical_id=logical,retry_count=1)
    cost.finish(second,response=fake_response(40,100))
    rows=records(account)
    assert [r["retry_count"] for r in rows]==[0,1]
    assert len({r["logical_id"] for r in rows})==1
    assert cost.summary()["requests"]==2
    assert cost.summary()["captured_api_cost_estimate_usd"]==pytest.approx((40*.5+100*6)/1_000_000)
    with pytest.raises(sqlite3.IntegrityError):
        cost.begin(model="gemini-3.8-flash-lite-tts",purpose="tts",
                   transport="api",input_text="A",logical_id=logical,retry_count=1)


def test_provider_thinking_tokens_included_in_output_cost(account):
    ident=cost.begin(model="gemini-3.8-flash",purpose="tts_qa",
                     transport="api",input_text="Listen")
    cost.finish(ident,response=fake_response(200,100,50))
    row=records(account)[0]
    assert row["output_tokens"]==150
    assert row["estimated_usd_cost"]==pytest.approx((200*.75+150*3.75)/1_000_000)


def test_unknown_model_never_guesses_usd(account):
    ident=cost.begin(model="new-unknown-model",purpose="tts",
                     transport="api",input_text="Speak")
    cost.finish(ident,response=fake_response())
    row=records(account)[0]
    assert row["estimated_usd_cost"] is None
    assert "unknown model" in row["billing_note"]


def test_no_raw_prompts_keys_or_audio_saved(account,monkeypatch):
    secret="SECRET_MUST_NEVER_APPEAR_IN_DB_1234"
    monkeypatch.setenv("GEMINI_API_KEY_1","PRIVATE_API_KEY_ABC123")
    ident=cost.begin(model="gemini-3.8-flash-lite-tts",purpose="tts",
                     transport="api",input_text=secret)
    cost.finish(ident,response=fake_response())
    all_text=" ".join(str(v) for row in records(account) for v in row.values())
    assert secret not in all_text
    assert "PRIVATE_API_KEY_ABC123" not in all_text
    assert not any("source.pdf" in str(v) for row in records(account) for v in row.values())


def test_export_csv_summary_are_reproducible(account,tmp_path):
    ident=cost.begin(model="gemini-3.8-flash-lite-tts",
                     purpose="tts",transport="api",input_text="hello")
    cost.finish(ident,response=fake_response(200,300))
    target=tmp_path/"ledger.csv"
    assert cost.export_csv(target)==1
    with target.open(encoding="utf8",newline="") as stream:
        rows=list(csv.DictReader(stream))
    assert rows[0]["chapter"]=="8"
    assert rows[0]["subsection"]=="8.2"
    assert rows[0]["purpose"]=="tts"
    assert float(rows[0]["estimated_usd_cost"])>0
    summary=cost.summary()
    assert summary["groups"][0]["requests"]==1
    assert "not invoiced" in summary["warning"]


def test_concurrent_requests_have_no_lost_or_duplicate_rows(account):
    def work(n):
        request=cost.begin(model="gemini-3.8-flash-lite-tts",
                           purpose="tts",transport="api",input_text=f"Slide {n}")
        cost.finish(request,response=fake_response(n+1,n+2))
        return request
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids=list(pool.map(work,range(32)))
    assert len(set(ids))==32
    assert len(records(account))==32


def test_api_metering_intercepts_sdk_response_and_failure(account):
    class Models:
        def generate_content(self,**kwargs):
            if kwargs["contents"]=="fail":
                raise TimeoutError("provider unconfirmed")
            return fake_response(22,33)
    client=SimpleNamespace(models=Models())
    wrapped=cost.MeteredGeminiClient(client,purpose="tts",
                                    logical_id="this-run",attempt=0)
    reply=wrapped.models.generate_content(model="gemini-3.8-flash-lite-tts",contents="ok")
    assert reply.usage_metadata.prompt_token_count==22
    assert len(records(account))==1
    assert records(account)[0]["status"]=="response_captured"
    retry=cost.MeteredGeminiClient(client,purpose="tts",
                                  logical_id="this-run",attempt=1)
    with pytest.raises(TimeoutError):
        retry.models.generate_content(model="gemini-3.8-flash-lite-tts",contents="fail")
    assert len(records(account))==2
    assert records(account)[1]["status"]=="send_uncertain"


def test_ledger_fails_closed_without_database_before_paid_request(tmp_path,monkeypatch):
    target=tmp_path/"blocker"
    target.write_text("not a folder")
    monkeypatch.setenv("MICROGEN_GEMINI_COST_LEDGER_PATH",str(target/"bad.sqlite3"))
    class Models:
        def generate_content(self,**kwargs):
            pytest.fail("Billing could have happened without an audit row")
    wrapped=cost.MeteredGeminiClient(SimpleNamespace(models=Models()),
                                    purpose="tts",logical_id="x",attempt=0)
    with pytest.raises((OSError,sqlite3.OperationalError)):
        wrapped.models.generate_content(model="gemini-3.8-flash-lite-tts",contents="hello")


def test_subsection_inferred_from_workfolder(account,tmp_path,monkeypatch):
    folder=tmp_path/"10"/"10.7"
    folder.mkdir(parents=True)
    cost.set_job_context(folder)
    ident=cost.begin(model="gemini-3.8-flash",purpose="scientific_review",
                     transport="selenium",input_text="Review physics")
    row=records(account)[0]
    assert row["chapter"]=="10"
    assert row["subsection"]=="10.7"


def test_same_browser_prompt_retries_share_logical_id(account,monkeypatch):
    monkeypatch.setenv("MICROGEN_LLM_MODEL","gemini-3.8-flash")
    client=SimpleNamespace(_microgen_cost_prompt_text="Check source only")
    cost.browser_begin(client)
    cost.browser_finish(client,status="send_uncertain")
    cost.browser_begin(client)
    cost.browser_finish(client,response_text="Recovered from a new claimed attempt")
    rows=records(account)
    assert [v["retry_count"] for v in rows]==[0,1]
    assert [v["attempt_number"] for v in rows]==[1,2]
    assert rows[0]["logical_id"]==rows[1]["logical_id"]


def test_audio_fallback_uses_duration_when_provider_usage_missing(account):
    # 2 seconds of mono 24-kHz 16-bit PCM = 96,000 bytes = about 50 tokens.
    audio=SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(
        parts=[SimpleNamespace(inline_data=SimpleNamespace(data=b"\0"*96000))]))])
    request=cost.begin(model="gemini-3.8-flash-lite-tts",
                       purpose="tts",transport="api",input_text="Speak hello")
    cost.finish(request,response=audio)
    row=records(account)[0]
    assert row["output_tokens"]==50
    assert row["output_token_source"]=="estimated_audio_duration_25_tokens_per_sec"
    assert row["estimated_usd_cost"]>0


def test_explicit_logical_id_resumes_after_crashed_child(account,monkeypatch):
    import gemini_keys
    logical="same-parent-tts-attempt"
    monkeypatch.setenv("MICROGEN_GEMINI_REQUEST_LOGICAL_ID",logical)
    class Models:
        def __init__(self,fail):
            self.fail=fail
        def generate_content(self,**kwargs):
            if self.fail:
                raise TimeoutError("worker watchdog")
            return fake_response(27,400)
    with patch("gemini_keys.assert_gemini_available"),patch(
        "gemini_keys.get_gemini_api_keys",return_value=["MOCK_NOT_REAL"]),patch(
        "gemini_keys._env_int",return_value=1),patch(
        "gemini_keys.time.sleep",return_value=None):
        with pytest.raises(TimeoutError):
            gemini_keys.call_with_client_failover(
                lambda key:SimpleNamespace(models=Models(True)),
                lambda client:client.models.generate_content(
                    model="gemini-3.8-flash-lite-tts",contents="one"),
                purpose="tts",max_retries=0)
        assert cost.next_attempt_index(logical)==1
        reply=gemini_keys.call_with_client_failover(
            lambda key:SimpleNamespace(models=Models(False)),
            lambda client:client.models.generate_content(
                model="gemini-3.8-flash-lite-tts",contents="two"),
            purpose="tts",max_retries=0)
    assert reply.usage_metadata.prompt_token_count==27
    rows=records(account)
    assert len(rows)==2
    assert [r["retry_count"] for r in rows]==[0,1]
    assert rows[0]["logical_id"]==logical==rows[1]["logical_id"]


def test_inactive_accounting_registry_blocks_send(account,monkeypatch,tmp_path):
    from selenium_pipeline import recovery_registry
    existing=json.loads(recovery_registry.REGISTRY_PATH.read_text(encoding="utf8"))
    entry=next(x for x in existing["entries"]
        if x["signature"]=="GEMINI_REQUEST_COST_SQLITE_V1")
    entry["enabled"]=False
    invalid=tmp_path/"disabled_registry.json"
    invalid.write_text(json.dumps(existing),encoding="utf8")
    monkeypatch.setattr(recovery_registry,"REGISTRY_PATH",invalid)
    class FakeModels:
        def generate_content(self,**kwargs):
            pytest.fail("A model Send escaped a disabled accounting registry")
    proxy=cost.MeteredGeminiClient(
        SimpleNamespace(models=FakeModels()),
        purpose="tts",logical_id="disabled",attempt=0)
    with pytest.raises(RuntimeError,match="GEMINI_ACCOUNTING_REGISTRY_INVALID_NO_SEND"):
        proxy.models.generate_content(
            model="gemini-3.8-flash-lite-tts",contents="hello")
