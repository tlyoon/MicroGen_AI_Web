"""Real MP4 pixel-based legacy G3 disposition and immutable rebuild handoff.

Recognizes a verified legacy PDF/WAV -> video parts series whose within-slide
frames do not change. Never equates an MP4, TTS transcript report, or video
metadata with source-math, independent listening or highlight acceptance.
Creates an isolated recovery worklist without modifying source files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import wave

from .recovery_registry import lookup_mechanism
from .development_continuity_executor_v71 import _atomic_json

KIND="g3_legacy_visual_recovery"
SIGNATURE="G3_LEGACY_STATIC_MP4_SOURCE_BOUND_REBUILD"
MECHANISM="VERIFY_REAL_ENCODED_FRAMES_STAGE_IMMUTABLE_ISOLATED_REBUILD"
MAX_SECONDS=600.0
PIXEL_DIFF_THRESHOLD=0.25
SAMPLE_SIZE=160*90*3
SOURCE_NAMES=("source.pdf","slides.pdf","script.txt")
REGEX=re.compile(r"slide([1-9][0-9]*)\.wav\Z")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def sha(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(),
            "Missing/redirected original evidence "+str(path))
    result=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024),b""):
            result.update(chunk)
    return result.hexdigest()


def _registered() -> None:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "No registered repair for legacy static G3 output")


def _json(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 1<=path.stat().st_size<=80000,
            "Missing or unsafe original source-bound video manifest")
    record=json.loads(path.read_text(encoding="utf-8-sig"))
    require(type(record) is dict,"Original manifest not an object")
    return record


def _frame(mp4: Path, second: float, exe: str) -> bytes:
    require(0<=second<MAX_SECONDS,
            "Requested video sample outside bounded part")
    out=subprocess.run([
        exe,"-nostdin","-hide_banner","-loglevel","error",
        "-ss",str(round(second,3)),"-i",str(mp4),
        "-frames:v","1","-vf","scale=160:90,format=rgb24",
        "-f","rawvideo","pipe:1",
    ],capture_output=True,timeout=20)
    require(out.returncode==0 and len(out.stdout)==SAMPLE_SIZE,
            "Actual encoded source frame could not be independently decoded")
    return out.stdout


def pixel_difference(a: bytes, b: bytes) -> float:
    require(type(a) is bytes and type(b) is bytes
            and len(a)==len(b)==SAMPLE_SIZE,
            "Malformed actual decoded video frame")
    return sum(abs(x-y) for x,y in zip(a,b))/SAMPLE_SIZE


def inspect_legacy(*,folder:Path,sampler=None,probe=None) -> dict:
    """Fail closed on stale/missing original hashes or visual motion identity."""
    _registered()
    root=Path(folder).absolute()
    require(root.is_dir() and not root.is_symlink(),
            "Invalid original section")
    hashes={name:sha(root/name) for name in SOURCE_NAMES}
    parts=_json(root/"slides_parts_manifest.json")
    sync=_json(root/"slide_narration_sync.json")
    require(sync.get("pdf_sha256")==hashes["slides.pdf"]
            and sync.get("script_sha256")==hashes["script.txt"]
            and parts.get("source_slides_pdf_sha256")==hashes["slides.pdf"]
            and type(sync.get("pages")) is int
            and 2<=sync["pages"]<=150
            and type(sync.get("wav")) is list
            and len(sync["wav"])==sync["pages"],
            "Source/slides/script WAV identity no longer matches original")
    n=sync["pages"]
    wavs={}
    wav_hashes={}
    for i, row in enumerate(sync["wav"],1):
        file=root/f"slide{i}.wav"
        actual_wav_sha=sha(file)
        require(type(row) is dict and row.get("file")==file.name
                and actual_wav_sha==row.get("sha256"),
                "Original numbered WAV or signed sync manifest changed")
        wav_hashes[file.name]=actual_wav_sha
        with wave.open(str(file),"rb") as wav:
            require(wav.getnchannels()==1
                    and wav.getsampwidth()==2
                    and wav.getframerate()==24000
                    and wav.getcomptype()=="NONE"
                    and wav.getnframes()>24000,
                    "Original WAV is not valid 24 kHz 16-bit PCM")
            seconds=wav.getnframes()/wav.getframerate()
        require(abs(seconds-row.get("duration_s",-100))<.03,
                "Original narration WAV duration not bound to manifest")
        wavs[i]=seconds
    actual_files={x.name for x in root.glob("slide*.wav")
                  if REGEX.fullmatch(x.name)}
    require(actual_files=={f"slide{i}.wav" for i in range(1,n+1)},
            "Extra or missing numbered WAV in original source")
    listed=parts.get("parts")
    require(type(listed) is list and 1<=len(listed)<=16
            and parts.get("active_deliverables")==[x.get("file") for x in listed]
            and parts.get("split_method")==
                "per_slide_boundary_with_separate_encoder_outputs"
            and sha(root/"slides.mp4")==parts.get("verified_full_sha256"),
            "Unrecognized or modified legacy multipart video generation")
    from .highlight_video_preview import ffmpeg_path,probe_mp4
    exe=None if sampler is not None and probe is not None else ffmpeg_path()
    read_frame=(lambda path,at:_frame(path,at,exe)) if sampler is None else sampler
    probe_part=(lambda path:probe_mp4(path,exe=exe)) if probe is None else probe
    examined=[]
    next_slide=1
    snapshots=[]
    for j, row in enumerate(listed,1):
        require(type(row) is dict and set(row)=={
            "file","sha256","duration_seconds","slides"},
            "Malformed original video part receipt")
        start,end=row["slides"]
        filename=f"slides_part{j:02d}.mp4"
        require(type(start) is int and type(end) is int
                and start==next_slide and start<=end<=n
                and row["file"]==filename
                and type(row["duration_seconds"]) in (int,float)
                and math.isfinite(row["duration_seconds"]),
                "Legacy parts do not cover consecutive original slides")
        next_slide=end+1
        file=root/filename
        actual_hash=sha(file)
        require(actual_hash==row["sha256"],
                "Actual MP4 part differs from signed original manifest")
        metadata=probe_part(file)
        duration=metadata["duration_s"]
        require(0<duration<MAX_SECONDS
                and abs(duration-row["duration_seconds"])<.75
                and abs(duration-sum(wavs[i] for i in range(start,end+1)))<1.5,
                "Actual MP4 duration does not match source WAV timing")
        eligible=[i for i in range(start,end+1) if wavs[i]>=12 and i>1]
        require(eligible,"No real narrated content slide for G3 pixel evidence")
        chosen=sorted({eligible[0],eligible[len(eligible)//2],eligible[-1]})
        for slide in chosen:
            position=sum(wavs[i] for i in range(start,slide))
            frames=[]
            for fraction in (.18,.48,.78):
                t=position+fraction*wavs[slide]
                require(t<duration-.05,
                        "Original narration timestamps exceed decoded MP4")
                frames.append(read_frame(file,t))
            diffs=[pixel_difference(frames[0],frames[1]),
                   pixel_difference(frames[1],frames[2])]
            examined.append({"part":filename,"slide":slide,
                             "max_within_slide_rgb_change":round(max(diffs),6),
                             "samples":3})
        snapshots.append({"file":filename,"sha256":actual_hash,
                          "duration_s":round(duration,3),
                          "slide_range":[start,end]})
    require(next_slide==n+1 and len(examined)>=len(listed)*2,
            "Incomplete independent full-series media sampling")
    changed=[x for x in examined
             if x["max_within_slide_rgb_change"]>PIXEL_DIFF_THRESHOLD]
    if not changed:
        disposition="G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED"
    else:
        disposition="G3_MOTION_OBSERVED_HIGHLIGHT_STILL_UNATTESTED"
    return {
        "schema_version":1,"status":disposition,
        "source_folder":str(root),"original_sha256":hashes,
        "original_slide_count":n,
        "legacy_parts_manifest_sha256":sha(root/"slides_parts_manifest.json"),
        "original_narration_sync_sha256":sha(root/"slide_narration_sync.json"),
        "original_full_video_sha256":sha(root/"slides.mp4"),
        "original_wav_sha256":wav_hashes,
        "legacy_parts":snapshots,"sampled_encoded_frames":3*len(examined),
        "sampled_content_slides":examined,
        "moving_slides":len(changed),
        "recovery_action":("STAGE_SOURCE_PINNED_ISOLATED_HIGHLIGHT_REBUILD"
                           if not changed else "INDEPENDENT_HIGHLIGHT_SYNC_REVIEW"),
        "independent_acoustic_acceptance":False,
        "independent_video_acceptance":False,
        "independent_scientific_acceptance":False,
        "paid_api_requests":0,
        "model_requests":0,
        "student_publication_authorized":False,
    }


def stage_recovery(*,report:dict,staging_root:Path) -> Path:
    """Immutable digest-bound recovery queue outside the source PDF folder."""
    _registered()
    require(report.get("status")=="G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED"
            and report.get("student_publication_authorized") is False
            and report.get("model_requests")==0,
            "Only a source-verified legacy static video can stage repair")
    source=Path(report["source_folder"]).absolute()
    root=Path(staging_root).absolute()
    require(root.is_dir() and not root.is_symlink()
            and not root.is_relative_to(source)
            and not source.is_relative_to(root)
            and root!=source,
            "Rebuild staging must be independently isolated")
    for name,old in report["original_sha256"].items():
        require(sha(source/name)==old,"Original PDF or script changed after audit")
    for item in report["legacy_parts"]:
        require(sha(source/item["file"])==item["sha256"],
                "Original MP4 part changed after pixel audit")
    for name,reference in (
        ("slides_parts_manifest.json",report["legacy_parts_manifest_sha256"]),
        ("slide_narration_sync.json",report["original_narration_sync_sha256"]),
        ("slides.mp4",report["original_full_video_sha256"]),
    ):
        require(sha(source/name)==reference,
                "Original manifest or video changed after independent audit")
    for name,reference in report["original_wav_sha256"].items():
        require(sha(source/name)==reference,
                "Original WAV changed after independent G3 pixel audit")
    key=hashlib.sha256(json.dumps(report,sort_keys=True,
                                 separators=(",",":")).encode()).hexdigest()
    path=root/("g3_legacy_static_"+key[:24]+".json")
    row={
        "schema_version":1,
        "status":"G3_ISOLATED_SOURCE_BOUND_HIGHLIGHT_REBUILD_WORKLIST",
        "source_folder":str(source),
        "source_sha256":report["original_sha256"]["source.pdf"],
        "slides_sha256":report["original_sha256"]["slides.pdf"],
        "script_sha256":report["original_sha256"]["script.txt"],
        "original_slide_count":report["original_slide_count"],
        "original_static_media_evidence_sha256":key,
        "technical_diagnosis":report,
        "next_action":"BUILD_NEW_ELEMENT_SYNCHRONIZED_VIDEO_IN_ISOLATED_STAGING_ONLY",
        "original_wavs_must_be_preserved":True,
        "no_overwrite_of_legacy_mp4":True,
        "requires_independent_acoustic_QA":True,
        "requires_independent_highlight_video_QA":True,
        "requires_independent_scientific_QA":True,
        "auto_acceptance":False,
        "student_release":False,
        "paid_api_requests":0,
    }
    if path.exists():
        require(_json(path)==row,
                "Prior isolated G3 repair worklist changed; no replacement")
    else:
        _atomic_json(path,row)
    return path


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--staging-root",type=Path,required=True)
    a=p.parse_args(argv)
    report=inspect_legacy(folder=a.folder)
    if report["status"]=="G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED":
        plan=stage_recovery(report=report,staging_root=a.staging_root)
        report["isolated_rebuild_worklist"]=str(plan)
    print(json.dumps(report,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
