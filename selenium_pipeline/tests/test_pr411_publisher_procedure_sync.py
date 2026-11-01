"""Four source-book procedure steps and genuine speech must be time distinct."""
import unittest
from selenium_pipeline.original_thomas84_slide8_procedure_sync import (
    KEYWORDS,SPOKEN_PREFIX,STATUS)
from selenium_pipeline.original_thomas84_multipart_qa_preview import split_slides

class PublisherSourceProcedureTests(unittest.TestCase):
    def test_all_four_original_mathematical_procedural_steps_are_distinct(self):
        self.assertEqual(sorted(KEYWORDS),[1,2,3,4])
        self.assertIn("differential",KEYWORDS[1])
        self.assertIn("integrand",KEYWORDS[2])
        self.assertIn("reversib",KEYWORDS[3])
        self.assertIn("triangle",KEYWORDS[4])

    def test_spoken_source_order_is_one_to_one(self):
        self.assertEqual([SPOKEN_PREFIX[i].split(",")[0]
                          for i in range(1,5)],
                         ["first","second","third","fourth"])

    def test_no_source_publisher_or_acoustic_approval_by_name_only(self):
        self.assertIn("SOURCE_TIMED_PENDING_PIXELS",STATUS)

    def test_600_sec_split_limit_remains_independent_of_one_clip(self):
        self.assertEqual(split_slides([44.08,565.0-44.08,196.42]),
                         [[1,2],[3]])

if __name__=="__main__":
    unittest.main()
