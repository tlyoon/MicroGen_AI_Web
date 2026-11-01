"""Source-verified original prerequisites for partial fractions and table formulas.

Two separate original lecture clips:
 §8.5 slide4 proper fraction and irreducible factorization.
 §8.6 slide3 n≠−1, n≠−2, a≠0, b>0 table constraints.
Every spoken element must correspond to original publisher exact math wording,
original authored Beamer inequalities, actual physical slide PDF rectangles,
original WAV SHA and independently measured genuine Vosk acoustic sentence
timestamps. Real H264/AAC OFF/ON decoded frame QA, never student release.
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
from .original_thomas85_86_first_math_highlights import SOURCE

CASES={
 "8.5":{
  "slide":4,"publisher_page":2,
  "book_requirements":(
    "General Description of the Method",
    "The degree of ƒ(x) must be less than the degree of g(x).",
    "If it isn’t, divide ƒ(x) by g(x) and work with the remainder term.",
    "real linear factors and real quadratic factors",
    "A quadratic polynomial (or factor) is irreducible",
  ),
  "latex":(
    r"\textbf{Proper Fraction:} The degree of $f(x)$ must be less than the degree of $g(x)$. If not, use polynomial long division first.",
    r"\textbf{Factorization:} We must know the factors of $g(x)$ as products of real linear and irreducible quadratic factors.",
  ),
  "events":(
    ("proper_numerator_degree",2,[41.0,90.0,350.5,114.5],
     ("fraction must be proper","degree of the numerator",
      "strictly less than the degree of the denominator"),10.0),
    ("factor_real_linear_irreducible_quadratic",4,[41.0,114.5,350.5,143.0],
     ("factor the denominator","real linear factors",
      "irreducible quadratic factors"),23.0),
  ),
 },
 "8.6":{
  "slide":3,"publisher_page":1,
  "book_requirements":(
    "Formula 21 requires \nn ≠-1",
    "Formula 27 requires n ≠-2",
    "divid-\ning by zero or taking even roots of negative numbers",
    "Formula 24 assumes \nthat a ≠0",
    "29a and 29b cannot be used unless b is positive",
  ),
  "latex":(
    r"$n \neq -1$ or $n \neq -2$",
    r"$a \neq 0$, $b > 0$",
  ),
  "events":(
    ("formula21_27_exponent_restrictions",4,[52.0,149.5,350.,166.0],
     ("variable n is not equal to negative one or negative two",),29.0),
    ("nonzero_a_positive_b_domain_restrictions",5,[52.,165.0,351.,186.0],
     ("avoid division by zero","even roots of negative numbers",
      "variable a cannot be zero","b must be positive"),40.0),
  ),
 },
}
STATUS="ORIGINAL_PUBLISHER_CONSTRAINTS_REAL_SPOKEN_VIDEO_PIXEL_QA_PASS_NONPRODUCTION"

def _mp4_seconds(mp4:Path)->float:
    info=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(mp4)],
        capture_output=True,text=True,timeout=25).stderr
    match=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",info)
    require(match is not None and "Video: h264" in info and "Audio: aac" in info,
            "Real source-constrained media streams not H264/AAC")
    return int(match[1])*3600+int(match[2])*60+float(match[3])

def audit(*,root:Path,timings:Path,out:Path)->dict:
    root,out=Path(root).absolute(),Path(out).absolute()
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(root),
            "Separate clean output for immutable original corpus")
    section_timing={
        t["section"]:t for t in
        json.loads(Path(timings).read_text(encoding="utf8"))["sections"]}
    report={}
    for section,cfg in CASES.items():
        d=root/section
        slide=cfg["slide"]
        inputs=[d/"source.pdf",d/"slides.tex",d/"slides.pdf",
                d/"script.txt",d/f"slide{slide}.wav"]
        require(all(x.is_file() and not x.is_symlink() for x in inputs),
                "Missing authentic original source corpus")
        sha={str(f):_sha(f) for f in inputs}
        require(sha[str(inputs[0])]==SOURCE[section]["publisher_sha"]
                and sha[str(inputs[2])]==SOURCE[section]["slides_pdf_sha"],
                "Not publisher-original §8.5/8.6 or original author slide PDF")
        with pymupdf.open(inputs[0]) as publisher,pymupdf.open(inputs[2]) as pdf:
            source=publisher[cfg["publisher_page"]-1].get_text()
            require(all(term in source for term in cfg["book_requirements"]),
                    "Publisher mathematical/domain prerequisites are not supported")
            page=pdf[slide-1]
            for _,_,rect,_,_ in cfg["events"]:
                box=pymupdf.Rect(rect)
                require(box.is_valid and not box.is_infinite
                        and page.rect.contains(box)
                        and len(page.get_text(clip=box))>=6,
                        "Source mathematical/condition region not physically visible")
        original_frames=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",
                            inputs[1].read_text(encoding="utf8"),re.S)
        require(len(original_frames)==SOURCE[section]["slides"]
                and all(term in original_frames[slide-1]
                        for term in cfg["latex"]),
                "Original authored mathematical inequalities or factors changed")
        original_narration=dict(blocks(
            inputs[3].read_text(encoding="utf-8-sig")))[slide]
        sentences,_=tokenize_reference_sentences(original_narration)
        audio=section_timing[section]["slides"][slide-1]
        require(audio["wav_sha256"]==_sha(inputs[4])
                and audio["slide"]==slide
                and len(sentences)==len(audio["sentence_timing_candidates"]),
                "Original real spoken source timings do not match source WAV")
        with wave.open(str(inputs[4]),"rb") as wav:
            duration=wav.getnframes()/wav.getframerate()
            require(wav.getnchannels()==1 and wav.getsampwidth()==2
                    and wav.getcomptype()=="NONE" and 0<duration<600,
                    "Original speech is not authenticated 16-bit mono PCM")
        events={}
        previous=0.
        for name,sentence,rect,words,focus in cfg["events"]:
            utterance=sentences[sentence-1]
            candidate=audio["sentence_timing_candidates"][sentence-1]
            require(candidate["narration_fragment_sha256"]==
                        utterance["narration_fragment_sha256"]
                    and candidate["word_timing_hypothesis_available"] is True
                    and candidate["actual_ASR_word_anchor_fraction"]>=.90
                    and all(word in utterance["narration_fragment"].casefold()
                            for word in words),
                    "Real original narration did not speak identified source restriction")
            a,b=candidate["first_matched_real_audio_second"],candidate[
                "last_matched_real_audio_second"]
            require(all(type(t) in (int,float) and math.isfinite(t) for t in (a,b))
                    and previous<a<focus<b<duration,
                    "No distinct REAL Vosk source-audio math times")
            previous=b
            events[name]={"source_math_rect_pt":rect,
                "original_sentence_index":sentence,
                "real_original_audio_start_s":a,
                "real_original_audio_end_s":b,
                "ASR_fraction":candidate["actual_ASR_word_anchor_fraction"],
                "actual_sample_time_s":focus}
        stem=f"thomas_{section}_slide{slide}_source_conditions"
        base=out/(stem+".png")
        video=out/(stem+".mp4")
        require(not base.exists() and not video.exists(),
                "Never overwrite existing original scientific QA evidence")
        with pymupdf.open(inputs[2]) as slides:
            slides[slide-1].get_pixmap(matrix=pymupdf.Matrix(2,2),
                                      alpha=False).save(str(base))
        vf=[]
        for item in events.values():
            x0,y0,x1,y1=item["source_math_rect_pt"]
            a,b=item["real_original_audio_start_s"],item[
                "real_original_audio_end_s"]
            vf.append(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                      f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                      f"color=yellow@0.95:t=4:"
                      f"enable='between(t,{a:.4f},{b:.4f})'")
        encoded=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
            "error","-loop","1","-framerate","10","-i",str(base),
            "-i",str(inputs[4]),"-vf",
            ",".join(vf)+",scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v","libx264","-preset","veryfast","-crf","19",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-t",f"{duration:.6f}","-shortest","-movflags","+faststart",
            str(video)],capture_output=True,text=True,timeout=150)
        require(encoded.returncode==0 and video.is_file()
                and video.stat().st_size>9000,
                f"Original publisher conditions encode failed: "+encoded.stderr[-500:])
        length=_mp4_seconds(video)
        require(0<length<600 and abs(length-duration)<.15,
                "Original source PCM and H264 video time not aligned")
        decoded=[]
        for label,t,active in ([("preword",.05,None)]+[
            (key,entry["actual_sample_time_s"],key)
            for key,entry in events.items()]):
            png=out/f"{stem}_independent_{label}.png"
            require(not png.exists(),"Never replace scientific decoded pixels")
            q=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
                "error","-i",str(video),"-ss",f"{t:.4f}",
                "-frames:v","1",str(png)],
                capture_output=True,text=True,timeout=45)
            require(q.returncode==0 and png.is_file(),
                    "Actual encoded math conditions cannot independently decode")
            scores={k:count_source_equation_side_border(
                png,event["source_math_rect_pt"])
                for k,event in events.items()}
            require(all((score>=6)==(k==active) for k,score in scores.items()),
                    f"Wrong publisher constraint focus in encoded video: {scores}")
            decoded.append({"real_frame_time_s":t,
                "expected_source_element":active,
                "observed_border_probes":scores,
                "independent_encoded_frame_sha256":_sha(png)})
        require(sha=={str(p):_sha(p) for p in inputs},
                "Original textbook/slide/audio changed during proof")
        report[section]={"original_textbook_sha256":_sha(inputs[0]),
            "original_slides_pdf_sha256":_sha(inputs[2]),
            "original_wav_sha256":_sha(inputs[4]),
            "original_physical_wav_duration_s":duration,
            "actual_encoded_video_duration_s":length,
            "source_verified_math_condition_events":events,
            "encoded_h264_aac_mp4_sha256":_sha(video),
            "actual_encoded_independent_pixel_samples":decoded,
            "entire_slide_source_approved":False}
    final={"status":STATUS,"real_original_source_sections":list(report),
           "source_verified_clips":report,
           "full_corpus_academic_accepted":False,
           "student_publication_authorized":False}
    with (out/"THOMAS_85_86_ORIGINAL_SOURCE_CONDITIONS_PIXEL_QA.json").open(
           "x",encoding="utf8") as f:
        json.dump(final,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,
                      "sections":list(report),
                      "real_independent_frames":
                        sum(len(r["actual_encoded_independent_pixel_samples"])
                            for r in report.values())}))
    return final

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("root","timings","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args(argv)
    audit(root=a.root,timings=a.timings,out=a.out)
if __name__=="__main__":
    main()
