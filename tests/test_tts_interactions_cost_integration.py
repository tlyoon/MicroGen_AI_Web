"""Regression: registered TTS SDK recovery and metered Gemini 3.8 Interactions."""
import base64
import io
import sqlite3
import wave
from types import SimpleNamespace

import pytest

from selenium_pipeline import gemini38_tts_interactions as interaction
from selenium_pipeline import tts
from selenium_pipeline.gemini_request_cost import MeteredGeminiClient


def _wav():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(24000)
        out.writeframes(b"\0\0" * 24000)
    return stream.getvalue()


class FakeInteractions:
    def __init__(self, response=None, error=None):
        self.calls = 0
        self.response = response
        self.error = error
        self.last = None

    def create(self, **request):
        self.calls += 1
        self.last = request
        if self.error is not None:
            raise self.error
        return self.response


def _client(api):
    return MeteredGeminiClient(
        SimpleNamespace(interactions=api), purpose="tts",
        logical_id="source-bound-test", attempt=0,
    )


def _rows(db):
    if not db.exists():
        return []
    with sqlite3.connect(db) as con:
        return con.execute(
            "SELECT purpose, model, chapter, subsection, status, "
            "input_tokens, output_tokens, output_token_source, retry_count "
            "FROM gemini_requests"
        ).fetchall()


@pytest.fixture()
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "requests.sqlite3"
    monkeypatch.setenv("MICROGEN_GEMINI_COST_LEDGER_PATH", str(path))
    monkeypatch.setenv("MICROGEN_ACTIVE_GENERATION_STAGE", "tts")
    monkeypatch.setenv("MICROGEN_CHAPTER", "8")
    monkeypatch.setenv("MICROGEN_SUBSECTION", "8.2")
    return path


def test_interactions_is_metered_with_provider_usage(ledger, monkeypatch):
    monkeypatch.setattr(interaction, "require_modern_tts_sdk", lambda: "2.29.0")
    wav = _wav()
    response = SimpleNamespace(
        output_audio=SimpleNamespace(
            data=base64.b64encode(wav).decode("ascii"), mime_type="audio/wav"),
        usage=SimpleNamespace(input_tokens=13, output_tokens=41),
    )
    api = FakeInteractions(response)
    assert tts._gemini_say(_client(api), "Physics and energy.",
                           "gemini-3.8-flash-lite-tts", "Kore") == wav
    assert api.calls == 1
    assert api.last["input"][0]["content"][0]["text"] == "Physics and energy."
    assert _rows(ledger) == [(
        "tts", "gemini-3.8-flash-lite-tts", "8", "8.2",
        "response_captured", 13, 41, "provider_reported_including_thinking", 0)]


def test_interactions_audio_duration_is_estimated_when_usage_absent(ledger, monkeypatch):
    monkeypatch.setattr(interaction, "require_modern_tts_sdk", lambda: "2.29.0")
    wav = _wav()
    response = SimpleNamespace(
        output_audio=SimpleNamespace(
            data=base64.b64encode(wav), mime_type="audio/wav"),
        usage=None,
    )
    assert tts._gemini_say(
        _client(FakeInteractions(response)), "Conservation of energy.",
        "gemini-3.8-flash-lite-tts", "Kore") == wav
    row = _rows(ledger)[0]
    assert row[4] == "response_captured"
    assert row[6] == 25
    assert row[7] == "estimated_audio_duration_25_tokens_per_sec"


def test_incompatible_sdk_blocks_before_ledger_or_http(ledger, monkeypatch):
    def refuse():
        raise interaction.InteractionsTTSCompatError("SDK 1.4 lacks Interactions")
    monkeypatch.setattr(interaction, "require_modern_tts_sdk", refuse)
    api = FakeInteractions()
    with pytest.raises(interaction.InteractionsTTSCompatError):
        tts._gemini_say(_client(api), "One source sentence.",
                        "gemini-3.8-flash-lite-tts", "Kore")
    assert api.calls == 0
    assert _rows(ledger) == []


def test_unapproved_qa_or_scientific_api_denied_without_send(ledger):
    api = FakeInteractions()
    disallowed = MeteredGeminiClient(
        SimpleNamespace(interactions=api), purpose="scientific_review",
        logical_id="not-authorized", attempt=0,
    )
    req = interaction.canonical_single_speaker_3_8_request(
        text="One source sentence.", model="gemini-3.8-flash-lite-tts",
        voice="Kore")
    with pytest.raises(Exception, match="PAID_GEMINI_API_CONTENT_FORBIDDEN"):
        disallowed.interactions.create(**req)
    assert api.calls == 0
    assert _rows(ledger) == []


def test_uncertain_provider_exception_remains_uncertain(ledger, monkeypatch):
    monkeypatch.setattr(interaction, "require_modern_tts_sdk", lambda: "2.29.0")
    api = FakeInteractions(error=TimeoutError("provider returned no response"))
    with pytest.raises(TimeoutError):
        tts._gemini_say(_client(api), "One source sentence.",
                        "gemini-3.8-flash-lite-tts", "Kore")
    assert api.calls == 1
    rows = _rows(ledger)
    assert len(rows) == 1
    assert rows[0][4] == "send_uncertain"


def test_incompatible_worker_registry_denial_is_fail_closed(monkeypatch):
    def refuse():
        raise interaction.InteractionsTTSCompatError("SDK obsolete")
    monkeypatch.setattr(interaction, "require_modern_tts_sdk", refuse)
    from selenium_pipeline import recovery_registry
    monkeypatch.setattr(recovery_registry, "lookup_mechanism",
                        lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="REGISTRY_MISSING_NO_SEND"):
        tts._verified_tts_worker_python()
