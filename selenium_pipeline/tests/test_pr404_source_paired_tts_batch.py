"""No paid TTS can render stale source speech or a third original slide."""
import unittest
from selenium_pipeline.runner import blocks
from selenium_pipeline.original_thomas84_corrected_tts_batch import (
    SLOTS,STAGE_IDS,source_bound_staging_script)
from selenium_pipeline.original_thomas84_arctangent_paired_repair import (
    NEW_WORDS,OLD_WORDS)
from selenium_pipeline.original_thomas84_cumulative_academic_repairs import (
    CORRECT_REVIEW_SPEECH,OLD_REVIEW_SPEECH)

class OriginalCumulativePairedTTSBatch(unittest.TestCase):
    def corrected(self):
        return {
            6: ("First, source verified inverse graph. "+" ".join(NEW_WORDS)),
            17: ("Questions on substitution and angle domains. "+
                 CORRECT_REVIEW_SPEECH),
            11: "Not authorized for production sound."}

    def test_only_two_consecutive_provider_slots_staged(self):
        staged=source_bound_staging_script(self.corrected())
        self.assertEqual([n for n,_ in blocks(staged)],list(STAGE_IDS))
        self.assertNotIn("Not authorized for production sound",staged)

    def test_mapping_source_6_17_not_replaced_by_one_two(self):
        self.assertEqual(SLOTS,(6,17))
        self.assertEqual(STAGE_IDS,(1,2))
        entries=dict(blocks(source_bound_staging_script(self.corrected())))
        self.assertTrue(all(word in entries[1] for word in NEW_WORDS))
        self.assertIn(CORRECT_REVIEW_SPEECH,entries[2])

    def test_original_wrong_graph_audio_text_is_rejected(self):
        source=self.corrected()
        source[6]=" ".join(OLD_WORDS)
        with self.assertRaises(Exception):
            source_bound_staging_script(source)

    def test_original_wrong_review_domain_audio_text_is_rejected(self):
        source=self.corrected()
        source[17]="Original: "+OLD_REVIEW_SPEECH
        with self.assertRaises(Exception):
            source_bound_staging_script(source)

    def test_missing_source_slide_fails_closed(self):
        source=self.corrected()
        del source[17]
        with self.assertRaises(Exception):
            source_bound_staging_script(source)

if __name__=="__main__":
    unittest.main()
