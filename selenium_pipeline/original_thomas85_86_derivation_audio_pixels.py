"""Prove & encode three more ORIGINAL Thomas source mathematical scenes.

Checks publisher source, exact ORIGINAL authored Beamer, real PDF geometry,
independent SymPy algebra/calculus, unmodified original mono PCM WAV + Vosk
real acoustic sentence-time SHA, and independently decoded actual H264/AAC
OFF/ON element pixels. Does not approve other slide elements or courseware.
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
from .original_thomas85_86_first_math_highlights import SOURCE

CASES={
  ("8.5",7): {
    "source_pages":((3,("EXAMPLE 3","First we divide the denominator")),
                    (4,("x2 + 2 ln 0 x + 10 + 3 ln 0 x - 30 + C."))),
    "math_tex":(r"\frac{2x^3-4x^2-x-3}{x^2-2x-3} = 2x + \frac{5x-3}{x^2-2x-3}",
                r"\int \left( 2x + \frac{2}{x+1} + \frac{3}{x-3} \right) dx = x^2 + 2\ln|x+1| + 3\ln|x-3| + C"),
    "events":(
      ("publisher_exact_polynomial_division",4,[100.,132.,285.,168.],
       ("yields a polynomial term","two times x","proper fraction remainder"),27.),
      ("publisher_integrated_improper_fraction",5,[38.,193.,347.,226.],
       ("integrate the resulting polynomial","partial fraction expansion",
        "x squared","natural logarithm"),40.),
    ),
  },
  ("8.5",8): {
    "source_pages":((4,("EXAMPLE 4","The denominator has an irreducible quadratic factor",
                    "A = 2","C = -A = -2","D = 4 - B + C = 1",
                    "ln (x2 + 1) + tan-1 x")),),
    "math_tex":(r"\frac{-2x+4}{(x^2+1)(x-1)^2} = \frac{Ax+B}{x^2+1} + \frac{C}{x-1} + \frac{D}{(x-1)^2}",
                 r"\ln(x^2+1) + \tan^{-1}x - 2\ln|x-1| - \frac{1}{x-1} + C"),
    "events":(
      ("verified_partial_fraction_coefficients",3,[31.,192.,309.,208.],
       ("coefficients gives two","one for the second",
        "negative two for the third","one for the fourth"),28.),
      ("original_quadratic_antiderivative",4,[81.,230.,307.,262.],
       ("final integration","logarithmic terms","inverse tangent term",
        "natural logarithm of x squared plus one"),44.),
    ),
  },
  ("8.6",7): {
    "source_pages":((2,("Reduction Formulas","The time required for repeated integrations",
                    "tann x dx","sinn x cosm x dx","n ≠-m")),),
    "math_tex":(r"\int \tan^n x \, dx &= \frac{1}{n-1} \tan^{n-1} x - \int \tan^{n-2} x \, dx \quad (n \neq 1)",
                 r"\int (\ln x)^n dx &= x(\ln x)^n - n \int (\ln x)^{n-1} dx",
                 r"\int \sin^n x \cos^m x \, dx &= -\frac{\sin^{n-1} x \cos^{m+1} x}{m+n} + \frac{n-1}{m+n} \int \sin^{n-2} x \cos^m x \, dx \quad (n \neq -m)"),
    "events":(
      ("publisher_integration_by_parts_reduction_principle",1,
       [31.,62.,352.,91.],
       ("reduction formulas shorten","repeated integration by parts","lower powers"),5.),
      ("publisher_tangent_reduction_identity",3,
       [60.,113.,353.,143.],
       ("tangent reduction formula","raised to the power n",
        "power n minus two","not equal to one"),27.),
    ),
  },
}
STATUS="THREE_MORE_ORIGINAL_MATH_DERIVATION_SLIDES_SIX_SOURCE_WORD_PIXEL_EVENTS_PASS"

def sympy_source_math()->dict:
    try:
        import sympy as s
    except ImportError:
        require(False,"Independent SymPy missing - no mathematical promotion")
    x=s.symbols("x",real=True)
    frac=(2*x**3-4*x*x-x-3)/(x*x-2*x-3)
    divided=2*x+(5*x-3)/(x*x-2*x-3)
    require(s.cancel(frac-divided)==0,
            "Original improper rational function polynomial division wrong")
    primitive=x*x+2*s.log(abs(x+1))+3*s.log(abs(x-3))
    for point in (-5,0,6):
        require(s.simplify(s.diff(primitive,x).subs(x,point)-
                           frac.subs(x,point))==0,
                "Original improper result fails at a real pole-separated interval")
    exact=(-2*x+4)/((x*x+1)*(x-1)**2)
    decomposed=(2*x+1)/(x*x+1)-2/(x-1)+1/(x-1)**2
    require(s.cancel(exact-decomposed)==0,
            "Original irreducible quadratic coefficient values wrong")
    result=s.log(x*x+1)+s.atan(x)-2*s.log(abs(x-1))-1/(x-1)
    for point in (-4,0,3):
        require(s.simplify(s.diff(result,x).subs(x,point)-
                           exact.subs(x,point))==0,
                "Original quadratic/repeated-linear primitive wrong")
    # Verify source tangent reduction identity n=5 (pointwise derivative):
    tangent=s.tan(x)**5
    base=s.tan(x)**4/4
    require(s.trigsimp(s.diff(base,x)-s.tan(x)**3-tangent)==0,
            "Publisher tangent reduction formula n=5 invalid")
    # Verify the authored independent logarithmic and sin/cos reduction identities.
    logarithm=s.log(x)**3
    require(s.simplify(s.diff(x*logarithm,x)-3*s.log(x)**2-logarithm)==0,
            "Publisher log reduction n=3 false")
    n,m=3,1
    trig=-s.sin(x)**(n-1)*s.cos(x)**(m+1)/(n+m)
    derivative=s.diff(trig,x)+(n-1)*s.sin(x)**(n-2)*s.cos(x)**m/(n+m)
    require(s.trigsimp(derivative-s.sin(x)**n*s.cos(x)**m)==0,
            "Publisher sin/cos reduction identity false")
    return {
        "85_improper_rational_polynomial_division_exact":True,
        "85_improper_primitive_all_three_connected_domains":True,
        "85_quadratic_plus_repeated_linear_exact_decomposition":True,
        "85_quadratic_primitive_both_real_domains":True,
        "86_tangent_power5_reduction":True,
        "86_logarithmic_power3_reduction":True,
        "86_sin_cos_m1_n3_reduction":True,
        "all_remaining_slide_formulas_mathematically_approved":False,
    }

def duration(video:Path)->float:
    info=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(video)],
                        capture_output=True,text=True,timeout=25).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",info)
    require(m is not None and "Video: h264" in info and "Audio: aac" in info,
            "Actual real source video lacks approved H264/AAC streams")
    return int(m[1])*3600+int(m[2])*60+float(m[3])

def create(*,root:Path,timing_receipt:Path,out:Path,
           cases:dict|None=None, identities:dict|None=None,
           status:str=STATUS,
           receipt_name:str="ORIGINAL_THOMAS_85_86_THREE_MATH_SLIDES_SIX_TIMED_PIXEL_EVENTS.json")->dict:
    root,out=Path(root).absolute(),Path(out).absolute()
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(root),
            "Use immutable publisher corpus and clean separate original QA output")
    identities=sympy_source_math() if identities is None else identities
    cases=CASES if cases is None else cases
    require(isinstance(cases,dict) and len(cases)>0,
            "Empty source math scenes never warrant video/academic success")
    require(isinstance(identities,dict) and identities,
            "Independent external math identity result required")
    transcripts=json.loads(Path(timing_receipt).read_text(encoding="utf8"))
    recognized={item["section"]:item for item in transcripts["sections"]}
    rows={}
    for (section,slide),cfg in cases.items():
        folder=root/section
        book,tex,pdf,script,wav=(
            folder/"source.pdf",folder/"slides.tex",folder/"slides.pdf",
            folder/"script.txt",folder/f"slide{slide}.wav")
        inputs=(book,tex,pdf,script,wav)
        require(all(f.is_file() and not f.is_symlink() for f in inputs),
                "Original publisher original lecture missing")
        before={str(p):_sha(p) for p in inputs}
        require(_sha(book)==SOURCE[section]["publisher_sha"]
                and _sha(pdf)==SOURCE[section]["slides_pdf_sha"],
                f"Publisher book/source does not belong to exact §{section}")
        with pymupdf.open(book) as source,pymupdf.open(pdf) as deck:
            require(len(deck)==SOURCE[section]["slides"],
                    "Wrong physical original slide count")
            for page,words in cfg["source_pages"]:
                text=source[page-1].get_text()
                require(all(w in text for w in words),
                        f"Original publisher source page{page} math witness missing")
            slide_pdf=deck[slide-1]
            for name,index,rect,terms,probe in cfg["events"]:
                b=pymupdf.Rect(rect)
                require(b.is_valid and not b.is_infinite
                        and slide_pdf.rect.contains(b)
                        and len(slide_pdf.get_text(clip=b).strip())>=6,
                        f"Original source equation {section}/{slide}/{name} visually missing")
        frames=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",
                          tex.read_text(encoding="utf8"),re.S)
        require(len(frames)==SOURCE[section]["slides"]
                and all(e in frames[slide-1] for e in cfg["math_tex"]),
                f"Entire original source authored scientific equation operators changed {section}/{slide}")
        sentences,_=tokenize_reference_sentences(
            dict(blocks(script.read_text(encoding="utf-8-sig")))[slide])
        record=recognized[section]["slides"][slide-1]
        require(record["slide"]==slide and record["wav_sha256"]==_sha(wav)
                and len(record["sentence_timing_candidates"])==len(sentences),
                "Source-audio Vosk hypothesis does not match original real WAV")
        with wave.open(str(wav),"rb") as pcm:
            seconds=pcm.getnframes()/pcm.getframerate()
            require(pcm.getnchannels()==1 and pcm.getsampwidth()==2
                    and pcm.getcomptype()=="NONE" and 0<seconds<600,
                    "No genuine original 16-bit mono WAV")
        events={}
        previous_end=-1.
        for name,sentence_index,rect,terms,probe in cfg["events"]:
            spoken=sentences[sentence_index-1]
            evidence=record["sentence_timing_candidates"][sentence_index-1]
            require(spoken["narration_fragment_sha256"]==
                        evidence["narration_fragment_sha256"]
                    and evidence["word_timing_hypothesis_available"] is True
                    and evidence["actual_ASR_word_anchor_fraction"]>=.87
                    and all(term in spoken["narration_fragment"].casefold()
                            for term in terms),
                    f"Original authentic math not in real narration {section}/{slide}/{name}")
            a,b=evidence["first_matched_real_audio_second"],evidence[
                "last_matched_real_audio_second"]
            require(previous_end<a<probe<b<seconds,
                    f"Original true acoustic word times not valid {section}/{slide}/{name}")
            previous_end=b
            events[name]={"original_source_slide_rect_pt":rect,
                "original_sentence_index":sentence_index,
                "genuine_audio_start_s":a,"genuine_audio_end_s":b,
                "real_source_probed_second":probe,
                "actual_ASR_anchor_fraction":evidence["actual_ASR_word_anchor_fraction"]}
        stem=f"Thomas_{section}_slide{slide}_source_full_math"
        base=out/(stem+".png")
        mp4=out/(stem+".mp4")
        require(not base.exists() and not mp4.exists(),
                "Do not overwrite academic source-video receipts or clips")
        with pymupdf.open(pdf) as deck:
            deck[slide-1].get_pixmap(
                matrix=pymupdf.Matrix(2,2),alpha=False).save(str(base))
        vf=[]
        for item in events.values():
            x0,y0,x1,y1=item["original_source_slide_rect_pt"]
            a,b=item["genuine_audio_start_s"],item["genuine_audio_end_s"]
            vf.append(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                      f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                      f"color=yellow@0.95:t=4:"
                      f"enable='between(t,{a:.4f},{b:.4f})'")
        q=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
            "error","-loop","1","-framerate","10","-i",str(base),
            "-i",str(wav),"-vf",
            ",".join(vf)+",scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v","libx264","-preset","veryfast","-crf","19",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-t",f"{seconds:.6f}","-shortest","-movflags","+faststart",
            str(mp4)],capture_output=True,text=True,timeout=150)
        require(q.returncode==0 and mp4.is_file() and mp4.stat().st_size>9000,
                "Genuine source Wav/slide encoded math video failure: "+q.stderr[-600:])
        actual=duration(mp4)
        require(abs(actual-seconds)<.15 and actual<600,
                "Original PCM and mathematically grounded source video duration differ")
        frames=[]
        for name,at,focus in ([("preword",.05,None)]+[
                (n,v["real_source_probed_second"],n)
                for n,v in events.items()]):
            image=out/(stem+f"_{name}.png")
            require(not image.exists(),"No overwriting independent source proof frame")
            q=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
                "error","-i",str(mp4),"-ss",str(at),
                "-frames:v","1",str(image)],capture_output=True,text=True,timeout=45)
            require(q.returncode==0 and image.is_file(),
                    "Actual original mathematical MP4 frame cannot independently decode")
            pixel={n:count_source_equation_side_border(
                image,event["original_source_slide_rect_pt"])
                for n,event in events.items()}
            require(all((score>=6)==(n==focus) for n,score in pixel.items()),
                    f"Wrong actual source-spoken mathematical element: {pixel}")
            frames.append({"second":at,"expected_source_focus":focus,
                "independent_decoded_border_probes":pixel,
                "real_frame_sha256":_sha(image)})
        require({str(p):_sha(p) for p in inputs}==before,
                "Original physics/math publisher/voice/slide source mutated")
        rows[f"{section}_slide{slide}"]={"book_sha256":_sha(book),
            "original_slides_pdf_sha256":_sha(pdf),
            "original_original_wav_sha256":_sha(wav),
            "encoded_h264_aac_video_sha256":_sha(mp4),
            "source_mathematical_spoken_events":events,
            "independent_decoded_pixel_probes":frames,
            "original_voice_s":seconds,"encoded_video_s":actual,
            "all_intermediate_source_math_and_figures_approved":False}
    report={"status":status,"source_math_sympy_derivation_proofs":identities,
        "original_source_mathematical_slide_clips":rows,
        "academic_all_source_elements_accepted":False,
        "student_publication_authorized":False}
    with (out/receipt_name).open(
         "x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":status,"original_math_slides":list(rows),
        "encoded_independent_frames":sum(len(v["independent_decoded_pixel_probes"])
                                         for v in rows.values())}))
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("root","timing-receipt","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args(argv)
    create(root=a.root,timing_receipt=a.timing_receipt,out=a.out)
if __name__=="__main__":
    main()
