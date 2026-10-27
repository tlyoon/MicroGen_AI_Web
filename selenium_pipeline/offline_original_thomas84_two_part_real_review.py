"""Encode BOTH actual Thomas 8.4 video PARTS, with a corrected Slide4.

Read protected ORIGINAL slides.pdf and all 17 real slide*.wav without edits.
Replace only Slide4 historical narration with the five newly synthesized,
source-registered, exact-PCM chunk-timed Flash-Lite/Kore candidates.

The other sixteen historical slide WAVs are retained; they DO NOT have proven
element-level highlighting. The resulting two real MP4s are therefore
watermarked REVIEW ONLY / PARTIAL HIGHLIGHT, never student-ready.

Each encoded segment and both actual MP4s are independently duration-probed.
Every original slide image, and the five Slide4 source-pixel highlights, are
verified by decoding one MP4 frame each. This is genuine original multimedia
progress while failing closed on full academic/media acceptance.
"""
from __future__ import annotations
from io import BytesIO
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import wave

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat
import pymupdf

from .offline_corrected_bundle_verify import (
    strict_json,verify_original_five_bundle,
)
from .original_slide4_real_pcm_chunk_highlight import (
    inspect_five_original_pcm_chunks,
)
from .original_replacement_video_handoff import _sha
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable


PARTITION=((1,8),(9,17))
PART_IDS=("part_01","part_02")
WIDTH,HEIGHT=1280,960
FPS=30
MAX_SECONDS_EXCLUSIVE=600.0


def need(ok:bool,why:str):
    if not ok:raise ValueError(why)


def pcm_details(path:Path)->dict:
    need(path.is_file() and not path.is_symlink(),"Original/real source WAV unavailable")
    with wave.open(str(path),"rb") as reader:
        frames=reader.getnframes()
        rate=reader.getframerate()
        nch=reader.getnchannels()
        width=reader.getsampwidth()
        compression=reader.getcomptype()
    need(frames>0 and nch==1 and width==2 and compression=="NONE"
         and rate==24000,"Expected real mono PCM16 24kHz original WAV")
    return {"path":str(path),"sha256":_sha(path),
            "duration_seconds":frames/rate,"frame_count":frames,
            "sample_rate":rate}


def _parse_source_review_media(
        original:Path,source_bundle:Path,corrected_audio:Path)->tuple[dict,dict]:
    result=verify_original_five_bundle(original=original,bundle=source_bundle)
    need(result["verified_image_count"]==5,
         "Five authentic source-PDF highlighted targets not validated")
    manifest=strict_json(source_bundle/"FIVE_CORRECTED_SEGMENTS_UNAPPROVED.json")
    corrected=inspect_five_original_pcm_chunks(
        original=original,bundle=source_bundle,audio_dir=corrected_audio)
    need(len(corrected["units"])==5 and corrected["total_frames"]>0,
         "Five new source-bound actual PCM audio chunks absent")
    expected=manifest["source_verified_tts_highlight_units"]
    for i,unit in enumerate(corrected["units"]):
        want=expected[i]
        png=source_bundle/want["preview_png_relative_path"]
        need(_sha(png)==want["preview_png_sha256"]
             and unit["source_highlight_png_sha256"]==want["preview_png_sha256"]
             and unit["corrected_text_sha256"]==want["corrected_tts_text_sha256"],
             "Source highlight or real WAV text-identity integrity failed")
    return manifest,corrected


def plan_real_original_thomas84_two_parts(
        *, original:Path,bundle:Path,audio_dir:Path)->dict:
    root=Path(original).absolute()
    staged=Path(bundle).absolute()
    voices=Path(audio_dir).absolute()
    need(root.is_dir() and not root.is_symlink()
         and staged.is_dir() and not staged.is_symlink()
         and voices.is_dir() and not voices.is_symlink()
         and not voices.is_relative_to(root.parent),
         "Original protected G folder and independent candidate PCM directory needed")
    manifest,corrected=_parse_source_review_media(root,staged,voices)
    with pymupdf.open(root/"slides.pdf") as pdf:
        need(len(pdf)==17,"Actual original Thomas 8.4 presentation is not 17 slides")
        page_dimensions=[(float(p.rect.width),float(p.rect.height)) for p in pdf]
    source_hashes={x:_sha(root/x) for x in (
        "source.pdf","slides.pdf","script.txt","slide4.wav","slides.mp4")}
    need(source_hashes["source.pdf"]==
         "b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
         and manifest["source_sha256"]==source_hashes["source.pdf"]
         and manifest["slides_sha256"]==source_hashes["slides.pdf"],
         "Unrecognized genuine textbook source/slide PDFs")
    original_wavs={i:pcm_details(root/f"slide{i}.wav") for i in range(1,18)}
    utterance_units=manifest["source_verified_tts_highlight_units"]
    parts=[]
    all_units=[]
    for pnum,(first,last) in enumerate(PARTITION,1):
        timeline=[]
        elapsed=0.0
        for slide in range(first,last+1):
            if slide==4:
                for i,u in enumerate(corrected["units"],1):
                    expected=utterance_units[i-1]
                    wav=voices/expected["tts_audio_relative_path_expected"]
                    original_pcm=pcm_details(wav)
                    need(original_pcm["sha256"]==u["wav_sha256"],
                         "Corrected source-register WAV altered")
                    unit={
                        "slide":4,
                        "element_index":i,
                        "media_source":"NEW_REAL_SOURCE_REGISTERED_KORE_REQUESTED_PCM",
                        "visual_source":"CORRECTED_ORIGINAL_PDF_SOURCE_HIGHLIGHT",
                        "visual_path":str(staged/expected["preview_png_relative_path"]),
                        "source_target_id":expected["source_verified_visual_target_id"],
                        "spoken_text_sha256":expected["corrected_tts_text_sha256"],
                        "spoken_words_certified":False,
                        "source_mathematics_independent_two_pass_pass":False,
                        "audio":original_pcm,
                    }
                    timeline.append(unit)
                    elapsed+=original_pcm["duration_seconds"]
            else:
                source_audio=original_wavs[slide]
                unit={
                    "slide":slide,
                    "element_index":None,
                    "media_source":"ORIGINAL_HISTORICAL_SLIDE_PCM",
                    "visual_source":"ORIGINAL_STATIC_PDF_PAGE_NO_ELEMENT_HIGHLIGHT_SYNC",
                    "visual_path":None,
                    "source_target_id":None,
                    "spoken_text_sha256":None,
                    "spoken_words_certified":False,
                    "source_mathematics_independent_two_pass_pass":False,
                    "audio":source_audio,
                }
                timeline.append(unit)
                elapsed+=source_audio["duration_seconds"]
        need(len(timeline)>=8 and elapsed<540.0 and elapsed>10.0,
             "Each original-PDF part must fit a real safe <540s audio budget")
        parts.append({
            "part_id":PART_IDS[pnum-1],
            "first_slide":first,"last_slide":last,
            "whole_original_slide_media_count":
                sum(u["element_index"] is None for u in timeline),
            "source_highlighted_new_TTS_element_count":
                sum(u["element_index"] is not None for u in timeline),
            "estimated_real_PCM_s":round(elapsed,6),
            "timeline_units":timeline,
        })
        all_units.extend(timeline)
    need(len(parts)==2 and len(all_units)==21
         and sum(p["source_highlighted_new_TTS_element_count"]
                 for p in parts)==5,
         "Real corrected Slide4 five elements or the other sixteen slides missing")
    return {
        "status":"ORIGINAL_THOMAS84_TWO_COMPLETE_REAL_AUDIO_PARTS_READY_FOR_REVIEW_ENCODING",
        "source_hashes":source_hashes,
        "pdf_page_dimensions":page_dimensions,
        "parts":parts,
        "original_script_math_approved":False,
        "all_seventeen_slides_have_true_element_level_synchronization":False,
        "only_slide4_five_source_elements_PCM_chunk_timed":True,
        "two_new_student_lecture_MP4s_accepted":False,
        "student_publication_authorized":False,
    }


def ff(exe:str,argv:list[str],timeout:int=135)->bytes:
    try:
        p=subprocess.run([exe,"-hide_banner","-nostdin","-loglevel","error",*argv],
                         capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("FFmpeg encoding/verification timed out; no approval") from exc
    need(p.returncode==0,"Real Windows FFmpeg failure: "+
         p.stderr.decode("utf8","replace")[-500:])
    return p.stdout


def _visual_for_unit(
        *, original:Path,pdf,p:dict,dest:Path)->Path:
    slide=p["slide"]
    idx=p["element_index"]
    if idx is None:
        page=pdf[slide-1]
        scale_x=WIDTH/float(page.rect.width)
        scale_y=HEIGHT/float(page.rect.height)
        pix=page.get_pixmap(matrix=pymupdf.Matrix(scale_x,scale_y),alpha=False)
        image=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
    else:
        source=Path(p["visual_path"])
        need(source.is_file() and not source.is_symlink(),
             "Verified five-element PDF image not present")
        with Image.open(source) as picture:
            image=picture.convert("RGB")
    if image.size!=(WIDTH,HEIGHT):
        image=image.resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
    draw=ImageDraw.Draw(image)
    # This warning is BURNED INTO every single frame; cannot be published
    # accidentally as a corrected/fully synchronized academic course lecture.
    draw.rectangle((0,0,WIDTH-1,37),fill=(121,0,0))
    banner=("REVIEW ONLY | REAL CORRECTED KORE-REQUESTED AUDIO | "
            "CHUNK-TIMED SOURCE HIGHLIGHT" if idx else
            "REVIEW ONLY | HISTORICAL AUDIO | "
            "STATIC SLIDE - NO ELEMENT-LEVEL SYNC")
    draw.text((8,11),banner,fill=(255,255,255))
    draw.rectangle((0,HEIGHT-28,WIDTH-1,HEIGHT-1),fill=(30,30,30))
    draw.text((8,HEIGHT-19),
              f"THOMAS 8.4  |  SLIDE {slide:02d}/17"+
              (f"  |  ELEMENT {idx}/5" if idx else
               "  |  REQUIRES NEW ACADEMIC/HIGHLIGHT ACCEPTANCE"),
              fill=(255,255,255))
    output=dest/(f"slide{slide:02d}"+
                 (f"_element{idx:02d}" if idx else "_historical")+".png")
    with output.open("xb") as stream:
        image.save(stream,format="PNG")
    return output


def _video_sample_error(
        *,exe:str,movie:Path,at:float,reference_png:Path)->float:
    decoded=ff(exe,["-ss",f"{at:.4f}","-i",str(movie),
                    "-frames:v","1","-f","image2pipe",
                    "-vcodec","png","pipe:1"],timeout=35)
    with Image.open(BytesIO(decoded)) as got:
        actual=got.convert("RGB")
    with Image.open(reference_png) as png:
        ref=png.convert("RGB")
    need(actual.size==ref.size,
         "Actual decoded MP4 source-video image dimensions drift")
    mismatch=sum(ImageStat.Stat(ImageChops.difference(actual,ref)).mean)/3
    need(math.isfinite(mismatch) and mismatch<17,
         "Wrong real original textbook source image/element in decoded MP4")
    return round(mismatch,4)


def encode_both_real_original_thomas84_review_parts(
        *,original:Path,bundle:Path,audio_dir:Path,out:Path)->dict:
    root=Path(original).absolute()
    staged=Path(bundle).absolute()
    voices=Path(audio_dir).absolute()
    output=Path(out).absolute()
    need(output.parent.is_dir() and not output.parent.is_symlink()
         and not output.exists() and not output.is_relative_to(root.parent)
         and not output.is_relative_to(staged) and not output.is_relative_to(voices),
         "New exclusive external AppData output; never overwrite original textbook")
    plan=plan_real_original_thomas84_two_parts(
        original=root,bundle=staged,audio_dir=voices)
    exe=ffmpeg_executable()
    output.mkdir()
    art=output/"review_source_frames"
    art.mkdir()
    audit_parts=[]
    with pymupdf.open(root/"slides.pdf") as pdf:
        for part in plan["parts"]:
            partdir=output/part["part_id"]
            partdir.mkdir()
            clipdir=partdir/"intermediate_source_video_clips"
            clipdir.mkdir()
            records=[]
            for index,unit in enumerate(part["timeline_units"],1):
                target=_visual_for_unit(original=root,pdf=pdf,
                                        p=unit,dest=art)
                wavefile=Path(unit["audio"]["path"])
                need(_sha(wavefile)==unit["audio"]["sha256"],
                     "Original/new audio altered during bounded render")
                clip=clipdir/f"clip_{index:03d}.mp4"
                ff(exe,["-n","-loop","1","-framerate",str(FPS),
                        "-i",str(target),"-i",str(wavefile),
                        "-map","0:v:0","-map","1:a:0",
                        "-t",f"{unit['audio']['duration_seconds']:.7f}",
                        "-c:v","libx264","-preset","ultrafast","-crf","23",
                        "-pix_fmt","yuv420p","-r",str(FPS),
                        "-c:a","aac","-b:a","96k",
                        "-shortest","-movflags","+faststart",
                        str(clip)],timeout=180)
                actual=_mp4_duration(clip,ffmpeg=exe)
                need(0<actual<180 and
                     abs(actual-unit["audio"]["duration_seconds"])<.14,
                     "Actual original PCM clip duration inconsistent with MP4 container")
                records.append({
                    "slide":unit["slide"],
                    "element_index":unit["element_index"],
                    "source_element_target_id":unit["source_target_id"],
                    "media_source":unit["media_source"],
                    "visual_source":unit["visual_source"],
                    "wav_sha256":unit["audio"]["sha256"],
                    "source_image_sha256":_sha(target),
                    "source_image":str(target),
                    "audio_frame_duration_s":round(unit["audio"]["duration_seconds"],6),
                    "real_encoded_clip_s":actual,
                    "real_encoded_clip_sha256":_sha(clip),
                    "real_encoded_clip":str(clip),
                    "full_source_math_approved":False,
                    "true_element_level_highlights":
                        unit["element_index"] is not None,
                })
                print("ORIGINAL_THOMAS84_CLIP_ENCODED",
                      part["part_id"],len(records),
                      f"slide{unit['slide']}",
                      f"element{unit['element_index']}",
                      f"{actual:.2f}s",flush=True)
            need(len(records)==len(part["timeline_units"]),
                 "Expected every original slide/audio item")
            listfile=partdir/"concat_list.txt"
            with listfile.open("x",encoding="utf8") as listout:
                for row in records:
                    listout.write("file '"+Path(row["real_encoded_clip"]).as_posix()+"'\n")
            target=partdir/(f"Thomas_8_4_{part['part_id']}_"
                            "ORIGINAL_SOURCE_REVIEW_ONLY.mp4")
            ff(exe,["-n","-f","concat","-safe","0","-i",str(listfile),
                    "-c","copy","-movflags","+faststart",
                    str(target)],timeout=180)
            actual_final=_mp4_duration(target,ffmpeg=exe)
            combined_audio=sum(x["audio_frame_duration_s"] for x in records)
            need(0<actual_final<MAX_SECONDS_EXCLUSIVE
                 and abs(actual_final-combined_audio)<3.0,
                 "Two-part MP4 exceeds strict cap or encoded playback duration drifts")
            sampled=[]
            position=0.0
            for row in records:
                # Inspect one actual decoded MP4 frame from EACH source slide
                # and EACH corrected Slide4 element, not intermediate images.
                time=position+min(.9,row["real_encoded_clip_s"]/2)
                pixel_error=_video_sample_error(
                    exe=exe,movie=target,at=time,
                    reference_png=Path(row["source_image"]))
                sampled.append({
                    "slide":row["slide"],"element_index":row["element_index"],
                    "sample_at_actual_mp4_s":round(time,4),
                    "decoded_pdf_source_pixel_mean_error":pixel_error,
                })
                position+=row["real_encoded_clip_s"]
            need(len(sampled)==len(records),
                 "Missing decoded textbook page/Slide4 highlight evidence")
            # Verify actual full MP4 rather than a JSON duration declaration.
            audit_parts.append({
                "part_id":part["part_id"],
                "slides":[part["first_slide"],part["last_slide"]],
                "expected_items":len(records),
                "actual_real_MP4_duration_s":actual_final,
                "MP4_SHA256":_sha(target),
                "MP4_bytes":target.stat().st_size,
                "MP4":str(target),
                "decoded_original_PDF_or_highlight_frames":sampled,
                "historical_static_slide_items":
                    sum(x["element_index"] is None for x in records),
                "corrected_Kore_requested_source_highlights":
                    sum(x["element_index"] is not None for x in records),
                "strict_less_than_600_seconds":actual_final<600,
                "all_original_source_slides_element_highlight_synced":False,
                "academic_mathematics_two_pass_review_approved":False,
                "lecture_released":False,
            })
            print("ORIGINAL_THOMAS84_REVIEW_PART_COMPLETE",
                  part["part_id"],"actual_MP4_seconds",actual_final,
                  "decoded_frames",len(sampled),flush=True)
    need(sum(x["corrected_Kore_requested_source_highlights"]
             for x in audit_parts)==5
         and sum(x["historical_static_slide_items"] for x in audit_parts)==16,
         "Partial Slide4-only element sync must be explicit in completion audit")
    for name,digest in plan["source_hashes"].items():
        need(_sha(root/name)==digest,
             "Protected source PDF, script, original WAV or MP4 changed")
    for p in plan["parts"]:
        for row in p["timeline_units"]:
            need(_sha(Path(row["audio"]["path"]))==row["audio"]["sha256"],
                 "Protected historical or new corrected WAV altered during encoding")
    receipt={
        "schema_version":1,
        "status":"TWO_ACTUAL_ORIGINAL_THOMAS84_MP4_PARTS_ENCODED_FOR_REVIEW_NOT_LECTURES",
        "source_hashes":plan["source_hashes"],
        "completed_actual_review_part_count":len(audit_parts),
        "actual_verified_parts":audit_parts,
        "actual_corrected_Kore_requested_slide4_PCM_chunks":5,
        "actual_historical_unchanged_slide_PCM_files":16,
        "source_verified_slide4_element_pixels":5,
        "every_other_original_slide_elements_synchronized":False,
        "new_tts_words_and_Kore_voice_independently_certified":False,
        "independent_original_source_math_passes":0,
        "actual_professor_approved_lecture_MP4_count":0,
        "student_publication_authorized":False,
        "history_preserved":True,
        "prohibited_use":["Moodle","YouTube","student_distribution"],
    }
    with (output/"REAL_FULL_SECTION_REVIEW_ONLY_RECEIPT.json").open(
            "x",encoding="utf8") as f:
        json.dump(receipt,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({
        "status":receipt["status"],
        "real_part_durations_s":[x["actual_real_MP4_duration_s"] for x in audit_parts],
        "real_encoded_original_pdf_frames":sum(
            len(x["decoded_original_PDF_or_highlight_frames"]) for x in audit_parts),
        "full_element_sync_accepted":False,
        "student_publication":False,
    }))
    return receipt


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--bundle",required=True,type=Path)
    p.add_argument("--audio-dir",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args(argv)
    encode_both_real_original_thomas84_review_parts(
        original=args.original,bundle=args.bundle,
        audio_dir=args.audio_dir,out=args.out)


if __name__=="__main__":
    main()
