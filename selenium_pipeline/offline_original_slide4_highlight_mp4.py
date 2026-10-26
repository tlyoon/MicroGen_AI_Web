"""Actual original-PDF Slide4 highlighted MP4 technical pilot, NOT synchronized.

Uses FIVE genuine original-source highlighted visual targets and the old
untouched slide4.wav. Equal time bins are explicitly UNSYNCHRONIZED, solely
for real Windows encoder/pixel-transition QA before corrected TTS arrives.
The visible watermark and evidence prevent accidental learner release.
"""
from __future__ import annotations
from io import BytesIO
import hashlib,json,math,re,subprocess,wave
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw,ImageStat,ImageOps
from .offline_corrected_bundle_verify import verify_original_five_bundle,strict_json
from .original_replacement_video_handoff import _sha
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

class OriginalVideoPilotError(ValueError):pass
def need(value,reason):
    if not value:raise OriginalVideoPilotError(reason)
def ffmpeg_run(exe,args,*,timeout=90):
    cmd=[exe,"-hide_banner","-nostdin","-loglevel","error",*args]
    p=subprocess.run(cmd,capture_output=True,timeout=timeout)
    need(p.returncode==0,"FFmpeg pilot failed: "+
         p.stderr.decode("utf8","replace")[-280:])
    return p.stdout

def video_only_duration(path:Path,exe:str)->float:
    """Measure intermediate H.264-only clips without falsely requiring audio."""
    p=subprocess.run([exe,"-hide_banner","-i",str(path)],
                     capture_output=True,text=True,timeout=25)
    info=p.stderr+"\n"+p.stdout
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",info)
    need(m is not None and "Video:" in info,
         "Intermediate source highlight segment has no encoded video")
    duration=int(m[1])*3600+int(m[2])*60+float(m[3])
    need(math.isfinite(duration) and 0<duration<600,
         "Intermediate video-only segment invalid duration")
    return duration

def create_original_slide4_highlight_pilot(*,original:Path,bundle:Path,
                                            output_dir:Path)->dict:
    root=Path(original).absolute();staging=Path(bundle).absolute()
    out=Path(output_dir).absolute()
    need(root.is_dir() and not root.is_symlink()
         and not out.exists() and out.parent.is_dir()
         and not out.is_relative_to(root)
         and not out.is_relative_to(staging),
         "New exclusive review-only output must be outside original/staging")
    checked=verify_original_five_bundle(original=root,bundle=staging)
    need(checked["verified_image_count"]==5 and not checked["tts_audio_validated"],
         "Five actual original-highlight PNGs must pass source pixel replay")
    manifest=strict_json(staging/"FIVE_CORRECTED_SEGMENTS_UNAPPROVED.json")
    old=root/"slide4.wav";old_sha=_sha(old)
    need(old_sha==manifest["historical_slide4_WAV_sha256"],
         "Historical audio drift from verified source-visual packet")
    with wave.open(str(old),"rb") as sound:
        rate=sound.getframerate();frames=sound.getnframes()
        need(sound.getnchannels()==1 and sound.getsampwidth()==2
             and sound.getcomptype()=="NONE" and frames>0 and rate>=8000,
             "Original Slide4 must be actual unmodified PCM")
        duration=frames/rate
    need(5<duration<300,"Original slide narration duration implausible")
    expected=manifest["source_verified_tts_highlight_units"]
    original_sha={name:_sha(root/name)
                  for name in ("source.pdf","slides.pdf","script.txt","slide4.wav")}
    exe=ffmpeg_executable()
    out.mkdir()
    assets=out/"frames";assets.mkdir()
    segments=out/"temporary_encoded_segments";segments.mkdir()
    watermark="REVIEW ONLY - HISTORICAL AUDIO - NOT SPEECH SYNC"
    original_png=[]
    for i,u in enumerate(expected,1):
        input_png=staging/u["preview_png_relative_path"]
        need(_sha(input_png)==u["preview_png_sha256"],
             "Original source PNG changed after revalidation")
        with Image.open(input_png) as im:
            actual=im.convert("RGB")
            # Real original Slide4 source raster is 726x545; H.264 4:2:0
            # requires even dimensions. Pad ONLY this external review copy.
            if actual.width%2 or actual.height%2:
                actual=ImageOps.expand(
                    actual,border=(0,0,actual.width%2,actual.height%2),
                    fill=(255,255,255))
            drawing=ImageDraw.Draw(actual)
            drawing.rectangle((0,0,min(actual.width-1,480),24),
                              fill=(120,0,0))
            drawing.text((6,5),watermark,fill=(255,255,255))
            target=assets/f"review_watermarked_source_{i:02d}.png"
            actual.save(target,format="PNG")
        original_png.append(target)
    need(len({_sha(p) for p in original_png})==5,
         "Distinct source visual targets collapsed")
    block_time=duration/5
    segment_records=[]
    for i,preview in enumerate(original_png,1):
        output=segments/f"frame_{i:02d}.mp4"
        ffmpeg_run(exe,["-y","-loop","1","-framerate","2",
                       "-i",str(preview),"-t",f"{block_time:.7f}",
                       "-an","-c:v","libx264","-preset","ultrafast",
                       "-crf","19","-pix_fmt","yuv420p","-r","2",
                       str(output)],timeout=60)
        actual=video_only_duration(output,exe)
        need(actual>0 and abs(actual-block_time)<.65,
             "Actual frame segment duration mismatches the proposed time bin")
        segment_records.append({"segment_index":i,
                                "source_highlight_png_sha256":
                                    expected[i-1]["preview_png_sha256"],
                                "encoded_review_frame_sha256":_sha(output),
                                "actual_encoded_video_segment_duration_s":actual,
                                "source_element_id":
                                    expected[i-1]["source_verified_visual_target_id"],
                                "source_text_sha256":
                                    expected[i-1]["corrected_tts_text_sha256"],
                                "spoken_text_verified":False})
    concat=out/"concat.txt"
    with concat.open("x",encoding="utf8") as f:
        for i in range(1,6):
            f.write("file '"+str((segments/f"frame_{i:02d}.mp4").resolve()).replace("\\","/")+"'\n")
    mute_video=out/"UNAPPROVED_intermediate_video_only.mp4"
    ffmpeg_run(exe,["-y","-f","concat","-safe","0","-i",str(concat),
                   "-c","copy",str(mute_video)],timeout=60)
    final=out/"REVIEW_ONLY_ORIGINAL_SLIDE4_HIGHLIGHTED_UNSYNCED.mp4"
    ffmpeg_run(exe,["-y","-i",str(mute_video),"-i",str(old),
                   "-map","0:v:0","-map","1:a:0","-c:v","copy",
                   "-c:a","aac","-b:a","96k","-shortest",
                   "-movflags","+faststart",str(final)],timeout=60)
    final_duration=_mp4_duration(final,ffmpeg=exe)
    need(0<final_duration<600 and abs(final_duration-duration)<1.2,
         "Actual encoded review-only video duration mismatches source audio")
    # Decode 5 REAL frames from MP4 and compare pixels against FIVE distinct
    # original-PDF highlights after adding the visible review-only banner.
    checked_frames=[]
    elapsed=0.0
    for i,row in enumerate(segment_records):
        sample_t=min(final_duration-.3,
                     elapsed+row["actual_encoded_video_segment_duration_s"]/2)
        frame=ffmpeg_run(exe,["-ss",f"{sample_t:.4f}","-i",str(final),
                              "-frames:v","1","-f","image2pipe",
                              "-vcodec","png","pipe:1"],timeout=35)
        with Image.open(BytesIO(frame)) as sampled:
            actual=sampled.convert("RGB")
        with Image.open(original_png[i]) as target:
            image=target.convert("RGB")
        need(actual.size==image.size,"Decoded encoded frame dimensions drift")
        differences=ImageStat.Stat(ImageChops.difference(actual,image)).mean
        mismatch=sum(differences)/3
        need(math.isfinite(mismatch) and mismatch<20,
             "Real decoded MP4 frame does not match its source highlight")
        checked_frames.append({"slide4_utterance_visual_index":i+1,
                               "actual_encoded_sample_time_s":round(sample_t,3),
                               "decoded_frame_mean_channel_error":round(mismatch,4),
                               "original_pdf_highlight_pixels_recovered":True,
                               "narrated_words_in_this_time_bin_verified":False})
        elapsed+=row["actual_encoded_video_segment_duration_s"]
    need(all(_sha(root/name)==digest for name,digest in original_sha.items()),
         "Protected original changed while encoding actual highlighted pilot")
    record={
        "status":"REAL_ORIGINAL_SLIDE4_FIVE_HIGHLIGHT_MP4_REVIEW_UNSYNCED",
        "source_sha256":checked["source_sha256"],
        "source_slide_pdf_sha256":manifest["slides_sha256"],
        "historical_original_wav_sha256":old_sha,
        "historical_original_wav_duration_s":round(duration,4),
        "actual_encoded_review_mp4_duration_s":final_duration,
        "actual_review_mp4_sha256":_sha(final),
        "actual_review_mp4_file":final.name,
        "real_source_visual_elements_rendered":5,
        "actual_encoded_pixel_sample_count":len(checked_frames),
        "actual_encoded_pixel_samples":checked_frames,
        "intermediate_visual_segments":segment_records,
        "timeline_method":"UNVERIFIED_EVEN_TIME_BINS_OVER_HISTORICAL_AUDIO",
        "new_corrected_Kore_audio_received":False,
        "actual_utterance_to_spoken_audio_alignment_verified":False,
        "independent_two_pass_source_mathematics_approved":False,
        "corrected_student_lecture_completed":False,
        "source_media_modified":False,
        "student_publication_authorized":False,
    }
    with (out/"ACTUAL_HIGHLIGHT_PIXEL_REVIEW_UNAPPROVED.json").open("x",encoding="utf8") as f:
        json.dump(record,f,indent=2,ensure_ascii=False)
    return record

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--bundle",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args(argv)
    r=create_original_slide4_highlight_pilot(
        original=a.original,bundle=a.bundle,output_dir=a.out)
    print(json.dumps({"status":r["status"],
                      "encoded_duration_s":r["actual_encoded_review_mp4_duration_s"],
                      "decoded_source_highlights":r["actual_encoded_pixel_sample_count"],
                      "actual_speech_sync_verified":False,
                      "student_publish":False}))
if __name__=="__main__":main()
