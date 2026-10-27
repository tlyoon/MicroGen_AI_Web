"""Google 3.8 TTS Interactions API: ZERO billable calls in this test suite."""
from __future__ import annotations
import base64
from io import BytesIO
import unittest
from unittest.mock import patch
import wave

from selenium_pipeline.gemini38_tts_interactions import (
    InteractionsTTSCompatError,
    canonical_single_speaker_3_8_request,
    generate_3_8_kore_wav,
    require_modern_tts_sdk,
)


class FakeAudio:
    def __init__(self,data):
        self.data=data
        self.mime_type="audio/pcm;rate=24000"


class FakeInteraction:
    def __init__(self,data):
        self.output_audio=FakeAudio(data)


class FakeInteractions:
    def __init__(self,data):
        self.data=data
        self.calls=[]
    def create(self,**kwargs):
        self.calls.append(kwargs)
        return FakeInteraction(self.data)


class FakeClient:
    def __init__(self,data):
        self.interactions=FakeInteractions(data)
        self.models=None  # Must NEVER call legacy generate_content


class Gemini38TTSCompatibility(unittest.TestCase):
    def test_legacy_sdk_fails_before_network(self):
        with patch("selenium_pipeline.gemini38_tts_interactions.version",
                   return_value="1.4.0"):
            with self.assertRaisesRegex(
                    InteractionsTTSCompatError,"requires google-genai"):
                require_modern_tts_sdk()
            client=FakeClient(base64.b64encode(b"\x00\x00"*24000).decode())
            with self.assertRaises(InteractionsTTSCompatError):
                generate_3_8_kore_wav(
                    client,"One exact original utterance.",
                    "gemini-3.8-flash-lite-tts","Kore")
            self.assertEqual(client.interactions.calls,[])

    def test_exact_source_text_and_one_Kore_voice(self):
        text="For x equals a tangent u, a is positive."
        request=canonical_single_speaker_3_8_request(
            text=text,model="gemini-3.8-flash-lite-tts",voice="Kore")
        self.assertEqual(request["input"],[{"type":"user_input",
            "content":[{"type":"text","text":text}]}])
        self.assertEqual(request["response_format"],{"type":"audio"})
        self.assertEqual(request["generation_config"],
                         {"speech_config":[{"voice":"Kore"}]})
        self.assertEqual(set(request),
                         {"model","input","response_format","generation_config"})

    def test_voice_and_model_changes_fail_closed(self):
        for model,voice in (("gemini-3.8-flash-lite-tts","Corey"),
                            ("gemini-2.5-flash-tts","Kore")):
            with self.subTest(model=model,voice=voice):
                with self.assertRaises(InteractionsTTSCompatError):
                    canonical_single_speaker_3_8_request(
                        text="Exact text.",model=model,voice=voice)
        with self.assertRaises(InteractionsTTSCompatError):
            canonical_single_speaker_3_8_request(
                text=" Truncated? ",model="gemini-3.8-flash-lite-tts",
                voice="Kore")

    def test_interactions_base64_PCM_produces_valid_real_WAV(self):
        frames=24000
        real_pcm=b"\x18\x0f" * frames
        client=FakeClient(base64.b64encode(real_pcm).decode())
        observation={}
        with patch("selenium_pipeline.gemini38_tts_interactions.require_modern_tts_sdk",
                   return_value="2.33.0"):
            payload=generate_3_8_kore_wav(
                client,"Text unchanged.","gemini-3.8-flash-lite-tts","Kore",
                request_observation=observation)
        self.assertTrue(payload.startswith(b"RIFF"))
        self.assertEqual(len(client.interactions.calls),1)
        self.assertEqual(client.interactions.calls[0]["input"],[
            {"type":"user_input","content":[{"type":"text","text":"Text unchanged."}]}])
        self.assertEqual(observation["provider_request_id"],None)
        with wave.open(BytesIO(payload),"rb") as r:
            self.assertEqual(r.getnframes(),frames)
            self.assertEqual(r.getframerate(),24000)
            self.assertEqual(r.getnchannels(),1)
            self.assertEqual(r.getsampwidth(),2)
            self.assertEqual(r.readframes(frames),real_pcm)

    def test_invalid_audio_return_is_not_approved(self):
        client=FakeClient("abc?")
        with patch("selenium_pipeline.gemini38_tts_interactions.require_modern_tts_sdk",
                   return_value="2.33.0"):
            with self.assertRaises(InteractionsTTSCompatError):
                generate_3_8_kore_wav(
                    client,"Text.","gemini-3.8-flash-lite-tts","Kore")

    def test_existing_tts_adapter_routes_to_interactions_only(self):
        from selenium_pipeline.tts import _gemini_say
        with patch("selenium_pipeline.gemini38_tts_interactions.generate_3_8_kore_wav",
                   return_value=b"test_wav") as method:
            actual=_gemini_say(object(),"verbatim","gemini-3.8-flash-lite-tts",
                               "Kore")
        self.assertEqual(actual,b"test_wav")
        self.assertEqual(method.call_count,1)


if __name__=="__main__":
    unittest.main()
