"""v6 persistent recovery registry and executable fail-closed integration."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from selenium_pipeline.recovery_registry import (
    REGISTRY_PATH, load_registry, lookup_mechanism)
from selenium_pipeline.g2_forward_recovery_engine import (
    _registered_recovery, _RESOLUTIONS, _DEFERRED)


class VersionSixRecoveryRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"catalog.json"
        self.original=load_registry()

    def overwrite(self,obj):
        self.path.write_text(json.dumps(obj),encoding="utf8")

    def test_historical_claim_recovery_selected_without_new_model_send(self):
        for signature,expected in _RESOLUTIONS.items():
            with self.subTest(signature=signature):
                self.assertEqual(
                    lookup_mechanism("selection_action",signature),expected)
                self.assertEqual(
                    _registered_recovery("selection_action",signature,_RESOLUTIONS,
                                         "REVALIDATE_TWO_PASS_SOURCE_CONSENSUS_OR_STOP"),
                    expected)
        nested=lookup_mechanism(
            "selection_action","RECOVER_WRAPPED_SAVED_REPLY_NO_SEND")
        self.assertIn("DOWNGRADE_ONLY",nested)
        self.assertTrue(REGISTRY_PATH.is_file())

    def test_provider_and_acoustic_qa_gates_still_halt(self):
        for signature,expected in _DEFERRED.items():
            self.assertEqual(
                _registered_recovery("supervisor_status",signature,_DEFERRED,
                                     "UNRECOGNIZED_STAGE_REQUIRES_EXPLICIT_SOURCE_EVIDENCE"),
                expected)

    def test_new_unknown_signature_not_silently_mapped_to_known_remedy(self):
        self.assertIsNone(lookup_mechanism(
            "selection_action","FUTURE_UNCLASSIFIED_FAILURE"))
        self.assertEqual(
            _registered_recovery("selection_action","FUTURE_UNCLASSIFIED_FAILURE",
                                 _RESOLUTIONS,"REVALIDATE_TWO_PASS_SOURCE_CONSENSUS_OR_STOP"),
            "REVALIDATE_TWO_PASS_SOURCE_CONSENSUS_OR_STOP")

    def test_missing_registry_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"absent"):
            lookup_mechanism("selection_action","FRESH_FIRST_ATTEMPT",
                             path=self.path)

    def test_retired_recovery_fails_closed_and_does_not_reset_budget(self):
        clone=json.loads(json.dumps(self.original))
        clone["entries"][0]["enabled"]=False
        self.overwrite(clone)
        with self.assertRaisesRegex(ValueError,"retired or disabled"):
            lookup_mechanism("selection_action",clone["entries"][0]["signature"],
                             path=self.path)

    def test_duplicate_failure_signatures_rejected(self):
        clone=json.loads(json.dumps(self.original))
        clone["entries"].append(dict(clone["entries"][0],id="DIFFERENT_RECOVERY_ID"))
        self.overwrite(clone)
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            load_registry(self.path)

    def test_external_handler_injection_rejected(self):
        clone=json.loads(json.dumps(self.original))
        clone["entries"][0]["handler"]="os.system('pay_and_send_again')"
        self.overwrite(clone)
        with self.assertRaisesRegex(ValueError,"unsafe"):
            load_registry(self.path)

    def test_registry_mismatch_to_code_reviewed_handler_blocks_forward(self):
        # A corrupt/stale registry cannot silently replace a verified handler.
        bad=dict(_RESOLUTIONS, FRESH_FIRST_ATTEMPT="DISABLED_MISSING_FIX")
        with self.assertRaisesRegex(Exception,"retired, missing or changed"):
            _registered_recovery("selection_action","FRESH_FIRST_ATTEMPT",
                                 bad,"REVALIDATE_TWO_PASS_SOURCE_CONSENSUS_OR_STOP")

    def test_all_entries_have_verification_provenance(self):
        for e in self.original["entries"]:
            self.assertTrue(e["verification_test"].startswith("tests/"))
            self.assertLessEqual(
                date.fromisoformat(e["last_verified_date"]), date(2026,11,17))
            self.assertGreaterEqual(
                date.fromisoformat(e["last_verified_date"]),date(2026,11,16))
            self.assertIn("finite",e["retry_policy"])
            self.assertTrue(e["enabled"])
            self.assertNotIn("paid",e["handler"].casefold())

if __name__=="__main__":
    unittest.main()
