"""Offline integration checks: actual fallback voice carries into QA and highlighting."""
from __future__ import annotations

import hashlib
import json
import unittest

from test_tts_qa_promotion import ReviewedAudioHandoffTests
from test_tts_reviewed_element_compat import ReviewedSlideAudioCompatibilityTests
from selenium_pipeline.tts_qa_promotion import audit, export_reviewed, AudioPromotionBlocked
from selenium_pipeline.tts_reviewed_element_compat import check, ElementAudioIncompatible
from selenium_pipeline.tts_effective_identity import (
    DEFAULT, GEMINI_FLASH, CLOUD, LITE, FLASH,
    verify_effective_identity, TTSEffectiveIdentityError,
)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def transform_manifest(doc, effective, chain):
    doc["primary"] = dict(effective)
    if chain:
        doc["requested_primary"] = dict(DEFAULT)
        doc["fallback_chain"] = list(chain)
        doc["all_slides_one_effective_voice"] = True
    else:
        doc.pop("requested_primary", None)
        doc.pop("fallback_chain", None)
        doc.pop("all_slides_one_effective_voice", None)
    for row in doc["slides"]:
        row.update({**effective, "fallback_used": bool(chain)})
        if chain:
            row.update({
                "primary_provider": DEFAULT["provider"],
                "primary_model": DEFAULT["model"],
                "primary_voice": DEFAULT["voice"],
                "voice_consistency": {
                    "mode": "full_batch_single_engine_voice",
                    "cross_model_voice_equivalence_verified": False,
                    "independent_listening_required": True,
                },
            })
    return doc


class FallbackProvenanceEndToEndTests(unittest.TestCase):
    def new_audio(self):
        case=ReviewedAudioHandoffTests("test_audit_read_only_and_requires_no_attestation")
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def mutate_audio(self, case, effective, chain):
        doc=transform_manifest(case.manifest,effective,chain)
        for folder in (case.source,case.review):
            (folder/"tts_input_manifest.json").write_text(
                json.dumps(doc),encoding="utf-8")
        case.receipt.update(
            provider=effective["provider"],tts_model=effective["model"],
            voice=effective["voice"],
            source_manifest_sha256=sha(case.source/"tts_input_manifest.json"))
        case.persist()
        case.original_snapshot["tts_input_manifest.json"] = (
            case.source/"tts_input_manifest.json").read_bytes()

    def new_element(self):
        case=ReviewedSlideAudioCompatibilityTests(
            "test_single_element_per_slide_can_be_checked_read_only")
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def mutate_element(self, case, effective, chain, *, correct_voice_id=True):
        manifest_file=case.audio/"tts_input_manifest.json"
        manifest=transform_manifest(json.loads(manifest_file.read_text()),
                                     effective,chain)
        manifest_file.write_text(json.dumps(manifest),encoding="utf-8")
        receipt_file=case.audio/"tts_reviewed_handoff.json"
        receipt=json.loads(receipt_file.read_text())
        receipt.update(provider=effective["provider"],
                       tts_model=effective["model"],voice=effective["voice"],
                       requested_primary=dict(DEFAULT),fallback_chain=list(chain),
                       fallback_used=bool(chain),
                       source_manifest_sha256=sha(manifest_file))
        receipt_file.write_text(json.dumps(receipt),encoding="utf-8")
        if correct_voice_id:
            case.fixture.plan_data["voice_id"]=(
                f"{effective['provider']}_{effective['model']}_{effective['voice']}_REVIEW_ONLY")
            case.fixture.save()

    def test_primary_flash_can_enter_review_audit(self):
        case=self.new_audio()
        self.mutate_audio(case,GEMINI_FLASH,[])
        result=audit(case.source,case.review)
        self.assertEqual(result["tts_model"],FLASH)
        self.assertEqual(result["voice"],"Kore")
        self.assertFalse(result["fallback_used"])

    def test_flash_fallback_is_source_bound_and_requires_change_attestation(self):
        case=self.new_audio()
        self.mutate_audio(case,GEMINI_FLASH,[LITE])
        proof=audit(case.source,case.review)
        self.assertEqual(proof["fallback_chain"],[LITE])
        doc=case.create_external_attestation()
        with self.assertRaisesRegex(AudioPromotionBlocked,"human listening"):
            export_reviewed(case.source,case.review,case.destination,
                            attestation_path=case.attestation_path,
                            confirm_reviewed_audio=True,
                            confirm_isolated_export=True)
        doc["fallback_provider_change_reviewed"]=True
        case.attestation_path.write_text(json.dumps(doc),encoding="utf-8")
        exported=export_reviewed(case.source,case.review,case.destination,
                            attestation_path=case.attestation_path,
                            confirm_reviewed_audio=True,
                            confirm_isolated_export=True)
        self.assertEqual(exported["tts_model"],FLASH)
        self.assertEqual(exported["voice"],"Kore")
        self.assertFalse(exported["video_publication_approved"])
        case.assert_originals_unchanged()

    def test_chirp_corey_never_adopts_a_kore_only_attestation(self):
        case=self.new_audio()
        self.mutate_audio(case,CLOUD,[LITE,FLASH])
        proof=audit(case.source,case.review)
        self.assertEqual(proof["voice_listening_field"],"voice_corey_listening_verified")
        doc=case.create_external_attestation()
        doc["fallback_provider_change_reviewed"]=True
        case.attestation_path.write_text(json.dumps(doc),encoding="utf-8")
        with self.assertRaisesRegex(AudioPromotionBlocked,"human listening"):
            export_reviewed(case.source,case.review,case.destination,
                            attestation_path=case.attestation_path,
                            confirm_reviewed_audio=True,
                            confirm_isolated_export=True)
        self.assertFalse(case.destination.exists())
        doc["voice_corey_listening_verified"]=True
        case.attestation_path.write_text(json.dumps(doc),encoding="utf-8")
        exported=export_reviewed(case.source,case.review,case.destination,
                            attestation_path=case.attestation_path,
                            confirm_reviewed_audio=True,
                            confirm_isolated_export=True)
        self.assertEqual(exported["voice"],CLOUD["voice"])
        self.assertEqual(exported["fallback_chain"],[LITE,FLASH])
        case.assert_originals_unchanged()

    def test_cloud_incomplete_chain_is_rejected_even_with_correct_voice(self):
        case=self.new_audio()
        self.mutate_audio(case,CLOUD,[LITE,FLASH])
        case.manifest["fallback_chain"]=[LITE]
        for root in (case.source,case.review):
            (root/"tts_input_manifest.json").write_text(
                json.dumps(case.manifest),encoding="utf-8")
        case.receipt["source_manifest_sha256"]=sha(case.source/"tts_input_manifest.json")
        case.persist()
        with self.assertRaisesRegex(AudioPromotionBlocked,"history"):
            audit(case.source,case.review)

    def test_mixed_corey_and_kore_slide_provenance_rejected(self):
        case=self.new_audio()
        self.mutate_audio(case,CLOUD,[LITE,FLASH])
        case.manifest["slides"][0]["voice"]="Kore"
        for root in (case.source,case.review):
            (root/"tts_input_manifest.json").write_text(
                json.dumps(case.manifest),encoding="utf-8")
        case.receipt["source_manifest_sha256"]=sha(case.source/"tts_input_manifest.json")
        case.persist()
        with self.assertRaisesRegex(AudioPromotionBlocked,"voice provenance"):
            audit(case.source,case.review)

    def test_flash_fallback_audio_compatible_with_single_element_plan(self):
        case=self.new_element()
        self.mutate_element(case,GEMINI_FLASH,[LITE])
        result=case.check()
        self.assertEqual(result["effective_voice"],"Kore")
        self.assertEqual(result["effective_model"],FLASH)
        self.assertEqual(result["fallback_chain"],[LITE])
        self.assertFalse(result["production_approved"])

    def test_corey_fallback_audio_compatible_with_matching_author_scene(self):
        case=self.new_element()
        self.mutate_element(case,CLOUD,[LITE,FLASH])
        result=case.check()
        self.assertEqual(result["effective_provider"],"chirp3")
        self.assertEqual(result["effective_voice"],CLOUD["voice"])
        self.assertFalse(result["scientific_element_mapping_approved"])

    def test_original_kore_scene_cannot_claim_corey_narration(self):
        case=self.new_element()
        self.mutate_element(case,CLOUD,[LITE,FLASH],correct_voice_id=False)
        with self.assertRaisesRegex(ElementAudioIncompatible,"same source/model/voice"):
            case.check()

    def test_forged_cloud_handoff_without_both_gemini_failures_is_rejected(self):
        case=self.new_element()
        self.mutate_element(case,CLOUD,[LITE,FLASH])
        manifest_file=case.audio/"tts_input_manifest.json"
        doc=json.loads(manifest_file.read_text())
        doc["fallback_chain"]=[LITE]
        manifest_file.write_text(json.dumps(doc),encoding="utf-8")
        receipt_file=case.audio/"tts_reviewed_handoff.json"
        receipt=json.loads(receipt_file.read_text())
        receipt["source_manifest_sha256"]=sha(manifest_file)
        receipt_file.write_text(json.dumps(receipt),encoding="utf-8")
        with self.assertRaisesRegex(ElementAudioIncompatible,"history"):
            case.check()


if __name__=="__main__":
    unittest.main()
