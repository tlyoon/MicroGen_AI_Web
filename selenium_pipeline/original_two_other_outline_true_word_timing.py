"""Genuine unprompted real PCM word-timed publisher topic outlines §§8.5/8.6.

§8.5 five source-provable outline topics; §8.6 four textbook-source-proven
outline topics. The §8.6 tank-exercise item intentionally remains static and
scientifically UNAPPROVED: its external original exercise/figure provenance
has not been established from §8.6's publisher source pages. Two original
PCM H264/AAC clips, actual independent on/off decoded encoded pixel checks,
unchanged original book/PDF/WAV SHA. Never claim formal course completion.
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
from .original_thomas84_offline_word_pdf_timing import (
    _real_local_vosk_transcribe,tokenize_reference_sentences)
from .original_thomas84_outline_real_word_focus import _phrase
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border
from .original_thomas85_86_first_math_highlights import SOURCE

TOPICS={
 "8.5":{
   1:("Introduction to Partial Fractions",[32.7,108.,182.,122.],
      ["begin","with","an","introduction","to","the","method"]),
   2:("General Method for Proper and Improper Fractions",[32.7,124.,269.,139.],
      ["handle","both","proper","and","improper","rational","functions"]),
   3:("Linear and Irreducible Quadratic Factors",[32.7,141.,220.,155.],
      ["examine","linear","and","irreducible","quadratic","factors"]),
   4:("The Heaviside Cover-Up Method",[32.7,157.,185.,172.],
      ["look","at","the","heavy","side","cover","up","method"]),
   5:("Alternative Techniques and Applications",[32.7,174.,219.,189.],
      ["review","some","alternative","techniques","in","applications"]),
 },
 "8.6":{
   1:("Using Integral Tables for Evaluation",[32.7,107.,199.,122.],
      ["exploring","extensive","integral","tables","and","learning"]),
   2:("Reduction Formulas",[32.7,124.,126.,139.],
      ["examined","reduction","formulas","that","simplify","repeated"]),
   3:("Integration with Computer Algebra Systems (CAS)",[32.7,141.,268.,155.],
      ["computer","algebra","systems","for","symbolic","and","numerical","evaluation"]),
   4:("Nonelementary Integrals",[32.7,157.,145.,172.],
      ["we","will","also","discuss","non","elementary"]),
 },
}
PUBLISHER={
 "8.5":((2,"General Description of the Method"),
        (2,"real linear factors and real quadratic factors"),
        (5,"Heaviside"),
        (7,"Other Ways to Determine the Coefficients")),
 "8.6":((1,"Integral Tables"),
        (2,"Reduction Formulas"),
        (3,"Computer Algebra"),
        (4,"Nonelementary Integrals")),
}
STATUS="TWO_ORIGINAL_OUTLINE_SOURCE_REAL_PCM_WORD_FRAME_QA_APPROVED_ONLY"


def _video_seconds(mp4:Path)->float:
    log=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(mp4)],
                       capture_output=True,text=True,timeout=25).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",log)
    require(m and "Video: h264" in log and "Audio: aac" in log,
            "Actual original publisher outline video not real H264/AAC")
    return int(m[1])*3600+int(m[2])*60+float(m[3])


def produce(*,root:Path,model_path:Path,word_receipt:Path,out:Path)->dict:
    root,model_path,out=(Path(p).absolute() for p in (root,model_path,out))
    require(out.is_dir() and not out.is_symlink() and not out.is_relative_to(root)
            and model_path.is_dir() and not model_path.is_symlink(),
            "Only untouched real publisher source and original offline ASR")
    word=json.loads(Path(word_receipt).read_text(encoding="utf8"))
    previous={s["section"]:s for s in word["sections"]}
    try:
        import vosk
    except ImportError:
        require(False,"No offline Vosk PCM word recognition; no fake timing bins")
    vosk.SetLogLevel(-1)
    model=vosk.Model(str(model_path))
    outputs={}
    for sec,approved in TOPICS.items():
        base=root/sec
        inputs=[base/n for n in ("source.pdf","slides.tex","slides.pdf",
                                 "script.txt","slide2.wav")]
        require(all(f.is_file() and not f.is_symlink() for f in inputs),
                f"Publisher source/real original WAV not physically present {sec}")
        hashes={str(p):_sha(p) for p in inputs}
        require(hashes[str(inputs[0])]==SOURCE[sec]["publisher_sha"]
                and hashes[str(inputs[2])]==SOURCE[sec]["slides_pdf_sha"],
                f"Original full publisher §{sec} source hash mismatch")
        with pymupdf.open(inputs[0]) as textbook,pymupdf.open(inputs[2]) as slides:
            require(len(slides)==SOURCE[sec]["slides"],
                    "Wrong original lecturer slide count")
            for page,s in PUBLISHER[sec]:
                require(s in textbook[page-1].get_text(),
                        f"Textbook original source topic not present §{sec}: {s}")
            visual=slides[1].get_text()
            require("Outline" in visual,
                    "Physical original Beamer outline slide missing")
            for title,rect,phrase in approved.values():
                b=pymupdf.Rect(rect)
                require(b.is_valid and not b.is_infinite and slides[1].rect.contains(b)
                        and visual.count(title)==1
                        and title in slides[1].get_text(clip=b),
                        "Physical publisher topic PDF rectangle failed original exact word match")
            if sec=="8.6":
                require("Applications (e.g., Tank Inventory Problem)" in visual,
                        "Unverified tank topic not present (must remain unapproved)")
        authored=inputs[1].read_text(encoding="utf8")
        frames=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",authored,re.S)
        require(len(frames)==SOURCE[sec]["slides"] and
                all(title in frames[1] for title,_,_ in approved.values()),
                "Author original exact topic labels missing from Beamer source")
        original_script=dict(blocks(inputs[3].read_text(encoding="utf-8-sig")))[2]
        original_sentences,_=tokenize_reference_sentences(original_script)
        old_timing=previous[sec]["slides"][1]
        require(old_timing["slide"]==2 and old_timing["wav_sha256"]==_sha(inputs[4])
                and len(original_sentences)==len(old_timing["sentence_timing_candidates"])
                and all(v["narration_fragment_sha256"]==
                        original_sentences[i]["narration_fragment_sha256"]
                        for i,v in enumerate(old_timing["sentence_timing_candidates"])),
                "Original author spoken narration was re-generated or modified")
        with wave.open(str(inputs[4]),"rb") as w:
            duration=w.getnframes()/w.getframerate()
            require(w.getnchannels()==1 and w.getsampwidth()==2
                    and w.getcomptype()=="NONE" and 0<duration<600.,
                    "Not original unaltered single-channel PCM WAV")
        recognized,utterance=_real_local_vosk_transcribe(
            model=model,exe=ffmpeg_executable(),audio_path=inputs[4])
        require(len(recognized)>=40 and all(
            0<=v["start"]<=v["end"]<duration and
            math.isfinite(v["start"]) and math.isfinite(v["end"])
            for v in recognized),"Offline original WAV recognition not real")
        regions={}
        previous_end=-1.
        for i,(title,rect,phrase) in approved.items():
            u,v=_phrase(recognized,phrase)
            a,b=recognized[u]["start"],recognized[v]["end"]
            require(previous_end<a<b<duration,
                    "No uniquely ordered original real audio topic phrasing")
            previous_end=b
            regions[str(i)]={"source_topic":title,
                "original_pdf_topic_rect_pt":rect,
                "real_source_pcm_start_s":float(a),
                "real_source_pcm_end_s":float(b),
                "actual_unprompted_first_word":recognized[u]["word"],
                "actual_unprompted_last_word":recognized[v]["word"],
                "textbook_topic_witness":True}
        if sec=="8.5":
            require("heavy side" in utterance and "techniques in applications" in utterance,
                    "Observed Vosk approximate Heaviside/audio words changed")
        if sec=="8.6":
            require("into girls" in utterance and "non elementary and two girls" in utterance,
                    "Observed original Vosk transcription changed: revalidate no guessing")
        stem=f"Thomas_{sec}_original_outline_true_word"
        image=out/(stem+".png")
        mp4=out/(stem+".mp4")
        require(not image.exists() and not mp4.exists(),"No previous QA overwrite")
        with pymupdf.open(inputs[2]) as pdf:
            pdf[1].get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False).save(str(image))
        vf=[]
        for t in regions.values():
            x0,y0,x1,y1=t["original_pdf_topic_rect_pt"]
            a,b=t["real_source_pcm_start_s"],t["real_source_pcm_end_s"]
            vf.append(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                      f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                      f"color=yellow@0.95:t=4:enable='between(t,{a:.4f},{b:.4f})'")
        q=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel","error",
            "-loop","1","-framerate","10","-i",str(image),"-i",str(inputs[4]),
            "-vf",",".join(vf)+",scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v","libx264","-preset","veryfast","-crf","19",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-t",f"{duration:.6f}","-shortest","-movflags","+faststart",
            str(mp4)],capture_output=True,text=True,timeout=150)
        require(q.returncode==0 and mp4.is_file() and mp4.stat().st_size>9000,
                "Failed original publisher outline real audio video encode "+q.stderr[-550:])
        encoded=_video_seconds(mp4)
        require(encoded<600 and abs(encoded-duration)<.15,
                "Original publisher PCM and actual H264 time not aligned")
        decoded=[]
        for key,at,target in [("before",.05,None)]+[
            (str(i),(r["real_source_pcm_start_s"]+r["real_source_pcm_end_s"])/2,str(i))
            for i,r in regions.items()]:
            png=out/(stem+f"_independent_{key}.png")
            require(not png.exists(),"Do not overwrite QA actual decoded pixels")
            p=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
                "error","-i",str(mp4),"-ss",str(at),"-frames:v","1",
                str(png)],capture_output=True,text=True,timeout=45)
            require(p.returncode==0 and png.is_file(),
                    "Genuine source video frame not independently decodable")
            scores={i:count_source_equation_side_border(
                png,ev["original_pdf_topic_rect_pt"]) for i,ev in regions.items()}
            require(all((score>=6)==(i==target) for i,score in scores.items()),
                    f"Original publisher topic focus not correctly spoken: {scores}")
            decoded.append({"actual_time_s":round(at,3),"expected":target,
                            "real_source_outline_border_counts":scores,
                            "independent_decoded_frame_sha256":_sha(png)})
        require(hashes=={str(p):_sha(p) for p in inputs},
                "Modified original publisher/voice or lecturer slide source")
        outputs[sec]={"original_source_sha256":_sha(inputs[0]),
            "original_slides_sha256":_sha(inputs[2]),
            "original_slide2_wav_sha256":_sha(inputs[4]),
            "original_real_audio_seconds":duration,
            "original_encoded_h264_seconds":encoded,
            "real_mp4_sha256":_sha(mp4),
            "publisher_verified_spoken_topic_events":regions,
            "original_unprompted_vosk_transcript":utterance,
            "observed_vosk_misrecognitions_not_source_truth":(
                ["heavy side","in applications"] if sec=="8.5" else
                ["into girls","non elementary and two girls"]),
            "decoded_independent_frame_samples":decoded,
            "unverified_external_tank_exercise_figure":sec=="8.6",
            "entire_slide_all_academic_content_approved":False}
    receipt={"status":STATUS,"original_section_outline_media":outputs,
             "full_41_slide_academic_release_accepted":False,
             "student_publication_authorized":False}
    with (out/"ORIGINAL_85_86_OUTLINE_WORD_REAL_PCM_SOURCE_PIXEL_QA.json").open(
         "x",encoding="utf8") as f:
        json.dump(receipt,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,"outline_topics":{
        k:len(v["publisher_verified_spoken_topic_events"]) for k,v in outputs.items()},
        "independent_encoded_frames":sum(len(v["decoded_independent_frame_samples"])
                                         for v in outputs.values())}))
    return receipt

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("root","model-path","word-receipt","out"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args(argv)
    produce(root=a.root,model_path=a.model_path,
            word_receipt=a.word_receipt,out=a.out)
if __name__=="__main__":
    main()
