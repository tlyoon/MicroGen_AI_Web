"""Only purely presentational title frames are exempt from math focus."""
import unittest
from selenium_pipeline.original_three_section_academic_remaining_inventory import (
    is_structural_title_only,
)

class OriginalBeamerTitleOnlyExemption(unittest.TestCase):
    def test_exact_empty_beamer_title_page_is_structural(self):
        self.assertTrue(is_structural_title_only(
            r"\begin{frame}"+"\n"+r"\titlepage"+"\n"+r"\end{frame}"))

    def test_title_plus_equation_is_not_exempt(self):
        self.assertFalse(is_structural_title_only(
            r"\begin{frame}"+"\n"+r"\titlepage"+"\n"
            +r"\[E=mc^2\]"+"\n"+r"\end{frame}"))

    def test_title_plus_figure_or_summary_is_not_exempt(self):
        self.assertFalse(is_structural_title_only(
            r"\begin{frame}"+"\n"+r"\titlepage"+"\n"
            +r"\includegraphics{figure.png}"+"\n"+r"\end{frame}"))
        self.assertFalse(is_structural_title_only(
            r"\begin{frame}{Summary}"+"\n"+r"\item Content"+"\n"+r"\end{frame}"))

    def test_unrelated_title_word_does_not_exempt(self):
        self.assertFalse(is_structural_title_only(
            r"\begin{frame}{Title}"+"\n"+"Summary of physics"
            +"\n"+r"\end{frame}"))


if __name__=="__main__":
    unittest.main()
