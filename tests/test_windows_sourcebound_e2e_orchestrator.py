"""Windows-only real-source reproduction remains isolated and fail-closed."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.windows_sourcebound_e2e_orchestrator import (
    PHASES,SourceboundE2EError,stage_tree,execute_windows)

class WindowsSourceBoundOrchestratorTests(unittest.TestCase):
    def test_copy_is_byte_exact_and_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);source=base/"orig";snap=base/"snapshot"
            f=source/"8"/"8.4"/"source.pdf";f.parent.mkdir(parents=True)
            f.write_bytes(b"%PDF-1.4\nSynthetic safe source for path test")
            a=stage_tree(source_root=source,snapshot_root=snap,subchapter="8.4")
            b=stage_tree(source_root=source,snapshot_root=snap,subchapter="8.4")
            self.assertEqual(a,b)
            self.assertEqual((snap/"8"/"8.4"/"source.pdf").read_bytes(),f.read_bytes())
    def test_conflicting_snapshot_fails_before_rerecording(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);source=base/"orig";snap=base/"snapshot"
            f=source/"8"/"8.4"/"source.pdf";f.parent.mkdir(parents=True)
            f.write_bytes(b"trusted")
            dest=snap/"8"/"8.4";dest.mkdir(parents=True)
            (dest/"source.pdf").write_bytes(b"foreign")
            with self.assertRaises(SourceboundE2EError):
                stage_tree(source_root=source,snapshot_root=snap,subchapter="8.4")
    def test_source_root_or_source_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/"8"/"8.4";source.mkdir(parents=True)
            (source/"source.pdf").write_bytes(b"keep")
            with self.assertRaises(SourceboundE2EError):
                stage_tree(source_root=root,snapshot_root=root,subchapter="8.4")
            self.assertEqual((source/"source.pdf").read_bytes(),b"keep")
    def test_no_unexpected_non_windows_execution(self):
        with patch("selenium_pipeline.windows_sourcebound_e2e_orchestrator.sys.platform","linux"):
            with self.assertRaisesRegex(SourceboundE2EError,"Windows"):
                execute_windows(source_root=Path("a"),snapshot_root=Path("b"),
                    work_root=Path("c"),subchapter="8.4",
                    pipeline_python=Path("py"),tts_python=Path("tts"),
                    repo=Path("repo"))
    def test_streaming_sha_is_compatible_with_dell_pipeline_python(self):
        from selenium_pipeline.windows_sourcebound_e2e_orchestrator import sha
        import hashlib
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"source.pdf"
            f.write_bytes(b"one-shot owner-protected mathematical source")
            expected=hashlib.sha256(f.read_bytes()).hexdigest()
            # No reliance on hashlib.file_digest: unavailable in Python 3.10.
            self.assertEqual(sha(f),expected)

    def test_live_routines_explicitly_source_bound(self):
        self.assertEqual([p[0] for p in PHASES],[
            "source_content","narrated_audio","sourcebound_video"])
        self.assertEqual(PHASES[-1][1],
                         ("--from-stage","video","--through-stage","video"))
    def test_no_production_can_proceed_without_real_interpreters(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);root=base/"orig";test=base/"temp"
            (root/"8"/"8.4").mkdir(parents=True)
            (root/"8"/"8.4"/"source.pdf").write_bytes(b"demo")
            with self.assertRaisesRegex(SourceboundE2EError,"Python"):
                execute_windows(source_root=root,snapshot_root=test,
                    work_root=base/"work",subchapter="8.4",
                    pipeline_python=base/"no.exe",tts_python=base/"no-tts.exe",
                    repo=base)
if __name__=="__main__":unittest.main()
