"""Two source text review candidates must not bypass genuine media gates."""
import os
from copy import deepcopy
from pathlib import Path
import unittest

from selenium_pipeline.original_slide4_audio_eligibility import (
    summarize_slide4_audio_gate,inspect_original_slide4_audio_readiness,
)
from tests.test_original_slide4_audio_eligibility import witness


def expanded_visual(job,prior):
    rows=[]
    for i,(u,c) in enumerate(zip(
            job["slides"][0]["utterances"],
            prior["utterance_candidates"])):
        visual=(i in (1,2,3))
        if visual:
            c.setdefault("candidate_highlight_bbox_pdf_pt",[60.,100.,120.,175.])
            c.setdefault("original_source_strip_sha256",f"{i+1:064x}")
        rows.append({
            **c,
            "candidate_kind":("SOURCE_MATCHED_TRIANGLE_RASTER_STRIP" if visual
                              else "VISIBLE_SLIDE_TEXT_REGION" if i==0
                              else "MULTILINE_RADICAL_AND_ABSOLUTE_VALUE_TEXT_REGION"),
            "review_target_id":c["candidate_panel_id"] if visual
                                else "s004.text.002" if i==0
                                else "s004.text.003-through-s004.text.006",
            "candidate_highlight_bbox_pdf_pt":(
                c["candidate_highlight_bbox_pdf_pt"] if visual
                else [10.909,57.794,339.762,82.252] if i==0
                else [32.727,186.691,126.5,240.062]),
            "actual_audio_start_s":None,
            "actual_audio_end_s":None,
            "source_math_independently_agreed":False,
            "actual_highlighted_video_frames_verified":False,
        })
    return {
        "status":"FIVE_ORIGINAL_SLIDE4_VISUAL_CANDIDATES_NOT_TIMED_OR_APPROVED",
        "source_sha256":job["source_sha256"],
        "slides_sha256":job["slides_sha256"],
        "script_sha256":job["script_sha256"],
        "utterance_candidate_count":5,
        "source_matched_figure_region_candidate_count":3,
        "original_slide_text_region_candidate_count":2,
        "unmapped_visual_candidate_count":0,
        "source_mathematical_review_approved":False,
        "narration_timing_verified":False,
        "highlighted_video_verified":False,
        "student_publication_authorized":False,
        "utterance_candidates":rows,
    }


class FiveCandidateAudioIntegration(unittest.TestCase):
    def run_gate(self,exp=None):
        job,prior,queue=witness()
        for i in (1,2,3):
            prior["utterance_candidates"][i].setdefault(
                "candidate_highlight_bbox_pdf_pt",[60.,100.,120.,175.])
            prior["utterance_candidates"][i].setdefault(
                "original_source_strip_sha256",f"{i+1:064x}")
        return summarize_slide4_audio_gate(
            job=job,candidates=prior,independently_reconciled=queue,
            complete_visual_review=expanded_visual(job,prior) if exp is None else exp)

    def test_five_review_targets_no_audio_or_math_approval(self):
        r=self.run_gate()
        self.assertEqual(r["visual_candidate_utterances"],5)
        self.assertEqual(r["unmapped_visual_utterances"],0)
        self.assertEqual(r["original_source_text_visual_candidates"],2)
        self.assertEqual(r["unreviewed_original_slide_utterances"],5)
        self.assertEqual(r["audited_original_element_WAV_count"],0)
        self.assertFalse(r["real_speech_timing_evidence_accepted"])
        self.assertFalse(r["student_publication_authorized"])
        self.assertFalse(r["permission_to_synthesize_or_publish"])

    def test_original_three_only_path_still_reports_two_unmapped(self):
        job,prior,queue=witness()
        r=summarize_slide4_audio_gate(
            job=job,candidates=prior,independently_reconciled=queue)
        self.assertEqual(r["visual_candidate_utterances"],3)
        self.assertEqual(r["unmapped_visual_utterances"],2)

    def test_wrong_source_or_review_status_fails(self):
        job,prior,_=witness()
        for field,value in (
            ("source_sha256","z"*64),
            ("status","FULLY_APPROVED"),
            ("original_slide_text_region_candidate_count",1),
            ("narration_timing_verified",True),
            ("student_publication_authorized",True)):
            data=expanded_visual(job,prior)
            data[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                self.run_gate(exp=data)

    def test_forged_timestamps_or_media_claim_refused(self):
        job,prior,_=witness()
        for change in (
            {"actual_audio_start_s":0.0},
            {"actual_audio_end_s":4.0},
            {"speech_to_visual_sync_verified":True},
            {"actual_highlighted_video_frames_verified":True},
            {"source_math_independently_agreed":True},
        ):
            data=expanded_visual(job,prior)
            data["utterance_candidates"][4].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.run_gate(exp=data)

    def test_changed_original_triangle_shas_or_introductions_refused(self):
        job,prior,_=witness()
        for change in (
            {"candidate_panel_id":"foreign"},
            {"candidate_highlight_bbox_pdf_pt":[1,2,3,4]},
            {"original_source_strip_sha256":"0"*64},
        ):
            data=expanded_visual(job,prior)
            data["utterance_candidates"][2].update(change)
            # Earlier fixture doesn't always define this key; but the newly
            # supplied source strip SHA is never proof unless old SHA matches.
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.run_gate(exp=data)
        data=expanded_visual(job,prior)
        data["utterance_candidates"][0]["candidate_panel_id"]="fabricated triangle"
        with self.assertRaises(ValueError):
            self.run_gate(exp=data)

    def test_real_full_queue_and_original_on_dell(self):
        folder=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        q=os.environ.get("MICROGEN_ORIGINAL_71_REVIEW_QUEUE")
        if not folder or not q:
            self.skipTest("Source-only Dell-115 real 71-unit review fixture required")
        r=inspect_original_slide4_audio_readiness(
            folder=Path(folder),queue_root=Path(q))
        self.assertEqual(r["full_original_queue_total"],71)
        self.assertEqual(r["original_slide_utterances"],5)
        self.assertEqual(r["visual_candidate_utterances"],5)
        self.assertEqual(r["original_source_text_visual_candidates"],2)
        self.assertEqual(r["full_original_queue_two_pass_agreements"],0)
        self.assertFalse(r["encoded_element_highlight_video_accepted"])


if __name__=="__main__":
    unittest.main()
