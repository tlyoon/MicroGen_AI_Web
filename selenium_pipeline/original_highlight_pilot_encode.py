"""Stage a REAL encoded MP4 for one original slide with provisional highlight cues.

This pilot proves that encoded visual changes and original audio can coexist.
Pause-derived element/word semantic synchronization remains UNVERIFIED.
"""
from __future__ import annotations
import argparse,hashlib,io,json,math,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
import pymupdf
from .original_wav_element_cues import propose_wav_pdf_element_highlights
from .highlight_video_preview import ffmpeg_path,probe_mp4
from .figure_source_identity import require,_sha

def _reference_frames(slides:Path,idx:int,events:list,out:Path,scale:float=2.0)->list[Path]:
    with pymupdf.open(slides) as deck:
        page=deck[idx-1]
        pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),
                            colorspace=pymupdf.csRGB,alpha=False)
        raw=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
        # Pad the existing rendered page by at most one white pixel on the
        # right/bottom for H.264 4:2:0, NEVER distort any original pixels.
        size=(pix.width+pix.width%2,pix.height+pix.height%2)
        base=Image.new("RGB",size,"white")
        base.paste(raw,(0,0))
    paths=[]
    for i,event in enumerate(events,1):
        canvas=base.copy()
        draw=ImageDraw.Draw(canvas)
        x0,y0,x1,y1=[round(n*scale) for n in event["original_pdf_rect_pt"]]
        gap=max(2,int(scale*2))
        area=(max(0,x0-gap),max(0,y0-gap),
              min(canvas.width-1,x1+gap),min(canvas.height-1,y1+gap))
        require(area[0]<area[2] and area[1]<area[3],
                "Invalid original slide element geometry")
        draw.rounded_rectangle(area,radius=5,width=4,outline=(255,110,0))
        target=out/f"highlight_{i:03d}.png"
        with target.open("xb") as fh:
            canvas.save(fh,format="PNG")
        paths.append(target)
    return paths

def _encoded_sample_pixels(exe:str,mp4:Path,ref:Path,sec:float)->float:
    import numpy as np
    ff=subprocess.run([exe,"-hide_banner","-loglevel","error","-ss",
                       f"{sec:.4f}","-i",str(mp4),"-frames:v","1",
                       "-f","image2pipe","-vcodec","png","-"],
                      capture_output=True,timeout=45)
    require(ff.returncode==0 and ff.stdout,"Encoded video could not be decoded at target time")
    with Image.open(io.BytesIO(ff.stdout)) as im:
        encoded=np.array(im.convert("RGB"),dtype=np.int16)
    with Image.open(ref) as im:
        expected=np.array(im.convert("RGB"),dtype=np.int16)
    require(encoded.shape==expected.shape,
            "Decoded encoded video dimensions differ from review reference")
    return float(np.abs(encoded-expected).mean())

def stage_original_slide_highlight_pilot(*,slides:Path,wav:Path,
                                        slide_index:int,output:Path)->dict:
    slides,wav,out=(Path(x).absolute() for x in (slides,wav,output))
    require(not out.exists() and out.parent.is_dir()
            and not out.is_relative_to(slides.parent)
            and not out.is_relative_to(wav.parent),
            "Pilot must have fresh isolated destination")
    for p in (slides,wav,out,out.parent):
        for ancestor in (p,*p.parents):
            require(not ancestor.is_symlink() and
                    not getattr(ancestor,"is_junction",lambda:False)(),
                    "Linked original or output path forbidden")
    before=(_sha(slides),_sha(wav))
    cues=propose_wav_pdf_element_highlights(
        slides=slides,wav=wav,slide_index=slide_index)
    require(cues["speech_alignment_verified"] is False
            and cues["student_publication_authorized"] is False,
            "Untrusted cue provenance")
    exe=ffmpeg_path()
    out.mkdir()
    try:
        reference=out/"reference_frames"
        reference.mkdir()
        images=_reference_frames(slides,slide_index,cues["events"],reference)
        timeline=out/"frames.ffconcat"
        with timeline.open("x",encoding="utf8") as fh:
            fh.write("ffconcat version 1.0\n")
            for row,image in zip(cues["events"],images):
                fh.write(f"file '{image.as_posix()}'\n")
                fh.write(f"duration {row['end_s']-row['start_s']:.7f}\n")
            fh.write(f"file '{images[-1].as_posix()}'\n")
        mp4=out/"slide_highlight_review.mp4"
        process=subprocess.run([
            exe,"-hide_banner","-loglevel","error","-y","-safe","0",
            "-f","concat","-i",str(timeline),
            "-i",str(wav),"-map","0:v:0","-map","1:a:0",
            "-vf","fps=5","-fps_mode","cfr","-c:v","libx264",
            "-crf","19","-preset","ultrafast",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-movflags","+faststart","-t",f"{cues['original_wav_duration_s']:.5f}",
            str(mp4)],capture_output=True,text=True,timeout=180)
        require(process.returncode==0 and mp4.is_file(),
                "Real encoded video pilot failed: "+process.stderr[-1000:])
        media=probe_mp4(mp4,exe=exe)
        require(abs(media["duration_s"]-cues["original_wav_duration_s"])<.5,
                "Recorded audio duration disagrees with actual encoded pilot")
        samples=[]
        for i in sorted(set((0,len(cues["events"])//2,len(cues["events"])-1))):
            e=cues["events"][i]
            sec=(e["start_s"]+e["end_s"])/2
            loss=_encoded_sample_pixels(exe,mp4,images[i],sec)
            require(loss<16,
                    "Decoded encoded frame does not resemble intended element highlight")
            samples.append({"element_id":e["element_id"],"time_s":round(sec,3),
                            "mean_rgb_encoding_difference":round(loss,4),
                            "encoded_pixels_present":True})
        require((_sha(slides),_sha(wav))==before,"Original teaching assets mutated")
        result={
            "schema_version":1,
            "status":"ACTUAL_ENCODED_PROVISIONAL_HIGHLIGHT_PILOT_REVIEW_ONLY",
            "slides_sha256":before[0],"original_wav_sha256":before[1],
            "encoded_mp4_sha256":_sha(mp4),
            "slide_index":slide_index,"original_wav_duration_s":cues["original_wav_duration_s"],
            "actual_encoded_mp4_duration_s":media["duration_s"],
            "decoded_frame_samples":samples,
            "candidate_element_count":len(cues["events"]),
            "all_sampled_encoded_highlight_pixels_plausible":True,
            "spoken_element_alignment_verified":False,
            "figure_mathematical_semantics_verified":False,
            "video_production_approved":False,
            "student_publication_authorized":False,
        }
        with (out/"review_receipt.json").open("x",encoding="utf8") as fh:
            json.dump(result,fh,indent=2,sort_keys=True)
        return result
    except Exception:
        shutil.rmtree(out)
        raise

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--wav",type=Path,required=True)
    p.add_argument("--slide-index",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    print(json.dumps(stage_original_slide_highlight_pilot(
        slides=a.slides,wav=a.wav,slide_index=a.slide_index,
        output=a.output),indent=2,sort_keys=True))
    return 2

if __name__=="__main__":
    raise SystemExit(main())
