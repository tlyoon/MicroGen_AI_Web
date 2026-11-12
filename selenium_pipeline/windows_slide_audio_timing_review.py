"""Original source slide-WAV timing review, not per-element production media.

Render actual slide images with genuine source-bound WAV audio; split by
measured PCM durations, every MP4 strictly under 600 seconds. A highlighted
slide index indicates only whole-slide timing. Never claim equation/panel
highlights, independent academic/audio semantics, or publication readiness.
No provider request, local-model/ASR dependency, TTS billing or source rewrite.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

from .evidence_reuse_contract import file_sha256
from .runner import blocks, check_valid
from .tts_effective_identity import verify_effective_identity
from .tts_pcm_contract import verify_pcm
from .highlight_video_preview import (
    ffmpeg_path, probe_mp4, H264_EVEN_DIMENSION_PAD_FILTER)
from .ffmpeg_fps_mode_compat import fps_mode_flags

class SlideTimingReviewBlocked(ValueError):
    pass

def need(ok, message):
    if not ok:
        raise SlideTimingReviewBlocked(message)

def groups_for_duration(seconds: list[float], *, max_part_seconds=570.0):
    need(type(seconds) is list and bool(seconds) and
         type(max_part_seconds) in (int,float) and
         1.0 < max_part_seconds < 600, "Invalid strict duration contract")
    result=[]
    current=[]
    total=0.0
    for idx, sec in enumerate(seconds,1):
        need(type(sec) in (float,int) and math.isfinite(sec)
             and 0.2 <= sec < max_part_seconds,
             "Individual WAV exceeds review duration limit")
        if current and total+sec >= max_part_seconds:
            result.append(current)
            current=[]
            total=0.0
        current.append(idx)
        total+=sec
    if current:
        result.append(current)
    need(all(sum(seconds[i-1] for i in part) < max_part_seconds
             for part in result), "Review grouping duration contract violated")
    return result

def inspect(*, audio_folder: Path, original_source: Path) -> dict:
    folder, original = Path(audio_folder).absolute(), Path(original_source).absolute()
    need(folder.is_dir() and not folder.is_symlink()
         and original.is_dir() and not original.is_symlink()
         and folder!=original and not folder.is_relative_to(original)
         and not original.is_relative_to(folder),
         "Require separate audio and SHA-locked original source folders")
    source_manifest=folder/"source_audio_stage_manifest.json"
    need(source_manifest.is_file() and not source_manifest.is_symlink(),
         "No source-locked initial audio staging manifest")
    record=json.loads(source_manifest.read_text(encoding="utf8"))
    need(record.get("status")=="SOURCE_SHA_BOUND_ROUTINE_GEMINI_TTS_CANDIDATE_STAGED"
         and record.get("student_publication_authorized") is False
         and record.get("element_highlight_semantics_verified") is False
         and record.get("model")=="gemini-3.8-flash-lite-tts"
         and record.get("voice")=="Kore"
         and record.get("source_trial")==str(original),
         "Audio staging provenance invalid")
    required=("source.pdf","slides.pdf","slides.tex","script.txt",
              "script_risk_report.json","script_risk_report.md",
              "math_semantic_report.json","math_semantic_repair_prompt.json")
    need(all((folder/n).is_file() and not (folder/n).is_symlink()
             and (original/n).is_file()
             and file_sha256(folder/n)==file_sha256(original/n)
             for n in required),"Original academic/text inputs changed")
    need(record.get("source_sha256")==file_sha256(folder/"source.pdf")
         and record.get("slides_sha256")==file_sha256(folder/"slides.pdf")
         and record.get("script_sha256")==file_sha256(folder/"script.txt")
         and check_valid("script_qa",folder)
         and check_valid("slides",folder)
         and check_valid("narration",folder), "Original source QA is not current")
    speech=blocks((folder/"script.txt").read_text(encoding="utf8"))
    count=len(speech)
    need(count==record.get("slide_count") and count>0,
         "Audio slide count differs from source stage")
    expected={f"slide{n}.wav" for n,_ in speech}
    observed={p.name for p in folder.glob("slide*.wav")}
    need(observed==expected, "Audio batch incomplete or contains extra WAV")
    tts=folder/"tts_input_manifest.json"
    need(tts.is_file() and not tts.is_symlink(),
         "No completed TTS producer manifest")
    tts_record=json.loads(tts.read_text(encoding="utf8"))
    effective=verify_effective_identity(tts_record, speech)
    if effective["fallback_used"]:
        # A homogeneous fallback is not enough: its original actual
        # provider timeout/retry journal must independently prove that
        # the primary models really exhausted their allowed attempts.
        from .tts_attempt_evidence import AttemptEvidence
        event_proof=tts_record.get("attempt_evidence")
        need(isinstance(event_proof,dict),
             "Effective fallback lacks observed provider attempt evidence")
        AttemptEvidence.verify_saved(folder,speech,event_proof)
    # The source review is diagnostic rather than released speech/video.
    # A complete same-engine fallback is allowed to be *measured*, but its
    # independent acoustic voice-equivalence gate is never promoted to PASS.
    # verify_effective_identity already rejects mixed-engine batches and
    # undocumented/misordered fallback chains.
    durations=[]
    evidence=[]
    for n,_ in speech:
        wav=folder/f"slide{n}.wav"
        proof=verify_pcm(wav.read_bytes(),label=wav.name)
        durations.append(proof["duration_seconds"])
        evidence.append({"slide":n,"name":wav.name,
                         "sha256":file_sha256(wav),**proof})
    chunks=groups_for_duration(durations)
    return {"source_sha256":record["source_sha256"],
            "slides_sha256":record["slides_sha256"],
            "script_sha256":record["script_sha256"],
            "tts_manifest_sha256":file_sha256(tts),
            "speaker":effective,
            "independent_voice_listening_verified":False,
            "fallback_voice_equivalence_not_asserted":bool(effective["fallback_used"]),
            "segments":evidence,
            "total_pcm_seconds":round(sum(durations),3),
            "parts":chunks,
            "per_element_sync_verified":False,
            "student_publication_authorized":False}

def _write_new(path:Path,data:bytes):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())

def _line(path:Path) -> str:
    # ffconcat paths can contain spaces; disallow quote/newline control chars.
    name=str(path).replace("\\","/")
    need("'" not in name and
         "\n" not in name and "\r" not in name,
         "Unsafe FFmpeg playlist path")
    return "file '"+name+"'\n"

def _render_page(pdf, slide:int, dest:Path):
    import pymupdf
    from PIL import Image,ImageDraw,ImageFont
    pg=pdf[slide-1]
    img=pg.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
    image=Image.frombytes("RGB",(img.width,img.height),img.samples)
    draw=ImageDraw.Draw(image)
    # Mark this as a coarse slide-level review, not native element sync.
    bar_height=38
    draw.rectangle((0,0,img.width,bar_height),fill=(30,38,52))
    try:
        font=ImageFont.truetype("arial.ttf",20)
    except OSError:
        font=ImageFont.load_default()
    draw.text((13,8),
              f"Slide {slide} - source-bound AUDIO TIMING REVIEW (no element sync)",
              fill=(255,255,255),font=font)
    image.save(dest,format="PNG")

def render(*, audio_folder:Path, original_source:Path,
           output_dir:Path) -> dict:
    folder,output=Path(audio_folder).absolute(),Path(output_dir).absolute()
    need(output.parent.is_dir() and not output.exists()
         and not output.is_symlink() and
         not output.is_relative_to(folder) and
         not folder.is_relative_to(output),
         "Review output must be new, external, nonoverwriting")
    proof=inspect(audio_folder=folder,original_source=original_source)
    import pymupdf
    exe=ffmpeg_path()
    fps=fps_mode_flags(exe,"vfr")
    output.mkdir()
    image_dir=output/"slide_frames"
    image_dir.mkdir()
    with pymupdf.open(folder/"slides.pdf") as pdf:
        need(len(pdf)==len(proof["segments"]),"Rendered PDF count changed")
        for item in proof["segments"]:
            _render_page(pdf,item["slide"],image_dir/f"slide{item['slide']}.png")
    reports=[]
    for part_i,numbers in enumerate(proof["parts"],1):
        playlist_images=output/f"part_{part_i:02d}_frames.ffconcat"
        playlist_audio=output/f"part_{part_i:02d}_audio.ffconcat"
        visual="ffconcat version 1.0\n"
        acoustic="ffconcat version 1.0\n"
        group_seconds=0.0
        for slide in numbers:
            item=proof["segments"][slide-1]
            group_seconds+=item["duration_seconds"]
            visual+=_line(image_dir/f"slide{slide}.png")
            visual+=f"duration {item['duration_seconds']:.6f}\n"
            acoustic+=_line(folder/f"slide{slide}.wav")
        visual+=_line(image_dir/f"slide{numbers[-1]}.png")
        _write_new(playlist_images,visual.encode("utf8"))
        _write_new(playlist_audio,acoustic.encode("utf8"))
        destination=output/f"Serway_6_4_audio_timing_review_part_{part_i:02d}.mp4"
        command=[
            exe,"-hide_banner","-nostdin","-loglevel","error",
            "-y","-f","concat","-safe","0","-i",str(playlist_images),
            "-f","concat","-safe","0","-i",str(playlist_audio),
            "-map","0:v:0","-map","1:a:0",
            "-c:v","libx264","-preset","veryfast","-tune","stillimage",
            "-crf","26","-vf",H264_EVEN_DIMENSION_PAD_FILTER,
            "-pix_fmt","yuv420p",
            *fps,"-c:a","aac","-b:a","96k",
            "-shortest",str(destination)
        ]
        completed=subprocess.run(command,capture_output=True,text=True,
                                 errors="replace",timeout=900)
        need(completed.returncode==0,
             "FFmpeg output refused: "+completed.stderr[-500:])
        decoded=probe_mp4(destination,exe=exe)
        need(decoded["duration_s"]>0
             and decoded["duration_s"]<600
             and abs(decoded["duration_s"]-group_seconds)<1.0,
             "Decoded MP4 duration/audio boundary differs from genuine WAVs")
        reports.append({"part":part_i,"slides":numbers,
                        "input_pcm_duration_s":round(group_seconds,3),
                        "actual_container_duration_s":decoded["duration_s"],
                        "mp4_file":destination.name,
                        "mp4_sha256":file_sha256(destination),
                        "decoded_audio_video_present":True,
                        "actual_element_highlighting_verified":False})
    need(all(file_sha256(folder/x)==proof[k]
             for x,k in (("source.pdf","source_sha256"),
                          ("slides.pdf","slides_sha256"),
                          ("script.txt","script_sha256"))),
         "Original source changed while encoding review")
    result={
        "schema_version":1,
        "status":"SOURCE_SHA_BOUND_SLIDE_LEVEL_AUDIO_TIMING_REVIEW_ONLY",
        "source_sha256":proof["source_sha256"],
        "slides_sha256":proof["slides_sha256"],
        "script_sha256":proof["script_sha256"],
        "tts_manifest_sha256":proof["tts_manifest_sha256"],
        "audio_wav_provenance":proof["segments"],
        "tts_voice":proof["speaker"],
        "independent_voice_listening_verified":False,
        "fallback_voice_equivalence_not_asserted":proof[
            "fallback_voice_equivalence_not_asserted"],
        "total_verified_input_audio_seconds":proof["total_pcm_seconds"],
        "part_count":len(reports),"parts":reports,
        "actual_per_element_highlight_sync_verified":False,
        "independent_audio_transcript_or_science_review_verified":False,
        "video_production_or_release_accepted":False,
        "student_publication_authorized":False,
        "model_or_tts_calls_during_review":0,
    }
    _write_new(output/"audio_timing_review_receipt.json",
               (json.dumps(result,indent=2,ensure_ascii=False)+"\n").encode("utf8"))
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audio-folder",type=Path,required=True)
    p.add_argument("--original-source",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--preflight-only",action="store_true")
    a=p.parse_args(argv)
    try:
        r=(inspect(audio_folder=a.audio_folder,original_source=a.original_source)
           if a.preflight_only else
           render(audio_folder=a.audio_folder,original_source=a.original_source,
                  output_dir=a.output_dir))
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
        r={"status":"SLIDE_AUDIO_TIMING_REVIEW_BLOCKED",
           "reason":str(exc),"student_publication_authorized":False}
    print(json.dumps(r,indent=2))
    return 0 if r.get("status")!="SLIDE_AUDIO_TIMING_REVIEW_BLOCKED" else 2

if __name__=="__main__":
    raise SystemExit(main())
