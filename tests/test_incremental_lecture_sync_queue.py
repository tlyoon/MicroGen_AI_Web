"""Portable fault injection for cross-subchapter incremental lecture recovery."""
import tempfile
import unittest
import wave
from pathlib import Path

import pymupdf

from selenium_pipeline.incremental_lecture_sync_queue import (
    inspect_batch, inspect_folder, main,
)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired


def make_subchapter(base:Path,number:str,*,with_figure:bool=True):
    folder=base/number
    folder.mkdir(parents=True)
    original=pymupdf.open()
    original.new_page(width=300,height=200).insert_text((20,20),"Source")
    original.save(folder/"source.pdf")
    original.close()
    pdf=pymupdf.open()
    for i in range(3):
        page=pdf.new_page(width=360,height=270)
        page.insert_text((40,50),f"Slide {i+1} visible explanation")
        if i==1 and with_figure:
            page.draw_rect(pymupdf.Rect(80,100,150,160),color=(0,0,1))
    pdf.save(folder/"slides.pdf")
    pdf.close()
    parts=["A clear first slide explains the topic.",
           "The middle slide shows the geometric figure.",
           "The last slide summarizes the solution."]
    (folder/"script.txt").write_text("".join(
        f"**Slide {i} [2 sec]:\n{text}**\n\n"
        for i,text in enumerate(parts,1)),encoding="utf8")
    for i in range(1,4):
        with wave.open(str(folder/f"slide{i}.wav"),"wb") as track:
            track.setnchannels(1)
            track.setsampwidth(2)
            track.setframerate(8000)
            track.writeframes(b"\x00\x00"*16000)
    return folder


class IncrementalLectureSyncQueueTests(unittest.TestCase):
    def test_one_math_figure_does_not_block_other_slides(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            make_subchapter(base,"8.4")
            q=inspect_batch(root=base,subchapters=("8.4",))
            result=q["subchapters"][0]
            self.assertEqual(result["slide_count"],3)
            self.assertEqual(result["original_wav_count"],3)
            self.assertEqual(len(result["candidate_parts"]),1)
            self.assertEqual(
                result["slides"][1]["element_mapping_next_action"],
                "SOURCE_MATH_OR_VECTOR_ELEMENT_MAPPING_NEEDED")
            self.assertEqual(
                result["slides"][0]["element_mapping_next_action"],
                "SOURCE_TEXT_ELEMENT_MAPPING_NEEDED")
            self.assertTrue(all(
                not x["ready_for_billed_element_tts"] for x in result["slides"]))
            self.assertFalse(q["figure83_layout_reopen_required"])
            self.assertFalse(q["spoken_to_element_timing_verified"])
    def test_all_real_original_utterances_and_hashes_are_frozen(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            folder=make_subchapter(base,"8.5")
            record=inspect_folder(folder)
            self.assertEqual(len(record["slides"]),3)
            self.assertEqual(sum(len(x["original_verbatim_utterances"])
                                 for x in record["slides"]),3)
            self.assertEqual(len(record["source_sha256"]),64)
            self.assertTrue(record["all_original_assets_preserved"])
            self.assertFalse(record["finished_lecture_production_authorized"])
    def test_missing_audio_fails_one_subchapter_instead_of_pretending_pass(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            folder=make_subchapter(base,"8.6")
            (folder/"slide2.wav").unlink()
            with self.assertRaises((ValueError,FigureIdentityReviewRequired)):
                inspect_folder(folder)
    def test_read_only_queue_written_only_to_new_external_path(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)/"teaching"
            base.mkdir()
            make_subchapter(base,"8.4")
            output=Path(t)/"queue.json"
            result=main(["--root",str(base),"--subchapters","8.4",
                         "--out",str(output)])
            self.assertEqual(result,0)
            self.assertTrue(output.is_file())
            with self.assertRaises(FigureIdentityReviewRequired):
                main(["--root",str(base),"--subchapters","8.4",
                      "--out",str(output)])
    def test_missing_one_subchapter_does_not_stall_independent_neighbors(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            make_subchapter(base,"8.4")
            make_subchapter(base,"8.6")
            result=inspect_batch(root=base,subchapters=("8.4","8.5","8.6"))
            self.assertEqual(result["independently_readable_subchapters"],2)
            self.assertEqual(result["blocked_subchapters"],1)
            self.assertEqual(
                result["subchapters"][1]["status"],
                "SOURCE_SUBCHAPTER_BLOCKED_INDEPENDENT_RECOVERY")
            self.assertEqual(result["subchapters"][0]["slide_count"],3)
            self.assertEqual(result["subchapters"][2]["slide_count"],3)
            self.assertFalse(result["student_publication_authorized"])
    def test_invalid_or_duplicate_chapter_names_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            for names in (("8.4","8.4"),("../8.4",),("8.4/../../",),("9",)):
                with self.assertRaises(FigureIdentityReviewRequired):
                    inspect_batch(root=base,subchapters=names)
