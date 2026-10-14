"""Uncaptioned exercise graphs require an explicit source-bound experiment scope."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.figure_practice_disposition import (
    PracticeDispositionError, ENABLE_FLAG, MANIFEST,
    create_experimental_disposition, practice_page_excluded,
)
from selenium_pipeline.runner import valid


class PracticeDispositionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        (self.root/"source.pdf").write_bytes(b"fixed synthetic pdf")
        self.page=self.root/"pages"/"page_9"
        self.page.mkdir(parents=True)
        (self.page/"page_9.png").write_bytes(b"image of page 9")
        self.crop=self.root/"crops"/"page_9"
        self.crop.mkdir(parents=True)
        (self.crop/"fig_1.png").write_bytes(b"graph from Exercise 1")
        (self.crop/"fig_2.png").write_bytes(b"graph from Exercise 2")
        (self.crop/"page_9.png").write_bytes(b"full page")
        # The fake text is standing in for reading the real PDF's text layer.
        self.pdf_text="Exercises 2.2  Limits from Graphs  For the function g(x) graphed here"
        self.text=patch(
            "selenium_pipeline.figure_practice_disposition._pdf_page_text",
            side_effect=lambda pdf,page:self.pdf_text
        )
        self.text.start()
        self.addCleanup(self.text.stop)

    def _create(self):
        return create_experimental_disposition(self.root,9,"Limits from Graphs")

    def _enabled(self):
        return patch.dict(os.environ,{ENABLE_FLAG:"1"})

    def test_default_requires_mapping_not_automatic_practice_exclusion(self):
        self.assertFalse(practice_page_excluded(self.root,9))
        self.assertFalse(valid("figures",self.root))
        self._create()
        with self.assertRaisesRegex(PracticeDispositionError,"explicit"):
            practice_page_excluded(self.root,9)

    def test_explicit_experiment_preserves_originals_and_blocks_publication(self):
        path=self._create()
        self.assertTrue(path.exists())
        data=json.loads(path.read_text())
        self.assertEqual(data["pages"][0]["scientific_review_status"],"unreviewed")
        self.assertFalse(data["pages"][0]["student_publication_permitted"])
        self.assertEqual(len(data["pages"][0]["original_crops"]),2)
        with self._enabled():
            self.assertTrue(practice_page_excluded(self.root,9))
            self.assertFalse(practice_page_excluded(self.root,8))
            self.assertTrue(valid("figures",self.root))
        self.assertEqual((self.crop/"fig_1.png").read_bytes(),b"graph from Exercise 1")

    def test_page_and_source_edits_invalidate_exclusion(self):
        self._create()
        with self._enabled():
            (self.root/"source.pdf").write_bytes(b"changed source")
            with self.assertRaisesRegex(PracticeDispositionError,"Source PDF changed"):
                practice_page_excluded(self.root,9)

    def test_crop_edits_invalidate_exclusion(self):
        self._create()
        with self._enabled():
            (self.crop/"fig_2.png").write_bytes(b"cropped incorrectly")
            with self.assertRaisesRegex(PracticeDispositionError,"do not match"):
                practice_page_excluded(self.root,9)

    def test_new_original_crop_invalidates_exclusion(self):
        self._create()
        with self._enabled():
            (self.crop/"fig_3.png").write_bytes(b"extra graph")
            with self.assertRaisesRegex(PracticeDispositionError,"do not match"):
                practice_page_excluded(self.root,9)

    def test_page_png_edit_invalidates_exclusion(self):
        self._create()
        with self._enabled():
            (self.page/"page_9.png").write_bytes(b"changed page image")
            with self.assertRaisesRegex(PracticeDispositionError,"do not match"):
                practice_page_excluded(self.root,9)

    def test_named_source_figures_cannot_be_skipped_as_exercises(self):
        self.pdf_text="Limits from Graphs Figure 2.10 and Exercises 2.2"
        with self.assertRaisesRegex(PracticeDispositionError,"numbered Figure"):
            self._create()
        self.assertFalse((self.root/MANIFEST).exists())

    def test_wrong_source_text_anchor_is_rejected(self):
        with self.assertRaisesRegex(PracticeDispositionError,"not found"):
            create_experimental_disposition(self.root,9,"Invented appendix caption")
        self.assertFalse((self.root/MANIFEST).exists())

    def test_refuse_silent_overwrite_and_manifest_tampering(self):
        self._create()
        with self.assertRaises(FileExistsError):
            self._create()
        f=self.root/MANIFEST
        data=json.loads(f.read_text(encoding="utf-8"))
        data["pages"][0]["student_publication_permitted"]=True
        f.write_text(json.dumps(data),encoding="utf-8")
        with self._enabled():
            with self.assertRaisesRegex(PracticeDispositionError,"do not match"):
                practice_page_excluded(self.root,9)

    def test_invalid_json_and_hidden_exclusion_does_not_fall_back(self):
        (self.root/MANIFEST).write_text("{not valid",encoding="utf-8")
        with self._enabled():
            with self.assertRaises(ValueError):
                practice_page_excluded(self.root,9)

    def test_no_unreviewed_practice_mode_without_explicit_flag(self):
        self._create()
        self.assertFalse((self.root/"Figure 2.9.png").exists())
        with self.assertRaises(PracticeDispositionError):
            valid("figures",self.root)


if __name__=="__main__":
    unittest.main()
