import json
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.spoken_math_review import build_review, main, NarrationReviewError

def sample():
    s={"schema_version":1,"part_id":"part_03",
       "slides":[{"slide_id":"p.s1","title":"Example",
       "elements":[{"element_id":"p.s1.e1","source_page":6}]}],
       "narration_segments":[{"segment_id":"n1","slide_id":"p.s1",
       "element_ids":["p.s1.e1"],
       "spoken_text":"Take the square root and divide by the denominator."}]}
    bind={"source_pdf_sha256":"a"*64,
          "bindings":{"p.s1.e1":{"source_pdf_page":6}}}
    return s,bind

class SpokenMathReviewTests(unittest.TestCase):
    def test_nonapproving_risk_packet(self):
        s,b=sample();out=build_review(s,b)
        self.assertIn("NOT APPROVED",out)
        self.assertIn("Radical scope",out)
        self.assertIn("Fraction scope",out)
        self.assertIn("Source PDF page(s): 6",out)

    def test_source_page_mismatch_fails(self):
        s,b=sample()
        b["bindings"]["p.s1.e1"]["source_pdf_page"]=7
        with self.assertRaisesRegex(NarrationReviewError,"Source binding mismatch"):
            build_review(s,b)

    def test_unknown_narrated_element_fails(self):
        s,b=sample()
        s["narration_segments"][0]["element_ids"]=["wrong"]
        with self.assertRaisesRegex(NarrationReviewError,"Cross-slide"):
            build_review(s,b)

    def test_existing_output_not_overwritten(self):
        s,b=sample()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            (p/"s.json").write_text(json.dumps(s))
            (p/"b.json").write_text(json.dumps(b))
            argv=["--storyboard",str(p/"s.json"),"--source-bindings",str(p/"b.json"),"--out",str(p/"review.md")]
            self.assertEqual(main(argv),0)
            with self.assertRaises(FileExistsError): main(argv)

if __name__=="__main__":
    unittest.main()
