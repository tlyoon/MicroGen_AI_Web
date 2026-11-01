"""Original source CAS/partial-fraction narrated principles, no invented math."""
import unittest
from selenium_pipeline.original_thomas85_86_summary_cas import CASES,STATUS
class TrueSourcePublisherSummary(unittest.TestCase):
    def test_original_publisher_summary_and_cas_pages(self):
        self.assertEqual(sorted(CASES),[("8.5",10),("8.6",9)])
        self.assertEqual([len(CASES[x]["events"]) for x in sorted(CASES)],[3,3])
        self.assertEqual([e[1] for e in CASES["8.5",10]["events"]],[1,2,3])
        self.assertEqual([e[1] for e in CASES["8.6",9]["events"]],[1,4,5])
    def test_original_cas_arbitrary_constant_warning_preserved(self):
        self.assertIn(r"$+C$",CASES["8.6",9]["math_tex"][-1])
        self.assertIn("polynomial long division",CASES["8.5",10]["events"][1][3][1])
        self.assertIn("PIXEL_QA_PASS",STATUS)
if __name__=="__main__":
    unittest.main()
