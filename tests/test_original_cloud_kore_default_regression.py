"""Original owner-approved Cloud/Kore default restored, never Corey.

Only hash-bound genuine Lite and Flash failures can authorize automatic
Cloud speech. These tests are entirely offline and cannot create charges.
"""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from selenium_pipeline.tts import _fallback_specs, _whole_batch_fallback
from selenium_pipeline.tts_effective_identity import (
    DEFAULT, GEMINI_FLASH, CLOUD, CHIRP, verify_effective_identity,
    TTSEffectiveIdentityError,
)

class OriginalCloudKoreContract(unittest.TestCase):
    def test_default_cloud_voice_matches_original_repository(self):
        self.assertEqual(DEFAULT["voice"],"Kore")
        self.assertEqual(CLOUD,{"provider":"chirp3","model":CHIRP,
                                "voice":"en-US-Chirp3-HD-Kore"})
        steps=_fallback_specs(DEFAULT["provider"],DEFAULT["model"],DEFAULT["voice"])
        self.assertEqual(steps,[GEMINI_FLASH,CLOUD])

    def test_original_voice_name_follows_requested_gemini_voice(self):
        # The original code constructs the Cloud voice from the selected name.
        for name in ("Kore","Aoede","Zephyr"):
            with self.subTest(name=name):
                steps=_fallback_specs("gemini","gemini-3.8-flash-lite-tts",name)
                self.assertEqual(steps[-1]["voice"],f"en-US-Chirp3-HD-{name}")

    def test_deprecated_corey_is_blocked_before_cloud_cost_or_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            items=[(1,"A complete source-bound mathematical narration.")]
            attempted={"count":0}
            def tracked(*args,**kwargs):
                attempted["count"]+=1
            ledger=SimpleNamespace(verify_before=lambda provider,model:
                {"lite":{"failed_slides":[1]},"flash":{"failed_slides":[1]}})
            wrong={**CLOUD,"voice":"en-US-Chirp3-HD-Corey"}
            with patch("selenium_pipeline.tts._synthesize_folder_unlocked",
                       side_effect=tracked),patch(
                       "selenium_pipeline.tts_billing_guard.require_tts_cost_authorization"
                       ) as bill:
                with self.assertRaisesRegex(RuntimeError,
                                            "original contract requires"):
                    _whole_batch_fallback(folder,items,wrong,
                        requested=DEFAULT,
                        completed_gemini_models=(
                            "gemini-3.8-flash-lite-tts","gemini-3.8-flash-tts"),
                        attempt_evidence=ledger)
                bill.assert_not_called()
            self.assertEqual(attempted["count"],0)
            self.assertFalse((folder/"tts_input_manifest.json").exists())

    def test_old_corey_provenance_is_rejected_not_relabelled(self):
        items=[(1,"Original text")]
        bad={"primary":{**CLOUD,"voice":"en-US-Chirp3-HD-Corey"},
             "requested_primary":DEFAULT,
             "all_slides_one_effective_voice":True,
             "fallback_chain":["gemini-3.8-flash-lite-tts",
                               "gemini-3.8-flash-tts"],
             "slides":[]}
        with self.assertRaises(TTSEffectiveIdentityError):
            verify_effective_identity(bad,items)

if __name__=="__main__":
    unittest.main()
