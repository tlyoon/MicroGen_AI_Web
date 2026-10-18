"""Single-publisher course-wide completion gate and Video 00 dispatch.

One authorized publishing PC waits for all assigned workers to finish;
no per-subchapter worker uploads and no fictional Drive distributed mutex.
"""
from __future__ import annotations
import argparse
import json
import re
import socket
import time
from pathlib import Path

from .youtube_course_publish import (
    YouTubeCourseError, require, plan_course, publish_course, authenticate_youtube,
)
from .course_video00 import plan_video00, render_video00, verify_video00

NAME=re.compile(r"^[a-zA-Z0-9_-]+$")
ALLOWED={"HP","Dell-115","Yoga6"}

def check_course_workers(root: Path, *, run_id: str) -> dict:
    """Read-only, require exact all-source coverage, not a pilot subset."""
    require(NAME.fullmatch(run_id) is not None,"Invalid run ID")
    root=Path(root).expanduser().resolve()
    coordination=root/".microgen_coordination"/run_id
    manifest=coordination/"assignments.json"
    require(manifest.is_file() and not manifest.is_symlink(),
            "No verified distributed-course assignment manifest")
    data=json.loads(manifest.read_text(encoding="utf-8"))
    assignment=data.get("assignments")
    require(isinstance(assignment,dict) and assignment,
            "No publisher-verifiable worker assignments")
    require(set(assignment).issubset(ALLOWED),"Disallowed worker (Zenbook excluded)")
    all_topics=set()
    seen_chapters=set()
    for worker,chapters in assignment.items():
        require(isinstance(chapters,list) and chapters and
                all(type(x) is int for x in chapters),
                "Invalid owner chapters in assignment manifest")
        require(not seen_chapters.intersection(chapters),
                "Two workers assigned overlapping chapters")
        seen_chapters.update(chapters)
        status_file=coordination/(worker+".json")
        require(status_file.is_file() and not status_file.is_symlink(),
                "Assigned PC has not reported completion: "+worker)
        status=json.loads(status_file.read_text(encoding="utf-8"))
        require(status.get("run_id")==run_id and status.get("worker")==worker
                and status.get("chapters")==chapters
                and status.get("phase")=="finished"
                and status.get("unfinished")==[],
                "Assigned PC still running, incomplete or wrong run: "+worker)
        expected=set()
        for chapter in chapters:
            folder=root/str(chapter)
            require(folder.is_dir(),f"Chapter source missing: {chapter}")
            for sub in folder.iterdir():
                if (sub.is_dir() and re.fullmatch(r"[0-9]+\.[0-9]+",sub.name)
                        and int(sub.name.split(".")[0])==chapter
                        and (sub/"source.pdf").is_file()):
                    expected.add(sub.name)
        require(expected,"Assigned worker has no source.pdf jobs")
        require(set(status.get("assigned",[]))==expected,
                f"Worker {worker} only completed a partial/pilot target set")
        jobs=status.get("jobs",{})
        require(isinstance(jobs,dict) and set(jobs)==expected,
                f"Worker {worker} lacks exact course worklist")
        for topic in expected:
            row=jobs[topic]
            require(isinstance(row,dict)
                    and row.get("status")=="complete"
                    and row.get("stage")=="video"
                    and row.get("verified") is True
                    and row.get("contract")=="accepted_synchronized_series",
                    f"Worker {worker} has no accepted technical video: {topic}")
        all_topics.update(expected)
    actual=set()
    for chapter in root.iterdir():
        if not chapter.is_dir() or not chapter.name.isdecimal():
            continue
        for folder in chapter.iterdir():
            if (folder.is_dir() and re.fullmatch(r"[0-9]+\.[0-9]+",folder.name)
                    and int(folder.name.split(".")[0])==int(chapter.name)
                    and (folder/"source.pdf").is_file()):
                actual.add(folder.name)
    require(all_topics==actual,"Distributed assignment excludes live course subchapters")
    return {"status":"ALL_ASSIGNED_PCS_TECHNICALLY_COMPLETE",
            "run_id":run_id,"workers":sorted(assignment),
            "topics":sorted(all_topics,key=lambda x:tuple(map(int,x.split(".")))),
            "human_review_required":False}

def audit_and_plan(*, root: Path, run_id: str, course_title: str) -> dict:
    worker=check_course_workers(root,run_id=run_id)
    course=plan_course(root,course_title=course_title,require_complete=True)
    require({x.subchapter for x in course["items"]}==set(worker["topics"]),
            "Worker completion differs from real fully verified source files")
    return {"status":"COURSE_READY_FOR_AUTOMATIC_VIDEO00_AND_YOUTUBE",
            "run":worker,"lecture_parts":len(course["items"]),
            "course_title":course_title,"publish_host_required":True}

def publish_completed_course(*, root: Path, run_id: str, course_title: str,
                             publisher_host: str, expected_channel_id: str | None,
                             expected_handle: str | None, visibility: str,
                             youtube=None) -> dict:
    """Unattended *after all QA*, but only on the designated PC."""
    require(socket.gethostname().casefold()==publisher_host.casefold()
            and bool(expected_channel_id or expected_handle),
            "This PC is not the pinned YouTube publisher/channel")
    root=Path(root).resolve()
    audit_and_plan(root=root,run_id=run_id,course_title=course_title)
    trailer=root/".microgen_youtube"/"trailer"/"video_00.mp4"
    if trailer.exists():
        verify_video00(trailer,source_root=root)
    else:
        planned=plan_video00(root,course_title=course_title)
        # Deterministic plan only; original source MP4/WAV never altered.
        render_video00(planned,source_root=root)
    verify_video00(trailer,source_root=root)
    full=plan_course(root,course_title=course_title,
                     trailer=trailer,require_complete=True)
    # Recheck statuses and actual original content after local rendering,
    # before any account login or remote action.
    audit_and_plan(root=root,run_id=run_id,course_title=course_title)
    if youtube is None:
        youtube=authenticate_youtube()
    published=publish_course(
        full,youtube=youtube,
        expected_channel_id=expected_channel_id,
        expected_handle=expected_handle,
        publisher_host=publisher_host,visibility=visibility)
    return {"status":"COURSE_YOUTUBE_AUTOMATIC_PUBLISH_COMPLETED",
            "run_id":run_id,"video00_included":True,**published}

def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description="MicroGen all-PC YouTube completion gate")
    parser.add_argument("command",choices=("audit","publish","watch"))
    parser.add_argument("--source-root",type=Path,required=True)
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--course-title",required=True)
    parser.add_argument("--publisher-host")
    parser.add_argument("--expected-channel-id")
    parser.add_argument("--expected-handle")
    parser.add_argument("--visibility",choices=("public","unlisted","private"),default="public")
    parser.add_argument("--poll-seconds",type=int,default=60)
    parser.add_argument("--max-wait-seconds",type=int,default=86400)
    args=parser.parse_args(argv)
    require(args.command=="audit" or
            (args.publisher_host and (args.expected_channel_id or args.expected_handle)),
            "Automatic publishing requires pinned host and YouTube channel")
    if args.command=="audit":
        result=audit_and_plan(root=args.source_root,run_id=args.run_id,
                              course_title=args.course_title)
    else:
        if args.command=="watch":
            require(10<=args.poll_seconds<=3600 and args.max_wait_seconds>=10,
                    "Unsupported watcher cadence or deadline")
            cutoff=time.monotonic()+args.max_wait_seconds
            while True:
                try:
                    audit_and_plan(root=args.source_root,run_id=args.run_id,
                                   course_title=args.course_title)
                    break
                except (YouTubeCourseError,OSError,ValueError):
                    if time.monotonic()>=cutoff:
                        raise YouTubeCourseError(
                            "Course never became technically complete by deadline")
                    time.sleep(min(args.poll_seconds,max(0,cutoff-time.monotonic())))
        result=publish_completed_course(
            root=args.source_root,run_id=args.run_id,
            course_title=args.course_title,
            publisher_host=args.publisher_host,
            expected_channel_id=args.expected_channel_id,
            expected_handle=args.expected_handle,
            visibility=args.visibility)
    print(json.dumps(result,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
