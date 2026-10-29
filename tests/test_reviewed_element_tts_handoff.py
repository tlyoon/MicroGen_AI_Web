"""No-network two-phase element narration tests: source review → Gemini → MP4 stage."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import io
import wave

import test_element_plan_autodraft as fixture
from selenium_pipeline.element_plan_review_bridge import promoted,PlanPromotionError
from selenium_pipeline.element_narration_gemini import main as tts_main
from selenium_pipeline.element_narration_stage import prepare
from selenium_pipeline.element_highlight_workflow import review


def mock_gemini_audio():
    buf=io.BytesIO()
    with wave.open(buf,"wb") as f:
        f.setnchannels(1);f.setsampwidth(2)
        f.setframerate(24000);f.writeframes(b"\x01\x10"*24000)
    return buf.getvalue()


class ReviewedTTSHandoffTests(unittest.TestCase):
    def setUp(self):
        self.c=fixture.CandidateAuthoringTests("test_no_words_are_generated_or_removed")
        self.c.setUp()
        self.addCleanup(self.c.doCleanups)
        self.root=self.c.root
        self.output=self.root/"new_gemini_tts_output"
        self.preplan=self.root/"two_phase_reviewed_request.json"
        self.final=self.root/"stageable_after_gemini.json"
        self.request=promoted(source=self.c.source,slides=self.c.slides,
            script=self.c.script,draft_path=self.c.draft_path,
            selection=self.c.selection,prepare_tts=True)
        self.preplan.write_text(json.dumps(self.request),encoding="utf8")
        self.args=["--authored-plan",str(self.preplan),"--output-folder",str(self.output),
                   "--voice","Kore","--model","gemini-3.8-flash-lite-tts"]
    def synth(self):
        with patch("selenium_pipeline.runner.load_microvid_env"), \
             patch("gemini_keys.get_gemini_api_keys",return_value=["mock-only"]), \
             patch("selenium_pipeline.tts._gemini_say_with_watchdog",
                   return_value=mock_gemini_audio()) as call:
            self.assertEqual(tts_main(self.args+[
                "--confirm-live","--confirm-reviewed-tts-request",
                "--confirm-gemini-api-cost"]),0)
        return call
    def promote(self):
        return promoted(source=self.c.source,slides=self.c.slides,
            script=self.c.script,draft_path=self.c.draft_path,
            selection=self.c.selection,audio=self.output,
            tts_request=self.preplan)

    def test_speech_plan_can_be_prepared_without_recordings_or_api(self):
        self.assertEqual(self.request["status"],
                         "reviewed_element_tts_request_unapproved")
        self.assertEqual(self.request["tts_voice"],"Kore")
        self.assertEqual(self.request["tts_model"],"gemini-3.8-flash-lite-tts")
        self.assertFalse(self.request["api_execution_authorized"])
        self.assertFalse(self.request["academic_approval"])
        self.assertEqual([x["part_id"] for x in self.request["parts"]],
                         ["part_01","part_02"])
        self.assertEqual(len([e for p in self.request["parts"]
            for s in p["slides"] for e in s["elements"]]),3)
        self.assertFalse(self.output.exists())

    def test_explicit_paid_api_authorization_required_before_any_wav(self):
        for flags in (
            [],["--confirm-live"],["--confirm-live","--confirm-reviewed-tts-request"],
            ["--confirm-live","--confirm-gemini-api-cost"],
        ):
            with self.subTest(flags=flags):
                with self.assertRaises(SystemExit):
                    tts_main(self.args+flags)
                self.assertFalse(self.output.exists())

    def test_two_phase_mocked_gemini_to_original_encoded_stage(self):
        call=self.synth()
        self.assertEqual(call.call_count,3)
        self.assertEqual(len(list(self.output.glob("*.wav"))),3)
        result=self.promote()
        self.assertEqual(result["status"],
                         "author_specified_unapproved_element_narration")
        self.assertEqual(result["voice_id"],self.request["voice_id"])
        self.final.write_text(json.dumps(result),encoding="utf8")
        receipt=prepare(source_pdf=self.c.source,slides_pdf=self.c.slides,
               authored_json=self.final,recorded_audio=self.output,
               destination=self.root/"staged_two_phase")
        self.assertEqual(receipt["status"],"review_only")
        staged=json.loads((self.root/"staged_two_phase"/"element_stage_receipt.json").read_text())
        self.assertEqual(staged["complete_lecture_coverage"],True)
        self.assertEqual(staged["audio_text_fidelity_verified"],False)
        self.assertEqual(staged["mathematical_approval"],False)
        # End-to-end real FFmpeg and decoded encoded-pixel test, using only
        # WAVs returned by a deterministic TEST DOUBLE, never a paid API.
        video=review(source=self.c.source,slides=self.c.slides,
            authored=self.final,audio=self.output,
            output_root=self.root/"two_phase_real_mp4_preview")
        self.assertEqual((video["covered_slides"],video["covered_elements"]),(3,3))
        self.assertTrue(all(part["encoded_pixels_rechecked"]
                            for part in video["parts"]))
        self.assertFalse(video["production_approved"])
        self.assertFalse(video["student_published"])

    def test_resume_and_tts_receipt_bound_to_pre_synthesis_request(self):
        self.synth()
        proof=self.output/"s01_e01.wav.verified.json"
        data=json.loads(proof.read_text())
        data["plan_sha256"]="0"*64
        proof.write_text(json.dumps(data),encoding="utf8")
        with self.assertRaisesRegex(PlanPromotionError,"different reviewed request"):
            self.promote()

    def test_model_voice_mismatch_fails_before_billing(self):
        self.request["voice_id"]="gemini_other_random_voice"
        self.preplan.write_text(json.dumps(self.request))
        with self.assertRaises(SystemExit):
            tts_main(self.args+["--confirm-live","--confirm-reviewed-tts-request",
                "--confirm-gemini-api-cost"])
        self.assertFalse(self.output.exists())

    def test_reviewer_tampering_invalidates_synthesis_binding(self):
        self.synth()
        self.c.decisions["reviewer_note"]+=" Different reviewer edit."
        self.c.save()
        with self.assertRaisesRegex(PlanPromotionError,"differs"):
            self.promote()

    def test_reject_fabricated_tts_job_identity(self):
        self.synth()
        path=self.output/"tts_job_identity.json"
        data=json.loads(path.read_text())
        data["voice"]="OtherVoice"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(PlanPromotionError,"not bound to exact"):
            self.promote()

    def test_staging_refuses_pre_synthesis_request(self):
        with self.assertRaises(Exception):
            prepare(source_pdf=self.c.source,slides_pdf=self.c.slides,
                authored_json=self.preplan,recorded_audio=self.c.wavdir,
                destination=self.root/"should_not_stage")
        self.assertFalse((self.root/"should_not_stage").exists())


if __name__=="__main__":unittest.main()
