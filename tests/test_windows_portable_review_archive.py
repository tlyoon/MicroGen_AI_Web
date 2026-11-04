"""Portable release-review source archive: original materials and secrets excluded."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from zipfile import ZipFile


class PortableWindowsReviewArchiveTests(unittest.TestCase):
    def test_git_head_archive_excludes_private_originals_and_has_real_operator(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as work:
            zipfile = Path(work) / "review_candidate.zip"
            run = subprocess.run(
                ["git", "-C", str(repo), "archive", "--format=zip",
                 f"--output={zipfile}", "HEAD"],
                capture_output=True, text=True, encoding="utf8", timeout=90)
            self.assertEqual(run.returncode, 0, run.stderr)
            with ZipFile(zipfile) as archive:
                names = [name for name in archive.namelist()
                         if not name.endswith("/")]
                required = (
                    "MicroGen-Windows.ps1",
                    "Install-MicroGen-Windows.ps1",
                    "selenium_pipeline/windows_operator.py",
                    "selenium_pipeline/windows_install_smoke.py",
                    "selenium_pipeline/windows_scoped_prior_full_media_acceptance.py",
                    "selenium_pipeline/windows_original_stage_sequence.py",
                    "selenium_pipeline/windows_reviewed_element_media_bridge.py",
                )
                self.assertTrue(set(required).issubset(set(names)))
                self.assertGreater(len(names), 100)
                forbidden = re.compile(
                    r"(?i)(^|/)(\.env|source\.pdf|credentials\.json|secrets\.json)$|"
                    r"\.(wav|mp4|pem|pfx|p12|key)$|(^|/)\.microgen_work(/|$)")
                self.assertFalse(
                    [name for name in names if forbidden.search(name)])
                self.assertFalse(any(name.startswith(".git/")
                                     for name in names))


if __name__ == "__main__":
    unittest.main()
