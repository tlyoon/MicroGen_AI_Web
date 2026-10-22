import unittest,tempfile,hashlib
from pathlib import Path
import pymupdf
from selenium_pipeline.original_packet_evidence_audit import audit_original_review_packet
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

def fixture(folder):
    folder.mkdir()
    for n in ("source.pdf","slides.pdf"):
        with pymupdf.open() as d:
            page=d.new_page(width=300,height=300)
            page.insert_text((20,30),"A visible equation")
            d.save(folder/n)
    (folder/"script.txt").write_text("1. A visible equation\n",encoding="utf8")
    sha=lambda n:hashlib.sha256((folder/n).read_bytes()).hexdigest()
    return {"status":"UNSIGNED_EXPLICIT_ELEMENT_REVIEW_PACKET",
        "original_source_sha256":sha("source.pdf"),
        "original_slides_sha256":sha("slides.pdf"),
        "original_script_sha256":sha("script.txt"),
        "tts_billing_authorized":False,"student_publication_authorized":False,
        "utterance_count":1,"review_items":[{"utterance_id":"s001.utterance.001",
            "spoken_text_sha256":"f"*64,
            "candidate_targets":[{"target_id":"s001.text.001",
                "actual_visible_pdf_bbox_pt":[20,15,100,33]}],
            "review_target_id":None,"reviewer_attestation":False}]}

class PacketEvidenceTests(unittest.TestCase):
    def test_bounded_original_candidates_never_promote_human_qa(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"original";pkt=fixture(f)
            r=audit_original_review_packet(folder=f,packet=pkt)
            self.assertEqual(r["pending_review_count"],1)
            self.assertFalse(r["human_math_semantics_verified"])
    def test_off_slide_and_stale_original_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"original";p=fixture(f)
            p["review_items"][0]["candidate_targets"][0]["actual_visible_pdf_bbox_pt"]=[0,0,500,10]
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_original_review_packet(folder=f,packet=p)
            p=fixture if False else p
            (f/"script.txt").write_text("changed")
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_original_review_packet(folder=f,packet=p)
