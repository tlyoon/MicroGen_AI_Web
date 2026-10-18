"""Offline preflight calibration safety and integrity."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.tts_duration_preflight import CalibrationError, calculate, main


def sample():
    talk=["This is the square root of x squared.",
          "Now divide the numerator by x squared."]
    segments=[{"segment_id":"seg_"+str(i), "spoken_text":words}
              for i,words in enumerate(talk,1)]
    pilot={"schema_version":1,"part_id":"part_01","narration_segments":segments}
    receipt={
     "status":"wave_chunk_timing_verified_spoken_content_unreviewed",
     "voice_id":"single-voice","sample_rate":24000,
     "wav_segments":[{"segment_id":s["segment_id"],"voice_id":"single-voice",
      "speech_sha256":hashlib.sha256(s["spoken_text"].encode()).hexdigest(),
      "sample_rate":24000,"frames":240000} for s in segments]
    }
    candidate={"schema_version":1,"part_id":"part_02","narration_segments":[
        {"segment_id":"n1","spoken_text":"The square root includes all of x squared plus one hundred."}]}
    return pilot,receipt,candidate


class PreflightTests(unittest.TestCase):
    def test_real_audio_and_nonapproving_estimate(self):
        p,r,c=sample()
        result=calculate(p,r,[c],video_seconds=20.12)
        self.assertEqual(result["pilot_wav_seconds"],20.)
        self.assertEqual(result["pilot_inserted_pause_seconds"],.12)
        self.assertFalse(result["tts_authorized"])
        self.assertFalse(result["student_publication_permitted"])
        self.assertGreater(result["parts"][0]["slow_rate_plus_reserve_s"],
                           result["parts"][0]["pilot_rate_s"])

    def test_strict_600_second_default_and_weak_overrides_rejected(self):
        p,r,c=sample()
        result=calculate(p,r,[c])
        self.assertEqual(result["strict_video_limit_seconds"],600.0)
        for bad in (600.1,620,629.9,630,float("inf"),float("nan"),True):
            with self.subTest(limit=bad), self.assertRaisesRegex(CalibrationError,"duration policy"):
                calculate(p,r,[c],limit_seconds=bad)
        self.assertEqual(calculate(p,r,[c],limit_seconds=599.9)["strict_video_limit_seconds"],599.9)

    def test_mismatched_spoken_hash_rejected(self):
        p,r,c=sample()
        p["narration_segments"][0]["spoken_text"]+=" corrupted"
        with self.assertRaisesRegex(CalibrationError,"script hash"):
            calculate(p,r,[c])

    def test_mixed_voice_rejected(self):
        p,r,c=sample()
        r["wav_segments"][1]["voice_id"]="other voice"
        with self.assertRaisesRegex(CalibrationError,"Mixed"):
            calculate(p,r,[c])

    def test_order_mismatch_rejected(self):
        p,r,c=sample()
        r["wav_segments"].reverse()
        with self.assertRaisesRegex(CalibrationError,"ordering"):
            calculate(p,r,[c])

    def test_video_shorter_than_wavs_rejected(self):
        p,r,c=sample()
        with self.assertRaisesRegex(CalibrationError,"shorter"):
            calculate(p,r,[c],video_seconds=19.)

    def test_duplicate_parts_and_missing_candidates(self):
        p,r,c=sample()
        with self.assertRaisesRegex(CalibrationError,"Duplicate candidate"):
            calculate(p,r,[c,c])
        with self.assertRaisesRegex(CalibrationError,"At least one"):
            calculate(p,r,[])

    def test_slow_scenario_over_cap_requires_repartition(self):
        p,r,c=sample()
        c["narration_segments"][0]["spoken_text"]="long expression "*600
        result=calculate(p,r,[c])
        self.assertTrue(result["parts"][0]["slow_scenario_exceeds_limit"])
        self.assertFalse(result["mp4_authorized"])

    def test_cli_does_not_overwrite_existing_report(self):
        p,r,c=sample()
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            for n,value in [("pilot.json",p),("receipt.json",r),("candidate.json",c)]:
                (root/n).write_text(json.dumps(value),encoding="utf8")
            args=["--pilot-storyboard",str(root/"pilot.json"),
                  "--pilot-wav-receipt",str(root/"receipt.json"),
                  "--pilot-video-duration-s","20.12",
                  "--candidate",str(root/"candidate.json"),
                  "--out",str(root/"report.json")]
            self.assertEqual(main(args),0)
            with self.assertRaises(FileExistsError):
                main(args)


if __name__=="__main__":
    unittest.main()
