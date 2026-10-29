"""Real original 8.4/8.5/8.6 media timing and no-false-acceptance tests."""
import hashlib,os,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.original_replacement_video_handoff import (
    build_original_replacement_handoff,check_replacement_audio_readiness,
)

class ProtectedMediaHandoff(unittest.TestCase):
    def test_no_original_folder_fails_closed(self):
        with self.assertRaises(ValueError):
            build_original_replacement_handoff(chapter_folder=Path("Z:/missing_thomas_originals"))

    def real_root(self):
        env=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        if not env:
            self.skipTest("Original §§8.4–8.6 exist only on owner Dell-115")
        return Path(env).parent

    def test_real_three_section_six_video_plan_is_not_approval(self):
        chapter=self.real_root()
        historical={(n,k):hashlib.sha256((chapter/n/k).read_bytes()).hexdigest()
                    for n in ("8.4","8.5","8.6")
                    for k in ("source.pdf","slides.pdf","script.txt","slides.mp4")}
        r=build_original_replacement_handoff(chapter_folder=chapter)
        self.assertEqual(r["total_new_parts_proposed"],6)
        self.assertEqual([s["part_count"] for s in r["sections"]],[2,2,2])
        self.assertEqual([s["original_slide_WAV_count"] for s in r["sections"]],[17,20,17])
        self.assertEqual([(s["proposed_parts"][0]["slide_start"],
                           s["proposed_parts"][0]["slide_end"],
                           s["proposed_parts"][1]["slide_start"],
                           s["proposed_parts"][1]["slide_end"])
                           for s in r["sections"]],
                         [(1,8,9,17),(1,11,12,20),(1,9,10,17)])
        self.assertTrue(all(s["original_encoded_MP4_duration_s"]>600
                            for s in r["sections"]))
        self.assertFalse(r["any_new_mp4_created"])
        self.assertFalse(r["all_parts_accepted"])
        self.assertFalse(r["student_publication_authorized"])
        self.assertFalse(any(p["new_per_element_same_voice_WAVs_received"]
                             for s in r["sections"] for p in s["proposed_parts"]))
        self.assertEqual(historical,{
              (n,k):hashlib.sha256((chapter/n/k).read_bytes()).hexdigest()
              for n,k in historical})

    def test_unapproved_legacy_audio_or_missing_replacements_rejected(self):
        chapter=self.real_root()
        r=build_original_replacement_handoff(chapter_folder=chapter)
        with self.assertRaises(ValueError):
            check_replacement_audio_readiness(handoff=r,replacements={})
        original=chapter/"8.4"/"slide4.wav"
        fake={"path":str(original),
              "source_text_sha256":"a"*64,"voice_id":"Kore",
              "provider":"Gemini Flash-Lite TTS","source_math_passes":2}
        with self.assertRaises(ValueError):
            check_replacement_audio_readiness(handoff=r,replacements={"8.4/4":fake})
        with tempfile.TemporaryDirectory() as td:
            other=Path(td)/"candidate.wav"
            other.write_bytes(original.read_bytes())
            with self.assertRaises(ValueError):
                check_replacement_audio_readiness(
                    handoff=r,replacements={"8.4/4":{**fake,"path":str(other)}})

    def test_no_synthetic_publication_even_with_new_bytes(self):
        chapter=self.real_root()
        r=build_original_replacement_handoff(chapter_folder=chapter)
        with tempfile.TemporaryDirectory() as td:
            fake=Path(td)/"pretend.wav";fake.write_bytes(b"not real PCM")
            row={"path":str(fake),"source_text_sha256":"a"*64,
                 "voice_id":"Kore","provider":"Gemini Flash-Lite TTS",
                 "source_math_passes":2}
            with self.assertRaises(ValueError):
                check_replacement_audio_readiness(handoff=r,
                                                  replacements={"8.4/4":row})
            with wave.open(str(fake),"wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(24000)
                stream.writeframes(b"\x01\x00"*24000)
            proof=check_replacement_audio_readiness(handoff=r,
                    replacements={"8.4/4":row})
            self.assertFalse(proof["student_publication_authorized"])
            self.assertFalse(proof["replaced"]["8.4/4"][
                                 "actual_spoken_words_independently_verified"])

if __name__=="__main__":unittest.main()
