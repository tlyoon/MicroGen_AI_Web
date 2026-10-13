"""Offline, no-Gemini regression tests for user-extensible teaching profiles."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.domains import (
    BUILTIN_PROFILES, PROFILE_STAGES, ProfileError,
    load_profile, render_stage_guidance, validate_profile,
)

ROOT = Path(__file__).resolve().parents[1]


class DomainProfileTests(unittest.TestCase):
    def test_builtin_profiles_declared_and_versioned(self):
        self.assertEqual(BUILTIN_PROFILES, ("general", "physics", "mathematics"))
        for name in BUILTIN_PROFILES:
            profile = load_profile(name)
            self.assertEqual(profile.id, name)
            self.assertEqual(profile.profile_version, "1.0.0")
            self.assertEqual(profile.maturity, "development")
            for stage in PROFILE_STAGES:
                self.assertTrue(profile.guidance(stage))

    def test_distinct_teaching_rules_and_common_source_fidelity(self):
        physics = render_stage_guidance(load_profile("physics"), "slides")
        math = render_stage_guidance(load_profile("mathematics"), "slides")
        self.assertIn("units", physics)
        self.assertIn("derivation", math)
        self.assertIn("source", physics.lower())
        self.assertNotEqual(physics, math)

    def test_history_custom_example_uses_unmodified_core(self):
        file = ROOT / "examples/history_profile.example.json"
        p = load_profile("history", profile_file=file)
        self.assertEqual(p.maturity, "experimental")
        self.assertIn("chronology", p.content_types)
        self.assertIn("timeline", render_stage_guidance(p, "highlighting"))
        self.assertNotIn("history", BUILTIN_PROFILES)

    def test_no_implicit_nonbuiltin_profile(self):
        with self.assertRaisesRegex(ProfileError, "Unknown built-in"):
            load_profile("history")

    def test_custom_profile_id_mismatch_fails_closed(self):
        file = ROOT / "examples/history_profile.example.json"
        with self.assertRaisesRegex(ProfileError, "differs"):
            load_profile("physics", profile_file=file)

    def test_unknown_stage_fails_closed(self):
        with self.assertRaisesRegex(ProfileError, "Unsupported"):
            load_profile("physics").guidance("video")

    def test_invalid_profile_payloads_rejected(self):
        good = json.loads(
            (ROOT / "selenium_pipeline/domains/profiles/mathematics.json").read_text()
        )
        bad = []
        for k, v in [
            ("schema_version", 2), ("schema_version", True),
            ("profile_version", "latest"), ("maturity", "official"),
            ("maturity", "certified"),
            ("id", "../malicious"), ("content_types", []),
            ("review_checks", ["duplicate", "duplicate"]),
        ]:
            obj = copy.deepcopy(good)
            obj[k] = v
            bad.append(obj)
        extra = copy.deepcopy(good)
        extra["python_hook"] = "os.system('bad')"
        bad.append(extra)
        missing = copy.deepcopy(good)
        del missing["prompt_sections"]["quality_review"]
        bad.append(missing)
        for obj in bad:
            with self.subTest(problem=obj):
                with self.assertRaises(ProfileError):
                    validate_profile(obj)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "bad.json"
            dest.write_text('{"id":"physics","id":"history"}', encoding="utf-8")
            with self.assertRaisesRegex(ProfileError, "Duplicate JSON key"):
                load_profile(profile_file=dest)

    def test_no_python_code_in_profile_accepted(self):
        p = json.loads(
            (ROOT / "examples/history_profile.example.json").read_text()
        )
        p["validator_python"] = "raise Exception('untrusted code')"
        with self.assertRaisesRegex(ProfileError, "unknown"):
            validate_profile(p)

    def test_cli_list_and_history_inspect_have_no_side_effects(self):
        cmd = [sys.executable, "-m", "selenium_pipeline.domains"]
        listed = subprocess.run([*cmd, "list"], cwd=ROOT, capture_output=True,
                                encoding="utf-8", check=True)
        self.assertIn("physics", listed.stdout)
        self.assertIn("mathematics", listed.stdout)
        self.assertNotIn("history:", listed.stdout)
        detail = subprocess.run([*cmd, "inspect", "--profile-file",
                                 str(ROOT / "examples/history_profile.example.json")],
                                cwd=ROOT, capture_output=True, encoding="utf-8", check=True)
        self.assertEqual(json.loads(detail.stdout)["maturity"], "experimental")
        self.assertIn("no domain quality is certified", detail.stdout)

    def test_error_code_on_unknown_domain(self):
        proc = subprocess.run([sys.executable, "-m", "selenium_pipeline.domains",
                               "inspect", "--domain", "history"],
                              cwd=ROOT, capture_output=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Unknown built-in", proc.stderr)


if __name__ == "__main__":
    unittest.main()
