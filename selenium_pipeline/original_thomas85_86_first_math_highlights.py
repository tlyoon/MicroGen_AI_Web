"""Start substantive original SOURCE-VERIFIED math/video work on §§8.5 and 8.6.

This is not an invented completion of these sections: exactly one physical
original slide per section, with independent textbook+authored LaTeX+SymPy
full-formula proof, true original narration WAV/SHA/Vosk sentence timings,
real FFmpeg H264/AAC and separately decoded ON/OFF pixels. All other section
slide math, figures and per-element media are unverified and fail closed.
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

SOURCE={
  "8.5":{
    "publisher_sha":"08f7b778ca0d6acd55870a45b236b7881cdc0d3d324e8cf69a7a4960c870c7de",
    "slides_pdf_sha":"36a43af33d8e7ddcc11bf283bee0e3d14809471a398a28fe57da1efd4e01aad8",
    "slides":11,"target":3,
    "source_words":(
        "8.5  Integration of Rational Functions by Partial Fractions",
        "5x - 3\nx2 - 2x - 3 =\n2\nx + 1 +\n3\nx - 3.",
        "2 ln0 x + 10 + 3 ln0 x - 30 + C.",
    ),
    "original_tex_required":(
        r"\frac{5x-3}{x^2-2x-3} = \frac{2}{x+1} + \frac{3}{x-3}",
        r"\int \frac{5x-3}{(x+1)(x-3)} dx = 2 \ln|x+1| + 3 \ln|x-3| + C",
    ),
    "events":(
        ("publisher_partial_fraction_identity",2,3,[32.7,108.0,263.8,152.0],
         ("rational function","five times x minus three","two simpler terms",
          "two divided by the sum of x and one","difference of x and three"),
         23.5),
        ("publisher_logarithmic_antiderivative",4,4,[71.0,159.5,313.0,189.5],
         ("integrate this expression term by term","natural logarithm",
          "x plus one","x minus three"),38.0),
    ),
  },
  "8.6":{
    "publisher_sha":"5c018ce8426dcf61eb3712fa1bf5dd707cf144c2a177bf83f3f736cebf7a5ab5",
    "slides_pdf_sha":"3e4c5abf0a9140c8f845439c076705b4b8677579bf7fe8cf806b1284c2ccdef1",
    "slides":13,"target":4,
    "source_words":(
        "8.6 Integral Tables and Computer Algebra Systems",
        "We use Formula 24 at the back of the book",
        "With a = 2 and b = 5, we have",
        "x\n2 - 5\n4 ln 0 2x + 50 + C.",
    ),
    "original_tex_required":(
        r"\int x(2x+5)^{-1} dx = \frac{x}{2} - \frac{5}{4} \ln|2x+5| + C",
    ),
    "events":(
        ("formula24_original_analytic_antiderivative",4,4,[105.0,190.0,293.0,225.5],
         ("resulting antiderivative","one half","five over four",
          "natural logarithm","two times the variable x plus five"),
         43.0),
    ),
  },
}
STATUS="TWO_NEW_SECTIONS_ORIGINAL_SOURCE_MATH_AV_PIXELS_PASS_REVIEW_ONLY"


def symbolic_integrity():
    try:
        import sympy as s
    except ImportError:
        require(False,"Independent offline SymPy required for exact source math")
    x=s.symbols("x",real=True)
    original=(5*x-3)/(x*x-2*x-3)
    proposed=2/(x+1)+3/(x-3)
    require(s.simplify(original-proposed)==0,
            "Publisher's rational function decomposition not algebraically valid")
    # Distinct connected domains handle the absolute values in the original
    # logarithmic answer correctly, without ignoring branch issues.
    branches=[
      2*s.log(x+1)+3*s.log(x-3),       # x>3
      2*s.log(x+1)+3*s.log(3-x),       # -1<x<3
      2*s.log(-x-1)+3*s.log(3-x),     # x<-1
    ]
    require(all(s.simplify(s.diff(a,x)-original)==0 for a in branches),
            "Original partial-fraction integrated logarithm derivative wrong")
    # §8.6 original table formula: exact symbolic antiderivative for
    # BOTH real connected domains x>-5/2 and x<-5/2.
    tab=x/(2*x+5)
    positive=x/2-s.Rational(5,4)*s.log(2*x+5)
    negative=x/2-s.Rational(5,4)*s.log(-2*x-5)
    require(s.simplify(s.diff(positive,x)-tab)==0
            and s.simplify(s.diff(negative,x)-tab)==0,
            "Publisher Formula24 source result does not differentiate correctly")
    return {"source_85_exact_decomposition_identity":True,
        "source_85_log_antiderivative_three_real_intervals":True,
        "source_86_formula24_two_real_intervals":True,
        "poles_and_logarithm_domain_ignored":False}


def _duration(mp4:Path)->float:
    info=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(mp4)],
                        capture_output=True,text=True,timeout=25).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",info)
    require(m is not None and "Video: h264" in info and "Audio: aac" in info,
            "Original textbook math video lacks real AV streams")
    return int(m[1])*3600+int(m[2])*60+float(m[3])


def build(*,root:Path,timing_receipt:Path,out:Path)->dict:
    root,out=Path(root).absolute(),Path(out).absolute()
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(root),
            "Separate scratch QA output, preserving original textbook source")
    genuine=json.loads(Path(timing_receipt).read_text(encoding="utf8"))
    section_audio={x["section"]:x for x in genuine["sections"]}
    require(set(SOURCE).issubset(section_audio),
            "Original Vosk receipt lacks section-specific real PCM")
    calculus=symbolic_integrity()
    receipts={}
    for name,config in SOURCE.items():
        d=root/name
        files=[d/"source.pdf",d/"slides.tex",d/"slides.pdf",
               d/"script.txt",d/f"slide{config['target']}.wav"]
        require(all(f.is_file() and not f.is_symlink() for f in files),
                f"Original publisher {name} files missing")
        before={str(p):_sha(p) for p in files}
        require(before[str(files[0])]==config["publisher_sha"]
                and before[str(files[2])]==config["slides_pdf_sha"],
                f"Not exact original Thomas source/slides for section {name}")
        authored=files[1].read_text(encoding="utf8")
        frames=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",authored,re.S)
        require(len(frames)==config["slides"],
                "Wrong original source author's lecture slide count")
        frame=frames[config["target"]-1]
        require(all(s in frame for s in config["original_tex_required"]),
                f"Publisher {name} full correct source mathematical operators changed")
        with pymupdf.open(files[0]) as textbook,pymupdf.open(files[2]) as deck:
            publisher="".join(p.get_text() for p in textbook)
            require(all(s in publisher for s in config["source_words"]),
                    f"Publisher {name} full formula not found in ORIGINAL book")
            original_page=deck[config["target"]-1]
            require(len(deck)==config["slides"]
                    and len(original_page.get_text())>100,
                    f"Original {name} mathematical slide is empty")
            for _,_,_,rect,*_ in config["events"]:
                box=pymupdf.Rect(rect)
                require(box.is_valid and not box.is_infinite
                        and original_page.rect.contains(box)
                        and len(original_page.get_text(clip=box))>=4,
                        f"Original {name} mathematical PDF target missing")
        narratives=dict(blocks(files[3].read_text(encoding="utf-8-sig")))
        refs,_=tokenize_reference_sentences(narratives[config["target"]])
        spoken=section_audio[name]["slides"][config["target"]-1]
        require(spoken["slide"]==config["target"]
                and spoken["wav_sha256"]==_sha(files[4])
                and len(refs)==len(spoken["sentence_timing_candidates"]),
                "Source-bound word timing from wrong original narrated WAV")
        with wave.open(str(files[4]),"rb") as audio:
            seconds=audio.getnframes()/audio.getframerate()
            require(audio.getnchannels()==1 and audio.getsampwidth()==2
                    and audio.getcomptype()=="NONE" and 0<seconds<600,
                    "Original recorded audio not PCM or over duration limit")
        targets=[]
        for label,first,last,rect,phrase,probe in config["events"]:
            assert first<=last
            fst=spoken["sentence_timing_candidates"][first-1]
            end=spoken["sentence_timing_candidates"][last-1]
            require(fst["narration_fragment_sha256"]==
                        refs[first-1]["narration_fragment_sha256"]
                    and end["narration_fragment_sha256"]==
                        refs[last-1]["narration_fragment_sha256"]
                    and all(x["word_timing_hypothesis_available"] is True
                            and x["actual_ASR_word_anchor_fraction"]>=.85
                            for x in spoken["sentence_timing_candidates"][first-1:last])
                    and all(p in " ".join(
                        r["narration_fragment"].casefold()
                        for r in refs[first-1:last]) for p in phrase),
                    f"Original {name} source formula not genuinely spoken")
            a,b=fst["first_matched_real_audio_second"],end[
                "last_matched_real_audio_second"]
            require(0<=a<probe<b<seconds,
                    "Original real spoken source math focus not within actual PCM")
            targets.append({"name":label,"physical_slide_rect_pt":rect,
                "source_sentence_first":first,"source_sentence_last":last,
                "genuine_acoustic_start_s":a,"genuine_acoustic_end_s":b,
                "original_pcm_sha256":_sha(files[4]),"real_probe_s":probe})
        require(all(t["genuine_acoustic_end_s"]<
                    u["genuine_acoustic_start_s"]
                    for t,u in zip(targets,targets[1:])),
                "Overlapping original textbook spoken math elements")
        base=out/f"Thomas_{name}_slide{config['target']}_source.png"
        mp4=out/f"Thomas_{name}_slide{config['target']}_math.mp4"
        require(not base.exists() and not mp4.exists(),
                "Do not overwrite original-source per-element audio/video QA")
        with pymupdf.open(files[2]) as pdf:
            pdf[config["target"]-1].get_pixmap(
                matrix=pymupdf.Matrix(2,2),alpha=False).save(str(base))
        vf=[]
        for event in targets:
            x0,y0,x1,y1=event["physical_slide_rect_pt"]
            a,b=event["genuine_acoustic_start_s"],event["genuine_acoustic_end_s"]
            vf.append(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                f"color=yellow@0.95:t=4:"
                f"enable='between(t,{a:.4f},{b:.4f})'")
        encoded=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
            "error","-loop","1","-framerate","10","-i",str(base),
            "-i",str(files[4]),"-vf",
            ",".join(vf)+",scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v","libx264","-preset","veryfast","-crf","19",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-t",f"{seconds:.6f}","-shortest","-movflags","+faststart",
            str(mp4)],capture_output=True,text=True,timeout=150)
        require(encoded.returncode==0 and mp4.is_file()
                and mp4.stat().st_size>10000,
                f"Original source {name} AVI encode failed: "+encoded.stderr[-500:])
        dsec=_duration(mp4)
        require(abs(dsec-seconds)<.15 and dsec<600,
                "Original source WAV and MP4 durations differ")
        pixel=[]
        cases=[("pre_math",.05,None)]+[
            (event["name"],event["real_probe_s"],event["name"])
            for event in targets]
        for label,at,focus in cases:
            image=out/f"Thomas_{name}_independent_{label}.png"
            require(not image.exists(),"No overwrites of genuine independent pixel QA")
            q=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
                "error","-i",str(mp4),"-ss",str(at),
                "-frames:v","1",str(image)],capture_output=True,text=True,timeout=40)
            require(q.returncode==0 and image.is_file(),
                    "Independent real recorded source video cannot decode")
            counts={e["name"]:count_source_equation_side_border(
                image,e["physical_slide_rect_pt"]) for e in targets}
            require(all((count>=6)==(n==focus)
                        for n,count in counts.items()),
                    f"Wrong actual original math highlighted {name} at {at}: {counts}")
            pixel.append({"second":at,"expected":focus,
                          "observed_yellow_probes":counts,
                          "encoded_pixel_sha256":_sha(image)})
        require(before=={str(p):_sha(p) for p in files},
                "Publisher textbook/slide/WAV modified by first source QA")
        receipts[name]={"book_sha256":_sha(files[0]),
            "original_slides_sha256":_sha(files[2]),
            "original_script_sha256":_sha(files[3]),
            "original_wav_sha256":_sha(files[4]),
            "encoded_h264_aac_mp4_sha256":_sha(mp4),
            "original_audio_seconds":seconds,
            "actual_encoded_seconds":dsec,
            "original_source_mathematical_event_targets":targets,
            "independently_decoded_original_frame_samples":pixel,
            "other_source_slide_elements_approved":False,
            "full_section_accepted":False}
    final={"status":STATUS,
           "original_sections":["8.5","8.6"],
           "original_book_sympy_proofs":calculus,
           "source_verified_real_media":receipts,
           "all_original_math_and_figures_verified":False,
           "both_sections_complete":False,
           "student_publication_authorized":False}
    with (out/"ORIGINAL_85_86_TWO_SOURCE_MATH_AV_PIXEL_RECEIPT.json").open(
            "x",encoding="utf8") as f:
        json.dump(final,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,
        "real_mp4_sections":list(receipts),
        "independent_pixel_samples":sum(len(r["independently_decoded_original_frame_samples"])
                                        for r in receipts.values())}))
    return final

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("root","timing-receipt","out"):
        p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args(argv)
    build(root=a.root,timing_receipt=a.timing_receipt,out=a.out)

if __name__=="__main__":
    main()
