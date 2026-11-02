"""Native Windows phase admission must be bound to original source and outputs.

These synthetic files exercise the same phase cache used by the real runner,
but cannot authorize any student-facing material or claim mathematical QA.
"""
import hashlib
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.windows_phase_output_evidence import (
    SCHEMA, PhaseEvidenceError, phase_output_manifest, admit_completed_phase,
)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

class StageAcceptedArtifactCache(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        (self.root/"source.pdf").write_bytes(b"%PDF-TEST source original")
        self.source_sha=sha(self.root/"source.pdf")
        (self.root/"slides.tex").write_text(r"\begin{document}\end{document}")
        import pymupdf
        with pymupdf.open() as doc:
            doc.new_page()
            doc.new_page()
            doc.save(self.root/"slides.pdf")
        (self.root/"script.txt").write_text("Slide 1. Real narration\nSlide 2. Real narration")
        (self.root/"Figure 8.3.png").write_bytes(b"actual-author-image")
        self.prior={"outcome":"stage_pass","return_code":0,
                    "log":"previous-original-author-stage.log","attempt":1}

    def test_stage_source_command_pass_can_adopt_existing_artifacts_without_rerun(self):
        receipt,adopt=admit_completed_phase(
            prior=self.prior,folder=self.root,phase="source_content",
            source_sha256=self.source_sha)
        self.assertTrue(adopt)
        self.assertEqual(receipt["schema"],SCHEMA)
        self.assertIn("Figure 8.3.png",receipt["output_files_sha256"])
        self.assertFalse(receipt["student_publication_authorized"])
        self.prior["output_evidence"]=receipt
        later,adopt_again=admit_completed_phase(
            prior=self.prior,folder=self.root,phase="source_content",
            source_sha256=self.source_sha)
        self.assertFalse(adopt_again)
        self.assertEqual(later,receipt)

    def test_changed_figure_or_math_script_cannot_reuse_old_stage_receipt(self):
        prior=dict(self.prior)
        prior["output_evidence"]=phase_output_manifest(
            folder=self.root,phase="source_content",
            source_sha256=self.source_sha)
        (self.root/"Figure 8.3.png").write_bytes(b"mutated-graph-labels")
        with self.assertRaises(PhaseEvidenceError):
            admit_completed_phase(prior=prior,folder=self.root,
                                  phase="source_content",source_sha256=self.source_sha)

    def test_multiple_digit_original_slide_wav_indices_do_not_false_block(self):
        import pymupdf
        (self.root/"slides.pdf").unlink()
        with pymupdf.open() as doc:
            for _ in range(12):
                doc.new_page()
            doc.save(self.root/"slides.pdf")
        for i in range(1,13):
            (self.root/f"slide{i}.wav").write_bytes(b"RIFF"+bytes([i])*160)
        (self.root/"tts_fidelity_report.json").write_text("{}")
        report=phase_output_manifest(folder=self.root,
            phase="narrated_audio",source_sha256=self.source_sha)
        self.assertEqual(sum(k.endswith(".wav") for k in report["output_files_sha256"]),12)

    def test_no_missing_original_narration_can_be_adopted(self):
        (self.root/"slide1.wav").write_bytes(b"RIFF"+"audio" .encode())
        (self.root/"tts_fidelity_report.json").write_text("{}")
        with self.assertRaises(PhaseEvidenceError):
            phase_output_manifest(folder=self.root,
                phase="narrated_audio",source_sha256=self.source_sha)

    def test_all_slide_numbered_pcm_and_tts_report_physical_counts(self):
        for i in (1,2):
            (self.root/f"slide{i}.wav").write_bytes(b"RIFF"+bytes([i])*160)
        (self.root/"tts_fidelity_report.json").write_text('{"status":"candidate"}')
        proof=phase_output_manifest(folder=self.root,
            phase="narrated_audio",source_sha256=self.source_sha)
        self.assertEqual(len([k for k in proof["output_files_sha256"]
                              if k.endswith(".wav")]),2)
        prior=dict(self.prior,output_evidence=proof)
        (self.root/"slide2.wav").write_bytes(b"RIFF"+b"changed")
        with self.assertRaises(PhaseEvidenceError):
            admit_completed_phase(prior=prior,folder=self.root,
                                  phase="narrated_audio",source_sha256=self.source_sha)

    def test_no_static_or_missing_encoded_video_can_be_reused(self):
        (self.root/"lecture_completion.json").write_text("{}")
        with self.assertRaises(PhaseEvidenceError):
            phase_output_manifest(folder=self.root,
                phase="sourcebound_video",source_sha256=self.source_sha)
        (self.root/"real_part01.mp4").write_bytes(b"videodata")
        p=phase_output_manifest(folder=self.root,
                phase="sourcebound_video",source_sha256=self.source_sha)
        self.assertIn("real_part01.mp4",p["output_files_sha256"])
        self.assertFalse(p["student_publication_authorized"])

    def test_source_digest_and_zero_exit_must_be_bound(self):
        with self.assertRaises(PhaseEvidenceError):
            phase_output_manifest(folder=self.root,
                phase="source_content",source_sha256="c"*64)
        with self.assertRaises(PhaseEvidenceError):
            admit_completed_phase(
                prior=dict(self.prior,return_code=1),folder=self.root,
                phase="source_content",source_sha256=self.source_sha)

    def test_actual_windows_e2e_runner_calls_gate_before_skip_or_pass(self):
        source=(Path(__file__).resolve().parents[1]/
                "selenium_pipeline"/"windows_sourcebound_e2e_orchestrator.py").read_text(
                    encoding="utf8")
        self.assertIn("admit_completed_phase(",source)
        self.assertIn("phase_output_manifest(",source)
        self.assertIn('entry["output_evidence"]=artifact_receipt',source)
        self.assertIn('state["phases"][name]["output_evidence"]=receipt',source)
        self.assertNotIn('stage already published without source',source)

if __name__=="__main__":
    unittest.main()
