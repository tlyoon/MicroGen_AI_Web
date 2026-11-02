"""Owner-binding no-duplicate work and immutable proof preflight regressions.

Offline synthetic witnesses only, no source modification / paid model / release.
"""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.evidence_reuse_contract import (
    AcceptedClaim, EvidenceReuseBlocked, ProposedCheck, file_sha256, preflight,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


class EvidenceReuseContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.receipt = self.root / "old-figure83-verified.json"
        self.receipt.write_text(json.dumps({
            "source_artwork_correspondence_proven": True,
            "full_math_semantics_verified": False,
            "student_publication_authorized": False,
        }), encoding="utf8")
        self.record = AcceptedClaim(
            component_id="Thomas 8.4/Figure 8.3",
            scope="publisher_artwork_identity",
            standard="publisher_original_v1",
            source_sha256=A,
            author_sha256=B,
            artifact_sha256=C,
            receipt_path=self.receipt,
            receipt_sha256=file_sha256(self.receipt),
            evidence_claim_path=("source_artwork_correspondence_proven",),
            previous_pr="#452",
        )
        self.task = ProposedCheck(
            component_id=self.record.component_id,
            scope=self.record.scope,
            standard=self.record.standard,
            source_sha256=A,
            author_sha256=B,
            artifact_sha256=C,
        )

    def test_same_figure83_source_artwork_must_reuse_not_repeat(self):
        decision = preflight(self.task, [self.record])
        self.assertEqual(decision.decision, "REUSE_VERIFIED")
        self.assertEqual(decision.reused_from_pr, "#452")
        self.assertEqual(decision.reused_receipt_sha256, file_sha256(self.receipt))
        self.assertFalse(decision.new_production_release_granted)

    def test_weaker_new_similarity_detector_cannot_reopen_solved_scope(self):
        request = ProposedCheck(
            **{**self.task.__dict__,
               "reopen_reason": "different generic whole-page similarity score fell below threshold"},
        )
        decision = preflight(request, [self.record])
        self.assertEqual(decision.decision, "BLOCK_UNJUSTIFIED_REOPEN")
        self.assertTrue(decision.original_verified_scope_preserved)

    def test_new_axes_labels_science_is_separate_unverified_work(self):
        task = ProposedCheck(
            **{**self.task.__dict__, "scope": "scientific_graph_axis_label_semantics"},
        )
        d = preflight(task, [self.record])
        self.assertEqual(d.decision, "COMPLETE_UNVERIFIED_SCOPE")
        self.assertEqual(d.reused_from_pr, "#452")
        self.assertFalse(d.new_production_release_granted)

    def test_original_input_sha_change_requires_targeted_revalidation(self):
        for changed_key in ("source_sha256", "author_sha256", "artifact_sha256"):
            with self.subTest(changed_key=changed_key):
                task = ProposedCheck(**{**self.task.__dict__, changed_key: D})
                d = preflight(task, [self.record])
                self.assertEqual(d.decision, "TARGETED_REVALIDATION")
                self.assertFalse(d.new_production_release_granted)

    def test_stronger_acceptance_standard_is_explicit_targeted_revalidation(self):
        task = ProposedCheck(**{**self.task.__dict__,
                                 "standard": "publisher_plus_axes_v2"})
        self.assertEqual(preflight(task, [self.record]).decision,
                         "TARGETED_REVALIDATION")

    def test_actual_independent_contradiction_requires_bound_physical_witness(self):
        path = self.root / "specific-contradiction.json"
        path.write_text(json.dumps({
            "status": "INDEPENDENT_SOURCE_CONTRADICTION",
            "source_sha256": A,
            "author_sha256": B,
            "artifact_sha256": C,
            "scope": self.task.scope,
            "reproducible_physical_source_discrepancy": True,
            "observed_difference":
                "Original publisher figure source curve differs from author panel 2",
            "student_publication_authorized": False,
        }), encoding="utf8")
        task = ProposedCheck(**{**self.task.__dict__,
                                 "reopen_reason": "independent physical contradiction",
                                 "contradiction_path": path,
                                 "contradiction_sha256": file_sha256(path)})
        self.assertEqual(preflight(task, [self.record]).decision,
                         "TARGETED_REVALIDATION")
        path.write_text('{"invalidated": true}', encoding="utf8")
        self.assertEqual(preflight(task, [self.record]).decision,
                         "BLOCK_UNJUSTIFIED_REOPEN")

    def test_old_witness_tamper_is_not_permission_to_recreate_figures(self):
        self.receipt.write_text('{"source_artwork_correspondence_proven": false}',
                                encoding="utf8")
        with self.assertRaises(EvidenceReuseBlocked):
            preflight(self.task, [self.record])

    def test_false_or_unproven_old_claim_cannot_pass_as_verified(self):
        self.receipt.write_text(json.dumps({
            "source_artwork_correspondence_proven": False,
            "student_publication_authorized": False,
        }), encoding="utf8")
        record = AcceptedClaim(**{**self.record.__dict__,
                                   "receipt_sha256": file_sha256(self.receipt)})
        with self.assertRaises(EvidenceReuseBlocked):
            preflight(self.task, [record])

    def test_partial_previous_receipt_cannot_promote_full_verification(self):
        record = AcceptedClaim(**{**self.record.__dict__, "state": "partial",
                                   "evidence_claim_path":
                                       ("full_math_semantics_verified",)})
        self.assertEqual(preflight(self.task, [record]).decision,
                         "COMPLETE_UNVERIFIED_SCOPE")

    def test_incorrect_sha_or_missing_historical_witness_is_blocked(self):
        with self.assertRaises(EvidenceReuseBlocked):
            preflight(ProposedCheck(**{**self.task.__dict__,
                                       "artifact_sha256": "not-a-sha"}),
                      [self.record])
        record = AcceptedClaim(**{**self.record.__dict__,
                                   "receipt_path": self.root / "missing.json"})
        with self.assertRaises(EvidenceReuseBlocked):
            preflight(self.task, [record])

    def test_contract_and_windows_ci_expose_mandatory_regression(self):
        root = Path(__file__).resolve().parents[1]
        policy = (root / "docs" /
                  "BINDING_VERIFIED_EVIDENCE_REUSE_NO_DUPLICATE_WORK_20261102.md")
        effective = (root / "docs" /
                     "EFFECTIVE_CONTRACT_AND_SUPERSESSION_20261018.md")
        workflow = (root / ".github" / "workflows" /
                    "microgen-reliability-tests.yml")
        self.assertTrue(policy.is_file())
        self.assertIn("REUSE_VERIFIED", policy.read_text(encoding="utf8"))
        self.assertIn("BLOCK_UNJUSTIFIED_REOPEN", policy.read_text(encoding="utf8"))
        self.assertIn("BINDING_VERIFIED_EVIDENCE_REUSE_NO_DUPLICATE_WORK_20261102.md",
                      effective.read_text(encoding="utf8"))
        self.assertIn("tests.test_verified_evidence_reuse_contract",
                      workflow.read_text(encoding="utf8"))

class FrozenOriginalLedgerIntegrationTests(unittest.TestCase):
    def test_real_adapter_reuses_artwork_and_separately_allows_axis_science(self):
        from unittest.mock import patch
        from selenium_pipeline.evidence_reuse_contract import source_artwork_preflight
        from selenium_pipeline import recover_pinned_original_thomas_corpus

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            original = base / "original"
            section = original / "8.4"
            section.mkdir(parents=True)
            (section / "source.pdf").write_bytes(b"immutable-publisher")
            (section / "slides.pdf").write_bytes(b"immutable-lecturer")
            art = section / "Figure 8.3.png"
            art.write_bytes(b"exact-original-figure8.3-bitmap")
            claims = {
                "status":
                    "ALL_SIX_ORIGINAL_AUTHOR_IMAGES_PUBLISHER_VISUAL_PROVEN_FULL_SCIENCE_STILL_PENDING",
                "student_publication_authorized": False,
                "original_frozen_41_source_slides": 41,
                "six_independently_version_bound_figure_identity_receipts": {
                    "8.3": {
                        "source_artwork_correspondence_proven": True,
                        "author_png_sha256": file_sha256(art),
                        "every_visible_label_axis_symbol_and_spoken_word_verified": False,
                    }
                },
            }
            ledger = base / "six-figure-verified-source-ledger.json"
            ledger.write_text(json.dumps(claims), encoding="utf8")
            with patch.dict(recover_pinned_original_thomas_corpus.ORIGINAL_PINS,
                            {"8.4": (file_sha256(section / "source.pdf"),
                                     file_sha256(section / "slides.pdf"))}):
                art_decision = source_artwork_preflight(
                    ledger=ledger, frozen_original_root=original, figure_id="8.3")
                self.assertEqual(art_decision.decision, "REUSE_VERIFIED")
                self.assertEqual(art_decision.reused_from_pr, "#454")
                semantic_decision = source_artwork_preflight(
                    ledger=ledger, frozen_original_root=original, figure_id="8.3",
                    requested_scope="scientific_graph_axis_label_semantics")
                self.assertEqual(semantic_decision.decision, "COMPLETE_UNVERIFIED_SCOPE")
                art.write_bytes(b"altered-image-must-not-silently-pass")
                with self.assertRaises(EvidenceReuseBlocked):
                    source_artwork_preflight(
                        ledger=ledger, frozen_original_root=original, figure_id="8.3")

    def test_binding_preflight_rejects_forged_old_source_approval(self):
        from unittest.mock import patch
        from selenium_pipeline.evidence_reuse_contract import source_artwork_preflight
        from selenium_pipeline import recover_pinned_original_thomas_corpus

        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            section=base/"8.4"
            section.mkdir()
            (section/"source.pdf").write_bytes(b"real-source")
            (section/"slides.pdf").write_bytes(b"real-deck")
            (section/"Figure 8.3.png").write_bytes(b"real-fig")
            receipt=base/"false-approved-ledger.json"
            receipt.write_text(json.dumps({
                "status":
                    "ALL_SIX_ORIGINAL_AUTHOR_IMAGES_PUBLISHER_VISUAL_PROVEN_FULL_SCIENCE_STILL_PENDING",
                "student_publication_authorized":False,
                "original_frozen_41_source_slides":41,
                "six_independently_version_bound_figure_identity_receipts":{
                    "8.3":{"source_artwork_correspondence_proven":False,
                           "author_png_sha256":file_sha256(section/"Figure 8.3.png")},
                },
            }),encoding="utf8")
            with patch.dict(recover_pinned_original_thomas_corpus.ORIGINAL_PINS,
                            {"8.4":(file_sha256(section/"source.pdf"),
                                    file_sha256(section/"slides.pdf"))}):
                with self.assertRaises(EvidenceReuseBlocked):
                    source_artwork_preflight(
                        ledger=receipt,frozen_original_root=base,figure_id="8.3")


if __name__ == "__main__":
    unittest.main()
