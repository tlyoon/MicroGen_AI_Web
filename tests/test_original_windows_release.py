"""Windows original-release integration, separate from scientific re-audits.

Only fixture-generated PDFs and mocks here. This does NOT certify that a
published textbook lecture has completed mathematical review or PCM QA.
"""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_original_multisource_recovery_campaign import (
    RealTwoSourceFaultRecoveryTests,
)
from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, run_campaign,
)
from selenium_pipeline.original_windows_release import inspect_campaign
from selenium_pipeline.evidence_reuse_contract import file_sha256


class WindowsOriginalReleaseCommandTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing verified Windows/PyMuPDF fixture rather than
        # rebuilding per-figure or per-source scientific test machinery.
        self.seed = RealTwoSourceFaultRecoveryTests(
            "test_two_original_sources_produce_durable_distinct_readiness_receipts"
        )
        self.seed.setUp()
        self.addCleanup(self.seed.doCleanups)
        self.seed.runit()
        self.out = self.seed.output

    def test_read_only_command_reuses_both_original_acceptance_receipts(self):
        original = {(Path(s["lecture"]) / n):
                    (Path(s["lecture"]) / n).read_bytes()
                    for s in self.seed.specs
                    for n in ("source.pdf", "slides.pdf", "script.txt")}
        with patch(
            "selenium_pipeline.original_source_e2e_acceptance.inspect_source_e2e",
            side_effect=AssertionError("Scientific inspection reran"),
        ), patch(
            "selenium_pipeline.original_source_e2e_acceptance.execute_prepared",
            side_effect=AssertionError("Render called during read-only status"),
        ):
            result = inspect_campaign(campaign=self.out)
        self.assertEqual(result["selected_sections"], 2)
        self.assertEqual(result["executed_original_sections"], 0)
        self.assertTrue(result[
            "source_and_evidence_sha_verified_without_semantic_reaudit"])
        self.assertTrue(all(
            not x["eligible_for_explicit_prepared_execution"]
            and x["status"] != "READY_FOR_STRICT_RECORDED_AUDIO_MULTIPART_RENDER"
            for x in result["sections"]))
        self.assertEqual({p: p.read_bytes() for p in original}, original)

    def test_blocked_explicit_render_does_not_enter_existing_renderer(self):
        with patch(
            "selenium_pipeline.original_source_e2e_acceptance.execute_prepared",
            side_effect=AssertionError("Premature original render"),
        ) as render:
            result = inspect_campaign(
                campaign=self.out, section="8.4", execute_prepared=True)
        self.assertEqual(result["executed_original_sections"], 0)
        self.assertEqual(result["sections"][0]["execution_status"],
                         "BLOCKED_BY_SOURCE_OR_MEDIA_GATE")
        render.assert_not_called()

    def test_rejects_tampered_immutable_section_receipt(self):
        target = self.out / "section_8_4_e2e.json"
        target.write_text(target.read_text("utf8").replace(
            '"section": "8.4"', '"section": "8.9"', 1), encoding="utf8")
        with self.assertRaises(CampaignRecoveryBlocked):
            inspect_campaign(campaign=self.out)

    def test_rejects_altered_original_source_pdf(self):
        source = Path(self.seed.specs[0]["lecture"]) / "source.pdf"
        with source.open("ab") as f:
            f.write(b"\nchanged original source\n")
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "original source or external evidence changed"):
            inspect_campaign(campaign=self.out)

    def test_rejects_wrong_or_missing_single_section_selection(self):
        with self.assertRaises(CampaignRecoveryBlocked):
            inspect_campaign(campaign=self.out, section="10.8")
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "one explicit --section"):
            inspect_campaign(campaign=self.out, execute_prepared=True)

    def test_new_partial_audio_requires_new_versioned_campaign(self):
        lecture = Path(self.seed.specs[0]["lecture"])
        (lecture / "element_narration_plan.json").write_text(
            "{}", encoding="utf8")
        with patch(
            "selenium_pipeline.original_source_e2e_acceptance.execute_prepared",
            side_effect=AssertionError("Stale receipt cannot render"),
        ):
            r = inspect_campaign(campaign=self.out, section="8.4",
                                 execute_prepared=True)
        self.assertEqual(r["sections"][0]["status"],
                         "NEW_DOWNSTREAM_EVIDENCE_REQUIRES_VERSIONED_CAMPAIGN")
        self.assertEqual(r["executed_original_sections"], 0)

    def test_mocked_ready_receipt_routes_only_chosen_section_through_strict_gate(self):
        # Adversarial integration dispatch: a test-only simulated ready receipt
        # is NOT a source review approval or authentic PCM validation.
        first = self.seed.specs[0]
        lecture = Path(first["lecture"])
        (lecture / "element_narration_plan.json").write_text(
            "{}", encoding="utf8")
        (lecture / "element_tts_manifest.json").write_text(
            "{}", encoding="utf8")
        (lecture / "element_wav").mkdir()
        out = self.seed.root / "synthetic_ready_campaign"
        out.mkdir()

        def test_only_ready_report(**kwargs):
            target = kwargs["lecture"]
            return {
                "status": (
                    "READY_FOR_STRICT_RECORDED_AUDIO_MULTIPART_RENDER"
                    if Path(target) == lecture else
                    "BLOCKED_UNRESOLVED_SOURCE_VISUAL_NARRATION"
                ),
                "source_inputs_sha256": {
                    n: file_sha256(Path(target) / n)
                    for n in ("source.pdf", "slides.pdf", "script.txt")
                },
                "new_model_or_tts_calls": False,
                "student_publication_authorized": False,
                "existing_per_element_recorded_audio_available":
                    Path(target) == lecture,
            }

        run_campaign(specs=self.seed.specs, outdir=out,
                     inspector=test_only_ready_report)
        synthetic_result = {
            "status": "ORIGINAL_SOURCE_STRICT_MULTIPART_TECHNICAL_PASS",
            "new_model_or_tts_calls": False,
            "student_publication_authorized": False,
        }
        with patch(
            "selenium_pipeline.original_source_e2e_acceptance.execute_prepared",
            return_value=synthetic_result,
        ) as renderer:
            report = inspect_campaign(campaign=out, section="8.4",
                                      execute_prepared=True)
        self.assertEqual(report["executed_original_sections"], 1)
        self.assertEqual(report["sections"][0]["execution_status"],
                         "ORIGINAL_SOURCE_STRICT_MULTIPART_TECHNICAL_PASS")
        renderer.assert_called_once()
        self.assertEqual(renderer.call_args.kwargs["lecture"], lecture)
        self.assertEqual(len(report["sections"]), 1)
        self.assertFalse(report["student_publication_authorized"])


if __name__ == "__main__":
    unittest.main()
