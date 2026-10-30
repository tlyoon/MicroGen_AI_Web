import sys
import tempfile
import os
import io
import json
import wave
import subprocess
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline.tts import (
    _configure_cloud_adc_from_microvid, _fallback_specs,
    _gemini_say_with_watchdog, _merge_wav_payloads, _split_tts_text,
    _tts_timeout_seconds, _tts_workspace_lock, synthesize_folder,
    TTSFallbackModelExhausted,
)

WAV = b"RIFF" + b"X" * 80


def response(data):
    return SimpleNamespace(candidates=[SimpleNamespace(
        content=SimpleNamespace(parts=[SimpleNamespace(
            inline_data=SimpleNamespace(data=data))]))])


class FakeModels:
    def __init__(self, fail_at=0):
        self.requests = []
        self.fail_at = fail_at

    def generate_content(self, **kwargs):
        self.requests.append(kwargs)
        if len(self.requests) == self.fail_at:
            raise RuntimeError("temporary API error")
        return response(WAV)


def fake_gemini_keys_module(models=None, keys=None):
    module = types.ModuleType("gemini_keys")
    module.get_gemini_api_keys = lambda: list(["TEST_NOT_REAL"] if keys is None else keys)
    module.create_gemini_client = lambda api_key: SimpleNamespace(models=models)

    def call_with_client_failover(client_factory, operation, **_kwargs):
        client = client_factory("TEST_NOT_REAL")
        return operation(client)

    module.call_with_client_failover = call_with_client_failover
    return module


def seed_reviewable_candidates(folder, slide_numbers):
    """Populate old in-progress cache with exact model/text/WAV proof."""
    import hashlib
    from selenium_pipeline.runner import blocks
    from selenium_pipeline.tts_candidate_integrity import (
        job_identity, prepare, record_one,
    )
    script=(folder / "script.txt").read_bytes()
    identity=job_identity(blocks(script.decode("utf-8")),
                          provider="gemini",model="gemini-3.8-flash-lite-tts",
                          voice="Kore",script_sha256=hashlib.sha256(script).hexdigest())
    candidate=folder / ".tts_candidate"
    candidate.mkdir()
    prepare(candidate,identity)
    for number in slide_numbers:
        name=f"slide{number}.wav"
        (candidate / name).write_bytes(WAV)
        record_one(candidate,name,identity)
    return candidate


class TTSTests(unittest.TestCase):
    def setUp(self):
        # These historical queue/failover tests use an intentionally minimal
        # generate_content FAKE and an intentionally nondecodable 84-byte WAV.
        # Do not send fake payloads through the REAL Gemini 3.8 Interactions
        # adapter (which correctly requires output_audio and valid PCM).
        # API request formatting/WAV decoding are tested independently in
        # tests.test_gemini38_tts_interactions_sdk.
        def synthetic_legacy_tts(client,text,model,voice,*,
                                 request_observation=None):
            response=client.models.generate_content(
                model=model,contents=[text])
            if request_observation is not None:
                request_observation["provider_request_id"]=None
            return response.candidates[0].content.parts[0].inline_data.data
        self._legacy_test_only_tts=patch(
            "selenium_pipeline.gemini38_tts_interactions.generate_3_8_kore_wav",
            side_effect=synthetic_legacy_tts)
        self._legacy_test_only_tts.start()
        self.addCleanup(self._legacy_test_only_tts.stop)

    def make_folder(self, root):
        folder = Path(root)
        (folder / "script.txt").write_text(
            "**Slide 1 [3 sec]:\nIntroduction**\n\n"
            "**Slide 2 [10 sec]:\nElectric flux is proportional to charge.**",
            encoding="utf-8")
        return folder

    def test_gemini_lite_publishes_complete_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            models = FakeModels()
            fake = fake_gemini_keys_module(models=models)
            with patch.dict(sys.modules, {"gemini_keys": fake}):
                synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")
            self.assertEqual((folder / "slide1.wav").read_bytes(), WAV)
            self.assertEqual((folder / "slide2.wav").read_bytes(), WAV)
            self.assertFalse((folder / ".tts_candidate").exists())
            self.assertFalse((folder / ".tts.lock").exists())
            manifest = json.loads((folder / "tts_input_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["slides"][1]["tts_text"], "Electric flux is proportional to charge.")
            self.assertEqual(models.requests[0]["model"], "gemini-3.8-flash-lite-tts")

    def test_failure_does_not_destroy_previous_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            (folder / "slide1.wav").write_bytes(b"RIFF" + b"A" * 60)
            models = FakeModels(fail_at=2)
            fake = fake_gemini_keys_module(models=models)
            with patch.dict(sys.modules, {"gemini_keys": fake}), patch.dict(
                os.environ,
                {
                    "MICROGEN_TTS_QUEUE_ROUNDS": "1",
                    "MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK": "0",
                    "MICROGEN_TTS_ENABLE_BATCH_FALLBACK": "0",
                },
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "Existing final TTS outputs require reviewed reconciliation"
                ):
                    synthesize_folder(folder, "gemini", "gemini-3.8-flash-tts", "Kore")
            self.assertEqual(len(models.requests), 0, "Must block before a paid API call")
            self.assertEqual((folder / "slide1.wav").read_bytes(), b"RIFF" + b"A" * 60)
            self.assertFalse((folder / "slide2.wav").exists())
            self.assertFalse((folder / ".tts_candidate").exists())
            self.assertFalse((folder / ".tts.lock").exists())

    def test_transient_failure_is_deferred_while_later_slide_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            models = FakeModels(fail_at=1)
            fake = fake_gemini_keys_module(models=models)
            with patch.dict(sys.modules, {"gemini_keys": fake}), patch.dict(
                os.environ,
                {
                    "MICROGEN_TTS_QUEUE_ROUNDS": "2",
                    "MICROGEN_TTS_QUEUE_DELAY_SECONDS": "0",
                },
            ):
                synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")
            self.assertEqual(len(models.requests), 3)
            self.assertTrue((folder / "slide1.wav").is_file())
            self.assertTrue((folder / "slide2.wav").is_file())

    def test_queue_exhaustion_preserves_successful_candidates(self):
        class AlwaysFailModels:
            def __init__(self):
                self.requests = 0

            def generate_content(self, **_kwargs):
                self.requests += 1
                raise RuntimeError("503 high demand")

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "script.txt").write_text(
                "**Slide 1 [3 sec]:\nOne**\n\n"
                "**Slide 2 [3 sec]:\nTwo**\n\n"
                "**Slide 3 [3 sec]:\nThree**",
                encoding="utf-8",
            )
            models = AlwaysFailModels()
            fake = fake_gemini_keys_module(models=models)
            with patch.dict(sys.modules, {"gemini_keys": fake}), patch.dict(
                os.environ,
                {
                    "MICROGEN_TTS_QUEUE_ROUNDS": "2",
                    "MICROGEN_TTS_QUEUE_DELAY_SECONDS": "0",
                    "MICROGEN_TTS_QUEUE_CIRCUIT_BREAKER_FAILURES": "2",
                    "MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK": "0",
                    "MICROGEN_TTS_ENABLE_BATCH_FALLBACK": "0",
                },
            ):
                with self.assertRaisesRegex(RuntimeError, r"queue.*exhausted"):
                    synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")
            # Each of three genuine rounds stops after two consecutive
            # transient failures. The never-submitted third slide must NOT
            # be counted as an actual attempted provider request.
            self.assertEqual(models.requests, 6)
            self.assertTrue((folder / ".tts_candidate").is_dir())
            self.assertFalse((folder / ".tts.lock").exists())

    def test_flash_lite_three_attempts_then_single_voice_flash_fallback(self):
        """Standing policy permits Flash only after a three-round Lite outage."""
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/"script.txt").write_text(
                "**Slide 1 [3 sec]:\nFallback title**\n\n"
                "**Slide 2 [3 sec]:\nReference two**\n\n"
                "**Slide 3 [3 sec]:\nReference three**",encoding="utf-8")
            candidate=seed_reviewable_candidates(folder,[2,3])
            class Fails:
                def __init__(self): self.calls=0
                def generate_content(self,**kwargs):
                    self.calls+=1
                    raise RuntimeError("503 high demand")
            models=Fails()
            fake=fake_gemini_keys_module(models=models)
            with patch.dict(sys.modules,{"gemini_keys":fake}), patch.dict(
                os.environ,{
                    "MICROGEN_TTS_QUEUE_ROUNDS":"1",
                    "MICROGEN_TTS_QUEUE_DELAY_SECONDS":"0",
                    "MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK":"1",
                    "MICROGEN_TTS_ENABLE_BATCH_FALLBACK":"1",
                }),patch("selenium_pipeline.tts._whole_batch_fallback") as batch, \
                patch("selenium_pipeline.tts._fallback_payload") as per_slide:
                synthesize_folder(folder,"gemini","gemini-3.8-flash-lite-tts","Kore")
                self.assertEqual(models.calls,3)
                batch.assert_called_once()
                self.assertEqual(batch.call_args.args[2]["model"],"gemini-3.8-flash-tts")
                self.assertEqual(batch.call_args.kwargs["completed_gemini_models"],
                                 ("gemini-3.8-flash-lite-tts",))
                per_slide.assert_not_called()
            self.assertFalse((folder/"slide1.wav").exists())
            self.assertEqual((candidate/"slide2.wav").read_bytes(),WAV)
            self.assertEqual((candidate/"slide3.wav").read_bytes(),WAV)

    def test_microvid_cloud_credentials_are_auto_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp)
            config = local / "Microvid"
            config.mkdir()
            credential = config / ("google_cloud_" + "credentials.json")
            credential.write_text("{}", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"LOCALAPPDATA": str(local)},
                clear=False,
            ):
                os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
                found = _configure_cloud_adc_from_microvid()
                self.assertEqual(found, credential)
                self.assertEqual(
                    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
                    str(credential),
                )
                os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

    def test_explicit_cloud_credentials_are_not_overridden(self):
        with tempfile.TemporaryDirectory() as tmp:
            explicit = Path(tmp) / "explicit.json"
            explicit.write_text("{}", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"GOOGLE_APPLICATION_CREDENTIALS": str(explicit)},
                clear=False,
            ):
                found = _configure_cloud_adc_from_microvid()
                self.assertEqual(found, explicit)
                self.assertEqual(
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
                    str(explicit),
                )

    def test_approved_fallback_model_order_is_explicit(self):
        lite=_fallback_specs("gemini","gemini-3.8-flash-lite-tts","Kore")
        self.assertEqual([(x["provider"],x["model"]) for x in lite],
            [("gemini","gemini-3.8-flash-tts"),("chirp3","chirp3-hd")])
        self.assertEqual(lite[0]["voice"],"Kore")
        self.assertEqual(lite[1]["voice"],"en-US-Chirp3-HD-Kore")
        self.assertEqual(_fallback_specs("chirp3","chirp3-hd","Corey"),[])

    def test_cloud_only_after_failed_flash_batch(self):
        """Never mix primary/Kore and Cloud/Chirp-Kore clips in a lecture."""
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/"script.txt").write_text(
                "**Slide 1 [3 sec]:\nFallback title**\n\n"
                "**Slide 2 [3 sec]:\nReference two**\n\n"
                "**Slide 3 [3 sec]:\nReference three**",encoding="utf-8")
            candidate=seed_reviewable_candidates(folder,[2,3])
            class Fails:
                def generate_content(self,**kwargs):
                    raise RuntimeError("503 high demand")
            seen=[]
            def fallback(target,items,spec,**kwargs):
                seen.append((spec["provider"],spec["model"],
                             kwargs["completed_gemini_models"]))
                raise TTSFallbackModelExhausted("503 retry queue exhausted")
            fake=fake_gemini_keys_module(models=Fails())
            with patch.dict(sys.modules,{"gemini_keys":fake}),patch.dict(
                os.environ,{"MICROGEN_TTS_QUEUE_ROUNDS":"3",
                            "MICROGEN_TTS_QUEUE_DELAY_SECONDS":"0",
                            "MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK":"1",
                            "MICROGEN_TTS_ENABLE_BATCH_FALLBACK":"1"}), \
                patch("selenium_pipeline.tts._whole_batch_fallback",
                      side_effect=fallback):
                with self.assertRaisesRegex(RuntimeError,"fallback exhausted"):
                    synthesize_folder(folder,"gemini","gemini-3.8-flash-lite-tts","Kore")
            self.assertEqual(seen,[
                ("gemini","gemini-3.8-flash-tts",
                 ("gemini-3.8-flash-lite-tts",)),
                ("chirp3","chirp3-hd",
                 ("gemini-3.8-flash-lite-tts","gemini-3.8-flash-tts"))])
            self.assertEqual((candidate/"slide2.wav").read_bytes(),WAV)
            self.assertEqual((candidate/"slide3.wav").read_bytes(),WAV)
            self.assertFalse((folder/"slide1.wav").exists())

    def test_direct_tts_blocks_ambiguous_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "script.txt").write_text(
                "**Slide 1 [3 sec]:\nSafe title**\n\n"
                "**Slide 2 [10 sec]:\nWe use A torsion balance here.**",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "TTS-ambiguous"):
                synthesize_folder(
                    folder,
                    "gemini",
                    "gemini-3.8-flash-lite-tts",
                    "Kore",
                )
            self.assertFalse((folder / ".tts.lock").exists())

    def test_no_secret_blocks_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            fake = fake_gemini_keys_module(models=FakeModels(), keys=[])
            with patch.dict(sys.modules, {"gemini_keys": fake}):
                with self.assertRaises(EnvironmentError):
                    synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")
            self.assertFalse((folder / ".tts.lock").exists())

    def test_second_live_writer_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with _tts_workspace_lock(folder):
                with self.assertRaisesRegex(RuntimeError, "already active"):
                    with _tts_workspace_lock(folder):
                        pass
            self.assertFalse((folder / ".tts.lock").exists())



    def test_adaptive_timeout_scales_with_narration_length(self):
        with patch.dict(os.environ, {}, clear=False):
            for key in (
                "MICROGEN_TTS_HARD_TIMEOUT_SECONDS",
                "MICROGEN_TTS_TIMEOUT_BASE_SECONDS",
                "MICROGEN_TTS_TIMEOUT_PER_100_CHARS_SECONDS",
                "MICROGEN_TTS_TIMEOUT_MAX_SECONDS",
            ):
                os.environ.pop(key, None)
            self.assertEqual(_tts_timeout_seconds("x" * 900), 225.0)
            self.assertEqual(_tts_timeout_seconds("x" * 100), 105.0)

    def test_explicit_timeout_override_is_preserved(self):
        with patch.dict(os.environ, {"MICROGEN_TTS_HARD_TIMEOUT_SECONDS": "240"}):
            self.assertEqual(_tts_timeout_seconds("x" * 900), 240.0)

    def test_sentence_aware_chunking(self):
        text = (
            "First sentence is short. "
            "Second sentence is somewhat longer but should remain intact. "
            "Third sentence finishes the narration."
        )
        chunks = _split_tts_text(text, max_chars=70)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(" ".join(chunks), text)

    def test_merge_wav_payloads_concatenates_pcm_frames(self):
        def make_wav(frames):
            out = io.BytesIO()
            with wave.open(out, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(24000)
                wav.writeframes(frames)
            return out.getvalue()

        merged = _merge_wav_payloads([make_wav(b"\x01\x00" * 4), make_wav(b"\x02\x00" * 3)])
        with wave.open(io.BytesIO(merged), "rb") as wav:
            self.assertEqual(wav.getnframes(), 7)
            self.assertEqual(wav.getframerate(), 24000)

    def test_watchdog_retries_and_times_out(self):
        timeout = subprocess.TimeoutExpired(cmd=["python"], timeout=10)
        with patch.dict(os.environ, {
            "MICROGEN_TTS_HARD_TIMEOUT_SECONDS": "10",
            "MICROGEN_TTS_REQUEST_ATTEMPTS": "2",
        }):
            with patch("selenium_pipeline.tts.subprocess.run", side_effect=timeout) as run:
                with self.assertRaises(TimeoutError):
                    _gemini_say_with_watchdog("hello", 7, "gemini-3.8-flash-lite-tts", "Kore")
                self.assertEqual(run.call_count, 2)

    def test_stale_lock_is_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / ".tts.lock").write_text("999999999\n", encoding="utf-8")
            with _tts_workspace_lock(folder):
                self.assertTrue((folder / ".tts.lock").exists())
            self.assertFalse((folder / ".tts.lock").exists())


if __name__ == "__main__":
    unittest.main()
