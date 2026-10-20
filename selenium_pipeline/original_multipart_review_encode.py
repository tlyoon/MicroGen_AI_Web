"""Render complete original-slide / original-WAV multipart REVIEW MP4s.

Preserves source, slides and all historical media; independently measures
encoded audio/video and decodes highlighted image samples. Pause-based timing
is not verified speech/element alignment, so NEVER marks production approval.
"""
from __future__ import annotations
import argparse,json,shutil,subprocess,wave
from pathlib import Path
import pymupdf

from .figure_source_identity import require,_sha,FigureIdentityReviewRequired
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .original_wav_element_cues import propose_wav_pdf_element_highlights
from .original_highlight_pilot_encode import _reference_frames,_encoded_sample_pixels
from .highlight_video_preview import ffmpeg_path,probe_mp4

def _original_element_fallback(slides:Path,wav:Path,idx:int,duration:float)->list[dict]:
    with pymupdf.open(slides) as deck:
        page=deck[idx-1]
        blocks=[b for b in page.get_text("blocks")
                if len(b)>=5 and str(b[4]).strip() and b[3]>8
                and b[2]>b[0] and b[3]>b[1]
                and b[0]<page.rect.width and b[1]<page.rect.height]
        if blocks:
            box=blocks[0][:4]
        else:
            # Original non-text figure image can be emphasized visually,
            # without claiming an independently spoken image caption.
            imgs=page.get_image_info(xrefs=True)
            if imgs:box=imgs[0]["bbox"]
            else:box=(page.rect.width*.2,page.rect.height*.2,
                      page.rect.width*.8,page.rect.height*.8)
        box=[round(float(v),3) for v in
             (max(0,box[0]),max(0,box[1]),
              min(page.rect.width,box[2]),min(page.rect.height,box[3]))]
        require(box[0]<box[2] and box[1]<box[3],
                "Fallback has no valid original slide graphic rectangle")
    return [{"element_id":f"slide_{idx:02d}_unverified_visual_01",
             "original_pdf_rect_pt":box,
             "start_s":0.0,"end_s":duration,
             "spoken_text_alignment_verified":False}]

def _slide_review_intervals(slides:Path,wav:Path,idx:int,duration:float)->tuple[list[dict],bool]:
    try:
        cues=propose_wav_pdf_element_highlights(
            slides=slides,wav=wav,slide_index=idx)
        require(cues["speech_alignment_verified"] is False,
                "Unverified original cues incorrectly marked aligned")
        return cues["events"],False
    except (FigureIdentityReviewRequired,wave.Error,EOFError,OSError):
        return _original_element_fallback(slides,wav,idx,duration),True

def stage_original_multipart_review(*,folder:Path,output:Path)->dict:
    src,out=Path(folder).absolute(),Path(output).absolute()
    require(src.is_dir() and not out.exists() and out.parent.is_dir()
            and not out.is_relative_to(src) and not src.is_relative_to(out),
            "Multipart candidate must be separate and new")
    for p in (src,out,out.parent):
        for ancestor in (p,*p.parents):
            require(not ancestor.is_symlink() and
                    not getattr(ancestor,"is_junction",lambda:False)(),
                    "Linked/overlapping source or output is forbidden")
    plan=inspect_original_slide_wav_plan(src)
    require(plan["status"]=="ORIGINAL_SLIDE_WAV_MULTIPART_CANDIDATE_NOT_RENDERED"
            and not plan["student_publication_authorized"],
            "Original immutable WAV inventory unavailable")
    sources=[src/"source.pdf",src/"slides.pdf"] + [
        src/f"slide{n}.wav" for n in range(1,plan["original_wav_count"]+1)]
    original_hash={str(p):_sha(p) for p in sources}
    slides=src/"slides.pdf"
    exe=ffmpeg_path()
    output_manifest=[]
    out.mkdir()
    try:
        for part in plan["proposed_parts"]:
            part_id=part["part_id"]
            dest=out/part_id
            dest.mkdir()
            frames_dir=dest/"reference_frames"
            frames_dir.mkdir()
            concat=dest/"frames.ffconcat"
            wav_dest=dest/"narration.wav"
            scenes=[]
            fallback=[]
            running=0.0
            with wave.open(str(wav_dest),"wb") as stream:
                stream.setnchannels(1);stream.setsampwidth(2)
                stream.setframerate(24000)
                for idx in range(part["slide_start"],part["slide_end"]+1):
                    origin=src/f"slide{idx}.wav"
                    with wave.open(str(origin),"rb") as read:
                        require(read.getnchannels()==1 and
                                read.getsampwidth()==2 and read.getframerate()==24000
                                and read.getcomptype()=="NONE",
                                "Original PCM16 mono voice format inconsistent")
                        samples=read.readframes(read.getnframes())
                        duration=read.getnframes()/read.getframerate()
                    stream.writeframes(samples)
                    events,used_fallback=_slide_review_intervals(
                        slides,origin,idx,duration)
                    if used_fallback:fallback.append(idx)
                    separate=frames_dir/f"slide_{idx:02d}"
                    separate.mkdir()
                    images=_reference_frames(slides,idx,events,separate)
                    for event,image in zip(events,images):
                        length=float(event["end_s"])-float(event["start_s"])
                        require(.001<length<550,
                                "Empty/oversized review frame interval")
                        scenes.append({"image":image,"duration_s":length,
                            "start_s":running,"end_s":running+length,
                            "element_id":event["element_id"],"slide_index":idx})
                        running+=length
            require(0<running<540.5 and
                    abs(running-part["original_wav_duration_sum_s"])<.15,
                    "Source narration coverage disagrees with original WAV plan")
            with concat.open("x",encoding="utf8") as fh:
                fh.write("ffconcat version 1.0\n")
                for event in scenes:
                    fh.write(f"file '{event['image'].as_posix()}'\n")
                    fh.write(f"duration {event['duration_s']:.8f}\n")
                fh.write(f"file '{scenes[-1]['image'].as_posix()}'\n")
            mp4=dest/f"{part_id}_review.mp4"
            run=subprocess.run([
                exe,"-hide_banner","-loglevel","error","-y",
                "-safe","0","-f","concat","-i",str(concat),
                "-i",str(wav_dest),"-map","0:v:0","-map","1:a:0",
                "-vf","fps=5","-fps_mode","cfr",
                "-c:v","libx264","-crf","22","-preset","ultrafast",
                "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
                "-movflags","+faststart","-t",f"{running:.5f}",str(mp4)],
                capture_output=True,text=True,timeout=300)
            require(run.returncode==0 and mp4.is_file(),
                    "Failed to encode real multipart review: "+run.stderr[-900:])
            media=probe_mp4(mp4,exe=exe)
            require(media["duration_s"]<600
                    and abs(media["duration_s"]-running)<.65,
                    "Actually encoded review MP4 duration violates contract")
            samples=[]
            for j in sorted(set((0,len(scenes)//2,len(scenes)-1))):
                e=scenes[j]
                at=(e["start_s"]+e["end_s"])/2
                pixel_loss=_encoded_sample_pixels(exe,mp4,e["image"],at)
                require(pixel_loss<16,
                        "Actual encoded highlight image frame wrong")
                samples.append({"element_id":e["element_id"],
                    "at_s":round(at,3),"decoded_mean_rgb_difference":round(pixel_loss,4)})
            receipt={
                "part_id":part_id,"slide_start":part["slide_start"],
                "slide_end":part["slide_end"],"slide_count":part["slide_count"],
                "original_audio_s":round(running,4),
                "encoded_mp4_duration_s":media["duration_s"],
                "encoded_mp4_sha256":_sha(mp4),
                "highlight_event_count":len(scenes),
                "fallback_to_unverified_single_element_slide_indices":fallback,
                "decoded_samples":samples,
                "all_parts_encoded_duration_strict_under_600":True,
                "spoken_element_alignment_verified":False,
                "student_publication_authorized":False,
            }
            with (dest/"review_receipt.json").open("x",encoding="utf8") as stream:
                json.dump(receipt,stream,indent=2,sort_keys=True)
            output_manifest.append(receipt)
        require(all(_sha(Path(p))==h for p,h in original_hash.items()),
                "Original content changed during multipart render")
        result={
            "schema_version":1,
            "status":"COMPLETE_REAL_ORIGINAL_WAV_MULTIPART_REVIEW_ONLY",
            "original_source_sha256":original_hash[str(src/"source.pdf")],
            "original_slides_sha256":original_hash[str(slides)],
            "part_count":len(output_manifest),
            "parts":output_manifest,
            "all_encoded_parts_strictly_shorter_than_600":True,
            "original_source_slide_wav_mutated":False,
            "spoken_element_highlight_semantics_verified":False,
            "scientific_figures_verified":False,
            "technical_production_approved":False,
            "student_publication_authorized":False,
        }
        with (out/"multipart_review_receipt.json").open("x",encoding="utf8") as stream:
            json.dump(result,stream,indent=2,sort_keys=True)
        return result
    except Exception:
        shutil.rmtree(out)
        raise

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    print(json.dumps(stage_original_multipart_review(
        folder=a.folder,output=a.output),indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
