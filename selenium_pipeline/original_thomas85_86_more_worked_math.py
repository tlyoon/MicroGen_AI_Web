"""Further authentic §8.5/§8.6 publisher worked-math focus clips.

Four complete original authored results, each independently differentiated
on its valid real domain, anchored to an identified original publisher example
page, a genuine original WAV's Vosk acoustic word interval, its original PDF
equation region, and actual decoded OFF/ON H264+AAC frames. This is partial
scientific acceptance only, not whole-slide or section approval.
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
from .runner import blocks
from .video_ffmpeg import ffmpeg_executable
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border
from .original_thomas85_86_first_math_highlights import SOURCE,symbolic_integrity

# Section, slide: publisher source page, original formula exact TeX, exact original
# narrated sentence (1 based), physical original PDF formula region, specific
# pronounced mathematical concept, independent ON and OFF sample real seconds.
WORKED={
 ("8.5",5): (2,
  r"\frac{3}{4}\ln|x-1| + \frac{1}{2}\ln|x+1| - \frac{1}{4}\ln|x+3| + K",
  5,[90.5,230.5,294.5,261.0],
  ("three quarters","natural logarithm","one half","minus one quarter"),45.0,20.0),
 ("8.5",6): (3,
  r"\int \left( \frac{6}{x+2} - \frac{5}{(x+2)^2} \right) dx = 6\ln|x+2| + \frac{5}{x+2} + C",
  4,[66.,223.0,318.,255.0],
  ("six times the natural logarithm","plus five divided by","constant of integration"),39.0,19.0),
 ("8.6",5): (1,
  r"\int \frac{dx}{x\sqrt{2x-4}} = \frac{2}{\sqrt{4}} \tan^{-1}\sqrt{\frac{2x-4}{4}} + C = \tan^{-1}\sqrt{\frac{x-2}{2}} + C",
  5,[46.,186.,337.5,219.0],
  ("simplifying this result","inverse tangent","square root","x minus two over two"),48.0,23.0),
 ("8.6",8): (2,
  r"\int \tan^5 x \, dx = \frac{1}{4} \tan^4 x - \frac{1}{2} \tan^2 x - \ln|\cos x| + C",
  5,[73.5,209.0,311.,240.0],
  ("combined final result","one quarter","minus one half","natural logarithm"),45.0,20.0),
}
STATUS="FOUR_ADDITIONAL_ORIGINAL_BOOK_FORMULA_REAL_WAV_ENCODED_PIXEL_QA_PASS"


def actual_mathematical_identities()->dict:
    try:
        import sympy as s
    except ImportError:
        require(False,"No independent SymPy, no academic math approval")
    symbolic_integrity()
    x=s.symbols("x",real=True)
    # Three physically separated poles for the original logarithmic example1.
    rational=(x*x+4*x+1)/((x-1)*(x+1)*(x+3))
    source=s.Rational(3,4)/(x-1)+s.Rational(1,2)/(x+1)-s.Rational(1,4)/(x+3)
    require(s.simplify(rational-source)==0,
            "Publisher §8.5 Example1 coefficient or denominator wrong")
    primitive=s.Rational(3,4)*s.log(abs(x-1))+s.Rational(1,2)*s.log(abs(x+1))-s.Rational(1,4)*s.log(abs(x+3))
    # symbolic abs derivative may form Piecewise; prove on each connected
    # real interval with explicit correct positive/negative argument.
    for probe in (-10,-2,0,2,10):
        derivative=s.diff(primitive,x).subs(x,s.Rational(probe))
        require(s.simplify(derivative-rational.subs(x,probe))==0,
                "Publisher Example1 logarithmic real-interval derivative wrong")
    linear=(6*x+7)/(x+2)**2
    require(s.simplify(6/(x+2)-5/(x+2)**2-linear)==0
            and s.simplify(s.diff(6*s.log(x+2)+5/(x+2),x)-linear)==0,
            "Repeated factor integral wrong in original §8.5")
    table=1/(x*s.sqrt(2*x-4))
    result=s.atan(s.sqrt((x-2)/2))
    require(s.simplify(s.diff(result,x)-table)==0,
            "Original §8.6 Formula29b inverse tangent derivative fails")
    for probe in (3,4,9):
        require(abs(float((s.diff(result,x)-table).subs(x,probe)))<1e-12,
                "Actual original square-root domain x>2 wrong")
    tan_integral=s.tan(x)**5
    result=s.tan(x)**4/4-s.tan(x)**2/2-s.log(s.cos(x))
    require(s.simplify(s.trigsimp(s.diff(result,x)-tan_integral))==0,
            "Original §8.6 tan^5 recurrence result wrong")
    return {"85_example1_exact_partial_fractions_and_four_log_intervals":True,
            "85_example2_repeated_linear_derivative":True,
            "86_example2_formula29b_positive_radicand":True,
            "86_example4_tan5_publisher_reduction":True,
            "all_unrelated_examples_source_approved":False}


def _encoded_time(p:Path)->float:
    result=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(p)],
                          capture_output=True,text=True,timeout=25).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",result)
    require(m and "Video: h264" in result and "Audio: aac" in result,
            "Original publisher math focus clip has missing media")
    return int(m[1])*3600+int(m[2])*60+float(m[3])


def produce(*,root:Path,timing_receipt:Path,out:Path)->dict:
    root,out=Path(root).absolute(),Path(out).absolute()
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(root),
            "Isolated unmodified publisher originals required")
    mathproof=actual_mathematical_identities()
    timing=json.loads(Path(timing_receipt).read_text(encoding="utf8"))
    sections={s["section"]:s for s in timing["sections"]}
    rows={}
    for (section,slide),(pubpage,exact_tex,sentence,rect,keywords,on,off) in WORKED.items():
        d=root/section
        source,tex,pdf,script,wav=(d/"source.pdf",d/"slides.tex",d/"slides.pdf",
                                    d/"script.txt",d/f"slide{slide}.wav")
        inputs=[source,tex,pdf,script,wav]
        require(all(p.is_file() and not p.is_symlink() for p in inputs),
                "Required original textbook, slide or voice unavailable")
        original={str(p):_sha(p) for p in inputs}
        require(original[str(source)]==SOURCE[section]["publisher_sha"]
                and original[str(pdf)]==SOURCE[section]["slides_pdf_sha"],
                f"Unexpected source §{section} version: no substitute textbook")
        with pymupdf.open(source) as publisher,pymupdf.open(pdf) as deck:
            require(len(deck)==SOURCE[section]["slides"]
                    and 1<=pubpage<=len(publisher)
                    and "EXAMPLE" in publisher[pubpage-1].get_text(),
                    "Original worked publisher page missing")
            physical=deck[slide-1]
            box=pymupdf.Rect(rect)
            require(box.is_valid and not box.is_infinite
                    and physical.rect.contains(box)
                    and len(physical.get_text(clip=box))>15,
                    f"Original mathematical formula region invalid {section}/{slide}")
        authored=tex.read_text(encoding="utf8")
        frames=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",authored,re.S)
        require(len(frames)==SOURCE[section]["slides"]
                and exact_tex in frames[slide-1],
                "Wrong mathematical operator, coefficient, source primitive or slide")
        narration=dict(blocks(script.read_text(encoding="utf-8-sig")))[slide]
        sentences,_=tokenize_reference_sentences(narration)
        source_times=sections[section]["slides"][slide-1]
        require(source_times["slide"]==slide
                and source_times["wav_sha256"]==_sha(wav)
                and len(sentences)==len(source_times["sentence_timing_candidates"]),
                "Original audio timing doesn't match source utterances")
        spoken=sentences[sentence-1]
        true=source_times["sentence_timing_candidates"][sentence-1]
        require(spoken["narration_fragment_sha256"]==true["narration_fragment_sha256"]
                and true["word_timing_hypothesis_available"] is True
                and true["actual_ASR_word_anchor_fraction"]>=.85
                and all(s in spoken["narration_fragment"].casefold() for s in keywords),
                "No genuine source text/acoustics binding to mathematical result")
        begin,end=true["first_matched_real_audio_second"],true[
            "last_matched_real_audio_second"]
        with wave.open(str(wav),"rb") as f:
            seconds=f.getnframes()/f.getframerate()
            require(f.getnchannels()==1 and f.getsampwidth()==2
                    and f.getcomptype()=="NONE" and
                    0<=begin<on<end<seconds<600 and
                    (off<begin or off>end),
                    "Original recorded PCM doesn't contain asserted word/visual timing")
        fname=f"Thomas_{section}_slide{slide}_additional_source_math"
        png=out/(fname+".png")
        mp4=out/(fname+".mp4")
        require(not png.exists() and not mp4.exists(),
                "Keep previously encoded source math evidence unchanged")
        with pymupdf.open(pdf) as deck:
            deck[slide-1].get_pixmap(matrix=pymupdf.Matrix(2,2),
                                    alpha=False).save(str(png))
        x0,y0,x1,y1=rect
        vf=(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
            f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
            f"color=yellow@0.95:t=4:enable='between(t,{begin:.4f},{end:.4f})',"
            "scale=trunc(iw/2)*2:trunc(ih/2)*2")
        q=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel","error",
            "-loop","1","-framerate","10","-i",str(png),"-i",str(wav),
            "-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","19",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-t",f"{seconds:.6f}","-shortest","-movflags","+faststart",
            str(mp4)],capture_output=True,text=True,timeout=150)
        require(q.returncode==0 and mp4.is_file() and mp4.stat().st_size>10000,
                f"Actual original §{section} slide{slide} H264 encode failed "+
                q.stderr[-550:])
        require(abs(_encoded_time(mp4)-seconds)<.15 and _encoded_time(mp4)<600,
                "Recorded source voice and encoded video duration mismatched")
        samples=[]
        for label,t,should_highlight in (("before",off,False),("spoken",on,True)):
            frame=out/(fname+f"_{label}.png")
            require(not frame.exists(),"Never replace previous decoded QA frames")
            dec=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
                    "error","-i",str(mp4),"-ss",str(t),"-frames:v","1",
                    str(frame)],capture_output=True,text=True,timeout=40)
            require(dec.returncode==0 and frame.is_file(),
                    "No independent encoded video mathematical pixel evidence")
            score=count_source_equation_side_border(frame,rect)
            require((score>=6)==should_highlight,
                    f"Original §{section} slide{slide} incorrect ON/OFF pixel {score}")
            samples.append({"time_s":t,"expected":should_highlight,
                            "actual_source_math_border_probes":score,
                            "decoded_frame_sha256":_sha(frame)})
        require(original=={str(p):_sha(p) for p in inputs},
                "An original publisher source/PCM/slide input was modified")
        rows[f"{section}_slide{slide}"]={
            "publisher_original_page":pubpage,
            "source_original_textbook_sha256":_sha(source),
            "original_source_latex_math_sha256":_sha(tex),
            "original_slides_pdf_sha256":_sha(pdf),
            "original_narration_wav_sha256":_sha(wav),
            "original_acoustic_real_sentence_index":sentence,
            "real_vosk_word_fraction":true["actual_ASR_word_anchor_fraction"],
            "genuine_spoken_start_s":begin,"genuine_spoken_end_s":end,
            "original_pdf_equation_rect_pt":rect,
            "encoded_mp4_sha256":_sha(mp4),
            "original_audio_duration_s":seconds,
            "actual_encoded_video_duration_s":_encoded_time(mp4),
            "independent_decoded_samples":samples,
            "other_mathematical_areas_approved":False,
            "student_publication_authorized":False}
    report={"status":STATUS,"independent_symbolic_math":mathproof,
            "publisher_approved_partial_equation_clip_keys":list(rows),
            "original_source_math_clips":rows,
            "entire_85_86_sections_production_approved":False}
    with (out/"FOUR_MORE_SOURCE_CALCULUS_REAL_VIDEOS_PIXEL_QA.json").open(
          "x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,"verified_original_clips":list(rows)}))
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("root","word-receipt","out"):
        parser.add_argument("--"+name,required=True,type=Path)
    a=parser.parse_args(argv)
    produce(root=a.root,timing_receipt=a.word_receipt,out=a.out)
if __name__=="__main__":
    main()
