"""Native PowerShell bridge smoke: inspect-only, no model submissions."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class WindowsLectureProgressionLauncherTests(unittest.TestCase):
    def setUp(self):
        if os.name != "nt" or shutil.which("powershell.exe") is None:
            self.skipTest("Native Windows PowerShell runner only")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "publisher"
        folder = self.source / "77" / "77.9"
        folder.mkdir(parents=True)
        (folder / "source.pdf").write_bytes(b"%PDF-1.7\n" + b"synthetic" * 50)
        self.trial = self.root / "never_model_submitted"
        self.trial.mkdir()
        self.script = Path(__file__).resolve().parents[1] / "MicroGen-Windows.ps1"
        self.env = os.environ.copy()
        self.env["LOCALAPPDATA"] = str(self.root)

    def invoke(self, *flags):
        return subprocess.run([
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(self.script), "-Python", str(Path(sys.executable)),
            *flags,
        ], capture_output=True, text=True, encoding="utf8",
           errors="replace", timeout=60, env=self.env)

    def test_lecture_candidates_is_read_only_no_model_or_tts(self):
        run = self.invoke(
            "-Mode", "LectureCandidates", "-SourceRoot", str(self.source),
            "-TrialRegistryRoot", str(self.trial))
        self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
        report = json.loads(run.stdout)
        self.assertEqual(report["status"],
                         "CANDIDATE_CATALOG_UNVERIFIED_WITHOUT_TRIAL_HISTORY")
        self.assertEqual(report["publisher_source_files_examined"], 1)
        self.assertFalse(report["automatic_model_generation_allowed"])
        self.assertFalse(report["new_model_or_tts_calls"])
        self.assertEqual(list(self.trial.iterdir()), [])

    def test_lecture_candidates_rejects_any_paid_content_flag(self):
        run = self.invoke(
            "-Mode", "LectureCandidates", "-SourceRoot", str(self.source),
            "-TrialRegistryRoot", str(self.trial),
            "-ConfirmContentApiCost")
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(list(self.trial.iterdir()), [])

    def test_launcher_lecture_status_reads_only_unclaimed_source(self):
        run = self.invoke(
            "-Mode", "LectureStatus", "-SourceRoot", str(self.source),
            "-Section", "77.9", "-TrialDir", str(self.trial))
        # The isolated source fixture has NO authenticated source-free
        # owned-new-turn canary. Under the new normal route gate, the
        # inspect-only launcher must halt safely rather than advertise
        # source readiness from a healthy temporary-capacity flag alone.
        self.assertEqual(run.returncode, 2, run.stderr + run.stdout)
        report = json.loads(run.stdout)
        self.assertEqual(report["next_stage"], "figures")
        self.assertEqual(report["status"],
                         "HALTED_UNVERIFIED_GEMINI_BROWSER_ROUTE_NO_SEND")
        self.assertFalse(report["new_source_browser_send_authorized"])
        self.assertFalse(report["new_model_or_tts_calls"])
        self.assertFalse(report["student_publication_authorized"])
        self.assertEqual(list(self.trial.iterdir()), [])

    def test_launcher_advance_requires_exact_source_inputs(self):
        run = self.invoke("-Mode", "LectureAdvance",
                          "-SourceRoot", str(self.source),
                          "-TrialDir", str(self.trial))
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(list(self.trial.iterdir()), [])

    def test_media_review_mode_blocks_when_source_stages_incomplete(self):
        args = [
            "-Mode", "LectureMediaReview",
            "-SourceRoot", str(self.source),
            "-Section", "77.9", "-TrialDir", str(self.trial),
            "-ReviewDraft", str(self.root / "not_yet_reviewed.json"),
            "-ReviewSelection", str(self.root / "review_selection.json"),
            "-TtsRequest", str(self.root / "not_yet_tts_request.json"),
            "-AudioDir", str(self.root / "no_wavs"),
            "-ReviewOutDir", str(self.root / "no_output"),
        ]
        run = self.invoke(*args)
        self.assertEqual(run.returncode, 2, run.stderr + run.stdout)
        self.assertEqual(
            json.loads(run.stdout)["status"],
            "MEDIA_PREREQUISITES_NOT_ACCEPTED_NO_ENCODING")
        self.assertFalse((self.root / "no_output").exists())

    def test_ffmpeg_render_switch_not_transferable_to_source_status(self):
        run = self.invoke(
            "-Mode", "LectureStatus",
            "-SourceRoot", str(self.source),
            "-Section", "77.9", "-TrialDir", str(self.trial),
            "-ConfirmMediaReviewRender")
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(list(self.trial.iterdir()), [])

    def test_launcher_api_needs_explicit_cost_consent_before_any_send(self):
        run = self.invoke(
            "-Mode", "LectureAdvance",
            "-CommunicationMode", "api",
            "-SourceRoot", str(self.source),
            "-Section", "77.9", "-TrialDir", str(self.trial))
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(list(self.trial.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
