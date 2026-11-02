"""Reconciled 38 focus cases are not exhaustive academic permission."""
import copy
import unittest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_all41_38_source_academic_gap_reconciler import (
    merge_new_real_source_receipt,STATUS,TITLES,PROVED_NEW,
)
from selenium_pipeline.original_thomas86_all41_thirtyeight_joined_qa import NEW_STATUS

def fake_legacy_and_38_evidence():
    records={}
    sections={}
    for sec,count in (("8.4",17),("8.5",11),("8.6",13)):
        oldseen=16 if sec=="8.4" else 10 if sec=="8.5" else 9
        sections[sec]={
            "at_least_one_verified_source_focus_slide_count":oldseen,
            "original_slides_without_verified_focus":[1] if sec!="8.6" else [1,6,11,12],
        }
        for n in range(1,count+1):
            k=f"{sec}_slide{n}"
            title=k in TITLES
            focus=not title and k not in PROVED_NEW
            records[k]={
                "actual_original_source_source_spoken_focus_scene_present":focus,
                "presentation_title_only_no_math_focus_required":title,
                "source_math_audio_focus_required":not title,
                "publisher_scientific_topic_or_example_source_verified":k in ("8.6_slide6","8.6_slide12"),
                "actual_author_image_files":[{"publisher_figure_science_identity_verified":True}] if k=="8.6_slide11" else [],
                "original_mathematical_figure_semantic_and_word_coverage_complete":False,
                "remaining_source_academic_requirements":
                  (["NO_PUBLISHER_MATCHED_SOURCE_WAV_PIXEL_FOCUS_CLIP"] if not focus and not title else
                   ["ONE_OR_MORE_SCENE_FOCUSES_PASS_BUT_ALL_VISUAL_ELEMENTS_NOT_CERTIFIED"] if focus else []),
            }
    old={
        "original_source_slides":41,
        "original_source_pixel_and_audio_math_focus_slides":35,
        "full_original_production_gate_passed":False,
        "student_publication_authorized":False,
        "detailed_original_slide_acceptance_deficits":records,
        "original_sections":sections,
    }
    proof={
        "status":NEW_STATUS,
        "original_source_slides_across_three_sections":41,
        "original_source_spoken_focus_slides_across_three_sections":38,
        "new_actual_8_6_joined_original_slide_samples":13,
        "new_actual_8_6_joined_spoken_element_samples":21,
        "total_distinct_source_spoken_element_samples_across_three_sections":47,
        "student_publication_authorized":False,
        "original_8_6_twelve_spoken_focus_slides":list(range(2,14)),
        "actual_source_slide_pixel_qa":[{}]*13,
        "actual_original_spoken_highlight_pixel_qa":[{}]*21,
    }
    return old,proof

class CurrentOriginalAcademicDeficitReconcile(unittest.TestCase):
    def test_upgraded_source_samples_without_release(self):
        old,proof=fake_legacy_and_38_evidence()
        result=merge_new_real_source_receipt(old=old,proof=proof)
        self.assertEqual(result["status"],STATUS)
        self.assertEqual(result["original_source_pixel_and_audio_math_focus_slides"],38)
        self.assertEqual(result["original_substantive_slides_without_approved_source_spoken_focus"],[])
        self.assertEqual(result["original_slides_without_any_verified_focus"],3)
        self.assertFalse(result["student_publication_authorized"])
        self.assertFalse(result["full_original_production_gate_passed"])
        self.assertFalse(result["original_all_math_equation_and_figure_label_checks_complete"])
        for k in PROVED_NEW:
            rec=result["detailed_original_slide_acceptance_deficits"][k]
            self.assertTrue(rec["actual_original_source_source_spoken_focus_scene_present"])
            self.assertFalse(rec["original_mathematical_figure_semantic_and_word_coverage_complete"])

    def test_refuses_fake_spoken_sample_count(self):
        old,proof=fake_legacy_and_38_evidence()
        proof["new_actual_8_6_joined_spoken_element_samples"]=20
        with self.assertRaises(FigureIdentityReviewRequired):
            merge_new_real_source_receipt(old=old,proof=proof)

    def test_refuses_fake_academic_release_flag(self):
        old,proof=fake_legacy_and_38_evidence()
        proof["student_publication_authorized"]=True
        with self.assertRaises(FigureIdentityReviewRequired):
            merge_new_real_source_receipt(old=old,proof=proof)

    def test_refuses_title_as_substantive_spoken_focus(self):
        old,proof=fake_legacy_and_38_evidence()
        old["detailed_original_slide_acceptance_deficits"]["8.5_slide1"][
            "actual_original_source_source_spoken_focus_scene_present"]=True
        with self.assertRaises(FigureIdentityReviewRequired):
            merge_new_real_source_receipt(old=old,proof=proof)

if __name__=="__main__":
    unittest.main()
