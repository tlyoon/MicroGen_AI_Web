"""Only true publisher-grounded formula targets can be promoted."""
import copy
import unittest
from selenium_pipeline.original_thomas84_five_worked_math_sync_batch import (
    WORKED,validate_config,BATCH_STATUS)

class FiveOriginalSourceFormulaHighlights(unittest.TestCase):
    def test_exact_real_original_worked_example_targets(self):
        validate_config()
        self.assertEqual(sorted(WORKED),[10,11,13,14,15])
        self.assertEqual([WORKED[n][0] for n in sorted(WORKED)],
                         ["example_1","example_2","example_3",
                          "example_4","example_4"])
        self.assertEqual([WORKED[n][1] for n in sorted(WORKED)],
                         ["final","final","final","input","final"])

    def test_real_math_acoustic_source_evidence_only_not_all_derivation(self):
        self.assertIn("SOURCE_VERIFIED_PIXEL_PASS",BATCH_STATUS)
        self.assertEqual([WORKED[n][2] for n in sorted(WORKED)],
                         [4,4,4,1,4])

    def test_wrong_or_missing_source_example_blocked(self):
        changed=copy.deepcopy(WORKED)
        changed[10]=("example_2",*changed[10][1:])
        with self.assertRaises(Exception):
            validate_config(changed)
        changed=copy.deepcopy(WORKED)
        del changed[13]
        with self.assertRaises(Exception):
            validate_config(changed)

    def test_nonfinite_rect_or_reversed_geometry_fails_closed(self):
        changed=copy.deepcopy(WORKED)
        row=list(changed[14])
        row[3]=[30.,float("nan"),228.,129.]
        changed[14]=tuple(row)
        with self.assertRaises(Exception):
            validate_config(changed)
        row[3]=[230.,73.,228.,129.]
        changed[14]=tuple(row)
        with self.assertRaises(Exception):
            validate_config(changed)

    def test_invalid_real_audio_probe_not_accepted(self):
        changed=copy.deepcopy(WORKED)
        row=list(changed[15])
        row[5]=row[6]
        changed[15]=tuple(row)
        with self.assertRaises(Exception):
            validate_config(changed)

if __name__=="__main__":
    unittest.main()
