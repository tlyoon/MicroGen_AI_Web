"""Real PCM-frame-timed five-source-highlight video, always review-only.

Unlike the historical Slide-4 pilot, this compositor does NOT distribute one
WAV evenly across five visuals. It requires five DISTINCT external PCM WAV
chunks and obtains each element switch from the genuine WAV frame count.

PCM and filenames cannot prove provider identity, the voice Kore, or spoken
words. Even a pixel/time-perfect output is NEVER accepted for student release
until independent source mathematics, speech and voice QA are performed.
"""
from __future__ import annotations

from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat

from .offline_corrected_audio_intake import inspect_corrected_five_pcm
from .offline_corrected_bundle_verify import strict_json
from .original_replacement_video_handoff import _sha
from .offline_original_slide4_highlight_mp4 import (
    ffmpeg_run, video_only_duration,
)
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable


class VerifiedChunkVideoError(ValueError):
    """Audio/source/timing mismatch must not become a student video."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise VerifiedChunkVideoError(message)


def inspect_five_original_pcm_chunks(
    *, original: Path, bundle: Path, audio_dir: Path,
) -> dict:
    """Source-bound exact WAV-frame durations, no invented utterance clock."""
    root = Path(original).absolute()
    source_bundle = Path(bundle).absolute()
    pcm_dir = Path(audio_dir).absolute()
    status = inspect_corrected_five_pcm(
        original=root, bundle=source_bundle, audio_dir=pcm_dir,
    )
    require(status["candidate_audio_count"] == 5,
            "All five genuine new, nonhistorical PCM chunks must be present")
    require(not status["tts_replacement_eligible"]
            and not status["same_voice_approved"]
            and not status["spoken_content_approved"],
            "Candidate WAVs are unapproved; cannot import a claim of voice/content")
    # Do not accept an old WAV copied from another protected subchapter.
    # The baseline five-unit intake only covers historical WAVs in 8.4.
    require(not pcm_dir.is_relative_to(root.parent),
            "Corrected audio candidate cannot be inside protected Thomas chapter")
    historic_across_chapter = set()
    for section in ("8.4","8.5","8.6"):
        p=root.parent/section
        require(p.is_dir() and not p.is_symlink(),
                "Original three-subchapter media inventory is incomplete")
        wave_files=list(p.glob("slide*.wav"))
        require(1<=len(wave_files)<=200,
                "Incomplete or unbounded protected slide WAV inventory")
        for file in wave_files:
            require(file.is_file() and not file.is_symlink(),
                    "Protected sibling slide WAV unexpectedly linked")
            historic_across_chapter.add(_sha(file))
    expected = strict_json(source_bundle/"FIVE_CORRECTED_SEGMENTS_UNAPPROVED.json")
    units = expected["source_verified_tts_highlight_units"]
    require(len(units) == 5 and len(status["units"]) == 5,
            "Source-bound five-utterance manifest count changed")
    waveform_format = None
    seen = set()
    running_frames = 0
    timing = []
    for i, (source_unit, candidate) in enumerate(zip(units, status["units"]), 1):
        path = pcm_dir/source_unit["tts_audio_relative_path_expected"]
        sha = _sha(path)
        require(sha == candidate["wav_sha256"] and sha not in seen
                and sha not in historic_across_chapter,
                "Changed, duplicated or protected-historical audio is not a new utterance")
        seen.add(sha)
        with wave.open(str(path),"rb") as reader:
            fmt = (reader.getnchannels(), reader.getsampwidth(),
                   reader.getframerate(), reader.getcomptype())
            nframes = reader.getnframes()
        require(fmt[0:2] == (1,2) and fmt[3] == "NONE"
                and 16000 <= fmt[2] <= 48000 and nframes > fmt[2]//4,
                "Expected bounded mono PCM16 corrected audio candidate")
        if waveform_format is None:
            waveform_format = fmt
        require(fmt == waveform_format,
                "WAV candidates need identical sample rate / PCM format")
        require(nframes/fmt[2] < 150.0,
                "A single source narration element exceeds audio cap")
        require(candidate["utterance_id"] == source_unit["original_utterance_id"]
                and candidate["text_sha256"] == source_unit["corrected_tts_text_sha256"],
                "Text/audio candidate manifest identity changed")
        timing.append({
            "index":i,
            "utterance_id":source_unit["original_utterance_id"],
            "source_target_id":source_unit["source_verified_visual_target_id"],
            "corrected_text_sha256":source_unit["corrected_tts_text_sha256"],
            "source_highlight_png_sha256":source_unit["preview_png_sha256"],
            "wav_sha256":sha,
            "wav_name":path.name,
            "start_frame":running_frames,
            "end_frame":running_frames+nframes,
            "start_ms":round(running_frames*1000/fmt[2],3),
            "end_ms":round((running_frames+nframes)*1000/fmt[2],3),
            "duration_s":round(nframes/fmt[2],6),
            "spoken_words_verbatim_verified":False,
            "same_voice_Kore_verified":False,
        })
        running_frames += nframes
    require(0 < running_frames/waveform_format[2] <= 540.0,
            "Corrected WAV alone exceeds safe reserve under strict 600s cap")
    return {
        "status":"FIVE_SOURCE_BOUND_ACTUAL_PCM_FRAME_BOUNDARIES_UNAPPROVED",
        "source_sha256":status.get("source_sha256",expected["source_sha256"]),
        "source_pdf_sha256":expected["source_sha256"],
        "slides_pdf_sha256":expected["slides_sha256"],
        "historical_slide4_WAV_sha256":expected["historical_slide4_WAV_sha256"],
        "wav_format":waveform_format,
        "sample_rate":waveform_format[2],
        "total_frames":running_frames,
        "duration_s":round(running_frames/waveform_format[2],6),
        "units":timing,
        "voice_identity_verified":False,
        "speech_matches_corrected_text_verified":False,
        "source_academic_independently_approved":False,
        "student_publication_authorized":False,
    }


def _make_source_review_frames(bundle:Path,output_dir:Path, units:list[dict])->list[Path]:
    paths = []
    for i,unit in enumerate(units,1):
        original = bundle / ("source_visual_preview/"
                             f"UNAPPROVED_source_slide4_candidate_{i:03d}.png")
        require(_sha(original) == unit["source_highlight_png_sha256"],
                "Source image no longer matches preview receipt")
        with Image.open(original) as im:
            base=im.convert("RGB")
        if base.width%2 or base.height%2:
            base=ImageOps.expand(
                base,border=(0,0,base.width%2,base.height%2),
                fill=(255,255,255))
        drawing=ImageDraw.Draw(base)
        drawing.rectangle((0,0,min(base.width-1,600),25),fill=(126,0,0))
        drawing.text((4,6),"REVIEW ONLY - WAV WORDS AND KORE VOICE UNVERIFIED",
                     fill=(255,255,255))
        dest=output_dir/f"actual_chunk_source_{i:02d}.png"
        base.save(dest,format="PNG")
        paths.append(dest)
    require(len({_sha(x) for x in paths})==5,
            "The five source highlights were not visually distinct")
    return paths


def _assemble_pcm(*,audio_dir:Path, output:Path, evidence:dict)->None:
    with output.open("xb") as fh:
        with wave.open(fh,"wb") as merged:
            merged.setnchannels(1)
            merged.setsampwidth(2)
            merged.setframerate(evidence["sample_rate"])
            for row in evidence["units"]:
                file=audio_dir/row["wav_name"]
                require(_sha(file)==row["wav_sha256"],"PCM changed during compose")
                with wave.open(str(file),"rb") as reader:
                    require(reader.getnframes()==row["end_frame"]-row["start_frame"],
                            "PCM frame length drift")
                    merged.writeframesraw(reader.readframes(reader.getnframes()))
            merged.writeframes(b"")
    with wave.open(str(output),"rb") as reader:
        require(reader.getnframes()==evidence["total_frames"],
                "Combined PCM frames mismatch intended utterance timing")


def encode_actual_chunk_highlight_review(
    *, original:Path, bundle:Path, audio_dir:Path, output_dir:Path,
) -> dict:
    """Encode actual speech-*chunk* switch times; not accepted word-level sync."""
    root=Path(original).absolute()
    src_bundle=Path(bundle).absolute()
    wav_root=Path(audio_dir).absolute()
    out=Path(output_dir).absolute()
    require(out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(root)
            and not out.is_relative_to(src_bundle)
            and not out.is_relative_to(wav_root),
            "Exclusive external review-only output directory required")
    originals={name:_sha(root/name) for name in (
        "source.pdf","slides.pdf","script.txt","slide4.wav","slides.mp4")}
    evidence=inspect_five_original_pcm_chunks(
        original=root,bundle=src_bundle,audio_dir=wav_root)
    expected=strict_json(src_bundle/"FIVE_CORRECTED_SEGMENTS_UNAPPROVED.json")
    require(originals["source.pdf"]==expected["source_sha256"]
            and originals["slides.pdf"]==expected["slides_sha256"]
            and originals["script.txt"]==expected["script_sha256"]
            and originals["slide4.wav"]==expected["historical_slide4_WAV_sha256"],
            "Original mathematical source/slide/audio differs from staged proof")
    exe=ffmpeg_executable()
    out.mkdir()
    frame_dir=out/"frames";frame_dir.mkdir()
    segments=out/"video_segments";segments.mkdir()
    original_png=_make_source_review_frames(
        src_bundle,frame_dir,evidence["units"])
    combined=out/"REVIEW_ONLY_actual_candidate_chunks.wav"
    _assemble_pcm(audio_dir=wav_root,output=combined,evidence=evidence)
    segment_durations=[]
    for row,path in zip(evidence["units"],original_png):
        clip=segments/f"element_{row['index']:02d}.mp4"
        ffmpeg_run(exe,["-n","-loop","1","-framerate","60",
                       "-i",str(path),
                       "-t",f"{row['duration_s']:.6f}",
                       "-an","-c:v","libx264",
                       "-preset","ultrafast","-crf","20",
                       "-pix_fmt","yuv420p","-r","60",
                       str(clip)],timeout=120)
        duration=video_only_duration(clip,exe)
        require(abs(duration-row["duration_s"]) < 0.038,
                "Actual 60fps source highlight boundary timing too imprecise")
        segment_durations.append(duration)
    concat=out/"concat.txt"
    with concat.open("x",encoding="utf8") as f:
        for i in range(1,6):
            f.write("file '"+str((segments/f"element_{i:02d}.mp4").absolute()
                                  ).replace("\\","/")+"'\n")
    visual=out/"REVIEW_ONLY_video_only.mp4"
    ffmpeg_run(exe,["-n","-f","concat","-safe","0",
                    "-i",str(concat),"-c","copy",str(visual)],timeout=60)
    target=out/"REVIEW_ONLY_ACTUAL_PCM_CHUNK_TIMED_UNVERIFIED_VOICE.mp4"
    ffmpeg_run(exe,["-n","-i",str(visual),"-i",str(combined),
                    "-map","0:v:0","-map","1:a:0",
                    "-c:v","copy","-c:a","aac","-b:a","96k",
                    "-shortest","-movflags","+faststart",str(target)],timeout=90)
    actual=_mp4_duration(target,ffmpeg=exe)
    require(actual<600 and abs(actual-evidence["duration_s"])<.11,
            "Actual encoded output differs from measured original PCM duration")
    pixels=[]
    offset=0.0
    for i,(row,origin_frame,video_len) in enumerate(
            zip(evidence["units"],original_png,segment_durations),1):
        actual_start=row["start_frame"]/evidence["sample_rate"]
        require(abs(offset-actual_start) < .075,
                "Cumulative H264 frame boundaries drift >75ms from actual PCM")
        sample_t=offset+min(0.18,video_len/2)
        decoded=ffmpeg_run(exe,["-ss",f"{sample_t:.4f}",
                               "-i",str(target),"-frames:v","1",
                               "-f","image2pipe","-vcodec","png","pipe:1"],
                           timeout=35)
        with Image.open(BytesIO(decoded)) as stream:
            frame=stream.convert("RGB")
        with Image.open(origin_frame) as ref:
            expected_image=ref.convert("RGB")
        require(frame.size==expected_image.size,
                "Actual decoded video mismatches source dimensions")
        error=sum(ImageStat.Stat(ImageChops.difference(
            frame,expected_image)).mean)/3
        require(math.isfinite(error) and error<20,
                "Decoded MP4 at WAV-frame-derived boundary displays wrong element")
        pixels.append({"index":i,"encoded_sample_time_s":round(sample_t,4),
                       "decoded_pixel_error":round(error,4),
                       "source_highlight_verified":True})
        offset+=video_len
    require(all(_sha(root/name)==digest for name,digest in originals.items()),
            "Protected original changed during review encoding")
    return_record={
        **evidence,
        "status":"FIVE_TRUE_PCM_CHUNK_TIMED_SOURCE_HIGHLIGHT_MP4_REVIEW_UNAPPROVED",
        "actual_encoded_mp4_sha256":_sha(target),
        "actual_encoded_duration_s":actual,
        "actual_encoded_video_name":target.name,
        "decoded_element_frame_samples":pixels,
        "frame_rate":60,
        "timestamp_basis":"REAL_UNMODIFIED_CANDIDATE_WAV_FRAME_BOUNDARIES",
        "five_source_highlight_switches_tied_to_actual_WAV_chunks":True,
        "spoken_words_match_corrected_text_verified":False,
        "voice_Kore_or_provider_verified":False,
        "source_math_independently_two_pass_approved":False,
        "student_publication_authorized":False,
        "historical_source_files_modified":False,
    }
    with (out/"REVIEW_ONLY_EXACT_WAV_CHUNK_TIMING.json").open("x",encoding="utf8") as f:
        json.dump(return_record,f,indent=2,ensure_ascii=False)
    return return_record


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--audio-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    result=encode_actual_chunk_highlight_review(
        original=a.original,bundle=a.bundle,
        audio_dir=a.audio_dir,output_dir=a.out)
    print(json.dumps({"status":result["status"],
                      "chunk_count":len(result["units"]),
                      "measured_audio_s":result["duration_s"],
                      "encoded_video_s":result["actual_encoded_duration_s"],
                      "decoded_frames":len(result["decoded_element_frame_samples"]),
                      "spoken_words_verified":False,"student_release":False}))
if __name__=="__main__":
    main()
