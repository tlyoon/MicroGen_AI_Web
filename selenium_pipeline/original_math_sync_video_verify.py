"""Independent pixel and media audit of the actual source-math pilot MP4.

Do not trust the generator's success response: decode actual encoded frames.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import subprocess
from pathlib import Path
from PIL import Image
from .figure_source_identity import require, _sha
from .video_ffmpeg import ffmpeg_executable
from .original_source_math_sync_pilot import discover_chains

SAMPLES=(("intro",2.0,None),("tangent",10.0,"tangent"),
         ("sine",33.0,"sine"),("outro",51.0,None))


def count_yellow_border(path:Path,rect:list[float])->int:
    image=Image.open(path).convert("RGB")
    x0,y0,x1,y1=rect
    left,right=int(x0*2)+4,int(x1*2)-4
    top=int(y0*2)-4
    require(0<=left<right<image.width and 0<=top<image.height,
            "Original source PDF rectangle exceeds actual video size")
    # Eight widely separated top-border probes avoid relying on codec-exact RGB.
    points=[(left+(right-left)*i//9,top) for i in range(1,9)]
    return sum(1 for x,y in points
               if (lambda c:c[0]>155 and c[1]>120 and c[2]<135)(
                   image.getpixel((x,y))))


def verify(*,root:Path,qa_dir:Path)->dict:
    root,qa_dir=Path(root).absolute(),Path(qa_dir).absolute()
    source=root/"8.4"/"source.pdf"
    deck=root/"8.4"/"slides.pdf"
    script=root/"8.4"/"script.txt"
    wav=root/"8.4"/"slide5.wav"
    artifacts=[qa_dir/"thomas84_slide5_source_math_sync_qa.json",
               qa_dir/"thomas84_slide5_source_math_sync_qa.mp4"]
    require(all(p.is_file() and not p.is_symlink() for p in artifacts),
            "Original encoded MP4 or independent provenance receipt absent")
    receipt=json.loads(artifacts[0].read_text(encoding="utf8"))
    require(receipt["status"]=="ENCODED_ORIGINAL_MATH_SYNC_PILOT_PENDING_PIXEL_QA"
            and receipt["full_41_slide_production_accepted"] is False,
            "Cannot audit unknown or falsely published video receipt")
    require([_sha(p) for p in (source,deck,script,wav)]==[
        receipt["source_sha256"],receipt["slides_sha256"],
        receipt["narration_sha256"],receipt["original_wav_sha256"]],
        "Original source, audio, or narration changed since actual encoding")
    require(_sha(artifacts[1])==receipt["encoded_qa_mp4_sha256"],
            "Actual encoded original video hash does not match producer receipt")
    chains=discover_chains(source=source,slides=deck)
    require([x["slide_equation"] for x in chains]==[
        x["slide_equation"] for x in receipt["original_textbook_chains"]],
        "Original math text changed between encoding and independent QA")
    ffmpeg=ffmpeg_executable()
    info=subprocess.run([ffmpeg,"-hide_banner","-i",str(artifacts[1])],
                        capture_output=True,text=True,timeout=20)
    details=info.stderr
    match=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",details)
    require(match is not None and "Audio: aac" in details and
            "Video: h264" in details,
            "Actual encoded QA clip missing audiovisual streams")
    actual_duration=int(match[1])*3600+int(match[2])*60+float(match[3])
    require(math.isfinite(actual_duration) and 0<actual_duration<600
            and abs(actual_duration-receipt["original_pcm_duration_s"])<.3,
            "Encoded QA clip fails strictly sub-600s duration/audio sync")
    rows=[]
    for name,seconds,expected in SAMPLES:
        frame=qa_dir/f"thomas84_slide5_encoded_{name}_qa.png"
        require(not frame.exists(),"Do not overwrite prior independent frame QA")
        result=subprocess.run([
            ffmpeg,"-hide_banner","-loglevel","error",
            "-i",str(artifacts[1]),"-ss",str(seconds),
            "-frames:v","1",str(frame)
        ],capture_output=True,text=True,timeout=45)
        require(result.returncode==0 and frame.is_file(),
                "Could not decode independent sampled encoded video frame")
        counts={x["function"]:count_yellow_border(frame,x["slide_rect_pt"])
                for x in chains}
        require(all((counts[key]>=6) == (key==expected)
                    for key in ("tangent","sine")),
                f"Encoded focus not synchronized to original narration at {seconds}s: {counts}")
        rows.append({"sample":name,"encoded_second":seconds,
                     "expected_highlight":expected,"observed_yellow_border_probes":counts,
                     "decoded_frame_sha256":_sha(frame)})
    return {"schema_version":1,
            "status":"INDEPENDENT_REAL_ENCODED_PIXEL_SAMPLES_PASS",
            "original_clip_mp4_sha256":_sha(artifacts[1]),
            "encoded_video_duration_s":actual_duration,
            "original_wav_duration_s":receipt["original_pcm_duration_s"],
            "samples":rows,
            "full_41_slide_production_accepted":False,
            "student_publication_authorized":False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--qa-dir",type=Path,required=True)
    a=p.parse_args(argv)
    result=verify(root=a.root,qa_dir=a.qa_dir)
    out=a.qa_dir/"thomas84_slide5_independent_encoded_pixel_qa.json"
    require(not out.exists(),"Never replace prior independent QA receipt")
    with out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=True)
        f.write("\n")
    print(json.dumps({"status":result["status"],
                      "duration":result["encoded_video_duration_s"],
                      "independent_frames":len(result["samples"])}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
