"""Cross-PC manifest and single-publisher fail-closed QA (offline)."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline.course_youtube_coordinator import (
    check_course_workers, audit_and_plan, publish_completed_course,
)
from selenium_pipeline.youtube_course_publish import YouTubeCourseError

class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.runid="batch_20261018"
        self.control=self.root/".microgen_coordination"/self.runid
        self.control.mkdir(parents=True)
        self.assignment={
            "HP":[8],
            "Dell-115":[10],
            "Yoga6":[12],
        }
        self.status={}
        for worker,chapters in self.assignment.items():
            topics=set()
            for ch in chapters:
                chapter=self.root/str(ch)
                chapter.mkdir()
                for i in (1,2):
                    topic=f"{ch}.{i}"
                    p=chapter/topic
                    p.mkdir()
                    (p/"source.pdf").write_bytes(topic.encode())
                    topics.add(topic)
            row={
                "run_id":self.runid,"worker":worker,
                "chapters":chapters,"assigned":sorted(topics),
                "phase":"finished","unfinished":[],
                "jobs":{t:{"status":"complete","stage":"video","verified":True,
                            "contract":"accepted_synchronized_series"}
                        for t in topics},
            }
            self.status[worker]=row
            self.store(worker)
        self.manifest={"assignments":self.assignment}
        self.save_manifest()

    def store(self,worker):
        (self.control/(worker+".json")).write_text(
            json.dumps(self.status[worker]),encoding="utf-8")

    def save_manifest(self):
        (self.control/"assignments.json").write_text(
            json.dumps(self.manifest),encoding="utf-8")

    def mock_plan(self):
        return {
            "items":[SimpleNamespace(subchapter=t) for t in
                 sorted((f.name for root in self.root.iterdir()
                        if root.is_dir() and root.name.isdecimal()
                        for f in root.iterdir() if f.is_dir()))],
            "source_root":str(self.root),
        }

    def test_all_workers_covered_full_course(self):
        report=check_course_workers(self.root,run_id=self.runid)
        self.assertEqual(report["status"],"ALL_ASSIGNED_PCS_TECHNICALLY_COMPLETE")
        self.assertEqual(len(report["topics"]),6)
        self.assertEqual(report["workers"],["Dell-115","HP","Yoga6"])
        with patch("selenium_pipeline.course_youtube_coordinator.plan_course",
                   return_value=self.mock_plan()):
            ready=audit_and_plan(root=self.root,run_id=self.runid,
                                 course_title="Physics Course")
        self.assertEqual(ready["lecture_parts"],6)

    def test_not_finished_blocks_without_upload(self):
        self.status["Yoga6"]["phase"]="second_pass"
        self.store("Yoga6")
        with self.assertRaisesRegex(YouTubeCourseError,"still running"):
            check_course_workers(self.root,run_id=self.runid)

    def test_technical_incomplete_blocks(self):
        self.status["Dell-115"]["jobs"]["10.1"]["verified"]=False
        self.store("Dell-115")
        with self.assertRaisesRegex(YouTubeCourseError,"accepted technical video"):
            check_course_workers(self.root,run_id=self.runid)

    def test_missing_worker_and_wrong_run_block(self):
        (self.control/"HP.json").unlink()
        with self.assertRaisesRegex(YouTubeCourseError,"not reported"):
            check_course_workers(self.root,run_id=self.runid)
        self.store("HP")
        self.status["Yoga6"]["run_id"]="old_run"
        self.store("Yoga6")
        with self.assertRaisesRegex(YouTubeCourseError,"wrong run"):
            check_course_workers(self.root,run_id=self.runid)

    def test_pilot_target_subset_blocks(self):
        self.status["HP"]["assigned"]=["8.1"]
        self.store("HP")
        with self.assertRaisesRegex(YouTubeCourseError,"partial/pilot"):
            check_course_workers(self.root,run_id=self.runid)

    def test_unassigned_chapter_source_blocks(self):
        p=self.root/"14"/"14.1"
        p.mkdir(parents=True)
        (p/"source.pdf").write_bytes(b"unassigned")
        with self.assertRaisesRegex(YouTubeCourseError,"excludes live"):
            check_course_workers(self.root,run_id=self.runid)

    def test_duplicate_chapter_assignment_blocks(self):
        self.manifest["assignments"]["Yoga6"]=[8]
        self.save_manifest()
        self.status["Yoga6"]["chapters"]=[8]
        self.store("Yoga6")
        with self.assertRaisesRegex(YouTubeCourseError,"overlapping"):
            check_course_workers(self.root,run_id=self.runid)

    def test_zenbook_not_an_authorized_worker(self):
        self.manifest["assignments"]["Zenbook"]=[14]
        self.save_manifest()
        with self.assertRaisesRegex(YouTubeCourseError,"Disallowed"):
            check_course_workers(self.root,run_id=self.runid)

    def test_single_publisher_synthetic_handoff(self):
        trailer=self.root/".microgen_youtube"/"trailer"/"video_00.mp4"
        self.root.joinpath(".microgen_youtube").mkdir()
        fake=SimpleNamespace()
        with patch("selenium_pipeline.course_youtube_coordinator.socket.gethostname",
                   return_value="HP-TEST"),patch(
                   "selenium_pipeline.course_youtube_coordinator.plan_course",
                   return_value=self.mock_plan()),patch(
                   "selenium_pipeline.course_youtube_coordinator.plan_video00",
                   return_value={"status":"test"}) as planned,patch(
                   "selenium_pipeline.course_youtube_coordinator.render_video00",
                   side_effect=lambda *a,**kw:(trailer.parent.mkdir(),trailer.write_bytes(b"FAKE MP4"))),patch(
                   "selenium_pipeline.course_youtube_coordinator.verify_video00",
                   return_value={"status":"SOURCE_BOUND_VIDEO00_VERIFIED"}) as verified,patch(
                   "selenium_pipeline.course_youtube_coordinator.publish_course",
                   return_value={"status":"YOUTUBE_COURSE_PUBLISHED",
                                 "playlist_url":"https://youtube.com/playlist?list=TEST",
                                 "videos":7} ) as publishing:
            data=publish_completed_course(
                root=self.root,run_id=self.runid,course_title="Physics",
                publisher_host="HP-TEST",expected_channel_id="UCtest",
                expected_handle=None,visibility="private",youtube=fake)
        self.assertTrue(data["video00_included"])
        self.assertEqual(publishing.call_count,1)
        self.assertTrue(verified.called)
        self.assertTrue(planned.called)

    def test_wrong_publisher_refuses_before_trailer_or_api(self):
        with patch("selenium_pipeline.course_youtube_coordinator.socket.gethostname",
                   return_value="WRONG-PC"):
            with self.assertRaisesRegex(YouTubeCourseError,"not the pinned"):
                publish_completed_course(
                    root=self.root,run_id=self.runid,
                    course_title="Physics",publisher_host="HP-TEST",
                    expected_handle="@tlyoon",expected_channel_id=None,
                    visibility="public",youtube=SimpleNamespace())
        self.assertFalse((self.root/".microgen_youtube").exists())

if __name__=="__main__":
    unittest.main()
