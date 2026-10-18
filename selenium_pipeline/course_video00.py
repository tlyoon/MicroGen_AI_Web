"""Source-grounded narrated course teaser (Video 00), no invented TTS.

Every excerpt preserves original audio and the already accepted synchronized
element highlights. This is an excerpt montage, not a new scripted lecture.
"""
from __future__ import annotations
import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

from .production_video_contract import _mp4_duration
from .tts_effective_identity import verify_effective_identity
from .video_ffmpeg import ffmpeg_executable
from .youtube_course_publish import plan_course, sha256, require, YouTubeCourseError, generate_course_cover
from .runner import blocks

def _identity(folder: Path) -> tuple[str,str,str]:
    try:
        data=json.loads((folder/"tts_input_manifest.json").read_text(encoding="utf-8"))
        speech=blocks((folder/"script.txt").read_text(encoding="utf-8"))
        info=verify_effective_identity(data,speech)
    except (ValueError,OSError,KeyError) as exc:
        raise YouTubeCourseError(f"{folder.name}: no source-bound consistent TTS proof") from exc
    return tuple(info[k] for k in ("provider","model","voice"))

def plan_video00(source_root: Path, *, course_title: str) -> dict:
    course=plan_course(source_root,course_title=course_title,require_complete=True)
    voices=set()
    by_topic={}
    for item in course["items"]:
        folder=item.mp4.parent.parent
        voices.add(_identity(folder))
        alignment=folder/item.part_id/"narration_alignment.json"
        require(alignment.is_file() and not alignment.is_symlink(),
                f"Missing segment alignment: {item.key}")
        data=json.loads(alignment.read_text(encoding="utf-8"))
        require(isinstance(data.get("events"),list),f"Invalid alignment {item.key}")
        for event in data["events"]:
            start,end=event.get("start_ms"),event.get("end_ms")
            require(type(start) is int and type(end) is int and
                    0<=start<end<=round(item.duration_s*1000)+400,
                    "Unbound or invalid original spoken interval")
            seconds=(end-start)/1000
            if 4 <= seconds <= 12:
                by_topic.setdefault(item.subchapter,[]).append({
                    "topic":item.subchapter,"key":item.key,
                    "mp4":str(item.mp4),"source_sha256":item.source_sha256,
                    "video_sha256":item.sha256,
                    "alignment_sha256":sha256(alignment),
                    "start_ms":start,"end_ms":end,
                    "duration_s":round(seconds,3)})
    require(len(voices)==1, "Video 00 refuses mixed TTS model/voice across lessons")
    require(len(by_topic)>=3,"Need >=3 technically accepted subchapters for a course trailer")
    order=sorted(by_topic,key=lambda s:tuple(map(int,s.split("."))))
    taken=set()
    chosen=[]
    for _ in range(12):
        for topic in order:
            available=[x for x in by_topic[topic] if
                       (x["mp4"],x["start_ms"],x["end_ms"]) not in taken]
            if not available:continue
            item=available[0]
            if sum(x["duration_s"] for x in chosen)+item["duration_s"]>53:
                continue
            chosen.append(item)
            taken.add((item["mp4"],item["start_ms"],item["end_ms"]))
            if 45<=sum(x["duration_s"] for x in chosen)<=53: break
        if 45<=sum(x["duration_s"] for x in chosen)<=53:break
    duration=sum(x["duration_s"] for x in chosen)
    require(45<=duration<=53 and len({x["topic"] for x in chosen})>=3,
            "Cannot produce a verified 45-55s multi-topic montage from whole speech events")
    return {"schema_version":1,"status":"SOURCE_BOUND_VIDEO00_PLAN",
            "course_title":course_title,"voice":dict(zip(("provider","model","voice"),next(iter(voices)))),
            "clips":chosen,"duration_s":round(duration,3),
            "synthesized_narration":False,
            "human_review_required":False}

def _check(plan: dict, root: Path) -> None:
    require(plan.get("status")=="SOURCE_BOUND_VIDEO00_PLAN","Missing Video 00 plan")
    clips=plan["clips"]
    require(45<=sum(x["duration_s"] for x in clips)<=53,
            "Out-of-range Video 00 plan")
    for row in clips:
        video=Path(row["mp4"])
        require(video.resolve().is_relative_to(root),"Video 00 source escapes course root")
        require(sha256(video)==row["video_sha256"],
                "Source video changed after Video 00 selection")
        require(sha256(video.parent.parent/"source.pdf")
                ==row["source_sha256"],
                "Source PDF changed after Video 00 selection")
        require(sha256(video.parent/"narration_alignment.json")
                ==row["alignment_sha256"],"Source timing changed after selection")
        voice=_identity(video.parent.parent)
        require(tuple(plan["voice"][key] for key in ("provider","model","voice"))
                ==voice,"TTS identity changed after Video 00 selection")
        require(row["end_ms"]>row["start_ms"],"Invalid original cue boundary")

def render_video00(plan: dict, *, source_root: Path, ffmpeg: str | None=None) -> dict:
    root=Path(source_root).expanduser().resolve()
    _check(plan,root)
    meta=root/".microgen_youtube"
    dest=meta/"trailer"
    require(not meta.is_symlink() and not dest.exists(),
            "Trailer output must be a fresh, non-symlink directory")
    exe=ffmpeg or ffmpeg_executable()
    meta.mkdir(exist_ok=True)
    require(meta.is_dir() and not meta.is_symlink(),
            "Trailer metadata directory is unsafe")
    dest.mkdir()
    try:
        out=dest/"video_00.mp4"
        # A two-second, silent title slate identifies the course before
        # unmodified, audible lecture excerpts. No new narration is invented.
        title=generate_course_cover(plan["course_title"],dest/"title_card.jpg")
        command=[exe,"-hide_banner","-nostdin","-loglevel","error","-n",
                 "-loop","1","-t","2","-i",str(title),
                 "-f","lavfi","-t","2","-i","anullsrc=r=22050:cl=mono"]
        clips=plan["clips"]
        for row in clips:
            command += ["-ss",f'{row["start_ms"]/1000:.3f}',
                        "-t",f'{row["duration_s"]:.3f}',"-i",row["mp4"]]
        filters=[
            "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=15,setpts=PTS-STARTPTS[vt]",
            "[1:a]atrim=duration=2,asetpts=PTS-STARTPTS[at]"]
        for i in range(len(clips)):
            source_index=i+2
            filters += [
                f"[{source_index}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=15,setpts=PTS-STARTPTS[v{i}]",
                f"[{source_index}:a]aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS[a{i}]"]
        filters += ["[vt][at]"+"".join(f"[v{i}][a{i}]" for i in range(len(clips)))+
                    f"concat=n={len(clips)+1}:v=1:a=1[outv][outa]"]
        command += ["-filter_complex",";".join(filters),
                    "-map","[outv]","-map","[outa]",
                    "-c:v","libx264","-preset","veryfast","-crf","24",
                    "-pix_fmt","yuv420p","-c:a","aac","-b:a","144k",
                    "-movflags","+faststart",str(out)]
        run=subprocess.run(command,capture_output=True,text=True,errors="replace",
                           timeout=300)
        require(run.returncode==0,"Video 00 FFmpeg error: "+run.stderr[-500:])
        measured=_mp4_duration(out)
        require(45<=measured<=55,
                "Encoded Video 00 violates 45-55-second target")
        _check(plan,root)
        result={"schema_version":1,"status":"SOURCE_BOUND_VIDEO00_VERIFIED",
                "plan":plan,"mp4_sha256":sha256(out),
                "title_card_sha256":sha256(title),
                "title_card_duration_s":2.0,
                "mp4_duration_s":round(measured,3),
                "human_review_required":False,
                "original_audio_only":True}
        with (dest/"video_00_receipt.json").open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2)
        return result
    except BaseException:
        shutil.rmtree(dest,ignore_errors=True) # exclusively new folder
        raise

def verify_video00(video: Path, *, source_root: Path) -> dict:
    root=Path(source_root).resolve()
    path=Path(video).resolve()
    require(path==root/".microgen_youtube"/"trailer"/"video_00.mp4",
            "Unrecognized trailer path")
    receipt=path.parent/"video_00_receipt.json"
    require(receipt.is_file() and not receipt.is_symlink(),
            "Missing immutable trailer evidence")
    data=json.loads(receipt.read_text(encoding="utf-8"))
    require(data.get("status")=="SOURCE_BOUND_VIDEO00_VERIFIED",
            "Trailer lacks source-bound verified status")
    require(sha256(path)==data["mp4_sha256"],"Video 00 MP4 changed")
    require(sha256(path.parent/"title_card.jpg")==data["title_card_sha256"],
            "Course title card changed after video encoding")
    _check(data["plan"],root)
    actual=_mp4_duration(path)
    require(45<=actual<=55 and abs(actual-data["mp4_duration_s"])<=0.15,
            "Trailer duration differs from recorded receipt")
    return data

def main(argv=None):
    ap=argparse.ArgumentParser(description="Source-bound course teaser Video 00")
    ap.add_argument("command",choices=("plan","render"))
    ap.add_argument("--source-root",required=True,type=Path)
    ap.add_argument("--course-title",required=True)
    args=ap.parse_args(argv)
    planned=plan_video00(args.source_root,course_title=args.course_title)
    out=planned if args.command=="plan" else render_video00(planned,source_root=args.source_root)
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
