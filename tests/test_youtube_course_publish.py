"""Offline mocked YouTube publishing acceptance and refusal checks.

No account authentication, network, TTS or real YouTube writes in these tests.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.youtube_course_publish import (
    YouTubeCourseError, _state, _reorder, plan_course, publish_course,
    sha256, summary, verify_channel,
)


class Result:
    def __init__(self, body):
        self.body = body

    def execute(self, **kwargs):
        return self.body


class FakeYouTube:
    def __init__(self):
        self.items = []
        self.playlist_count = 0
        self.pl_id = None
        self.video_ids = {}
        self.videos_inserted = 0
        self.playlist_inserted = 0
        self.caption_inserted = 0
        self.cover_inserted = 0
        self.reorders = 0
        self.visible = "public"
        self.channel_id = "UC-course-owner-123"

    def channels(self):
        return self

    def list(self, **kwargs):
        if kwargs.get("mine"):
            return Result({"items": [{"id": self.channel_id,
                    "snippet": {"customUrl": "@tlyoon"}}]})
        if kwargs.get("part") == "snippet,status" and kwargs.get("id"):
            return Result({"items": [{
                "id": kwargs["id"],
                "snippet": {"channelId": self.channel_id},
                "status": {"privacyStatus": self.visible},
            }]})
        if kwargs.get("part") == "id,snippet,status":
            ident = kwargs["id"]
            return Result({"items": [{"id": ident, "snippet": {
                "channelId": self.channel_id}, "status": {
                    "privacyStatus": self.visible}}]})
        if kwargs.get("playlistId"):
            return Result({"items": [{"id": x["id"], "snippet": {
                "resourceId": {"videoId": x["video_id"]}}}
                for x in self.items]})
        return Result({})

    def playlists(self):
        return self

    def playlistItems(self):
        return PlaylistItems(self)

    def videos(self):
        return self

    def insert(self, **kwargs):
        # This object is used by playlist create (video uploads mocked).
        self.playlist_count += 1
        self.pl_id = "PL-microgen-course-123"
        return Result({"id": self.pl_id})

    def captions(self):
        return CaptionUploads(self)

    def playlistImages(self):
        return CoverUploads(self)


class PlaylistItems:
    def __init__(self, parent):
        self.parent = parent

    def insert(self, **kwargs):
        par = self.parent
        par.playlist_inserted += 1
        snip = kwargs["body"]["snippet"]
        id = f"PLI-{par.playlist_inserted}"
        par.items.insert(snip["position"], {
            "id": id, "video_id": snip["resourceId"]["videoId"]})
        return Result({"id": id})

    def list(self, **kwargs):
        return Result({"items": [
            {"id": x["id"], "snippet": {
                "resourceId": {"videoId": x["video_id"]}}}
            for x in self.parent.items]})

    def update(self, **kwargs):
        par = self.parent
        snip = kwargs["body"]["snippet"]
        ident = kwargs["body"]["id"]
        idx = next(i for i, x in enumerate(par.items) if x["id"] == ident)
        par.items.insert(snip["position"], par.items.pop(idx))
        par.reorders += 1
        return Result({"id": ident})


class CaptionUploads:
    def __init__(self, parent):
        self.parent = parent
    def insert(self, **kwargs):
        self.parent.caption_inserted += 1
        return Result({"id": "caption-001"})


class CoverUploads:
    def __init__(self, parent):
        self.parent = parent
    def insert(self, **kwargs):
        self.parent.cover_inserted += 1
        return Result({"id": "cover-001"})


class CourseUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "course"
        self.root.mkdir()
        self.local_auth = Path(self.temp.name) / "local_auth"
        self.local_auth.mkdir()
        self.original_env = os.environ.get("MICROVID_CONFIG_DIR")
        os.environ["MICROVID_CONFIG_DIR"] = str(self.local_auth)
        self.addCleanup(self.reset_env)
        self.folders = []
        for chapter, subtopics in ((8, (1, 2)), (10, (1,))):
            directory = self.root / str(chapter)
            directory.mkdir()
            for sub in subtopics:
                topic = f"{chapter}.{sub}"
                folder = directory / topic
                folder.mkdir()
                (folder / "source.pdf").write_bytes(f"source {topic}".encode())
                parts = 2 if topic == "8.2" else 1
                for i in range(1, parts+1):
                    ident=f"part_{i:02d}"
                    dest=folder/ident
                    dest.mkdir()
                    (dest/(ident+".mp4")).write_bytes(f"encoded-mp4-{topic}-{i}".encode())
                    if topic == "8.1":
                        (dest/(ident+".srt")).write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
                self.folders.append(folder)
        self.youtube=FakeYouTube()
        self.video_calls=0

    def reset_env(self):
        if self.original_env is None:
            os.environ.pop("MICROVID_CONFIG_DIR", None)
        else:
            os.environ["MICROVID_CONFIG_DIR"] = self.original_env

    def tech(self, folder):
        folder = Path(folder)
        indices=sorted((p for p in folder.iterdir() if p.is_dir()
                        and p.name.startswith("part_")))
        return {"status":"accepted_synchronized_series",
                "verification_scope":"technical_media_only",
                "parts":[{"part_id":p.name,"duration_s":100.0,
                          "highlight_events":3} for p in indices]}

    def plan(self, **kw):
        with patch("selenium_pipeline.youtube_course_publish.verify_series",
                   side_effect=self.tech):
            return plan_course(self.root, course_title="Physics 8 and 10", **kw)

    def publish(self, plan, *, fake=None, **kw):
        fake=fake or self.youtube
        with patch("selenium_pipeline.youtube_course_publish.verify_series",
                   side_effect=self.tech), patch(
                    "selenium_pipeline.youtube_course_publish.socket.gethostname",
                    return_value="HP-TEST"), patch(
                    "selenium_pipeline.youtube_course_publish._upload_mp4",
                    side_effect=self._upload), patch(
                    "selenium_pipeline.youtube_course_publish._upload_caption",
                    return_value="caption-test") as caption, patch(
                    "selenium_pipeline.youtube_course_publish._upload_cover",
                    return_value="cover-test") as cover:
            result=publish_course(plan,youtube=fake,
                                  expected_handle="@tlyoon",
                                  publisher_host="HP-TEST",**kw)
        return result,caption.call_count,cover.call_count

    def _upload(self,youtube,item,**kwargs):
        self.video_calls+=1
        return f"ytvideo{self.video_calls:06d}"

    def test_order_and_real_byte_hashes_for_multipart(self):
        plan=self.plan()
        self.assertEqual([x.key for x in plan["items"]],
                         ["8.1/part_01","8.2/part_01",
                          "8.2/part_02","10.1/part_01"])
        self.assertEqual(summary(plan)["upload_count"],4)
        self.assertEqual(plan["items"][0].caption_sha256,
                         sha256(self.root/"8"/"8.1"/"part_01"/"part_01.srt"))
        self.assertEqual(plan["items"][0].sha256,
                         sha256(plan["items"][0].mp4))
        self.assertFalse(plan["human_approval_required"])
        self.assertTrue(plan["technical_qa_required"])
        self.assertFalse((self.root/".microgen_youtube").exists())

    def test_incomplete_source_blocks_publication_by_default(self):
        with patch("selenium_pipeline.youtube_course_publish.verify_series",
                   side_effect=lambda folder: self.tech(folder) if Path(folder).name!="8.2"
                   else (_ for _ in ()).throw(ValueError("bad highlight"))):
            with self.assertRaisesRegex(YouTubeCourseError,"Course incomplete"):
                plan_course(self.root,course_title="Physics 8 and 10")
            partial=plan_course(self.root,course_title="Physics 8 and 10",
                                require_complete=False)
        self.assertEqual(partial["excluded"][0]["subchapter"],"8.2")
        self.assertFalse(partial["complete_course"])

    def test_upload_multipart_once_and_resume_without_duplicates(self):
        plan=self.plan()
        result,caps,covers=self.publish(plan)
        self.assertEqual(result["status"],"YOUTUBE_COURSE_PUBLISHED")
        self.assertEqual(result["videos"],4)
        self.assertEqual(self.video_calls,4)
        self.assertEqual(self.youtube.playlist_inserted,4)
        self.assertEqual(self.youtube.playlist_count,1)
        self.assertEqual(caps,1)
        self.assertEqual(covers,1)
        self.assertEqual([x["video_id"] for x in self.youtube.items],
                         [f"ytvideo{i:06d}" for i in range(1,5)])
        state=_state(self.root/".microgen_youtube"/"publish_state.json")
        self.assertTrue(state["complete"])
        self.assertEqual(len(state["uploads"]),4)
        self.assertTrue(all(len(x["sha256"])==64 for x in state["uploads"].values()))
        result2,caps2,covers2=self.publish(plan)
        self.assertEqual(result2["videos"],4)
        self.assertEqual(self.video_calls,4)
        self.assertEqual(caps2,0)
        self.assertEqual(covers2,0)
        self.assertEqual(self.youtube.playlist_count,1)

    def test_mismatched_channel_rejected_before_playlist_or_upload(self):
        plan=self.plan()
        with patch("selenium_pipeline.youtube_course_publish.verify_series",
                   side_effect=self.tech), patch(
                    "selenium_pipeline.youtube_course_publish.socket.gethostname",
                    return_value="HP-TEST"):
            with self.assertRaisesRegex(YouTubeCourseError,"differs"):
                publish_course(plan,youtube=self.youtube,expected_handle="@other",
                               publisher_host="HP-TEST")
        self.assertEqual(self.youtube.playlist_count,0)
        self.assertEqual(self.video_calls,0)

    def test_refuse_wrong_publisher_host_before_youtube_calls(self):
        plan=self.plan()
        with self.assertRaisesRegex(YouTubeCourseError,"Wrong publisher PC"):
            publish_course(plan,youtube=self.youtube,expected_handle="@tlyoon",
                           publisher_host="NOT-A-PC")
        self.assertEqual(self.youtube.playlist_count,0)

    def test_changed_mp4_blocks_resume_even_if_same_byte_count(self):
        plan=self.plan()
        self.publish(plan)
        mp4=plan["items"][0].mp4
        data=mp4.read_bytes()
        mp4.write_bytes(b"Z"*len(data))
        changed=self.plan()
        self.assertNotEqual(plan["items"][0].sha256,changed["items"][0].sha256)
        with self.assertRaisesRegex(YouTubeCourseError,"Previously published bytes changed"):
            self.publish(changed)
        self.assertEqual(self.video_calls,4)

    def test_modified_mp4_after_preflight_blocks_before_remote_write(self):
        plan=self.plan()
        plan["items"][0].mp4.write_bytes(b"corrupt-after-plan")
        with self.assertRaisesRegex(YouTubeCourseError,"changed after preflight"):
            self.publish(plan)
        self.assertEqual(self.youtube.playlist_count,0)

    def test_playlist_owner_mismatch_rejected_before_upload(self):
        plan=self.plan()
        fake=self.youtube
        fake.channel_id="UC-other"
        self.assertEqual(fake.playlist_count,0)
        # A forged state claims one existing playlist for the wrong owner.
        statefile=self.root/".microgen_youtube"/"publish_state.json"
        statefile.parent.mkdir()
        statefile.write_text(json.dumps({
            "schema_version":1,"playlist":{"id":"PL-other"},
            "uploads":{},"channel_id":"UC-expected",
        }),encoding="utf-8")
        with self.assertRaisesRegex(YouTubeCourseError,"another channel"):
            self.publish(plan)
        self.assertEqual(self.video_calls,0)

    def test_youtube_forces_wrong_privacy_visibility_fails(self):
        plan=self.plan()
        self.youtube.visible="private"
        with self.assertRaisesRegex(YouTubeCourseError,"visibility"):
            self.publish(plan)
        self.assertEqual(self.video_calls,0)

    def test_unauthorized_channel_id_is_not_a_handle_match(self):
        with self.assertRaisesRegex(YouTubeCourseError,"channel ID"):
            verify_channel(self.youtube,expected_channel_id="UC-wrong",
                           expected_handle="@tlyoon")

    def test_caption_sha_change_blocks_resume(self):
        plan=self.plan()
        self.publish(plan)
        caption=plan["items"][0].caption
        data=caption.read_bytes()
        caption.write_bytes(b"a" * len(data))
        changed=self.plan()
        self.assertNotEqual(plan["items"][0].caption_sha256,
                            changed["items"][0].caption_sha256)
        with self.assertRaisesRegex(YouTubeCourseError,"changed"):
            self.publish(changed)

    def test_same_publish_state_different_publisher_host_rejected(self):
        plan=self.plan()
        self.publish(plan)
        path=self.root/".microgen_youtube"/"publish_state.json"
        state=json.loads(path.read_text(encoding="utf-8"))
        state["publisher_host"]="DIFFERENT-HOST"
        path.write_text(json.dumps(state),encoding="utf-8")
        with self.assertRaisesRegex(YouTubeCourseError,"different publisher"):
            self.publish(plan)

    def test_missing_channel_pin_rejected(self):
        with self.assertRaisesRegex(YouTubeCourseError,"pinned"):
            verify_channel(self.youtube,expected_channel_id=None,expected_handle=None)

    def test_interrupted_remote_upload_does_not_blindly_retry(self):
        plan=self.plan()
        def failure(youtube,item,**kw):
            self.video_calls+=1
            raise OSError("network dropped after YouTube may have committed")
        with patch("selenium_pipeline.youtube_course_publish.verify_series",
                   side_effect=self.tech), patch(
                    "selenium_pipeline.youtube_course_publish.socket.gethostname",
                    return_value="HP-TEST"), patch(
                    "selenium_pipeline.youtube_course_publish._upload_mp4",
                    side_effect=failure):
            with self.assertRaisesRegex(OSError,"network dropped"):
                publish_course(plan,youtube=self.youtube,
                               expected_handle="@tlyoon",
                               publisher_host="HP-TEST")
        self.assertEqual(self.video_calls,1)
        with self.assertRaisesRegex(YouTubeCourseError,"Ambiguous interrupted"):
            self.publish(plan)
        self.assertEqual(self.video_calls,1)

    def test_interrupted_playlist_create_does_not_make_duplicate_playlist(self):
        plan=self.plan()
        original=self.youtube.insert
        def remote_drop(**kwargs):
            self.youtube.playlist_count += 1
            raise OSError("YouTube created playlist but response was lost")
        self.youtube.insert=remote_drop
        with self.assertRaisesRegex(OSError,"response was lost"):
            self.publish(plan)
        self.assertEqual(self.youtube.playlist_count,1)
        self.youtube.insert=original
        with self.assertRaisesRegex(YouTubeCourseError,
                                    "Ambiguous interrupted playlist creation"):
            self.publish(plan)
        self.assertEqual(self.youtube.playlist_count,1)
        self.assertEqual(self.video_calls,0)

    def test_unverified_trailer_rejected_and_verified_trailer_first(self):
        path=self.root/".microgen_youtube"/"trailer"/"video_00.mp4"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"promo mp4")
        with patch("selenium_pipeline.youtube_course_publish._mp4_duration",return_value=59.0):
            with self.assertRaisesRegex(YouTubeCourseError,"<59"):
                self.plan(trailer=path)
        with patch("selenium_pipeline.youtube_course_publish._mp4_duration",return_value=52.0), patch(
                "selenium_pipeline.course_video00.verify_video00",
                return_value={"status":"SOURCE_BOUND_VIDEO00_VERIFIED",
                              "plan":{"course_title":"Physics 8 and 10"}}):
            plan=self.plan(trailer=path)
        self.assertEqual(plan["items"][0].key,"video_00")
        self.assertEqual(plan["items"][0].duration_s,52.0)
        self.assertTrue(plan["trailer_included"])

    def test_trailer_for_different_course_title_is_rejected(self):
        path=self.root/".microgen_youtube"/"trailer"/"video_00.mp4"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"source bound placeholder")
        with patch("selenium_pipeline.youtube_course_publish._mp4_duration",
                   return_value=50.0),patch(
                "selenium_pipeline.course_video00.verify_video00",
                return_value={"status":"SOURCE_BOUND_VIDEO00_VERIFIED",
                              "plan":{"course_title":"Different course"}}):
            with self.assertRaisesRegex(YouTubeCourseError,
                                        "not bound to this YouTube course"):
                self.plan(trailer=path)

    def test_removing_local_approval_files_is_irrelevant_to_technical_plan(self):
        self.assertFalse(any((folder/"lecture_human_approval.json").exists()
                             for folder in self.folders))
        self.assertEqual(len(self.plan()["items"]),4)
        self.assertFalse((self.root/".microgen_youtube").exists())


if __name__=="__main__":
    unittest.main()
