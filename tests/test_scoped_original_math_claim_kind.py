"""An original section heading is source metadata, not mathematical validation."""
import unittest
from selenium_pipeline.scoped_original_math_consensus import _agreed_evidence_kind


class SourceAgreementType(unittest.TestCase):
    def setUp(self):
        self.title="8.4 Trigonometric Substitutions"
        self.job={"slides":[{"slide":1,"visual_targets":[{
            "id":"s001.text.001","visible_text":self.title}]}]}
        self.original={"spoken_text":self.title}
        self.first={"target_id":"s001.text.001",
                    "verbatim_source_quote":self.title}
        self.challenge={"verbatim_source_quote":self.title}

    def classify(self):
        return _agreed_evidence_kind(
            job=self.job,original=self.original,
            first=self.first,challenge=self.challenge)

    def test_real_title_analog_is_only_metadata(self):
        self.assertEqual(self.classify(),"ORIGINAL_SECTION_TITLE_METADATA_ONLY")

    def test_nonmatching_source_page_quote_is_not_title(self):
        self.challenge["verbatim_source_quote"]="Trigonometric identities"
        self.assertEqual(self.classify(),"UNCLASSIFIED_DOMAIN_CLAIM")

    def test_equation_does_not_qualify_from_unrelated_title(self):
        self.original["spoken_text"]="x equals a tan u"
        self.assertEqual(self.classify(),"UNCLASSIFIED_DOMAIN_CLAIM")

    def test_title_must_be_visible_on_same_selected_target(self):
        self.job["slides"][0]["visual_targets"][0]["visible_text"]="Different title"
        self.assertEqual(self.classify(),"UNCLASSIFIED_DOMAIN_CLAIM")

    def test_non_section_formula_on_slide_one_is_not_metadata(self):
        formula="x = a tan u"
        self.original["spoken_text"]=formula
        self.job["slides"][0]["visual_targets"][0]["visible_text"]=formula
        self.first["verbatim_source_quote"]=formula
        self.challenge["verbatim_source_quote"]=formula
        self.assertEqual(self.classify(),"UNCLASSIFIED_DOMAIN_CLAIM")

    def test_later_slide_is_never_autocategorized(self):
        self.job["slides"][0]["slide"]=3
        self.assertEqual(self.classify(),"UNCLASSIFIED_DOMAIN_CLAIM")

    def test_missing_target_cannot_be_classified_as_supported_title(self):
        self.first["target_id"]="invented"
        self.assertEqual(self.classify(),"UNCLASSIFIED_DOMAIN_CLAIM")

    def test_untrusted_no_speech_is_not_metadata(self):
        self.original["spoken_text"]=None
        self.assertEqual(self.classify(),"UNCLASSIFIED_DOMAIN_CLAIM")


if __name__=="__main__":
    unittest.main()
