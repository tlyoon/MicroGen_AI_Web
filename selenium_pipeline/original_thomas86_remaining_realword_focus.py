"""Original Thomas 8.6 slides 6/11/12: real WAV-word focus H264/AAC pilots.

Source-science verified by separate scholarly receipts. Offline Vosk phrases are
UNPROMPTED; ASR's 'sign', 'enter girls', 'hi' are NOT mathematical truth.
Only publisher-original authored slide PDF, original mono16 WAV and true source
figure/maths are used; outputs are independent QA assets, NOT student release.
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

from .figure_source_identity import require, _sha
from .video_ffmpeg import ffmpeg_executable
from .original_thomas84_offline_word_pdf_timing import _real_local_vosk_transcribe
from .original_thomas84_outline_real_word_focus import _phrase
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border
from .original_thomas86_tank_ex62_source_provenance import verify_tank_publisher_source
from .original_thomas86_example3_summary_source_math import verify_source as verify_example_summary
from .original_thomas85_86_first_math_highlights import SOURCE

# Rectangles are real publisher-original authored PDF regions, in PDF points.
# Vosk anchor phrases are independently observed, not generated script times.
EVENTS={
  6: (
   ("original_example_three_integral",[32.73,64.19,190.32,79.35],
    "the integral of the variable x times the inverse sign"),
   ("formula106_first_step",[32.73,84.98,321.69,137.0],
    "in the first step we apply a reduction formula"),
   ("formula106_n1_a1_reduction",[124.91,165.39,258.05,194.26],
    "this breaks the interval down into a polynomial term"),
   ("formula49_second_step",[32.73,204.72,341.52,229.18],
    "in the second step we evaluate that remaining integral"),
  ),
  11: (
   ("original_tank_exercise62_problem_context",[32.73,41.8,350.27,93.35],
    "consider the tank inventory problem where we need to calculate"),
   ("exact_publisher_tank_volume_integral",[127.06,95.11,256.42,127.93],
    "we formulate the volume as two times the length l"),
   ("publisher_original_tank_measuring_figure",[109.236,161.721,253.599,271.829],
    "measuring stick hi data directly into accurate volume inventories"),
  ),
  12: (
   ("publisher_integral_table_summary",[32.73,74.81,345.62,99.27],
    "interval tables offer a rapid way to access standard formulas"),
   ("publisher_reduction_formula_summary",[32.73,104.9,342.81,129.36],
    "reduction formula systematically lower powers through integration by parts"),
   ("publisher_cas_summary",[32.73,134.99,333.33,159.45],
    "computer algebra systems provide powerful symbolic solutions"),
   ("publisher_nonelementary_integrals_summary",[32.73,165.08,338.08,189.53],
    "non elementary enter girls frequently appear in physics and engineering"),
   ("publisher_tank_volume_application_summary",[32.73,195.16,338.29,219.62],
    "finally real world applications demonstrate how definite inter girls model physical quantities"),
  ),
}
PDF_TERMS={
  6: ("Example 3", "Formula 106", "Formula 49"),
  11: ("Tank Inventory", "Volume Integral Formulation"),
  12: ("Integral tables", "Reduction formulas", "Computer algebra systems",
       "Nonelementary integrals", "tank volume calculations"),
}
STATUS="ORIGINAL_THOMAS86_THREE_SOURCE_REAL_PCM_SPOKEN_12_FOCUS_PILOTS_NONPRODUCTION"

def _pcm_seconds(path:Path)->float:
    with wave.open(str(path),"rb") as audio:
        require(audio.getnchannels()==1 and audio.getsampwidth()==2
                and audio.getcomptype()=="NONE"
                and 0<audio.getnframes()/audio.getframerate()<570,
                "Original source WAV not authentic mono16 PCM")
        return audio.getnframes()/audio.getframerate()

def _duration(mp4:Path)->float:
    info=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(mp4)],
                        capture_output=True,text=True,timeout=35).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",info)
    require(m is not None and "Video: h264" in info and "Audio: aac" in info,
            "Actual encoded QA media missing H264/AAC")
    return int(m[1])*3600+int(m[2])*60+float(m[3])

def verify_geometry(pdf:pymupdf.Document, slide:int)->dict:
    page=pdf[slide-1]
    visible=page.get_text()
    require(all(term.casefold() in visible.casefold()
                for term in PDF_TERMS[slide]),
            f"Original slide {slide} does not contain required publisher-grounded concepts")
    image_rect=None
    if slide==11:
        image_blocks=[pymupdf.Rect(b["bbox"]) for b in page.get_text("dict")["blocks"]
                      if b["type"]==1 and b.get("width",0)>200]
        require(len(image_blocks)==1,
                "Original tank publisher image bbox on authored slide11 is ambiguous")
        image_rect=image_blocks[0]
    for index,(name,rect,_) in enumerate(EVENTS[slide]):
        target=pymupdf.Rect(rect)
        require(target.is_valid and not target.is_infinite
                and page.rect.contains(target) and target.width>10
                and target.height>8,"Invalid source figure/math highlight rectangle")
        if slide==11 and index==2:
            require(image_rect is not None
                    and abs(image_rect.x0-target.x0)<1
                    and abs(image_rect.y0-target.y0)<1
                    and abs(image_rect.x1-target.x1)<1
                    and abs(image_rect.y1-target.y1)<1,
                    "Tank image highlight is not the actual publisher author's PDF image")
        else:
            require(len(page.get_text(clip=target).strip())>5,
                    f"Highlighted math element has no actual authored PDF words: {name}")
    return {"rectangles_inside_original_publisher_authored_pdf":len(EVENTS[slide]),
            "original_authored_pdf_slide_raster_source_sha256":SOURCE["8.6"]["slides_pdf_sha"]}

def build(*,root:Path,model_path:Path,out:Path)->dict:
    from vosk import Model,SetLogLevel
    root,model_path,out=(Path(x).absolute() for x in (root,model_path,out))
    require(root.is_dir() and not root.is_symlink()
            and model_path.is_dir() and not model_path.is_symlink()
            and out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(root),
            "Source, offline recognition and exclusive QA output paths required")
    originals=[root/n for n in ("source.pdf","slides.pdf","slides.tex","script.txt")]
    originals += [root/f"slide{i}.wav" for i in EVENTS]
    require(all(p.is_file() and not p.is_symlink() for p in originals),
            "Pinned source publisher/author PCM originals not physically present")
    hashes={str(f):_sha(f) for f in originals}
    require(hashes[str(root/"source.pdf")]==SOURCE["8.6"]["publisher_sha"]
            and hashes[str(root/"slides.pdf")]==SOURCE["8.6"]["slides_pdf_sha"],
            "Wrong publisher-original corpus; do not substitute live regenerated slides")
    original=verify_tank_publisher_source(folder=root)
    example=verify_example_summary(folder=root)
    require(original["author_source_image_same_publisher_visual_verified"]
            and original["symbolic_volume_derivative_equals_2L_sqrt_2rd_minus_d_squared"]
            and example["slide6"]["symbolic_antiderivative_exact"]
            and example["slide12"]["five_publisher_topics_author_slides_script_matched"],
            "No publisher-backed mathematical/figure source proof")
    with pymupdf.open(root/"slides.pdf") as pdf:
        require(len(pdf)==13,"No original thirteen-slide source")
        pdf_geometry={s:verify_geometry(pdf,s) for s in EVENTS}
        for s in EVENTS:
            png=out/f"thomas86_original_slide{s:02d}_source.png"
            require(not png.exists(),"No prior source raster overwrite")
            pdf[s-1].get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False).save(str(png))
    SetLogLevel(-1)
    model=Model(str(model_path))
    report={}
    ffmpeg=ffmpeg_executable()
    for slide,events in EVENTS.items():
        wav=root/f"slide{slide}.wav"
        duration=_pcm_seconds(wav)
        words,recognized=_real_local_vosk_transcribe(
            model=model,exe=ffmpeg,audio_path=wav)
        require(len(words)>45 and all(
            math.isfinite(float(w["start"])) and math.isfinite(float(w["end"]))
            and 0<=w["start"]<w["end"]<duration for w in words),
            "Original unprompted WAV speech recognition not temporally grounded")
        prepared={}
        previous_end=-1.
        for name,rect,phrase in events:
            a,b=_phrase(words,phrase.split())
            start,end=float(words[a]["start"]),float(words[b]["end"])
            require(previous_end<start<end<duration,
                    "Publisher-original narrated source event not uniquely ordered")
            previous_end=end
            prepared[name]={
                "publisher_original_visual_rect_pt":rect,
                "original_unprompted_vosk_phrase":phrase,
                "actual_start_s":start,"actual_end_s":end,
                "recognized_start_word":words[a]["word"],
                "recognized_end_word":words[b]["word"],
                "source_publisher_mathematical_visual_identity_verified":True,
            }
        png=out/f"thomas86_original_slide{slide:02d}_source.png"
        video=out/f"thomas86_original_slide{slide:02d}_realword_h264.mp4"
        require(not video.exists(),"Never overwrite existing video QA")
        filters=[]
        for item in prepared.values():
            x0,y0,x1,y1=item["publisher_original_visual_rect_pt"]
            a,b=item["actual_start_s"],item["actual_end_s"]
            filters.append(
                f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                f"color=yellow@0.95:t=4:enable='between(t,{a:.4f},{b:.4f})'")
        cmd=[ffmpeg,"-hide_banner","-nostdin","-loglevel","error",
             "-loop","1","-framerate","10","-i",str(png),"-i",str(wav),
             "-vf",",".join(filters)+",scale=trunc(iw/2)*2:trunc(ih/2)*2",
             "-c:v","libx264","-preset","veryfast","-crf","19",
             "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
             "-t",f"{duration:.6f}","-shortest","-movflags","+faststart",str(video)]
        encoded=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
        require(encoded.returncode==0 and video.is_file()
                and video.stat().st_size>10000,
                "Original publisher WAV-video H264 encode failed: "+encoded.stderr[-450:])
        actual=_duration(video)
        require(actual<600 and abs(actual-duration)<0.16,
                "Original source WAV and encoded video duration differ")
        sampled=[]
        probes=[("before",0.05,None)]
        probes.extend((name,(r["actual_start_s"]+r["actual_end_s"])/2,name)
                      for name,r in prepared.items())
        for label,at,target in probes:
            decoded=out/f"thomas86_original_slide{slide:02d}_decoded_{label}.png"
            require(not decoded.exists(),"Never overwrite independent decoded frame")
            q=subprocess.run([ffmpeg,"-hide_banner","-nostdin","-loglevel",
                              "error","-i",str(video),"-ss",f"{at:.4f}",
                              "-frames:v","1",str(decoded)],
                             capture_output=True,text=True,timeout=45)
            require(q.returncode==0 and decoded.is_file(),
                    "Actual encoded H264 independent frame undecodable")
            counts={name:count_source_equation_side_border(
                decoded,region["publisher_original_visual_rect_pt"])
                for name,region in prepared.items()}
            require(all((score>=6)==(name==target) for name,score in counts.items()),
                    f"Wrong actual decoded source visual focus at {slide}/{label}: {counts}")
            sampled.append({"decoded_timestamp_s":round(at,4),
                            "active_math_figure_element":target,
                            "independent_real_encoded_frame_border_counts":counts,
                            "actual_decoded_frame_sha256":_sha(decoded)})
        require(hashes=={str(p):_sha(p) for p in originals},
                "Original publisher/author/script/WAV input unexpectedly mutated")
        report[str(slide)]={
            "original_publisher_sha256":hashes[str(root/"source.pdf")],
            "original_author_slide_sha256":hashes[str(root/"slides.pdf")],
            "original_wav_sha256":hashes[str(wav)],
            "original_PCM_duration_s":duration,
            "encoded_H264_AAC_duration_s":actual,
            "encoded_original_video_sha256":_sha(video),
            "actual_offline_unprompted_recognized_word_count":len(words),
            "actual_unprompted_asr_not_scientific_truth":recognized,
            "publisher_audio_visual_events":prepared,
            "real_encoded_independent_pixel_samples":sampled,
            "source_visual_geometry":pdf_geometry[slide],
            "all_individual_math_figure_label_narration_complete":False,
        }
        print(f"SLIDE {slide}: real unique anchored events={len(prepared)}, decoded samples={len(sampled)}")
    receipt={
        "status":STATUS,"original_section":"8.6",
        "source_slide_count":13,
        "source_verified_real_spoken_highlight_slides":[6,11,12],
        "total_real_spoken_source_highlight_events":sum(len(e) for e in EVENTS.values()),
        "pilot_original_86_spoken_video_evidence":report,
        "publisher_exercise62_original_source_figure_proven":True,
        "publisher_example3_summary_math_source_proven":True,
        "full_41_slide_academic_production_accepted":False,
        "student_publication_authorized":False,
    }
    with (out/"ORIGINAL_86_THREE_GENUINE_SPOKEN_SOURCE_FOCUS_QA.json").open(
            "x",encoding="utf8") as f:
        json.dump(receipt,f,indent=2,ensure_ascii=False)
        f.write("\n")
    return receipt

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("root","model-path","out"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args(argv)
    result=build(root=a.root,model_path=a.model_path,out=a.out)
    print(json.dumps({"status":result["status"],
                      "events":result["total_real_spoken_source_highlight_events"],
                      "scenes":len(result["source_verified_real_spoken_highlight_slides"]),
                      "production":False}))

if __name__=="__main__":
    main()
