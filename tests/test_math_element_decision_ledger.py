import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.math_element_decision_ledger import create
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

class LedgerTests(unittest.TestCase):
    def test_cannot_accept_forged_original_hashes(self):
        with patch('selenium_pipeline.math_element_decision_ledger._sha',return_value='a'), patch('selenium_pipeline.math_element_decision_ledger.original_utterances',return_value={'original_slide_count':5,'original_utterance_count':8,'source_sha256':'b','slides_sha256':'a','script_sha256':'a'}), patch('selenium_pipeline.math_element_decision_ledger.figure_hints',return_value={}):
            with self.assertRaises(FigureIdentityReviewRequired):
                create(source=Path('s'),slides=Path('d'),script=Path('t'))
