"""Refine remaining source figures/math/phonetics worklist without release."""
import unittest
from selenium_pipeline.original_all41_38_source_academic_gap_reconciler import (
    NEW_FOCUS_PARTIAL_MATH_WARNINGS,
    merge_new_real_source_receipt,
)
from selenium_pipeline.tests.test_pr445_original_38_source_scholarly_deficit_reconciliation import (
    fake_legacy_and_38_evidence,
)

class OriginalRemainingElementCoverage(unittest.TestCase):
    def test_stale_missing_wav_focus_not_left_after_true_recorded_proof(self):
        old,new=fake_legacy_and_38_evidence()
        for key,(obsolete,current) in NEW_FOCUS_PARTIAL_MATH_WARNINGS.items():
            old["detailed_original_slide_acceptance_deficits"][key][
                "remaining_source_academic_requirements"].append(obsolete)
        reconciled=merge_new_real_source_receipt(old=old,proof=new)
        for key,(obsolete,current) in NEW_FOCUS_PARTIAL_MATH_WARNINGS.items():
            flags=reconciled["detailed_original_slide_acceptance_deficits"][key][
                "remaining_source_academic_requirements"]
            self.assertNotIn(obsolete,flags)
            self.assertIn(current,flags)
            self.assertFalse(reconciled["student_publication_authorized"])

    def test_exact_scholarly_worklist_is_inventory_only_not_source_proof(self):
        old,new=fake_legacy_and_38_evidence()
        entry=old["detailed_original_slide_acceptance_deficits"]["8.6_slide6"]
        entry["remaining_source_academic_requirements"].append(
            "FULL_EQUIVALENCE_OF_EACH_INTERMEDIATE_MATH_TOKEN_NOT_PROVEN")
        entry["author_math_command_occurrence_count"]=6
        entry["author_equation_environment_count"]=2
        entry["author_source_item_count"]=3
        other=old["detailed_original_slide_acceptance_deficits"]["8.4_slide4"]
        other["actual_author_image_files"].append({
            "publisher_figure_science_identity_verified":False,
            "source_file":"Figure 8.2.png","sha256":"demo-pinned-sha",
            "rendered_pdf_has_images":True})
        result=merge_new_real_source_receipt(old=old,proof=new)
        backlog=result["unverified_intermediate_mathematical_source_per_slide_worklist"]
        self.assertEqual(backlog[0]["slide"],"8.6_slide6")
        self.assertFalse(backlog[0]["full_equation_scientific_equivalence_verified"])
        figures=result["figure_identity_and_full_panel_label_worklist_for_this_register"]
        self.assertEqual(figures[0]["author_source_figure"],"Figure 8.2.png")
        self.assertTrue(figures[0]["earlier_specialized_figure_evidence_may_exist"])
        self.assertFalse(result["original_all_math_equation_and_figure_label_checks_complete"])

if __name__=="__main__":
    unittest.main()
