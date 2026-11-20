"""Batch source-verified equation-only highlights for original four worked examples.

Each proof binds a complete authored source-TeX final antiderivative or input
to the original publisher source + independent SymPy differentiation (PR400),
the unchanged actual slide PDF, the physically original WAV SHA and a
sentence's independently real Vosk word timings. Output five new isolated
H264/AAC source-driven QA videos and a decoded-frame ON/OFF receipt.

This is ONE mathematically verified element per example slide, NOT a blanket
approval of its intermediate calculations or geometric figure panel.
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
from .original_thomas84_multiline_math_witness import audit as symbolic_source_audit
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border

# n: (source example, source math type, narration sentence number,
#     complete physical visible math region, meaningful actual narration tokens,
#     sample while formula is spoken, independent sample while formula is NOT spoken).
WORKED={
  10:("example_1","final",4,[62.,210.,170.,257.],
      ("final result","natural logarithm","square root of four"),45.,20.),
  11:("example_2","final",4,[108.,192.,277.,230.],
      ("inverse hyperbolic sine","natural logarithm"),42.,30.),
  13:("example_3","final",4,[45.,190.,190.,220.],
      ("final expanded antiderivative","nine halves","arcsine"),40.,15.),
  14:("example_4","input",1,[30.,73.,228.,129.],
      ("asks us to evaluate","twenty five","greater than two fifths"),6.,30.),
  15:("example_4","final",4,[50.,213.,184.,258.],
      ("final antiderivative","one fifth","square root"),40.,15.),
}
BATCH_STATUS="FIVE_ORIGINAL_WORKED_EXAMPLE_MATH_CLIPS_SOURCE_VERIFIED_PIXEL_PASS"

def _encoded_duration(mp4:Path)->float:
    p=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(mp4)],
                     capture_output=True,text=True,timeout=30).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",p)
    require(m and "Audio: aac" in p and "Video: h264" in p,
            "Encoded real source worked example lacks H264/AAC media")
    return int(m[1])*3600+int(m[2])*60+float(m[3])

def validate_config(config:dict=WORKED)->None:
    require(set(config)=={10,11,13,14,15},
            "Actual original four worked-example slide IDs changed")
    require([r[0] for r in config.values()]==
            ["example_1","example_2","example_3","example_4","example_4"],
            "The original source Example 1–4 witness order drifted")
    for n,(example,kind,idx,rect,words,focus,off) in config.items():
        require(kind in ("final","input") and
                idx>=1 and idx<=6 and
                isinstance(rect,list) and len(rect)==4
                and all(type(v) in (int,float) and math.isfinite(v) for v in rect)
                and rect[0]<rect[2] and rect[1]<rect[3]
                and len(words)>=2 and focus!=off and
                0<=focus<100 and 0<=off<100,
                f"Invalid original example {example} physical math focus")

def build(*,original:Path,corrected:Path,real_timing:Path,out:Path)->dict:
    validate_config()
    original,corrected,out=[Path(x).absolute()
                            for x in (original,corrected,out)]
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and not out.is_relative_to(corrected),
            "Use empty separate immutable-source-independent academic QA directory")
    book=original/"source.pdf"
    authored=original/"slides.tex"
    original_slides=original/"slides.pdf"
    script=original/"script.txt"
    revised=corrected/"slides.pdf"
    protected=[book,authored,original_slides,script,revised]
    protected.extend(original/f"slide{n}.wav" for n in WORKED)
    require(all(x.is_file() and not x.is_symlink() for x in protected),
            "Original source or recorded worked example audio is missing")
    checksums={str(x):_sha(x) for x in protected}
    evidence=symbolic_source_audit(source=book,latex=authored)
    require(evidence["status"]==
            "FOUR_ORIGINAL_MULTILINE_WORKED_EXAMPLES_SOURCE_ANCHORED_SYMBOLICALLY_PROVED"
            and evidence["complete_worked_examples_proved"]==4
            and evidence["differentiated_antiderivative_formulas_proved"]==5
            and evidence["source_pdf_sha256"]==_sha(book)
            and evidence["original_slide_latex_sha256"]==_sha(authored),
            "Actual original textbook four complete integral derivatives not proved")
    witnesses={r["example"]:r for r in evidence["source_context_math_witnesses"]}
    for slide,(name,kind,*_) in WORKED.items():
        entry=witnesses[name]
        require(entry["original_input_slide" if kind=="input" else
                      "original_complete_result_slide"]==slide
                and entry["exact_complete_slide_source_math_present"] is True,
                f"Original publisher Example {name} source math not on this PDF slide")
    speech=dict(blocks(script.read_text(encoding="utf-8-sig")))
    timing=json.loads(Path(real_timing).read_text(encoding="utf8"))
    section=next(x for x in timing["sections"] if x["section"]=="8.4")
    results={}
    with pymupdf.open(original_slides) as original_pdf,pymupdf.open(
            revised) as fixed:
        require(len(original_pdf)==len(fixed)==17,
                "Wrong original/corrected lecture PDF count")
        for slide,(name,kind,sentence_index,rect,tokens,on,off) in WORKED.items():
            old,new=original_pdf[slide-1],fixed[slide-1]
            require(old.get_text()==new.get_text()
                    and old.get_pixmap(alpha=False).samples==
                        new.get_pixmap(alpha=False).samples,
                    f"Original academic correction unexpectedly altered example slide{slide}")
            area=pymupdf.Rect(rect)
            require(area.is_valid and not area.is_infinite
                    and new.rect.contains(area)
                    and len(new.get_text(clip=area).strip())>=3,
                    f"Visible authored worked example {name} math not physically present")
            wav=original/f"slide{slide}.wav"
            audio=section["slides"][slide-1]
            require(audio["slide"]==slide and
                    audio["wav_sha256"]==_sha(wav),
                    "Original worked example timing was paired with wrong WAV")
            sentences,_=tokenize_reference_sentences(speech[slide])
            row=audio["sentence_timing_candidates"][sentence_index-1]
            sentence=sentences[sentence_index-1]
            require(sentence["narration_fragment_sha256"]==
                    row["narration_fragment_sha256"]
                    and all(term in sentence["narration_fragment"].casefold()
                            for term in tokens)
                    and row["actual_ASR_word_anchor_fraction"]>=.79
                    and row["word_timing_hypothesis_available"] is True,
                    "Original source example final math was not genuinely spoken")
            start,end=row["first_matched_real_audio_second"],row[
                "last_matched_real_audio_second"]
            require(start<on<end and (off<start or off>end)
                    and 0<=start<end<600,
                    "Original spoken source formula/acoustic sample timing invalid")
            with wave.open(str(wav),"rb") as pcm:
                duration=pcm.getnframes()/pcm.getframerate()
                require(pcm.getnchannels()==1 and pcm.getsampwidth()==2
                        and pcm.getcomptype()=="NONE" and
                        0<end<duration<600,"Original physical WAV duration/format invalid")
            base=out/f"thomas84_slide{slide:02d}_source_math_base.png"
            video=out/f"thomas84_slide{slide:02d}_single_verified_math.mp4"
            require(not base.exists() and not video.exists(),
                    "Do not overwrite existing real source math QA video")
            new.get_pixmap(matrix=pymupdf.Matrix(2,2),
                           alpha=False).save(str(base))
            x0,y0,x1,y1=rect
            vf=(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                f"color=yellow@0.95:t=4:"
                f"enable='between(t,{start:.4f},{end:.4f})',"
                "scale=trunc(iw/2)*2:trunc(ih/2)*2")
            cmd=[ffmpeg_executable(),"-hide_banner","-loglevel","error",
                 "-loop","1","-framerate","10","-i",str(base),
                 "-i",str(wav),"-vf",vf,
                 "-c:v","libx264","-preset","veryfast","-crf","19",
                 "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
                 "-t",f"{duration:.6f}","-shortest",
                 "-movflags","+faststart",str(video)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=150)
            require(result.returncode==0 and video.is_file() and
                    video.stat().st_size>10000,
                    f"Actual publisher-worked example slide{slide} render failed "+
                    result.stderr[-650:])
            mp4secs=_encoded_duration(video)
            require(abs(duration-mp4secs)<.15 and mp4secs<600,
                    "Physical original PCM and encoded worked example duration differ")
            observations=[]
            for name_sample,second,expected in [
                ("source_math_OFF",off,False),
                ("source_math_ON",on,True)]:
                frame=out/f"thomas84_slide{slide:02d}_{name_sample}.png"
                require(not frame.exists(),"Cannot overwrite independent source sample")
                q=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
                    "error","-i",str(video),"-ss",str(second),
                    "-frames:v","1",str(frame)],
                    capture_output=True,text=True,timeout=45)
                require(q.returncode==0 and frame.is_file(),
                        f"Unable to independently decode original slide{slide} video")
                score=count_source_equation_side_border(frame,rect)
                require((score>=6)==expected,
                        f"Physical formula highlight failed slide{slide} {name_sample}: {score}")
                observations.append({"time_s":second,"expected_highlight":expected,
                                     "pixel_border_probes":score,
                                     "real_decoded_frame_sha256":_sha(frame)})
            results[str(slide)]={
                "original_publisher_example":name,
                "publisher_book_page":witnesses[name]["original_publisher_source_page"],
                "source_verified_math_type":kind,
                "original_source_math_tex_verified":True,
                "actual_math_target_rect_pt":rect,
                "original_spoken_sentence_index":sentence_index,
                "actual_ASR_anchor_fraction":row["actual_ASR_word_anchor_fraction"],
                "real_narration_start_s":start,
                "real_narration_end_s":end,
                "actual_original_wav_sha256":_sha(wav),
                "encoded_h264_aac_mp4_sha256":_sha(video),
                "physical_original_audio_duration_s":round(duration,4),
                "original_encoded_duration_s":round(mp4secs,4),
                "actual_independent_decoded_pixel_samples":observations,
                "source_verified_individual_formula_highlight":True,
                "all_intermediate_math_and_figure_panels_verified":False}
    require(checksums=={str(q):_sha(q) for q in protected},
            "Original source/math/PCM or independent corrected PDF was modified")
    batch={"status":BATCH_STATUS,
           "original_book_sha256":_sha(book),
           "original_math_latex_sha256":_sha(authored),
           "corrected_pdf_sha256":_sha(revised),
           "original_source_calculus_proof_status":evidence["status"],
           "original_slide_numbers_verified":list(WORKED),
           "source_verified_math_clips":results,
           "all_original_lecture_elements_verified":False,
           "student_publication_authorized":False}
    with (out/"FIVE_ORIGINAL_WORKED_MATH_CLIPS_INDEPENDENT_SOURCE_QA.json").open(
            "x",encoding="utf8") as f:
        json.dump(batch,f,indent=2,ensure_ascii=False);f.write("\n")
    return batch

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("original","corrected","word-receipt","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args(argv)
    result=build(original=a.original,corrected=a.corrected,
                 real_timing=a.word_receipt,out=a.out)
    print(json.dumps({"status":result["status"],
                      "actual_verified_worked_example_slides":
                      result["original_slide_numbers_verified"]}))
if __name__=="__main__":
    main()
