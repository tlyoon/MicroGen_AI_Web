"""Preserve old corrected-author QA separately from frozen uncorrected slide lineage."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline import recover_pinned_original_thomas_corpus
from selenium_pipeline.original_thomas84_corrected_lineage_reuse import (
    REPORT, AUTHOR, MOVIES, STATUS, reconcile
)
from selenium_pipeline.evidence_reuse_contract import file_sha256

class OldCorrectedAuthorIsNotFrozenOriginal(unittest.TestCase):
    def setUp(self):
        ctx=tempfile.TemporaryDirectory()
        self.addCleanup(ctx.cleanup)
        self.root=Path(ctx.name)
        self.orig=self.root/"original"
        self.orig.mkdir()
        self.paths={
            "pub":self.orig/"source.pdf",
            "old":self.orig/"slides.pdf",
            "new":self.root/AUTHOR,
            "one":self.root/MOVIES[0],
            "two":self.root/MOVIES[1],
            "proof":self.root/REPORT,
        }
        for key,p in self.paths.items():
            p.parent.mkdir(parents=True,exist_ok=True)
            if key!="proof":p.write_bytes(("CORRECTED_ORIGINAL_"+key).encode())
        self.record={
            "status":"THOMAS84_ALL_THREE_QA_CHECKS_COMPLETED_SOURCE_MATH_PHONETIC_MEDIA_PASS_REVIEW_ONLY",
            "original_textbook_sha256":file_sha256(self.paths["pub"]),
            "corrected_actual_source_pdf_sha256":file_sha256(self.paths["new"]),
            "independently_audited_actual_final_movie_SHA256":[
                file_sha256(self.paths["one"]),file_sha256(self.paths["two"])],
            "real_complete_movies_seconds":[426.89,313.81],
            "math_source_automated_review_criteria_satisfied":True,
            "owner_flexible_soundalike_TTS_criteria_satisfied":True,
            "source_visual_element_relevance_criteria_satisfied":True,
            "actual_H264_AAC_media_integrity_criteria_satisfied":True,
            "release_candidate_QA_gate_pass":True,
            "student_publication_authorized":False,
            "publication_was_performed":False,
            "independent_human_aural_voice_identity_certified":False,
            "every_individual_spoken_word_acoustically_proven":False,
        }
        self._save()
        pin=patch.dict(recover_pinned_original_thomas_corpus.ORIGINAL_PINS,
                       {"8.4":(file_sha256(self.paths["pub"]),
                               file_sha256(self.paths["old"]))})
        pin.start()
        self.addCleanup(pin.stop)

    def _save(self):
        self.paths["proof"].write_text(json.dumps(self.record),encoding="utf8")

    def test_corrected_author_existing_QA_reused_not_frozen(self):
        out=reconcile(original=self.orig,checkpoint=self.root)
        self.assertEqual(out["status"],STATUS)
        self.assertEqual(out["prior_scope_decision"],"REUSE_VERIFIED")
        self.assertEqual(out["separate_original_author_version_decision"],
                         "TARGETED_REVALIDATION")
        self.assertFalse(out["student_publication_authorized"])
        self.assertNotEqual(out["frozen_uncorrected_original_author_pdf_sha256"],
                            out["prior_corrected_author_pdf_sha256"])

    def test_old_video_tampering_blocks_reuse(self):
        self.paths["two"].write_bytes(b"CHANGED_VIDEO")
        with self.assertRaises(FigureIdentityReviewRequired):
            reconcile(original=self.orig,checkpoint=self.root)

    def test_wrong_original_source_blocks_cross_revision_promotion(self):
        self.paths["pub"].write_bytes(b"CHANGED_PUBLISHER")
        with self.assertRaises(FigureIdentityReviewRequired):
            reconcile(original=self.orig,checkpoint=self.root)

    def test_old_partial_reviewer_voice_claim_not_full_authorization(self):
        self.record["student_publication_authorized"]=True
        self._save()
        with self.assertRaises(FigureIdentityReviewRequired):
            reconcile(original=self.orig,checkpoint=self.root)

    def test_old_math_or_audio_failure_would_not_reuse(self):
        self.record["owner_flexible_soundalike_TTS_criteria_satisfied"]=False
        self._save()
        with self.assertRaises(FigureIdentityReviewRequired):
            reconcile(original=self.orig,checkpoint=self.root)

if __name__=="__main__":
    unittest.main()
