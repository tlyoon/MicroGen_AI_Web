import hashlib,math,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from selenium_pipeline.incremental_element_review_encoder import encode_segment_highlight_review
from selenium_pipeline.highlight_video_preview import ffmpeg_path
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired,_sha

def inputs(root):
    original=root/"teaching";original.mkdir()
    pdf=pymupdf.open();page=pdf.new_page(width=320,height=220)
    page.insert_text((20,70),"Synthetic area one")
    page.insert_text((20,150),"Synthetic area two")
    pdf.save(original/"slides.pdf");pdf.close()
    sound=root/"recorded";sound.mkdir()
    wave_receipts=[]
    jobs=[]
    for i,(seconds,bbox) in enumerate(((.5,[10,30,180,95]),(.7,[10,115,180,180])),1):
        name=f"s001.utterance.00{i}"
        wav=sound/f"{i}.wav"
        with wave.open(str(wav),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            pcm=bytearray()
            for j in range(round(16000*seconds)):
                amp=round(8000*math.sin(2*math.pi*(440+100*i)*j/16000))
                pcm+=int(amp).to_bytes(2,byteorder="little",signed=True)
            w.writeframes(bytes(pcm))
        wave_receipts.append({"job_id":name,"voice_id":"Kore",
             "wav_path":str(wav),"wav_sha256":_sha(wav)})
        jobs.append({"job_id":name,"target_slide_index":1,
                     "target_pdf_page_bbox_pt":bbox})
    manifest={"status":"REVIEWED_ELEMENT_CHUNK_REQUESTS_NOT_YET_DISPATCHED",
              "slides_sha256":_sha(original/"slides.pdf"),
              "paid_tts_execution_authorized":False,
              "student_publication_authorized":False,
              "voice":"Kore","chunk_jobs":jobs}
    return original/"slides.pdf",manifest,wave_receipts

class ActualTechnicalReviewEncoderTests(unittest.TestCase):
    def test_wrong_hash_and_unsafe_destination_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);pdf,jobs,audio=inputs(root)
            wrong=dict(jobs);wrong["slides_sha256"]="f"*64
            with self.assertRaises(FigureIdentityReviewRequired):
                encode_segment_highlight_review(slides=pdf,jobs=wrong,clips=audio,
                                               destination=root/"reject")
            with self.assertRaises(FigureIdentityReviewRequired):
                encode_segment_highlight_review(slides=pdf,jobs=jobs,clips=audio,
                                               destination=pdf.parent/"reject")
    @unittest.skipUnless(Path(ffmpeg_path()).is_file(),
                         "Actual imageio FFmpeg binary unavailable")
    def test_real_encoded_two_separately_timed_elements(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);pdf,jobs,audio=inputs(root)
            before=_sha(pdf)
            report=encode_segment_highlight_review(
                slides=pdf,jobs=jobs,clips=audio,
                destination=root/"technical_review")
            self.assertEqual(report["status"],
                "REAL_PCM_BOUNDARY_HIGHLIGHT_VIDEO_REVIEW_ONLY")
            self.assertEqual(len(report["events"]),2)
            self.assertAlmostEqual(report["events"][0]["end_seconds"],.5,places=4)
            self.assertAlmostEqual(report["events"][1]["start_seconds"],.5,places=4)
            self.assertAlmostEqual(report["events"][1]["end_seconds"],1.2,places=4)
            self.assertFalse(report["production_video_accepted"])
            self.assertFalse(report["student_publication_authorized"])
            self.assertTrue(report["decoded_highlight_midpoint_samples_verified"])
            self.assertFalse(report["all_encoded_element_transition_frames_verified"])
            self.assertEqual(len(report["decoded_highlight_transition_samples"]),2)
            self.assertLess(report["actual_encoded_duration_s"],600)
            self.assertEqual(_sha(pdf),before)
            self.assertTrue((root/"technical_review"/"element_highlight_review.mp4").is_file())
