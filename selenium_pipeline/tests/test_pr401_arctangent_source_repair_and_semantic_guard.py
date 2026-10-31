"""Two original Figure 8.3 academic defects must block future production."""
import unittest

from selenium_pipeline.automatic_math_semantic_qa import _detect
from selenium_pipeline.original_thomas84_arctangent_paired_repair import (
    OLD_WORDS,NEW_WORDS,OLD_TEX,NEW_TEX)

class ArctangentMathematicalNarrationGuardTests(unittest.TestCase):
    def test_original_vertical_asymptote_confusion_blocks(self):
        findings=_detect(6,OLD_WORDS[1])
        self.assertIn("arctangent_horizontal_not_vertical_asymptotes",
                      {x["rule"] for x in findings})

    def test_original_inverse_not_one_to_one_confusion_blocks(self):
        self.assertIn("inverse_function_one_to_one_confusion",
                      {x["rule"] for x in _detect(6,OLD_WORDS[0])})

    def test_corrected_words_have_no_wrong_graph_math(self):
        self.assertEqual(_detect(6,NEW_WORDS[0]+" "+NEW_WORDS[1]),[])

    def test_legitimate_vertical_asymptote_of_tangent_is_allowed(self):
        statement=("The tangent function has vertical asymptotes "
                   "at negative pi over two and positive pi over two.")
        self.assertEqual(_detect(6,statement),[])

    def test_legitimate_arctangent_horizontal_asymptote_is_allowed(self):
        statement=("The arctangent function has horizontal asymptotes "
                   "at negative pi over two and positive pi over two.")
        self.assertEqual(_detect(6,statement),[])

    def test_new_slide_notation_changes_exact_one_source_bullet(self):
        lecture=r"\begin{frame}{Reversibility and Inverse Functions (1)}"+"\n"
        original=lecture+OLD_TEX+"\n"+r"\end{frame}"
        changed=original.replace(OLD_TEX,NEW_TEX)
        self.assertEqual(changed.replace(NEW_TEX,OLD_TEX),original)
        self.assertEqual(changed.count(NEW_TEX),1)

    def test_both_wrong_sentences_are_distinct(self):
        self.assertEqual(len(OLD_WORDS),len(NEW_WORDS))
        self.assertEqual(len(set(OLD_WORDS)),2)
        self.assertTrue(all(a!=b for a,b in zip(OLD_WORDS,NEW_WORDS)))

if __name__=="__main__":
    unittest.main()
