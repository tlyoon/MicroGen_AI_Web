import tempfile,unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.incremental_review_selection import exact_source_text_selections
from selenium_pipeline.incremental_element_candidate_map import candidate_map
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class ExactSourceTextFastLaneTests(unittest.TestCase):
    def test_nonliteral_realistic_slides_remain_blocked_without_blocking_queue(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.4")
            r=exact_source_text_selections(folder=folder)
            self.assertEqual(r["utterances_total"],3)
            self.assertEqual(r["source_literal_matches"],0)
            self.assertFalse(r["ready_for_paid_tts"])
    def test_literal_source_text_pdf_block_permitted_for_review_not_publication(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.5",with_figure=False)
            # This synthetic source is authored to contain verbatim existing
            # original slide narrator text for exactly one matching slide.
            doc=pymupdf.open()
            doc.new_page().insert_text((20,40),"The last slide summarizes the solution.")
            doc.save(folder/"source_new.pdf")
            doc.close()
            (folder/"source.pdf").write_bytes((folder/"source_new.pdf").read_bytes())
            (folder/"source_new.pdf").unlink()
            # Render full original slide 3 text identical to narration.
            slides=pymupdf.open()
            for number in range(3):
                page=slides.new_page(width=360,height=270)
                page.insert_text((25,45),"The last slide summarizes the solution."
                        if number==2 else f"Other {number+1}")
            slides.save(folder/"slides_new.pdf");slides.close()
            (folder/"slides.pdf").write_bytes((folder/"slides_new.pdf").read_bytes())
            (folder/"slides_new.pdf").unlink()
            r=exact_source_text_selections(folder=folder)
            self.assertEqual(r["source_literal_matches"],1)
            self.assertTrue(r["slides"][2]["utterances"][0]["exact_source_pdf_text_match_verified"])
            self.assertFalse(r["whole_lecture_math_semantics_verified"])
            self.assertFalse(r["ready_for_paid_tts"])
    def test_wrong_candidate_source_sha_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_subchapter(Path(t),"8.6")
            candidates=candidate_map(folder=folder)
            candidates["script_sha256"]="0"*64
            with self.assertRaises(FigureIdentityReviewRequired):
                exact_source_text_selections(folder=folder,candidates=candidates)
