"""Original Slide4 five visual candidates: real text plus original Figure8.2 strips."""
import os
from copy import deepcopy
from pathlib import Path
import unittest

from selenium_pipeline.original_slide4_five_visual_candidates import (
    complete_review_only_visual_candidates,inspect_original_slide4_five_visual_candidates,
)


def fixture():
    utterances=[{
        "id":f"s004.utterance.{i:03d}",
        "spoken_sha256":f"{i:064x}",
        "spoken_text":s,
    } for i,s in enumerate((
        "These algebraic substitutions correspond directly to right triangles with acute angle u.",
        "When x equals a tangent u, x and a represent opposite and adjacent legs.",
        "For sine, x is the opposite leg.",
        "For secant, hypotenuse is x.",
        "Taking the principal square root formally introduces absolute values, such as a times the absolute value of secant u.",
    ),1)]
    texts=[
        ("Geometric Reference Triangles",[8.504,14.826,186.124,29.172]),
        ("Each substitution corresponds to a geometric right triangle with angle u\nand sides x, a, and the respective hypotenuse or leg.",[10.909,57.794,339.762,82.252]),
        ("√",[32.727,186.691,41.814,197.6]),
        ("a2 + x2 = a| sec u|\n√",[32.727,192.926,125.56,214.138]),
        ("a2 −x2 = a| cos u|\n√",[32.727,209.323,126.167,230.676]),
        ("x2 −a2 = a| tan u|",[41.818,225.861,126.5,240.062]),
    ]
    job={"status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
         "source_sha256":"a"*64,"slides_sha256":"b"*64,
         "script_sha256":"c"*64,"utterance_count":5,
         "slides":[{"slide":4,"utterances":utterances,
                    "visual_targets":[{"id":f"s004.text.{i:03d}",
                                       "kind":"text_block",
                                       "visible_text":t,
                                       "bbox_pdf_pt":r}
                                       for i,(t,r) in enumerate(texts,1)]}]}
    prior={"status":"ORIGINAL_SLIDE4_THREE_RASTER_REGION_CANDIDATES_REVIEW_ONLY",
           "original_source_sha256":"a"*64,
           "original_slides_sha256":"b"*64,
           "original_script_sha256":"c"*64,
           "proposed_figure_region_utterance_count":3,
           "unmapped_original_utterance_count":2,
           "utterance_candidates":[
               {"utterance_id":u["id"],"original_spoken_sha256":u["spoken_sha256"],
                "candidate_panel_id":f"strip.{i}" if i in (2,3,4) else None,
                "candidate_highlight_bbox_pdf_pt":[60.,100.,120.,175.] if i in (2,3,4) else None,
                "speaking_start_s":None,"speaking_end_s":None,
                "speech_to_visual_sync_verified":False}
                for i,u in enumerate(utterances,1)]}
    return job,prior


class FiveOriginalSlide4VisualCandidateTests(unittest.TestCase):
    def evaluate(self,job=None,prior=None):
        j,p=fixture()
        return complete_review_only_visual_candidates(
            job=j if job is None else job,
            prior=p if prior is None else prior)

    def test_five_candidates_two_new_visible_text_regions(self):
        r=self.evaluate()
        self.assertEqual(r["utterance_candidate_count"],5)
        self.assertEqual(r["unmapped_visual_candidate_count"],0)
        self.assertEqual(r["source_matched_figure_region_candidate_count"],3)
        self.assertEqual(r["original_slide_text_region_candidate_count"],2)
        self.assertEqual(r["utterance_candidates"][0]["review_target_id"],"s004.text.002")
        self.assertEqual(r["utterance_candidates"][4]["candidate_highlight_bbox_pdf_pt"],
                         [32.727,186.691,126.5,240.062])
        self.assertFalse(r["narration_timing_verified"])
        self.assertFalse(r["source_mathematical_review_approved"])
        self.assertFalse(r["student_publication_authorized"])

    def test_missing_or_swapped_visible_slide_target_fails_closed(self):
        for edit in ("drop","swap"):
            j,p=fixture()
            if edit=="drop":j["slides"][0]["visual_targets"].pop()
            else:
                t=j["slides"][0]["visual_targets"]
                t[3],t[4]=t[4],t[3]
            with self.subTest(edit=edit),self.assertRaises(ValueError):
                self.evaluate(job=j,prior=p)

    def test_wrong_or_missing_original_radical_expression_rejected(self):
        for i in (2,3,4,5):
            j,p=fixture()
            j["slides"][0]["visual_targets"][i]["visible_text"]="unrelated"
            with self.subTest(i=i),self.assertRaises(ValueError):
                self.evaluate(job=j,prior=p)

    def test_wrong_intro_text_or_narration_rejected(self):
        j,p=fixture()
        j["slides"][0]["visual_targets"][1]["visible_text"]="wrong introduction"
        with self.assertRaises(ValueError):self.evaluate(job=j,prior=p)
        j,p=fixture()
        j["slides"][0]["utterances"][0]["spoken_text"]="totally unrelated"
        with self.assertRaises(ValueError):self.evaluate(job=j,prior=p)

    def test_wrong_principal_root_narration_rejected(self):
        j,p=fixture()
        j["slides"][0]["utterances"][4]["spoken_text"]="Forget root and sign."
        with self.assertRaises(ValueError):self.evaluate(job=j,prior=p)

    def test_invalid_off_slide_or_overlap_bounds_rejected(self):
        j,p=fixture()
        j["slides"][0]["visual_targets"][4]["bbox_pdf_pt"][3]=400
        with self.assertRaises(ValueError):self.evaluate(job=j,prior=p)
        j,p=fixture()
        j["slides"][0]["visual_targets"][1]["bbox_pdf_pt"][3]=200
        with self.assertRaises(ValueError):self.evaluate(job=j,prior=p)

    def test_changed_original_spoken_sha_refused(self):
        j,p=fixture()
        p["utterance_candidates"][4]["original_spoken_sha256"]="d"*64
        with self.assertRaises(ValueError):self.evaluate(job=j,prior=p)

    def test_prior_three_panels_must_remain_and_not_be_approved(self):
        j,p=fixture()
        p["utterance_candidates"][2]["candidate_panel_id"]=None
        with self.assertRaises(ValueError):self.evaluate(job=j,prior=p)
        r=self.evaluate()
        self.assertTrue(all(not x["actual_highlighted_video_frames_verified"]
                            for x in r["utterance_candidates"]))

    def test_source_hash_mismatch_rejected(self):
        j,p=fixture()
        p["original_script_sha256"]="0"*64
        with self.assertRaises(ValueError):self.evaluate(job=j,prior=p)

    def test_real_original_source_when_mount_present(self):
        path=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not path:
            self.skipTest("Actual original source only on authorized Dell-115")
        r=inspect_original_slide4_five_visual_candidates(folder=Path(path))
        self.assertEqual(r["utterance_candidate_count"],5)
        self.assertEqual(r["unmapped_visual_candidate_count"],0)
        self.assertFalse(r["voice_provenance_verified"])
        self.assertFalse(r["student_publication_authorized"])


if __name__=="__main__":
    unittest.main()
