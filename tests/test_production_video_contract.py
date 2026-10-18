"""Strict MicroGen contract: no silent >600s or static unhighlighted success."""
from __future__ import annotations
import copy
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path

from selenium_pipeline.production_video_contract import VideoContractError, verify_series


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf8")


class ContractAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/"source.pdf").write_bytes(b"Immutable synthetic source PDF fixture")
        self.part = self.root/"part_01"
        self.part.mkdir()
        self.media = self.part/"part_01.mp4"
        self.media.write_bytes(b"Mock MP4 bytes; real production probes FFmpeg")
        self.audio = self.part/"narration.wav"
        self.seconds=98
        with wave.open(str(self.audio), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\0\0" * (8000*self.seconds))
        self.events=[
            {"slide_id":"slide_01","target_id":"equation_1","start_ms":1000,"end_ms":42000},
            {"slide_id":"slide_01","target_id":"diagram_1","start_ms":44000,"end_ms":90000},
        ]
        self.cues={"status":"approved_audio_timed_visual_cues",
                   "audio_sha256":sha(self.audio),
                   "events":copy.deepcopy(self.events)}
        self.alignment={"status":"verified_final_audio_alignment",
                   "audio_sha256":sha(self.audio),"duration_ms":98000,
                   "events":copy.deepcopy(self.events)}
        data(self.part/"visual_cues.json", self.cues)
        data(self.part/"narration_alignment.json", self.alignment)
        self.receipt={"schema_version":1,"part_id":"part_01",
                      "status":"accepted_synchronized_part",
                      "renderer":"audio_timed_highlight_renderer","unverified":[],
                      "mp4_sha256":sha(self.media),"audio_sha256":sha(self.audio),
                      "visual_cues_sha256":sha(self.part/"visual_cues.json"),
                      "alignment_sha256":sha(self.part/"narration_alignment.json"),
                      "duration_s":98.0,
                      "encoded_transition_qa":{"verified_transition_count":3,
                                               "max_encoded_frame_drift_s":0.08}}
        self.put_receipt()
        self.manifest={"schema_version":1,"status":"accepted_synchronized_series",
                       "source_sha256":sha(self.root/"source.pdf"),
                       "parts":[{"part_id":"part_01",
                                 "receipt_sha256":sha(self.part/"part_receipt.json")}]}
        self.put_manifest()

    def put_receipt(self):
        data(self.part/"part_receipt.json",self.receipt)

    def put_manifest(self):
        self.manifest["parts"][0]["receipt_sha256"]=sha(self.part/"part_receipt.json")
        data(self.root/"lecture_completion.json",self.manifest)

    def accept(self, seconds=98.0):
        return verify_series(self.root,probe=lambda _path:seconds)

    def test_valid_real_audio_binding_and_highlight_receipt_pass(self):
        outcome=self.accept()
        self.assertEqual(outcome["status"],"accepted_synchronized_series")
        self.assertEqual(outcome["parts"][0]["highlight_events"],2)

    def test_legacy_static_video_cannot_pass_without_series_receipt(self):
        (self.root/"lecture_completion.json").unlink()
        with self.assertRaisesRegex(VideoContractError,"Required receipt missing"):
            self.accept()

    def test_exactly_ten_minutes_rejected(self):
        with self.assertRaisesRegex(VideoContractError,"strict <600"):
            self.accept(seconds=600)

    def test_more_than_ten_minutes_rejected(self):
        with self.assertRaisesRegex(VideoContractError,"strict <600"):
            self.accept(seconds=762.18)

    def test_no_highlights_are_not_certified(self):
        self.cues["events"]=[]
        data(self.part/"visual_cues.json",self.cues)
        self.receipt["visual_cues_sha256"]=sha(self.part/"visual_cues.json")
        self.put_receipt();self.put_manifest()
        with self.assertRaisesRegex(VideoContractError,"no confirmed synchronized highlights"):
            self.accept()

    def test_mismatched_spoken_target_rejected(self):
        self.cues["events"][1]["target_id"]="wrong_diagram"
        data(self.part/"visual_cues.json",self.cues)
        self.receipt["visual_cues_sha256"]=sha(self.part/"visual_cues.json")
        self.put_receipt();self.put_manifest()
        with self.assertRaisesRegex(VideoContractError,"not bound to spoken events"):
            self.accept()

    def test_unverified_preview_receipt_rejected(self):
        self.receipt["unverified"]=["final_production_lecture_acceptance"]
        self.put_receipt();self.put_manifest()
        with self.assertRaisesRegex(VideoContractError,"static or experimental"):
            self.accept()

    def test_tampered_mp4_rejected(self):
        self.media.write_bytes(b"Changed MP4")
        with self.assertRaisesRegex(VideoContractError,"Stale or modified"):
            self.accept()

    def test_modified_WAV_rejected(self):
        self.audio.write_bytes(b"tampered")
        with self.assertRaisesRegex(VideoContractError,"Stale or modified"):
            self.accept()

    def test_missing_transition_proof_rejected(self):
        self.receipt["encoded_transition_qa"]["verified_transition_count"]=0
        self.put_receipt();self.put_manifest()
        with self.assertRaisesRegex(VideoContractError,"encoded transition"):
            self.accept()

    def test_unapproved_alignment_rejected(self):
        self.alignment["status"]="experimental"
        data(self.part/"narration_alignment.json",self.alignment)
        self.receipt["alignment_sha256"]=sha(self.part/"narration_alignment.json")
        self.put_receipt();self.put_manifest()
        with self.assertRaisesRegex(VideoContractError,"need verification"):
            self.accept()

    def test_slide_target_overlaps_rejected(self):
        self.cues["events"][1]["start_ms"]=41000
        self.alignment["events"][1]["start_ms"]=41000
        data(self.part/"visual_cues.json",self.cues)
        data(self.part/"narration_alignment.json",self.alignment)
        self.receipt["visual_cues_sha256"]=sha(self.part/"visual_cues.json")
        self.receipt["alignment_sha256"]=sha(self.part/"narration_alignment.json")
        self.put_receipt();self.put_manifest()
        with self.assertRaisesRegex(VideoContractError,"overlapping"):
            self.accept()

    def test_missing_part_rejected(self):
        self.part.rename(self.root/"archived_part")
        with self.assertRaisesRegex(VideoContractError,"Required file missing"):
            self.accept()

    def test_legacy_encoder_aborts_overlong_audio_before_ffmpeg(self):
        from unittest.mock import patch
        from selenium_pipeline import video_ffmpeg
        entries=[(1,self.root/"slide1.pdf",self.audio,600.0)]
        with patch.object(video_ffmpeg,"check_inputs",return_value=entries):
            with patch.object(video_ffmpeg,"ffmpeg_executable",
                              side_effect=AssertionError("FFmpeg must not launch")):
                with self.assertRaisesRegex(RuntimeError,"disabled"):
                    video_ffmpeg.assemble(self.root)

    def test_runner_video_acceptance_uses_new_manifest_gate(self):
        from unittest.mock import patch
        from selenium_pipeline.runner import check_valid
        # Unit fixture is not a real MP4. Stub ONLY independent media probing.
        # Production always probes the real MP4 using the installed FFmpeg.
        with patch("selenium_pipeline.production_video_contract._mp4_duration",
                   return_value=98.0):
            # A technically valid MP4 is not automatically academically accepted.
            self.assertFalse(check_valid("video",self.root))
            (self.root/"slides.pdf").write_bytes(b"synthetic deck")
            (self.root/"script.txt").write_text(
                "**Slide 1 [10 sec]:\\nSynthetic math narration**".replace("\\n","\n"),
                encoding="utf8")
            tts={
                "version":2,
                "primary":{"provider":"gemini","model":"gemini-3.8-flash-lite-tts","voice":"Kore"},
                "slides":[{
                    "slide":1,"source_text":"Synthetic math narration",
                    "tts_text":"Synthetic math narration","provider":"gemini",
                    "model":"gemini-3.8-flash-lite-tts","voice":"Kore","fallback_used":False,
                }],
            }
            data(self.root/"tts_input_manifest.json",tts)
            human={
                "schema_version":1,"status":"human_academic_review_approved",
                "human_authored_explicit_approval":True,
                "reviewed_by":"Synthetic test reviewer",
                "approved_at_utc":"2026-10-18T11:05:00Z",
                "subject":"entire_source_bound_lecture",
                "source_sha256":sha(self.root/"source.pdf"),
                "slides_sha256":sha(self.root/"slides.pdf"),
                "narration_script_sha256":sha(self.root/"script.txt"),
                "technical_series_sha256":sha(self.root/"lecture_completion.json"),
                "tts_input_manifest_sha256":sha(self.root/"tts_input_manifest.json"),
                "effective_tts_model":"gemini-3.8-flash-lite-tts",
                "effective_tts_voice":"Kore",
                "mathematics_approved":True,
                "all_figures_complete_and_legible":True,
                "original_narration_listened_and_approved":True,
                "spoken_element_highlights_approved":True,
            }
            data(self.root/"lecture_human_approval.json",human)
            self.assertTrue(check_valid("video",self.root))
            self.media.write_bytes(b"bad")
            self.assertFalse(check_valid("video",self.root))


if __name__=="__main__":
    unittest.main()
