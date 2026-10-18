"""Inspect actual encoded video pixels against the scheduled semantic highlights.

Timing alone is insufficient: this decoder checks that the *real MP4* is
closer to the expected highlighted frame than to the unhighlighted base,
inside each geometrically verified target region. Source meaning and audio
word fidelity still require separate review.
"""
from __future__ import annotations

import bisect
import math
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from .highlight_video_preview import ffmpeg_path


class EncodedPixelQAError(ValueError):
    """Encoded video does not visibly match its timed highlighted elements."""


def _frame_pts(mp4: Path, *, exe: str) -> list[tuple[int,float]]:
    """Read ALL actual decoded VFR frame timestamps once, preserving index."""
    proc=subprocess.run(
        [exe,"-hide_banner","-loglevel","info",
         "-i",str(mp4),"-vf","showinfo","-an","-f","null","-"],
        capture_output=True,text=True,errors="replace",timeout=120,
    )
    if proc.returncode:
        raise EncodedPixelQAError("FFmpeg could not decode VFR frame timeline")
    matches=re.findall(
        r"\bn:\s*(\d+)\s+pts:\s*-?\d+\s+pts_time:\s*(-?\d+(?:\.\d+)?)",
        proc.stderr,
    )
    result=[(int(index),float(pts)) for index,pts in matches]
    if not result or any(idx!=i for i,(idx,_t) in enumerate(result)):
        raise EncodedPixelQAError("No reliable ordered encoded VFR frames")
    if any(t<0 or not math.isfinite(t) or
           (i and t<result[i-1][1]) for i,(_idx,t) in enumerate(result)):
        raise EncodedPixelQAError("Invalid decoded MP4 timestamps")
    return result


def _decode_selected(mp4: Path, indices: list[int], *, output_dir: Path,
                     exe: str) -> dict[int, Path]:
    """Decode all required speech frames in ONE FFmpeg pass, not per-event."""
    wanted=sorted(set(indices))
    if not wanted or any(type(i) is not int or i<0 for i in wanted):
        raise EncodedPixelQAError("Invalid list of encoded frame indices")
    # Filter expressions are supplied as a direct argument (never a shell).
    selection="+".join(f"eq(n\\,{i})" for i in wanted)
    target=output_dir/"selected_%06d.png"
    proc=subprocess.run([
        exe,"-hide_banner","-loglevel","error",
        "-i",str(mp4),"-vf",f"select={selection}",
        "-vsync","0","-an","-frames:v",str(len(wanted)),
        "-f","image2",str(target),
    ],capture_output=True,text=True,errors="replace",timeout=130)
    if proc.returncode:
        raise EncodedPixelQAError("FFmpeg indexed-frame batch extraction failed: "
                                  +proc.stderr[-320:])
    mapped={idx:output_dir/f"selected_{i:06d}.png"
            for i,idx in enumerate(wanted,1)}
    if not all(path.is_file() for path in mapped.values()):
        raise EncodedPixelQAError("Decoded frame extraction missed a spoken cue")
    return mapped

def _fit(image: Image.Image, width: int, height: int) -> Image.Image:
    # Encoder is allowed to pad at most one pixel for H.264 even dimensions.
    if abs(image.width-width) > 1 or abs(image.height-height) > 1:
        raise EncodedPixelQAError("Encoded dimensions do not match source slide")
    if image.size == (width,height):
        return image.copy()
    frame=Image.new("RGB",(width,height),(0,0,0))
    frame.paste(image,(0,0))
    return frame


def _mae(a: Image.Image, b: Image.Image) -> float:
    return sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3


def verify_encoded_highlight_pixels(
    *, mp4: Path, frames_dir: Path, geometry: dict,
    timeline: dict, scale: float=2.0, encoder: str | None=None,
) -> dict:
    """Fail when encoded MP4 omits a scheduled source-linked visual emphasis.

    Re-renders neither anchors nor timelines. Geometry and timeline must
    already pass the hash-bound source/slide/audio checks in the composer.
    """
    video=Path(mp4)
    frames=Path(frames_dir)
    if not video.is_file() or not frames.is_dir():
        raise EncodedPixelQAError("Missing candidate MP4 or reference frames")
    events=timeline.get("events",[])
    if not isinstance(events,list) or not events:
        raise EncodedPixelQAError("No scheduled source-bound highlight events")
    lookup={x["element_id"]:x for x in geometry.get("elements",[])}
    slide_lookup={x["slide_id"]:int(x["page_index"])+1
                  for x in geometry.get("pages",[])}
    # Geometry page schema has page_index. Do not guess video pages.
    for page in geometry.get("pages",[]):
        if type(page.get("page_index")) is not int:
            raise EncodedPixelQAError("Geometry page index missing")
    ffmpeg=encoder or ffmpeg_path()
    pts=_frame_pts(video,exe=ffmpeg)
    timestamps=[time for _idx,time in pts]
    def encoded_at(seconds: float) -> tuple[int,float]:
        offset=bisect.bisect_right(timestamps,seconds+0.0001)-1
        if offset<0:
            raise EncodedPixelQAError("No encoded frame preceding scheduled emphasis")
        return pts[offset]

    # Midpoint-only checking could accept a video that highlights the correct
    # element for a single frame while showing the wrong one during most of
    # its narration. Sample start, middle and end of each spoken interval.
    # VFR still images may map all three times to the SAME encoded frame;
    # that is valid only when the image remains correct at all sample times.
    chosen=[]
    window_samples=[]
    for event in events:
        start,end=event.get("start_ms"),event.get("end_ms")
        if type(start) is not int or type(end) is not int or end-start<250:
            raise EncodedPixelQAError("Invalid spoken event sample interval")
        span=end-start
        samples=[encoded_at((start+span*fraction)/1000)
                 for fraction in (0.10,0.50,0.90)]
        chosen.append(samples[1])
        window_samples.append(samples)

    # Pauses in the actual WAV should NOT display the previous element's
    # active emphasis. Compare decoded pause frames with the no-highlight
    # reference for the slide being displayed by the encoder.
    pauses=[]
    prev_end=0
    prev_event=None
    prev_number=None
    for number,event in enumerate(events,1):
        start=event["start_ms"]
        if start<prev_end:
            raise EncodedPixelQAError("Overlapping spoken intervals")
        if start-prev_end >= 80:
            slide=(prev_event or event)["slide_id"]
            anchor=prev_event or event
            pauses.append((encoded_at((start+prev_end)/2000),slide,anchor,
                           prev_number if prev_number is not None else number))
        prev_end=event["end_ms"]
        prev_event=event
        prev_number=number
    total_ms=timeline.get("duration_ms")
    if type(total_ms) is not int or total_ms<prev_end:
        raise EncodedPixelQAError("Malformed combined WAV duration")
    if total_ms-prev_end >= 80:
        pauses.append((encoded_at((total_ms+prev_end)/2000),
                       events[-1]["slide_id"],events[-1],len(events)))
    wanted=[idx for idx,_t in chosen]
    wanted.extend(idx for samples in window_samples
                  for idx,_t in samples)
    wanted.extend(sample[0][0] for sample in pauses)
    checks=[]
    time_window_checks=[]
    pause_checks=[]
    with tempfile.TemporaryDirectory(prefix="microgen_pixel_qa_") as temporary:
        extracted=_decode_selected(video,sorted(set(wanted)),
             output_dir=Path(temporary),exe=ffmpeg)
        for i,event in enumerate(events,1):
            sid=event.get("slide_id")
            start,end=event.get("start_ms"),event.get("end_ms")
            eids=event.get("element_ids")
            if (sid not in slide_lookup or type(start) is not int
                or type(end) is not int or end-start<250
                or not isinstance(eids,list) or not eids):
                raise EncodedPixelQAError("Invalid or too-short highlight event")
            page_index=slide_lookup[sid]
            ref_base=frames/f"base_{page_index:04d}.png"
            ref_highlight=frames/f"event_{i:04d}.png"
            if not (ref_base.is_file() and ref_highlight.is_file()):
                raise EncodedPixelQAError("Missing generated base or highlight frame")
            timepoint=(start+end)/2000
            frame_index,frame_time=chosen[i-1]
            sample=extracted[frame_index]
            with Image.open(sample) as raw:
                decoded=raw.convert("RGB")
            try:
                with Image.open(ref_base) as base0, Image.open(ref_highlight) as active0:
                    base=_fit(base0.convert("RGB"),*decoded.size)
                    active=_fit(active0.convert("RGB"),*decoded.size)
                element_checks=[]
                for eid in eids:
                    region=lookup.get(eid)
                    if not isinstance(region,dict) or region.get("slide_id")!=sid:
                        raise EncodedPixelQAError("Highlight target has no matching geometry")
                    coords=region.get("rect_pt")
                    if not isinstance(coords,list) or len(coords)!=4:
                        raise EncodedPixelQAError("Invalid target rectangle")
                    x0,y0,x1,y1=[float(v)*scale for v in coords]
                    margin=8*scale
                    bounds=(max(0,int(x0-margin)),max(0,int(y0-margin)),
                            min(decoded.width,math.ceil(x1+margin)),
                            min(decoded.height,math.ceil(y1+margin)))
                    if bounds[0]>=bounds[2] or bounds[1]>=bounds[3]:
                        raise EncodedPixelQAError("Invalid decoded element bounds")
                    cropped=decoded.crop(bounds)
                    expected=active.crop(bounds)
                    baseline=base.crop(bounds)
                    try:
                        err_expected=_mae(cropped,expected)
                        err_base=_mae(cropped,baseline)
                    finally:
                        cropped.close();expected.close();baseline.close()
                    gain=err_base-err_expected
                    # A RELATIVE improvement alone admits catastrophic
                    # corruption: a blacked-out video may be marginally
                    # closer to the active reference than to the base (e.g.
                    # 219 vs 238 RGB MAE). Require both an absolute match
                    # and a substantial relative improvement in the actual
                    # encoded pixels. The 30-point MAE limit is deliberately
                    # conservative for H.264 re-encoding; quality below that
                    # level is not suitable for technical lecture release.
                    if (gain < 1.0 or err_expected > 30.0
                            or err_expected > 0.80 * err_base):
                        raise EncodedPixelQAError(
                            f"Encoded event {i} element {eid} has no verified "
                            "target highlight: insufficient absolute or "
                            "relative pixel agreement "
                            f"(active MAE {err_expected:.3f}, "
                            f"base MAE {err_base:.3f}, "
                            f"improvement {gain:.3f})"
                        )
                    element_checks.append({"element_id":eid,
                             "decoded_active_error":round(err_expected,3),
                             "decoded_base_error":round(err_base,3),
                             "highlight_evidence_gain":round(gain,3)})
                checks.append({"event":i,"slide_id":sid,"sample_time_s":round(timepoint,3),
                               "encoded_frame_index":frame_index,
                               "encoded_frame_pts_s":round(frame_time,4),
                               "target_checks":element_checks})
            finally:
                decoded.close()

        # Re-use the same ONE FFmpeg batch of extracted indexed frames for
        # independent 10%- and 90%-through-speech checks. Apply exactly the
        # same absolute/relative decoded-pixel criteria used at mid-utterance.
        for i,(event,samples) in enumerate(zip(events,window_samples),1):
            sid=event["slide_id"]
            ids=event["element_ids"]
            base_path=frames/f"base_{slide_lookup[sid]:04d}.png"
            high_path=frames/f"event_{i:04d}.png"
            for position,frame in zip(("start","end"),(samples[0],samples[2])):
                idx,pts_s=frame
                with Image.open(extracted[idx]) as raw, Image.open(base_path) as ref_base, Image.open(high_path) as ref_active:
                    decoded=raw.convert("RGB")
                    base=_fit(ref_base.convert("RGB"),*decoded.size)
                    active=_fit(ref_active.convert("RGB"),*decoded.size)
                    try:
                        for eid in ids:
                            region=lookup.get(eid)
                            if not isinstance(region,dict) or region.get("slide_id")!=sid:
                                raise EncodedPixelQAError("Window sample lost source-linked geometry")
                            coords=region["rect_pt"]
                            x0,y0,x1,y1=[float(x)*scale for x in coords]
                            margin=8*scale
                            bounds=(max(0,int(x0-margin)),max(0,int(y0-margin)),
                                    min(decoded.width,math.ceil(x1+margin)),
                                    min(decoded.height,math.ceil(y1+margin)))
                            if bounds[0]>=bounds[2] or bounds[1]>=bounds[3]:
                                raise EncodedPixelQAError("Window sample target outside the slide")
                            with decoded.crop(bounds) as candidate, active.crop(bounds) as expected, base.crop(bounds) as baseline:
                                err_active=_mae(candidate,expected)
                                err_base=_mae(candidate,baseline)
                            if (err_base-err_active<1.0 or err_active>30.0
                                    or err_active>0.80*err_base):
                                raise EncodedPixelQAError(
                                    f"Encoded event {i} {position}-window has no verified target "
                                    f"highlight for {eid} (active MAE={err_active:.3f}, "
                                    f"baseline MAE={err_base:.3f})")
                            time_window_checks.append({
                                "event":i,"position":position,
                                "element_id":eid,"encoded_frame_pts_s":round(pts_s,4),
                                "active_error":round(err_active,3),
                                "base_error":round(err_base,3)})
                    finally:
                        decoded.close();base.close();active.close()
        for i,(frame,sid,anchor,highlight_number) in enumerate(pauses,1):
            idx,pts_s=frame
            baseline=frames/f"base_{slide_lookup[sid]:04d}.png"
            highlighted=frames/f"event_{highlight_number:04d}.png"
            eid=anchor["element_ids"][0]
            target=lookup.get(eid)
            if not isinstance(target,dict) or target.get("slide_id")!=sid:
                raise EncodedPixelQAError("Pause has no source-linked slide element")
            with Image.open(extracted[idx]) as raw, Image.open(baseline) as reference, Image.open(highlighted) as high_reference:
                decoded=raw.convert("RGB")
                expected=_fit(reference.convert("RGB"),*decoded.size)
                active=_fit(high_reference.convert("RGB"),*decoded.size)
                try:
                    coords=target["rect_pt"]
                    x0,y0,x1,y1=[float(x)*scale for x in coords]
                    margin=8*scale
                    bounds=(max(0,int(x0-margin)),max(0,int(y0-margin)),
                            min(decoded.width,math.ceil(x1+margin)),
                            min(decoded.height,math.ceil(y1+margin)))
                    if bounds[0]>=bounds[2] or bounds[1]>=bounds[3]:
                        raise EncodedPixelQAError("Pause sample target outside the slide")
                    with decoded.crop(bounds) as candidate, expected.crop(bounds) as base, active.crop(bounds) as bad_highlight:
                        err=_mae(candidate,base)
                        err_active=_mae(candidate,bad_highlight)
                    # The idle frame must resemble the UNhighlighted image
                    # considerably more than the active image. An absolute
                    # threshold alone would admit a wrong small bright border.
                    if err>30.0 or err_active-err<1.0 or err>0.80*err_active:
                        raise EncodedPixelQAError(
                            f"Encoded pause {i} displays an unexpected active "
                            f"highlight (base MAE={err:.3f}, "
                            f"active MAE={err_active:.3f})")
                    pause_checks.append({
                        "pause":i,"slide_id":sid,"encoded_frame_pts_s":round(pts_s,4),
                        "unhighlighted_base_error":round(err,3),
                        "wrong_active_highlight_error":round(err_active,3)})
                finally:
                    decoded.close();expected.close();active.close()
    return {
        "status":"encoded_highlight_pixels_checked_semantics_unreviewed",
        "count_events":len(checks),
        "checks":checks,
        "time_window_samples_checked":len(time_window_checks),
        "time_window_checks":time_window_checks,
        "pause_samples_checked":len(pause_checks),
        "pause_checks":pause_checks,
        "scientific_approval":False,
        "spoken_word_fidelity_verified":False,
    }
