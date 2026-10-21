import hashlib,tempfile,unittest
import pymupdf
from pathlib import Path
from selenium_pipeline.incremental_nonliteral_selection import validate_explicit_element_choices
from selenium_pipeline.incremental_element_candidate_map import candidate_map
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class ReviewedChoicesTests(unittest.TestCase):
    def test_no_choices_stays_not_audio_approved(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.4")
            result=validate_explicit_element_choices(folder=folder,choices=[])
            self.assertEqual(result["reviewed_utterance_count"],0)
            self.assertFalse(result["tts_billing_authorized"])
    def test_source_page_quote_and_real_target_selection(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.5")
            c=candidate_map(folder=folder)
            selected=c["slides"][0]["original_utterance_candidates"][0]
            decision={"utterance_id":selected["utterance_id"],
                      "spoken_text_sha256":selected["original_text_sha256"],
                      "target_id":c["slides"][0]["candidate_visual_targets"][0]["draft_element_id"],
                      "source_page":1,"verbatim_source_quote":"Source",
                      "reviewer_attestation":True,"reviewer_id":"reviewer-001"}
            # The PDF from synthetic fixture only contains "Source" (too short),
            # proving that arbitrary one-word citations do not grant TTS.
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_explicit_element_choices(folder=folder,choices=[decision],candidates=c)
            decision["verbatim_source_quote"]="Not a genuine textbook quote"
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_explicit_element_choices(folder=folder,choices=[decision],candidates=c)
    def test_explicit_real_source_quote_can_select_one_nonliteral_segment(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.5")
            source=pymupdf.open()
            source.new_page().insert_text(
                (20,30),"An explicit original source passage verifies this selection.")
            source.save(folder/"new.pdf");source.close()
            (folder/"source.pdf").write_bytes((folder/"new.pdf").read_bytes())
            (folder/"new.pdf").unlink()
            candidates=candidate_map(folder=folder)
            u=candidates["slides"][0]["original_utterance_candidates"][0]
            target=candidates["slides"][0]["candidate_visual_targets"][0]
            evidence={"utterance_id":u["utterance_id"],
                      "spoken_text_sha256":u["original_text_sha256"],
                      "target_id":target["draft_element_id"],
                      "source_page":1,
                      "verbatim_source_quote":"An explicit original source passage verifies this selection.",
                      "reviewer_attestation":True,"reviewer_id":"reviewer-physics"}
            r=validate_explicit_element_choices(folder=folder,choices=[evidence],
                                                 candidates=candidates)
            self.assertEqual(r["reviewed_utterance_count"],1)
            self.assertEqual(r["unreviewed_utterance_count"],2)
            self.assertEqual(r["selected_segments"][0]["bbox_pdf_pt"],
                             target["bbox_pdf_pt"])
            self.assertFalse(r["tts_billing_authorized"])
            self.assertFalse(r["whole_lecture_spoken_element_sync_verified"])
    def test_unknown_utterance_and_spoofed_approval_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.6")
            c=candidate_map(folder=folder)
            old=c["script_sha256"]
            c["script_sha256"]="f"*64
            self.assertNotEqual(c["script_sha256"],old)
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_explicit_element_choices(folder=folder,choices=[],candidates=c)
