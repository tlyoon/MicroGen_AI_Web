"""Real Windows PowerShell forward-source entrypoint, synthetic PDF only.

Calls the installed source-only seven-stage DRY-RUN and zero provider Sends.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(os.name=="nt" and shutil.which("powershell.exe"),
                     "Native Windows PowerShell integration only")
class NativeForwardSourceLauncherTests(unittest.TestCase):
    def setUp(self):
        holder=tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.home=Path(holder.name)/"LOCALAPPDATA"
        self.home.mkdir()
        self.publisher=Path(holder.name)/"publisher"
        self.publisher.mkdir()
        self.registry=self.home/"source_registry"
        self.registry.mkdir()
        self.script=Path(__file__).resolve().parents[1]/"MicroGen-Windows.ps1"
        self.originals=[]
        import pymupdf
        for section in ("77.9","78.1"):
            folder=self.publisher/section.split(".")[0]/section
            folder.mkdir(parents=True)
            pdf=folder/"source.pdf"
            with pymupdf.open() as document:
                page=document.new_page()
                page.insert_text((60,80),
                    "Original controlled dry-run test source "+section)
                document.save(pdf)
            self.originals.append(pdf)
        self.before=[f.read_bytes() for f in self.originals]

    def run_launcher(self,*,extra=()):
        env={**os.environ,"LOCALAPPDATA":str(self.home)}
        args=["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass",
              "-File",str(self.script),
              "-Mode","ForwardSourceDryRuns",
              "-SourceRoot",str(self.publisher),
              "-TrialRegistryRoot",str(self.registry),
              "-CampaignName","independent_publisher_stress_v1",
              "-MaxNewSources","2",
              "-Python",str(Path(sys.executable)),*extra]
        return subprocess.run(args,env=env,capture_output=True,
              text=True,encoding="utf8",errors="replace",timeout=120)

    def test_two_distinct_originals_stage_and_resume_without_model_send(self):
        first=self.run_launcher()
        self.assertEqual(first.returncode,0,first.stderr+"\n"+first.stdout)
        payload=json.loads(first.stdout)
        self.assertEqual(payload["selected_distinct_original_sources"],2)
        self.assertEqual(payload["new_independent_source_dry_runs"],2)
        self.assertEqual(payload["new_provider_sends"],0)
        self.assertEqual(payload["new_tts_calls"],0)
        self.assertFalse(payload["media_encoded"])
        self.assertFalse(payload["verified_pdf_to_mp4_complete"])
        self.assertFalse(payload["student_publication_authorized"])
        self.assertEqual(payload["rejected_source_sections"],0)
        self.assertTrue(all(
            x["dry_run_status"]=="FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY"
            for x in payload["section_results"]))
        # Real runner stages exact byte-copy in external local trial folders.
        for original,row in zip(self.originals,payload["section_results"]):
            trial_dir=next(
                (self.registry/"independent_publisher_stress_v1").glob(
                    "source_"+row["section"].replace(".","_")+"_*"))
            # Ignore .dryrun.json receipts and look for the actual trial.
            if trial_dir.is_file():
                trial_dir=next(p for p in (
                    self.registry/"independent_publisher_stress_v1").glob(
                    "source_"+row["section"].replace(".","_")+"_*")
                    if p.is_dir())
            staged=trial_dir/"source_tree"/(
                row["section"].split(".")[0])/row["section"]/"source.pdf"
            self.assertEqual(staged.read_bytes(),original.read_bytes())
            self.assertFalse((trial_dir/"figures_attempt_started.json").exists())
        self.assertEqual(self.before,[f.read_bytes() for f in self.originals])
        replay=self.run_launcher()
        self.assertEqual(replay.returncode,0,replay.stderr+replay.stdout)
        second=json.loads(replay.stdout)
        self.assertEqual(second["new_independent_source_dry_runs"],0)
        self.assertEqual(second["reused_source_dry_runs"],2)
        self.assertEqual(second["new_provider_sends"],0)
        self.assertEqual(self.before,[f.read_bytes() for f in self.originals])

    def test_paid_api_mode_cannot_be_transferred_to_forward_source(self):
        unsafe=self.run_launcher(extra=(
            "-CommunicationMode","api","-ConfirmContentApiCost"))
        self.assertNotEqual(unsafe.returncode,0)
        self.assertFalse((
            self.registry/"independent_publisher_stress_v1").exists())


if __name__=="__main__":
    unittest.main()
