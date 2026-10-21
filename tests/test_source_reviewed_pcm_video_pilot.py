import math,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired,_sha
from selenium_pipeline.source_review_packet_bridge import export_review_packet
from selenium_pipeline.source_reviewed_pcm_video_pilot import stage_source_reviewed_pcm_video_pilot
from selenium_pipeline.highlight_video_preview import ffmpeg_path

def synthetic_review_fixture(root:Path):
    folder=root/"original"
    folder.mkdir()
    pdf=pymupdf.open()
    pdf.new_page(width=320,height=220).insert_text((20,30),"Original source explains both referenced elements.")
    pdf.save(folder/"source.pdf");pdf.close()
    slides=pymupdf.open()
    page=slides.new_page(width=320,height=220)
    page.insert_text((25,70),"First concept has a definition")
    page.insert_text((25,150),"Second concept has an equation")
    slides.save(folder/"slides.pdf");slides.close()
    (folder/"script.txt").write_text(
        "**Slide 1 [2 sec]:\n"
        "The first concept has a definition. "
        "The second concept has an equation.**\n\n",encoding="utf8")
    with wave.open(str(folder/"slide1.wav"),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000)
        w.writeframes(b"\x00\x00"*16000)
    packet=export_review_packet(folder=folder,output=root/"review.json")
    assert packet["utterance_count"]==2
    used=set()
    for unit in packet["review_items"]:
        available=[v for v in unit["candidate_targets"] if v["target_id"] not in used]
        assert available,"Both original narrations need distinct real visible blocks"
        chosen=available[0];used.add(chosen["target_id"])
        unit.update(review_target_id=chosen["target_id"],source_page=1,
            verbatim_source_quote="Original source explains both referenced elements.",
            reviewer_attestation=True,reviewer_id="synthetic-qa-reviewer")
    external=root/"separate_chunks";external.mkdir()
    receipt=[]
    for i,item in enumerate(packet["review_items"],1):
        wav=external/f"utterance{i}.wav"
        with wave.open(str(wav),"wb") as a:
            a.setnchannels(1);a.setsampwidth(2);a.setframerate(16000)
            duration=[.5,.7][i-1]
            frames=b"".join(int(7000*math.sin(2*math.pi*(370+70*i)*n/16000)).to_bytes(
                2,byteorder="little",signed=True) for n in range(int(16000*duration)))
            a.writeframes(frames)
        receipt.append({"job_id":item["utterance_id"],
            "original_spoken_text_sha256":item["spoken_text_sha256"],
            "claimed_model":"gemini-3.8-flash-lite-tts",
            "claimed_voice":"Kore",
            "provider_output_not_verified_acoustically":True,
            "wav_path":str(wav),"wav_sha256":_sha(wav)})
    return folder,packet,receipt

class OriginalSourceBoundTechnicalPilotTests(unittest.TestCase):
    @unittest.skipUnless(Path(ffmpeg_path()).is_file(),"FFmpeg binary unavailable")
    def test_actual_encoded_source_decisions_pcm_start_stop_and_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder,pkt,wavs=synthetic_review_fixture(root)
            before=_sha(folder/"slides.pdf")
            report=stage_source_reviewed_pcm_video_pilot(
                folder=folder,packet=pkt,wav_receipts=wavs,destination=root/"encoded")
            self.assertEqual(report["physical_element_pcm_chunk_count"],2)
            self.assertEqual(report["independent_boundary_transition_checks"],1)
            self.assertLess(report["actual_encoded_mp4_duration_s"],600)
            self.assertFalse(report["spoken_text_audio_fidelity_verified"])
            self.assertFalse(report["student_publication_authorized"])
            self.assertTrue((root/"encoded"/"element_highlight_review.mp4").is_file())
            self.assertEqual(_sha(folder/"slides.pdf"),before)
    def test_missing_or_forged_original_pcm_chunks_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder,pkt,wavs=synthetic_review_fixture(root)
            with self.assertRaises(FigureIdentityReviewRequired):
                stage_source_reviewed_pcm_video_pilot(folder=folder,
                    packet=pkt,wav_receipts=wavs[:1],destination=root/"unapproved")
            pkt["review_items"][0]["reviewer_attestation"]=False
            with self.assertRaises(FigureIdentityReviewRequired):
                stage_source_reviewed_pcm_video_pilot(folder=folder,
                    packet=pkt,wav_receipts=wavs,destination=root/"unapproved")
