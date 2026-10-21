"""Independent decoded MP4 verification AROUND element audio-clock transitions.

A midpoint-only inspection misses wrong transition times; inspect the encoded
clip immediately before/after every exact PCM segment boundary. Never infer
speech/text meaning, human academic QA or publication authorization.
"""
from __future__ import annotations
import io,json,math,subprocess
from pathlib import Path
from PIL import Image
from .figure_source_identity import require,_sha
from .highlight_video_preview import ffmpeg_path,probe_mp4

def _frame(mp4:Path,second:float,exe:str)->Image.Image:
    result=subprocess.run([exe,"-hide_banner","-loglevel","error","-nostdin",
        "-i",str(mp4),"-ss",f"{second:.6f}","-frames:v","1","-f",
        "image2pipe","-vcodec","png","-"],capture_output=True,timeout=40)
    require(result.returncode==0 and len(result.stdout)>1000,
            "Encoded frame at PCM timing boundary was not decoded")
    with Image.open(io.BytesIO(result.stdout)) as img:
        return img.convert("RGB").copy()

def _active(frame:Image.Image,events:list[dict])->list[bool]:
    out=[]
    for event in events:
        box=event.get("element_bbox_pdf_pt")
        require(type(box) is list and len(box)==4 and all(
            type(v) in (int,float) and math.isfinite(v) for v in box),
            "Unbounded encoded-highlight target")
        x0,y0,x1,y1=box
        require(0<=x0<x1 and 0<=y0<y1,
                "Invalid annotated PDF region")
        # PR214 renders at 2x original PDF-point resolution.
        x,y=round(x0+x1),round(2*y0+2)
        require(0<=x<frame.width and 0<=y<frame.height,
                "Target sample outside encoded frame")
        r,g,b=frame.getpixel((x,y))
        out.append(r>170 and r>g+65 and r>b+65)
    return out

def verify_encoded_boundaries(*,mp4:Path,receipt:dict,
                              slides:Path,sample_margin_s:float=.12,
                              exe:str|None=None)->dict:
    mp4,slides=Path(mp4).absolute(),Path(slides).absolute()
    require(mp4.is_file() and slides.is_file()
            and type(receipt) is dict
            and receipt.get("status")=="REAL_PCM_BOUNDARY_HIGHLIGHT_VIDEO_REVIEW_ONLY"
            and receipt.get("original_slides_sha256")==_sha(slides)
            and receipt.get("encoded_review_sha256")==_sha(mp4)
            and receipt.get("production_video_accepted") is False
            and receipt.get("student_publication_authorized") is False
            and type(sample_margin_s) in (int,float)
            and .06<=sample_margin_s<=.3,
            "Require unchanged review-only encoded video and original slide")
    events=receipt.get("events")
    require(type(events) is list and 2<=len(events)<=40,
            "At least two independently timed visual highlights required")
    require(all(type(e) is dict and
                type(e.get("start_seconds")) in (float,int)
                and type(e.get("end_seconds")) in (float,int)
                and 0<=e["start_seconds"]<e["end_seconds"]<540
                for e in events), "Unbounded original PCM timeline")
    exe=exe or ffmpeg_path()
    duration=probe_mp4(mp4,exe=exe)["duration_s"]
    require(0<duration<600
            and abs(duration-events[-1]["end_seconds"])<=.4,
            "Actual encoded MP4 runtime violates PCM duration")
    checks=[]
    for i in range(1,len(events)):
        prev,after=events[i-1],events[i]
        t=after["start_seconds"]
        require(abs(t-prev["end_seconds"])<=.003 and
                t-prev["start_seconds"]>=.25 and
                after["end_seconds"]-t>=.25,
                "Transition may not have sufficient sampled PCM interval")
        at0=t-sample_margin_s
        at1=t+sample_margin_s
        before=_active(_frame(mp4,at0,exe),events)
        next_=_active(_frame(mp4,at1,exe),events)
        require(before[i-1] and sum(before)==1
                and next_[i] and sum(next_)==1,
                "Decoded MP4 active element did not switch at PCM boundary")
        checks.append({"before_s":round(at0,4),
                       "after_s":round(at1,4),
                       "verified_prior_element":prev["job_id"],
                       "verified_next_element":after["job_id"]})
    require(_sha(slides)==receipt["original_slides_sha256"]
            and _sha(mp4)==receipt["encoded_review_sha256"],
            "Inputs changed during boundary verification")
    return {"status":"INDEPENDENT_ENCODED_PCM_TRANSITIONS_VERIFIED_REVIEW_ONLY",
            "encoded_mp4_sha256":receipt["encoded_review_sha256"],
            "transition_count":len(checks),
            "decoded_checks":checks,
            "source_words_acoustically_verified":False,
            "element_semantics_academically_verified":False,
            "student_publication_authorized":False}
