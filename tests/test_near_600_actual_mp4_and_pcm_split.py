"""Actual FFmpeg near-limit MP4s plus exact original PCM split accounting."""
import subprocess,tempfile,unittest
from pathlib import Path
from selenium_pipeline.highlight_video_preview import ffmpeg_path,probe_mp4,HighlightVideoError
from selenium_pipeline.element_pcm_sample_clock_split import plan_verified_element_pcm_parts
class StrictBoundary(unittest.TestCase):
 def test_exact_frame_accounting_without_missing_or_duplicate_elements(self):
  rate=24000
  clips=[dict(job_id=f"original_{n}",sample_frames=int(rate*x),
              sample_rate=rate) for n,x in enumerate(
              (119,119,119,119,63.999),1)]
  planned=plan_verified_element_pcm_parts(clips=clips,maximum_pcm_s=540)
  ids=[event["job_id"] for part in planned["parts"] for event in part["events"]]
  self.assertEqual(ids,[row["job_id"] for row in clips])
  self.assertEqual(sum(p["total_pcm_frames"] for p in planned["parts"]),
                   sum(c["sample_frames"] for c in clips))
  self.assertTrue(all(p["exact_pcm_seconds"]<540 for p in planned["parts"]))
  self.assertEqual(planned["proposed_part_count"],1)
 def test_exact_540_uses_new_part_not_reaching_limit(self):
  rate=24000
  clips=[dict(job_id=f"u{i}",sample_frames=90*rate,sample_rate=rate)
         for i in range(6)]
  plan=plan_verified_element_pcm_parts(clips=clips)
  self.assertEqual(plan["proposed_part_count"],2)
  self.assertEqual([len(p["events"]) for p in plan["parts"]],[5,1])
  self.assertEqual(plan["parts"][0]["exact_pcm_seconds"],450)
  self.assertEqual(plan["parts"][1]["events"][0]["part_pcm_start_frame"],0)
 def test_actual_599_second_and_600_second_encoded_container(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for duration,accepted in ((599.0,True),(600.0,False)):
    output=root/(f"duration_{duration}.mp4")
    cmd=[ffmpeg_path(),"-nostdin","-v","error",
         "-f","lavfi","-i","color=c=black:s=64x64:r=1",
         "-f","lavfi","-i","sine=frequency=440:sample_rate=8000",
         "-t",str(duration),"-c:v","mpeg4","-c:a","aac",
         "-b:a","16k","-y",str(output)]
    p=subprocess.run(cmd,capture_output=True,timeout=105)
    self.assertEqual(p.returncode,0,p.stderr[-300:])
    if accepted:
     self.assertLess(probe_mp4(output,exe=ffmpeg_path())["duration_s"],600)
    else:
     with self.assertRaises(HighlightVideoError):
      probe_mp4(output,exe=ffmpeg_path())
