"""Publisher-grounded four-step original Thomas §8.4 procedure synchronization.

The original textbook page 2 explicitly enumerates the 4-step procedure.
Every highlighted authored slide8 bullet must independently match the
publisher's numbered step's core mathematical/procedural terms AND its
real source-WAV spoken sentence/timing. Source files never modified.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import subprocess
import wave
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .video_ffmpeg import ffmpeg_executable
from .runner import blocks
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border
from .original_thomas84_multiline_math_witness import EXPECTED_SOURCE_SHA

KEYWORDS={
  1:("substitut","differential","selected","values"),
  2:("trigonom","differential","integrand","simplif"),
  3:("integrat","restrict","reversib"),
  4:("triangle","reverse","original","variable"),
}
SPOKEN_PREFIX={
  1:"first, write down the substitution",
  2:"second, substitute the trigonometric expression",
  3:"third, integrate the resulting",
  4:"fourth, draw an appropriate reference triangle",
}
STATUS="ORIGINAL_SLIDE8_FOUR_PROCEDURE_ELEMENTS_SOURCE_TIMED_PENDING_PIXELS"

def _source_procedure(publisher:Path,slide_pdf:Path)->dict:
    require(_sha(publisher)==EXPECTED_SOURCE_SHA,
            "Not independently identified publisher Thomas §8.4 source")
    with pymupdf.open(publisher) as book,pymupdf.open(slide_pdf) as deck:
        require(len(book)>=2 and len(deck)==17,"Wrong publisher or generated lecture")
        source=book[1].get_text()
        block=re.search(
            r"Procedure for a Trigonometric Substitution\s*\n(.*?)\nEXAMPLE 1",
            source,re.S)
        require(block is not None,"Original publisher numbered procedure not found")
        parts=re.split(r"(?m)^([1-4])\.\s",block[1])
        require(len(parts)==9 and parts[0].strip()=="",
                "Publisher textbook does not contain exactly four ordered steps")
        printed={i:parts[i*2] for i in range(1,5)}
        page=deck[7]
        lines=[]
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines",[]):
                text="".join(t["text"] for t in l["spans"])
                if text.strip():
                    lines.append((text,list(map(float,l["bbox"]))))
        locations={}
        for n,terms in KEYWORDS.items():
            indices=[i for i,(text,_) in enumerate(lines) if
                     re.match(rf"^{n}\s+\S",text)]
            require(len(indices)==1 and indices[0]+1<len(lines),
                    f"Original slide8 procedure step {n} missing/ambiguous")
            k=indices[0]
            raw=lines[k][0]+" "+lines[k+1][0]
            original=printed[n]
            require(all(term in raw.casefold() and term in original.casefold()
                        for term in terms),
                    f"Source textbook and slide step {n} differ in procedural mathematics")
            x0=min(lines[k][1][0],lines[k+1][1][0])
            y0=min(lines[k][1][1],lines[k+1][1][1])
            x1=max(lines[k][1][2],lines[k+1][1][2])
            y1=max(lines[k][1][3],lines[k+1][1][3])
            require(0<=x0<x1<=page.rect.width+1
                    and 0<=y0<y1<=page.rect.height+1,
                    "Original numbered procedural visual region outside slide")
            locations[n]={"original_publisher_step":original.strip(),
                          "actual_slide_bullet_text":raw,
                          "rect_pt":[x0,y0,x1,y1],
                          "publisher_page":2,
                          "same_order_source_mathematical_terms_verified":True}
    require(len(locations)==4,"Four numbered source steps required")
    return locations

def _duration(video:Path)->float:
    result=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(video)],
                          capture_output=True,text=True,timeout=25).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",result)
    require(m is not None and "Video: h264" in result and "Audio: aac" in result,
            "Encoded actual original slide clip has no video/audio streams")
    return int(m[1])*3600+int(m[2])*60+float(m[3])

def create(*,original:Path,corrected:Path,word_receipt:Path,out:Path)->dict:
    original,corrected,out=[Path(x).absolute() for x in
                            (original,corrected,out)]
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and not out.is_relative_to(corrected),
            "Isolated review-only output required")
    source=original/"source.pdf"
    slide=original/"slides.pdf"
    fixed=corrected/"slides.pdf"
    script=original/"script.txt"
    wav=original/"slide8.wav"
    inputs=[source,slide,fixed,script,wav]
    require(all(p.is_file() and not p.is_symlink() for p in inputs),
            "Missing original physical source or WAV")
    sha=[_sha(p) for p in inputs]
    evidence=_source_procedure(source,slide)
    with pymupdf.open(slide) as deck,pymupdf.open(fixed) as corrected_deck:
        require(deck[7].get_text()==corrected_deck[7].get_text()
                and deck[7].get_pixmap(alpha=False).samples==
                    corrected_deck[7].get_pixmap(alpha=False).samples,
                "Independent cumulative academic fix changed slide8 unexpectedly")
    timing=json.loads(Path(word_receipt).read_text(encoding="utf8"))
    observed=next(s for s in timing["sections"] if s["section"]=="8.4")[
        "slides"][7]
    require(observed["slide"]==8 and observed["wav_sha256"]==sha[-1],
            "Acoustic hypotheses are not bound to original recorded slide8 WAV")
    spoken,_=tokenize_reference_sentences(dict(blocks(
        script.read_text(encoding="utf-8-sig")))[8])
    timestamps=observed["sentence_timing_candidates"]
    require(len(spoken)==len(timestamps)==5,
            "Original procedure narration sentence order/count changed")
    intervals={}
    for n in range(1,5):
        sentence=spoken[n]
        anchor=timestamps[n]
        require(sentence["narration_fragment"].casefold().startswith(
                    SPOKEN_PREFIX[n])
                and sentence["narration_fragment_sha256"]==
                    anchor["narration_fragment_sha256"]
                and anchor["word_timing_hypothesis_available"] is True
                and anchor["actual_ASR_word_anchor_fraction"]>=.85,
                "Publisher-corresponding procedure speech not genuinely timed")
        a,b=anchor["first_matched_real_audio_second"],anchor[
            "last_matched_real_audio_second"]
        require(all(type(q) in (int,float) and math.isfinite(q)
                    for q in (a,b)) and 0<a<b,
                "No trustworthy real recorded speech interval")
        intervals[n]=(float(a),float(b))
    require(all(intervals[n][1]<intervals[n+1][0] for n in range(1,4)),
            "Real recorded step speech ordering inconsistent with publisher")
    with wave.open(str(wav),"rb") as pcm:
        duration=pcm.getnframes()/pcm.getframerate()
        require(pcm.getnchannels()==1 and pcm.getsampwidth()==2
                and pcm.getcomptype()=="NONE" and
                0<intervals[4][1]<duration<600,
                "Original step narration is not valid PCM audio")
    base=out/"thomas84_slide8_original_procedure.png"
    video=out/"thomas84_slide8_four_step_sync_qa.mp4"
    receipt=out/"thomas84_slide8_source_procedure_qa.json"
    require(all(not p.exists() for p in (base,video,receipt)),
            "Never replace an earlier generated QA video")
    with pymupdf.open(fixed) as deck:
        deck[7].get_pixmap(matrix=pymupdf.Matrix(2,2),
                          alpha=False).save(str(base))
    filters=[]
    for n,location in evidence.items():
        x0,y0,x1,y1=location["rect_pt"]
        start,end=intervals[n]
        filters.append(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                       f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                       f"color=yellow@0.95:t=4:"
                       f"enable='between(t,{start:.4f},{end:.4f})'")
    ffmpeg=ffmpeg_executable()
    proc=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error",
        "-loop","1","-framerate","10","-i",str(base),"-i",str(wav),
        "-vf",",".join(filters)+",scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","128k","-t",f"{duration:.6f}","-shortest",
        "-movflags","+faststart",str(video)],
        capture_output=True,text=True,timeout=150)
    require(proc.returncode==0 and video.is_file() and video.stat().st_size>10000,
            "Original source procedure timed rendering failed: "+proc.stderr[-850:])
    encoded=_duration(video)
    require(0<encoded<600 and abs(encoded-duration)<.15,
            "Original source narrated procedure lost AV duration sync")
    require([_sha(f) for f in inputs]==sha,
            "Original publisher PDF, slide/script or voice changed")
    report={
        "status":STATUS,
        "publisher_original_source_sha256":sha[0],
        "original_slides_pdf_sha256":sha[1],
        "academic_corrected_slides_sha256":sha[2],
        "original_script_sha256":sha[3],
        "original_slide8_wav_sha256":sha[4],
        "real_source_pcm_duration_s":round(duration,4),
        "real_encoded_mp4_duration_s":round(encoded,4),
        "original_publisher_corresponding_procedure_steps":evidence,
        "genuine_spoken_procedure_step_intervals_s":{
            str(n):list(v) for n,v in intervals.items()},
        "encoded_actual_mp4_sha256":_sha(video),
        "other_unmapped_lecture_elements_source_approved":False,
        "production_section_accepted":False,
        "student_publication_authorized":False,
    }
    with receipt.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    return report

def verify(*,original:Path,out:Path)->dict:
    original,out=Path(original).absolute(),Path(out).absolute()
    report=json.loads((out/"thomas84_slide8_source_procedure_qa.json").read_text(encoding="utf8"))
    clip=out/"thomas84_slide8_four_step_sync_qa.mp4"
    require(report["status"]==STATUS and
            _sha(clip)==report["encoded_actual_mp4_sha256"]
            and _sha(original/"slide8.wav")==report["original_slide8_wav_sha256"],
            "Original PCM/source proof or encoded slide8 clip changed")
    actual=_duration(clip)
    require(0<actual<600 and abs(actual-report["real_source_pcm_duration_s"])<.15,
            "Independent real media duration no longer matches original narration")
    samples=[]
    for label,time,expected in (
        ("intro",2.,None),("step1",10.,1),("step2",20.,2),
        ("step3",29.,3),("step4",39.,4)
    ):
        path=out/f"thomas84_slide8_independent_{label}.png"
        require(not path.exists(),"Never overwrite independent pixel samples")
        proc=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
            "error","-i",str(clip),"-ss",str(time),"-frames:v","1",str(path)],
            capture_output=True,text=True,timeout=45)
        require(proc.returncode==0 and path.is_file(),
                "Cannot independently decode original slide8 encoded video")
        scores={str(n):count_source_equation_side_border(path,item["rect_pt"])
                for n,item in report[
                    "original_publisher_corresponding_procedure_steps"].items()}
        require(all((num>=6)==(str(expected)==str(n) if expected is not None
                              else False)
                    for n,num in scores.items()),
                f"Source-grounded procedure target false highlight at {time}s: {scores}")
        samples.append({"time_s":time,"expect_step":expected,
                        "observed_border_probes":scores,
                        "actual_decoded_frame_sha256":_sha(path)})
    receipt={"status":"ORIGINAL_SLIDE8_FOUR_SOURCE_PROCEDURE_HIGHLIGHTS_PIXEL_QA_PASS",
             "actual_encoded_mp4_sha256":_sha(clip),
             "actual_independent_sample_count":len(samples),
             "real_source_wav_sha256":report["original_slide8_wav_sha256"],
             "full_lecture_accepted":False,
             "student_publication_authorized":False,
             "samples":samples}
    with (out/"thomas84_slide8_independent_pixel_qa.json").open(
            "x",encoding="utf8") as f:
        json.dump(receipt,f,indent=2);f.write("\n")
    return receipt

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("original","corrected","word-receipt","out"):
        p.add_argument("--"+field,type=Path,required=True)
    a=p.parse_args(argv)
    create(original=a.original,corrected=a.corrected,
           word_receipt=a.word_receipt,out=a.out)
    verified=verify(original=a.original,out=a.out)
    print(json.dumps({"status":verified["status"],
                      "actual_video_frame_samples":verified["actual_independent_sample_count"]}))
if __name__=="__main__":
    main()
