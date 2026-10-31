"""Preserve full displayed formulas and source anchors, reject silent corruptions."""
import unittest

from selenium_pipeline.original_thomas84_multiline_math_witness import (
    EXPECTED,math_compact,assert_original_math_present)

class MultilineSourceMathTests(unittest.TestCase):
    def source_pages(self):
        pages=[""]*6
        for rec in EXPECTED.values():
            pages[rec["source_page"]-1]+="\n"+rec["source_context"]
        return pages

    def frames(self):
        frames=[""]*17
        for e in EXPECTED.values():
            frames[e["input_slide"]-1]+="\n"+e["input"]
            frames[e["result_slide"]-1]+="\n"+e["final"]
        return frames

    def test_original_complete_four_example_math_cases(self):
        rows=assert_original_math_present(
            frames=self.frames(),source_pages=self.source_pages())
        self.assertEqual([r["example"] for r in rows],
                         list(EXPECTED))

    def test_corrupt_integral_radical_sign_fails(self):
        frames=self.frames()
        frames[11]=frames[11].replace(r"\sqrt{9 - x^{2}}",
                                      r"\sqrt{9 + x^{2}}")
        with self.assertRaises(Exception):
            assert_original_math_present(frames=frames,
                                         source_pages=self.source_pages())

    def test_corrupt_final_antiderivative_coefficient_fails(self):
        frames=self.frames()
        frames[14]=frames[14].replace(r"\frac{1}{5}\ln",
                                      r"\frac{2}{5}\ln")
        with self.assertRaises(Exception):
            assert_original_math_present(frames=frames,
                                         source_pages=self.source_pages())

    def test_omitted_original_publisher_example_anchor_fails(self):
        pages=self.source_pages()
        pages[3]=pages[3].replace("EXAMPLE 4","UNKNOWN")
        with self.assertRaises(Exception):
            assert_original_math_present(frames=self.frames(),source_pages=pages)

    def test_missing_or_reflowed_complete_result_blocks(self):
        frames=self.frames()
        frames[12]=frames[12].replace(r"\sin^{-1}",r"\cos^{-1}")
        with self.assertRaises(Exception):
            assert_original_math_present(frames=frames,
                                         source_pages=self.source_pages())

    def test_math_whitespace_is_allowed_but_symbols_not(self):
        self.assertEqual(math_compact(r"\sqrt{ 9 - x^{2} }"),
                         math_compact(r"\sqrt{9-x^{2}}"))
        self.assertNotEqual(math_compact(r"\sqrt{ 9 + x^{2} }"),
                            math_compact(r"\sqrt{9-x^{2}}"))

if __name__=="__main__":
    unittest.main()
