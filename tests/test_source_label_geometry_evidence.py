"""Offline real-rendered-PDF source label anchoring; never auto-approve figure."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.source_label_geometry_evidence import (
    inspect,SourceLabelGeometryError,main,
)


def make_assets(root:Path,*,duplicate_source_figure=False,duplicate_slide_label=False):
    with pymupdf.open() as doc:
        first=doc.new_page()
        first.insert_text((35,55),"EXAMPLE 1",fontsize=16)
        first.insert_text((35,100),"FIGURE 2.3",fontsize=16)
        if duplicate_source_figure:
            second=doc.new_page()
            second.insert_text((35,55),"FIGURE 2.3",fontsize=16)
        doc.save(root/"source.pdf")
    with pymupdf.open() as doc:
        first=doc.new_page()
        first.insert_text((35,55),"Example 1",fontsize=16)
        first.insert_text((35,100),"Figure 2.3",fontsize=16)
        if duplicate_slide_label:
            first.insert_text((35,130),"Example 1",fontsize=16)
        doc.save(root/"slides.pdf")
    (root/"script.txt").write_text(
        "**Slide 1 [3 sec]:\nThe original example illustrates the source expression.",
        encoding="utf8")


class SourceLabelGeometryTests(unittest.TestCase):
    def test_unique_source_headers_are_exact_pdf_geometry_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            make_assets(folder)
            originals={p.name:p.read_bytes() for p in folder.iterdir()}
            report=inspect(source=folder/"source.pdf",slides=folder/"slides.pdf",
                           script=folder/"script.txt")
            self.assertEqual(report["slide_count"],1)
            self.assertEqual(report["labels_detected"],2)
            self.assertEqual(report["uniquely_source_grounded_label_count"],2)
            for row in report["slides"][0]["labels"]:
                self.assertEqual(row["original_header_source_pages"],[1])
                self.assertEqual(len(row["label_bbox_pdf_pt"]),4)
                self.assertEqual(len(row["candidate_source_visual_id"]),24)
                self.assertFalse(row["highlight_approved"])
                self.assertFalse(row["figure_body_geometry_verified"])
                self.assertFalse(row["narrated_word_timing_verified"])
            self.assertFalse(report["production_video_approved"])
            self.assertEqual(originals,{p.name:p.read_bytes() for p in folder.iterdir()})

    def test_caption_label_not_timed_without_explicit_script_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);make_assets(folder)
            report=inspect(source=folder/"source.pdf",slides=folder/"slides.pdf",
                           script=folder/"script.txt")
            self.assertEqual(report["source_anchored_labels_explicitly_spoken"],0)
            (folder/"script.txt").write_text(
                "**Slide 1 [3 sec]:\nExample one includes Figure two point three.",
                encoding="utf8")
            named=inspect(source=folder/"source.pdf",slides=folder/"slides.pdf",
                          script=folder/"script.txt")
            self.assertEqual(named["source_anchored_labels_explicitly_spoken"],2)
            self.assertFalse(named["word_timing_verified"])
            self.assertFalse(named["production_video_approved"])

    def test_repeated_source_figure_header_rejected_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);make_assets(folder,duplicate_source_figure=True)
            report=inspect(source=folder/"source.pdf",slides=folder/"slides.pdf",
                           script=folder/"script.txt")
            rows={v["label"]:v for v in report["slides"][0]["labels"]}
            self.assertFalse(rows["Figure 2.3"]["unique_source_header_and_visible_bbox"])
            self.assertIsNone(rows["Figure 2.3"]["source_pdf_page"])
            self.assertIsNone(rows["Figure 2.3"]["label_bbox_pdf_pt"])
            self.assertTrue(rows["Example 1"]["unique_source_header_and_visible_bbox"])

    def test_duplicate_slide_label_never_approves_bbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);make_assets(folder,duplicate_slide_label=True)
            report=inspect(source=folder/"source.pdf",slides=folder/"slides.pdf",
                           script=folder/"script.txt")
            example=next(x for x in report["slides"][0]["labels"]
                         if x["label"]=="Example 1")
            self.assertFalse(example["unique_source_header_and_visible_bbox"])

    def test_script_page_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);make_assets(folder)
            (folder/"script.txt").write_text(
                "**Slide 1 [2 sec]:\nFirst.\n\n**Slide 2 [2 sec]:\nSecond.",encoding="utf8")
            with self.assertRaisesRegex(SourceLabelGeometryError,"count invalid"):
                inspect(source=folder/"source.pdf",slides=folder/"slides.pdf",
                        script=folder/"script.txt")

    def test_cli_cannot_overwrite_or_write_in_original_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"original"
            folder.mkdir()
            make_assets(folder)
            args=["--source",str(folder/"source.pdf"),
                  "--slides",str(folder/"slides.pdf"),
                  "--script",str(folder/"script.txt"),
                  "--output",str(folder/"anchor.json")]
            with self.assertRaisesRegex(SourceLabelGeometryError,"Never write"):
                main(args)
            self.assertFalse((folder/"anchor.json").exists())


if __name__=="__main__":
    unittest.main()
