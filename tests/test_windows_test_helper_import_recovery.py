"""Source-only regression for registry-backed local test fixture import bootstrap."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked,
)
from selenium_pipeline.windows_test_helper_import_recovery import (
    _audit_siblings, bootstrap,
)

ROOT = Path(__file__).resolve().parent.parent


class TestHelperImportRecoveryTests(unittest.TestCase):
    def test_real_legacy_sibling_inventory_and_idempotent_normal_path(self):
        result = bootstrap(str(ROOT / "tests" / "__init__.py"))
        self.assertEqual(result["status"],
                         "SOURCE_VERIFIED_LOCAL_TEST_HELPERS_RESOLVABLE")
        self.assertGreaterEqual(result["legacy_sibling_import_count"], 60)
        self.assertGreater(result["unique_local_sibling_helpers"], 10)
        self.assertGreater(result["scanned_test_source_count"], 400)
        target = str(ROOT / "tests")
        self.assertEqual(sys.path.count(target), 1)
        self.assertFalse(result["student_publication_authorized"])
        self.assertEqual(result["provider_calls"], 0)
        second = bootstrap(str(ROOT / "tests" / "__init__.py"))
        self.assertEqual(second["legacy_sibling_import_count"],
                         result["legacy_sibling_import_count"])
        self.assertEqual(sys.path.count(target), 1)

    def test_clean_external_process_package_style_sibling_imports(self):
        # No injected tests/ path; imports must work using the package's
        # normal executable bootstrap, not a shell-env operator workaround.
        code = (
            "import sys,tests;from pathlib import Path;"
            "import tests.test_reviewed_element_tts_handoff as handoff;"
            "import tests.test_tts_fallback_downstream_provenance as fallback;"
            "import tests.test_ai_academic_review_queue as review;"
            "print('IMPORT_BOOTSTRAP_PASS',"
            "handoff.ReviewedTTSHandoffTests.__name__,"
            "fallback.__name__,review.__name__,"
            "sys.path.count(str(Path(tests.__file__).parent)))"
        )
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        out = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT, env=env, capture_output=True,
            text=True, timeout=45,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("IMPORT_BOOTSTRAP_PASS", out.stdout)

    def test_missing_sibling_fixture_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as path:
            folder = Path(path)
            (folder / "test_a.py").write_text(
                "import test_missing_critical_fixture\n", encoding="utf8")
            with self.assertRaises(CampaignRecoveryBlocked):
                _audit_siblings(folder)

    def test_non_local_package_target_refused(self):
        with tempfile.TemporaryDirectory() as path:
            fake = Path(path) / "tests"
            fake.mkdir()
            (fake / "__init__.py").write_text("# forged\n", encoding="utf8")
            before = list(sys.path)
            with self.assertRaises(CampaignRecoveryBlocked):
                bootstrap(str(fake / "__init__.py"))
            self.assertEqual(sys.path, before)

    def test_retired_registry_refuses_import_bootstrap(self):
        with patch(
            "selenium_pipeline.recovery_registry.lookup_mechanism",
            return_value=None,
        ):
            before = list(sys.path)
            with self.assertRaises(CampaignRecoveryBlocked):
                bootstrap(str(ROOT / "tests" / "__init__.py"))
            self.assertEqual(sys.path, before)

    def test_local_sibling_inventory_rejects_symlink_file(self):
        with tempfile.TemporaryDirectory() as path:
            base = Path(path)
            f = base / "test_fixture.py"
            f.write_text("x=1\n", encoding="utf8")
            link = base / "test_linked.py"
            try:
                link.symlink_to(f)
            except (OSError, NotImplementedError):
                self.skipTest("Windows symlink permissions unavailable")
            with self.assertRaises(CampaignRecoveryBlocked):
                _audit_siblings(base)


if __name__ == "__main__":
    unittest.main()
