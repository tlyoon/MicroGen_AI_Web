import copy,tempfile,unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.source_review_packet_bridge import export_review_packet,validate_signed_review_packet
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class SourceReviewPacketTests(unittest.TestCase):
    def test_fully_formed_packet_is_initially_unreviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=make_subchapter(root/"source","8.4")
            packet=export_review_packet(folder=folder,output=root/"review.json")
            result=validate_signed_review_packet(folder=folder,packet=packet)
            self.assertEqual(result["reviewed_utterances"],0)
            self.assertEqual(result["unreviewed_utterances"],packet["utterance_count"])
            self.assertFalse(result["tts_billing_authorized"])
    def test_explicit_original_source_quote_validated_no_autofilled_reviews(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=make_subchapter(root/"source","8.5")
            pdf=pymupdf.open();pdf.new_page().insert_text((25,45),"A genuine cited passage from this textbook page.")
            pdf.save(folder/"replacement.pdf");pdf.close()
            (folder/"source.pdf").write_bytes((folder/"replacement.pdf").read_bytes())
            (folder/"replacement.pdf").unlink()
            packet=export_review_packet(folder=folder,output=root/"review.json")
            item=packet["review_items"][0]
            item["review_target_id"]=item["candidate_targets"][0]["target_id"]
            item["source_page"]=1
            item["verbatim_source_quote"]="A genuine cited passage from this textbook page."
            item["reviewer_attestation"]=True;item["reviewer_id"]="physics-reviewer"
            result=validate_signed_review_packet(folder=folder,packet=packet)
            self.assertEqual(result["reviewed_utterances"],1)
            self.assertEqual(result["unreviewed_utterances"],packet["utterance_count"]-1)
            fake=copy.deepcopy(packet);fake["review_items"][1]["source_page"]=1
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_signed_review_packet(folder=folder,packet=fake)
