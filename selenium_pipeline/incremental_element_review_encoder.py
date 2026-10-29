"""Encode a genuine *chunk-boundary synchronized* highlight REVIEW clip.

Every visual transition derives from exact independently measured element WAV
frame counts. No pause-based word guess, speech recognition, academic approval,
production replacement, billed TTS or publication is performed.
"""
from __future__ import annotations
import hashlib,io,json,math,subprocess,wave
from pathlib import Path
import pymupdf
from PIL import Image,ImageDraw
from .figure_source_identity import require,_sha
from .highlight_video_preview import ffmpeg_path,probe_mp4

def encode_segment_highlight_review(*,slides:Path,jobs:dict,
                                    clips:list[dict],destination:Path,
                                    exe:str|None=None)->dict:
    slides,destination=Path(slides).absolute(),Path(destination).absolute()
    require(slides.is_file() and not slides.is_symlink()
            and destination.parent.is_dir() and not destination.exists()
            and not destination.is_relative_to(slides.parent),
            "Require a NEW independent review directory, preserving original slide")
    before=_sha(slides)
    require(type(jobs) is dict
            and jobs.get("status")=="REVIEWED_ELEMENT_CHUNK_REQUESTS_NOT_YET_DISPATCHED"
            and jobs.get("slides_sha256")==before
            and jobs.get("paid_tts_execution_authorized") is False
            and jobs.get("student_publication_authorized") is False
            and jobs.get("voice")=="Kore"
            and type(jobs.get("chunk_jobs")) is list
            and 1<=len(jobs["chunk_jobs"])<=40
            and type(clips) is list and len(clips)==len(jobs["chunk_jobs"]),
            "Source-bound, already recorded element chunks required; not unbilled requests")
    spec=None
    segments=[];payloads=[]
    with pymupdf.open(slides) as deck:
        for job,clip in zip(jobs["chunk_jobs"],clips):
            require(type(job) is dict and type(clip) is dict
                    and clip.get("job_id")==job.get("job_id")
                    and clip.get("voice_id")=="Kore"
                    and type(clip.get("wav_sha256")) is str
                    and clip.get("wav_sha256")==_sha(Path(clip.get("wav_path","")))
                    and type(job.get("target_slide_index")) is int
                    and 1<=job["target_slide_index"]<=len(deck),
                    "WAV source identity / order / voice not verified")
            path=Path(clip["wav_path"]).absolute()
            require(path.is_file() and not path.is_symlink()
                    and not path.is_relative_to(slides.parent)
                    and path.suffix.lower()==".wav",
                    "Element clip must be original-safe independently staged WAV")
            with wave.open(str(path),"rb") as w:
                this=(w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getcomptype())
                frames=w.getnframes()
                require(this[0]==1 and this[1]==2 and this[3]=="NONE"
                        and 8000<=this[2]<=96000
                        and (spec is None or this==spec),
                        "Require consistent bounded PCM 16-bit mono")
                spec=this
                require(.15<=frames/this[2]<120,"Element WAV duration invalid")
                pcm=w.readframes(frames)
            page=deck[job["target_slide_index"]-1]
            bbox=job.get("target_pdf_page_bbox_pt")
            require(type(bbox) is list and len(bbox)==4
                    and all(type(v) in (int,float) and math.isfinite(v)
                            for v in bbox)
                    and 0<=bbox[0]<bbox[2]<=page.rect.width
                    and 0<=bbox[1]<bbox[3]<=page.rect.height,
                    "Spoken element highlight escapes genuine PDF slide")
            pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),
                               colorspace=pymupdf.csRGB,alpha=False)
            image=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
            draw=ImageDraw.Draw(image)
            xy=[round(2*v) for v in bbox]
            draw.rectangle(xy,outline=(255,25,15),width=6)
            fragments=segments[-1]["end_frame"] if segments else 0
            segments.append({"job_id":job["job_id"],
                             "slide":job["target_slide_index"],
                             "start_frame":fragments,
                             "end_frame":fragments+frames,
                             "start_seconds":fragments/this[2],
                             "end_seconds":(fragments+frames)/this[2],
                             "element_bbox_pdf_pt":bbox,
                             "wav_sha256":clip["wav_sha256"],
                             "audio_text_fidelity_verified":False,
                             "highlight_semantics_academically_verified":False})
            payloads.append((image,pcm))
    require(spec is not None and segments[-1]["end_seconds"]<540
            and len(segments)==len(payloads),
            "Review exceeds strict safe audio window")
    require(_sha(slides)==before,"Original slide changed while making review")
    destination.mkdir()
    audio_path=destination/"narration.wav"
    with wave.open(str(audio_path),"wb") as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(spec[2])
        for _,audio in payloads:
            out.writeframesraw(audio)
        out.writeframes(b"")
    # Stream fixed-FPS RGB pixels into FFmpeg. The earlier VFR concat-image
    # method can silently shift/drop visual frames even while audio survives;
    # a measured PCM clock and explicit encoded-pixel recheck avoid that.
    target=destination/"element_highlight_review.mp4"
    runner=exe or ffmpeg_path()
    frame_rate=20
    sizes={(im.width,im.height) for im,_ in payloads}
    require(len(sizes)==1,"Different page sizes require a safe normalized canvas")
    width,height=next(iter(sizes))
    encoded_frame_counts=[]
    for event in segments:
        duration=event["end_seconds"]-event["start_seconds"]
        n=max(1,round(duration*frame_rate))
        encoded_frame_counts.append(n)
    require(abs(sum(encoded_frame_counts)/frame_rate -
                segments[-1]["end_seconds"])<=.05*len(segments),
            "Video frame quantization drifts from measured WAV sample clock")
    proc=subprocess.Popen(
        [runner,"-hide_banner","-loglevel","error","-nostdin",
         "-f","rawvideo","-pix_fmt","rgb24","-video_size",f"{width}x{height}",
         "-framerate",str(frame_rate),"-i","pipe:0","-i",str(audio_path),
         "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",
         "-vf","pad=ceil(iw/2)*2:ceil(ih/2)*2",
         "-c:a","aac","-shortest","-y",str(target)],
        cwd=str(destination),stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE)
    try:
        for (im,_),count in zip(payloads,encoded_frame_counts):
            data=im.tobytes()
            for _ in range(count):
                proc.stdin.write(data)
        proc.stdin.close()
        diagnostic=proc.stderr.read()
        proc.stderr.close()
        try:
            code=proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill();proc.wait()
            raise
    except BaseException:
        proc.kill();proc.wait()
        raise
    require(code==0 and target.is_file() and target.stat().st_size>1000,
            "Fixed-FPS encoded element highlight review video failed")
    encoded=probe_mp4(target,exe=runner)
    require(0<encoded["duration_s"]<600
            and abs(encoded["duration_s"]-segments[-1]["end_seconds"])<=.40,
            "Actual encoded MP4 exceeds ten-minute or segment-clock contract")
    # Independently decode the ENCODED video at the interior of each
    # source WAV interval. A mere PNG/timeline claim cannot certify that
    # the highlight was actually present on the video frames.
    decoded=[]
    for i,event in enumerate(segments):
        at=(event["start_seconds"]+event["end_seconds"])/2
        frame=subprocess.run(
            [runner,"-hide_banner","-loglevel","error","-nostdin",
             "-i",str(target),"-ss",f"{at:.6f}",
             "-frames:v","1","-f","image2pipe","-vcodec","png","-"],
            capture_output=True,timeout=45)
        require(frame.returncode==0 and len(frame.stdout)>1000,
                "Actual encoded MP4 video sample could not be decoded")
        with Image.open(io.BytesIO(frame.stdout)) as sample:
            rgb=sample.convert("RGB")
            red=[]
            for event_to_check in segments:
                x0,y0,x1,_=event_to_check["element_bbox_pdf_pt"]
                px=(round(x0+x1),round(2*y0+2))
                require(0<=px[0]<rgb.width and 0<=px[1]<rgb.height,
                        "Encoded target rectangle escaped actual video frame")
                r,g,b=rgb.getpixel(px)
                red.append(r>170 and r>g+65 and r>b+65)
        # Distinct narrated utterances may legitimately point to the same
        # original equation/figure. Deduplicate identical target geometry
        # when checking an encoded frame: a persistent highlight is correct,
        # not evidence of an incorrectly highlighted second element.
        wanted=tuple(event["element_bbox_pdf_pt"])
        require(red[i] and all(
                    not is_red or tuple(target_event["element_bbox_pdf_pt"])==wanted
                    for is_red,target_event in zip(red,segments)),
                "Encoded review frame highlights incorrect DISTINCT narrated element")
        decoded.append({"event_index":i+1,"frame_time_s":round(at,5),
                        "only_expected_encoded_target_red":True})
    require(_sha(slides)==before,"Original PDF modified during video rendering")
    report={"status":"REAL_PCM_BOUNDARY_HIGHLIGHT_VIDEO_REVIEW_ONLY",
            "original_slides_sha256":before,
            "source_audio_sha256":_sha(audio_path),
            "encoded_review_sha256":_sha(target),
            "element_timing_source":"EXACT_INDIVIDUAL_PCM_WAV_FRAME_BOUNDARIES",
            "events":segments,
            "actual_encoded_duration_s":encoded["duration_s"],
            "decoded_highlight_transition_samples":decoded,
            "original_source_words_aurally_verified":False,
            "decoded_highlight_midpoint_samples_verified":True,
            "all_encoded_element_transition_frames_verified":False,
            "human_academic_QA_verified":False,
            "production_video_accepted":False,
            "student_publication_authorized":False}
    with (destination/"review_receipt.json").open("x",encoding="utf8") as out:
        json.dump(report,out,indent=2)
        out.write("\n")
    return report
