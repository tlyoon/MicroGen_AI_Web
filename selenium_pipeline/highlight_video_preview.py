"""Deterministic synthetic MP4 composition from source-verified highlight timing.

This is NOT final production video release; it encodes a tested storyboard
preview from an already-clean PDF and verified per-segment WAV chunks.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import wave

import pymupdf
from PIL import Image

from .highlight_frames import render_highlight_frames
from .pdf_element_geometry import URI_PREFIX
from .storyboard_gate import canonical_sha256


class HighlightVideoError(ValueError):
    """Highlight media does not match validated upstream inputs."""


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def ffmpeg_path() -> str:
    try:
        import imageio_ffmpeg
        path=imageio_ffmpeg.get_ffmpeg_exe()
        if Path(path).is_file():
            return path
    except (ImportError,RuntimeError,OSError):
        pass
    path=shutil.which("ffmpeg")
    if not path:
        raise HighlightVideoError("FFmpeg is not available")
    return path


def probe_mp4(filename: Path, *, exe: str) -> dict:
    """Independent FFmpeg stream and actual container duration gate."""
    result=subprocess.run([exe,"-hide_banner","-i",str(filename)],
                          capture_output=True,text=True,timeout=30)
    details=result.stderr+"\n"+result.stdout
    match=re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",details)
    if not match or "Video:" not in details or "Audio:" not in details:
        raise HighlightVideoError("MP4 lacks measured duration or video/audio stream")
    duration=int(match[1])*3600+int(match[2])*60+float(match[3])
    if not math.isfinite(duration) or not 0<duration<600:
        raise HighlightVideoError("Encoded MP4 violates strict <600-second duration limit")
    return {"duration_s":round(duration,3),"video":True,"audio":True}


def verify_encoded_transition_times(
    mp4: Path, *, exe: str, intervals: list[dict],
    tolerance_s: float=0.15,
) -> dict:
    """Decode encoded video and match its VFR change points to speech timeline."""
    run=subprocess.run([
        exe,"-hide_banner","-loglevel","info","-i",str(mp4),
        "-vf","showinfo","-an","-f","null","-",
    ],capture_output=True,text=True,timeout=80)
    if run.returncode!=0:
        raise HighlightVideoError("Could not decode MP4 to inspect frame timestamps")
    pts=sorted(set(float(x) for x in re.findall(
        r"pts_time:\s*(\d+(?:\.\d+)?)",run.stderr
    )))
    if not pts:
        raise HighlightVideoError("No decoded MP4 video frame timestamps found")
    expected=[0.0]
    running=0.0
    for row in intervals[:-1]:
        running+=row["duration_s"]
        expected.append(running)
    errors=[min(abs(value-actual) for actual in pts) for value in expected]
    if max(errors)>tolerance_s:
        raise HighlightVideoError(
            f"Encoded VFR frames drift from narration boundaries: "
            f"worst={max(errors):.3f} seconds"
        )
    return {"verified_transition_count":len(expected),
            "max_encoded_frame_drift_s":round(max(errors),4),
            "tolerance_s":tolerance_s}


def _render_base_frames(pdf: Path, storyboard: dict, workspace: Path,
                        *, scale: float) -> dict[str, str]:
    files={}
    with pymupdf.open(pdf) as document:
        if len(document)!=len(storyboard["slides"]):
            raise HighlightVideoError("Clean PDF and storyboard slide counts differ")
        for i,slide in enumerate(storyboard["slides"],1):
            page=document[i-1]
            if any(str(x.get("uri","")).startswith(URI_PREFIX) for x in page.get_links()):
                raise HighlightVideoError("PDF still contains interactive instrumentation links")
            image=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
            name=f"base_{i:04d}.png"
            path=workspace/name
            with path.open("xb") as stream:
                Image.frombytes("RGB",(image.width,image.height),image.samples).save(
                    stream,format="PNG"
                )
            files[slide["slide_id"]]=name
    return files


def compose_highlight_preview(
    *, clean_pdf: str | Path, clean_receipt: dict, storyboard: dict,
    geometry: dict, timeline: dict, wav_file: str | Path,
    workspace: str | Path, output_mp4: str | Path, scale: float=2.0,
    encoder: str | None=None,
) -> dict:
    """Create a static-slide VFR MP4 with highlight switches at WAV frame times.

    Emits base-slide intervals during narration pauses; NO post-hoc splitting,
    trimming of the instructional material or invented timing.
    """
    clean=Path(clean_pdf).resolve()
    wav=Path(wav_file).resolve()
    out=Path(output_mp4).resolve()
    work=Path(workspace).resolve()
    if not all(p.is_file() for p in (clean,wav)):
        raise HighlightVideoError("Missing verified PDF or WAV")
    if not work.is_dir() or not out.parent.is_dir() or out.exists():
        raise HighlightVideoError("Workspace/output missing or output already exists")
    if any(work.iterdir()):
        raise HighlightVideoError("Workspace must be empty to prevent stale assets")
    if clean_receipt.get("clean_pdf_sha256") != sha256_file(clean):
        raise HighlightVideoError("Clean PDF differs from its pixel-equivalence receipt")
    if clean_receipt.get("status")!="clean_static_pdf_exact_pixel_match":
        raise HighlightVideoError("PDF cleanup has no accepted pixel comparison")
    if timeline.get("audio_sha256")!=sha256_file(wav):
        raise HighlightVideoError("Narration WAV no longer matches measured timing")
    binding=canonical_sha256(storyboard)
    if geometry.get("storyboard_sha256")!=binding or timeline.get("storyboard_sha256")!=binding:
        raise HighlightVideoError("Stale storyboard/geometry/timeline relationship")
    if timeline.get("slide_pdf_sha256")!=geometry.get("instrumented_pdf_sha256"):
        raise HighlightVideoError("Timeline references another PDF generation")
    with wave.open(str(wav),"rb") as stream:
        wav_length=stream.getnframes()/stream.getframerate()
    if wav_length>=600 or wav_length<=0:
        raise HighlightVideoError("Actual WAV does not fit strict video limit")
    audio_ms=timeline["duration_ms"]
    if abs(audio_ms/1000-wav_length)>0.002:
        raise HighlightVideoError("Timeline length differs from actual WAV")
    events=timeline.get("events",[])
    if not events or any(type(x.get("start_ms")) is not int or
                         type(x.get("end_ms")) is not int for x in events):
        raise HighlightVideoError("Missing or malformed exact speech times")
    if abs(scale-round(scale,2))>1e-6 or not 0.5<=scale<=4:
        raise HighlightVideoError("Invalid rendering scale")

    seq=[]
    prev_end=0
    prev_slide=None
    for event in events:
        start,end=event["start_ms"],event["end_ms"]
        if start<prev_end or end<=start or end>audio_ms:
            raise HighlightVideoError("Overlapping, reversed or out-of-range speech events")
        sid=event["slide_id"]
        seq.append((start,end,sid))
        prev_end=end
    # Preflight passed: emit temporary assets under the isolated workspace.
    bases=_render_base_frames(clean,storyboard,work,scale=scale)
    previews=render_highlight_frames(clean,storyboard,geometry,timeline,
                                     output_dir=work,scale=scale)
    durations=[]
    cursor=0
    for event,preview in zip(events,previews):
        start,end=event["start_ms"],event["end_ms"]
        if start>cursor:
            # Pause interval: display the previously active slide WITHOUT highlighting.
            slide=durations[-1]["slide_id"] if durations else event["slide_id"]
            durations.append({"file":bases[slide],"duration_s":(start-cursor)/1000,
                              "slide_id":slide,"highlight":False})
        durations.append({"file":Path(preview["file"]).name,
                          "duration_s":(end-start)/1000,
                          "slide_id":event["slide_id"],"highlight":True})
        cursor=end
    if audio_ms>cursor:
        durations.append({"file":bases[events[-1]["slide_id"]],
                          "duration_s":(audio_ms-cursor)/1000,
                          "slide_id":events[-1]["slide_id"],"highlight":False})
    manifest=work/"frames.ffconcat"
    # All filenames are internally generated ASCII safe paths.
    with manifest.open("x",encoding="ascii",newline="\n") as f:
        f.write("ffconcat version 1.0\n")
        for event in durations:
            f.write(f"file '{event['file']}'\n")
            f.write(f"duration {event['duration_s']:.6f}\n")
        f.write(f"file '{durations[-1]['file']}'\n")
    tmp=work/"encoded_candidate.mp4"
    exe=encoder or ffmpeg_path()
    cmd=[exe,"-hide_banner","-loglevel","error",
         "-f","concat","-safe","0","-i",str(manifest),
         "-i",str(wav),"-map","0:v:0","-map","1:a:0",
         "-c:v","libx264","-preset","veryfast","-crf","22",
         # Beamer page point dimensions are often fractional: rendering at
         # valid scales can yield odd pixel width/height (e.g. 681x383).
         # H.264 yuv420p requires both dimensions divisible by two. Pad by
         # at most one pixel; never rescale or crop source figure panels.
         "-vf","pad=ceil(iw/2)*2:ceil(ih/2)*2",
         "-pix_fmt","yuv420p","-fps_mode","vfr",
         "-c:a","aac","-b:a","160k",
         "-movflags","+faststart","-t",f"{wav_length:.6f}",
         str(tmp)]
    proc=subprocess.run(cmd,cwd=work,capture_output=True,text=True,timeout=130)
    if proc.returncode!=0 or not tmp.is_file():
        raise HighlightVideoError("FFmpeg preview encode failed: "+proc.stderr[-1500:])
    report=probe_mp4(tmp,exe=exe)
    if abs(report["duration_s"]-wav_length)>0.25:
        raise HighlightVideoError("Encoded MP4 is not aligned to combined WAV duration")
    transition_qa=verify_encoded_transition_times(tmp,exe=exe,intervals=durations)
    if out.exists():
        raise HighlightVideoError("Refusing to replace MP4 created by another worker")
    tmp.rename(out)
    return {
        "status":"synthetic_timed_mp4_preview_semantic_and_word_qa_pending",
        "mp4_sha256":sha256_file(out),
        "duration_s":report["duration_s"],
        "audio_duration_s":round(wav_length,6),
        "highlight_segments":len(events),
        "encoded_transition_qa":transition_qa,
        "base_and_highlight_intervals":durations,
        "unverified":["actual_tts_word_fidelity","domain_scientific_correctness",
                      "all_composite_figure_panels","final_production_lecture_acceptance"],
    }
