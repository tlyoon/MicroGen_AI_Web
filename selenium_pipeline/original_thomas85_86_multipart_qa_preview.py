"""Full original §8.5/§8.6 audiovisual QA previews, never student release.

Includes every physically original authored slide and original WAV, using
ONLY separately textbook+SymPy+Vosk+pixel-verified source mathematical
highlights for three original slides per section. Remaining original slides
are unchanged static visuals and must NOT be marked academically approved.
All original source hashes pinned and full H264/AAC videos <600s.
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
from .original_thomas85_86_first_math_highlights import SOURCE,STATUS as FIRST_STATUS
from .original_thomas85_86_more_worked_math import WORKED,STATUS as MORE_STATUS
from .original_thomas85_86_academic_constraints_focus import STATUS as CONSTRAINTS_STATUS
from .original_thomas84_multipart_qa_preview import split_slides

# Exactly 3 standalone original scholarly math highlight scenes for each
# other section; no accidental promotion of future unverified candidates.
FOCUS={
 "8.5":{
   4:("20261101_PR425_ORIGINAL_SOURCE_ACADEMIC_CONSTRAINTS",
      "thomas_8.5_slide4_source_conditions.mp4","constraints"),
   3:("20261101_PR421_FIRST_85_86_REAL_SOURCE_MATH",
      "Thomas_8.5_slide3_math.mp4","first"),
   5:("20261101_PR422_MORE_85_86_ORIGINAL_MATH",
      "Thomas_8.5_slide5_additional_source_math.mp4","more"),
   6:("20261101_PR422_MORE_85_86_ORIGINAL_MATH",
      "Thomas_8.5_slide6_additional_source_math.mp4","more"),
 },
 "8.6":{
   3:("20261101_PR425_ORIGINAL_SOURCE_ACADEMIC_CONSTRAINTS",
      "thomas_8.6_slide3_source_conditions.mp4","constraints"),
   4:("20261101_PR421_FIRST_85_86_REAL_SOURCE_MATH",
      "Thomas_8.6_slide4_math.mp4","first"),
   5:("20261101_PR422_MORE_85_86_ORIGINAL_MATH",
      "Thomas_8.6_slide5_additional_source_math.mp4","more"),
   8:("20261101_PR422_MORE_85_86_ORIGINAL_MATH",
      "Thomas_8.6_slide8_additional_source_math.mp4","more"),
 }}
STATUS="ORIGINAL_85_86_FULL_SOURCE_AUDIO_QA_FOUR_EACH_APPROVED_HIGHLIGHT_SCENES_NOT_PRODUCTION"
MAX_DURATION=570.0


def _pcm(p:Path)->float:
    require(p.is_file() and not p.is_symlink(),"Original WAV missing")
    with wave.open(str(p),"rb") as wav:
        require(wav.getnchannels()==1 and wav.getsampwidth()==2
                and wav.getcomptype()=="NONE",
                "Physical original PCM must be real mono16 not synthetic")
        sec=wav.getnframes()/wav.getframerate()
    require(0<sec<570.,"Original WAV source exceeds per-clip limit")
    return sec


def _media_seconds(mp4:Path)->float:
    output=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(mp4)],
                          capture_output=True,text=True,timeout=25).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",output)
    require(m and "Video: h264" in output and "Audio: aac" in output,
            "Real encoded QA clip missing H264/AAC streams")
    duration=int(m[1])*3600+int(m[2])*60+float(m[3])
    require(0<duration<600.0,"Strictly under 600 seconds per source MP4")
    return duration


def _source_witnesses(*,section:str,original:Path,checkpoint:Path)->tuple[dict,dict]:
    first=json.loads((checkpoint/
        "20261101_PR421_FIRST_85_86_REAL_SOURCE_MATH"/
        "ORIGINAL_85_86_TWO_SOURCE_MATH_AV_PIXEL_RECEIPT.json").read_text(encoding="utf8"))
    more=json.loads((checkpoint/
        "20261101_PR422_MORE_85_86_ORIGINAL_MATH"/
        "FOUR_MORE_SOURCE_CALCULUS_REAL_VIDEOS_PIXEL_QA.json").read_text(encoding="utf8"))
    constraint=json.loads((checkpoint/
        "20261101_PR425_ORIGINAL_SOURCE_ACADEMIC_CONSTRAINTS"/
        "THOMAS_85_86_ORIGINAL_SOURCE_CONDITIONS_PIXEL_QA.json").read_text(encoding="utf8"))
    require(first["status"]==FIRST_STATUS and
            more["status"]==MORE_STATUS
            and constraint["status"]==CONSTRAINTS_STATUS and
            first["both_sections_complete"] is False and
            more["entire_85_86_sections_production_approved"] is False,
            "Not actual independently checked first/further scholarly source clips")
    require(first["source_verified_real_media"][section][
        "book_sha256"]==_sha(original/"source.pdf"),
        "Wrong publisher original §8.5/8.6 textbook")
    for s,(_,_,kind) in FOCUS[section].items():
        if kind=="more":
            record=more["original_source_math_clips"][f"{section}_slide{s}"]
            require(record["source_original_textbook_sha256"]==_sha(original/"source.pdf")
                    and record["original_slides_pdf_sha256"]==_sha(original/"slides.pdf")
                    and record["other_mathematical_areas_approved"] is False,
                    "Original additional formula mathematical source review not complete")
    require(constraint["source_verified_clips"][section]["original_textbook_sha256"]==
            _sha(original/"source.pdf")
            and constraint["source_verified_clips"][section]["original_slides_pdf_sha256"]==
                _sha(original/"slides.pdf")
            and constraint["student_publication_authorized"] is False,
            "Publisher source mathematical prerequisites clip receipt invalid")
    return first,more,constraint


def build(*,root:Path,checkpoint:Path,out:Path)->dict:
    root,checkpoint,out=(Path(p).absolute() for p in (root,checkpoint,out))
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(root)
            and out!=checkpoint,
            "Separate untouched publisher and verifiable QA parent required")
    ff=ffmpeg_executable()
    summaries={}
    for section,meta in SOURCE.items():
        original=root/section
        physical=[original/"source.pdf",original/"slides.pdf",
                  original/"slides.tex",original/"script.txt"]
        physical.extend(original/f"slide{i}.wav" for i in range(1,meta["slides"]+1))
        require(all(p.is_file() and not p.is_symlink() for p in physical),
                "Original complete textbook/slides/audio source is physically missing")
        before={str(p):_sha(p) for p in physical}
        require(_sha(original/"source.pdf")==meta["publisher_sha"] and
                _sha(original/"slides.pdf")==meta["slides_pdf_sha"],
                f"Original textbook source of §{section} does not match pinned hash")
        first,more,constraint=_source_witnesses(section=section,original=original,checkpoint=checkpoint)
        actual={}
        for slide in range(1,meta["slides"]+1):
            wav=original/f"slide{slide}.wav"
            seconds=_pcm(wav)
            if slide in FOCUS[section]:
                folder,file,kind=FOCUS[section][slide]
                video=checkpoint/folder/file
                require(video.is_file() and not video.is_symlink(),
                        "Only genuine original mathematically reviewed MP4 can be reused")
                if kind=="first":
                    receipt=first["source_verified_real_media"][section]
                    require(slide==meta["target"]
                            and receipt["encoded_h264_aac_mp4_sha256"]==_sha(video)
                            and receipt["original_wav_sha256"]==_sha(wav)
                            and receipt["full_section_accepted"] is False,
                            "Original initial math source/acoustic/pixel proof invalid")
                elif kind=="constraints":
                    receipt=constraint["source_verified_clips"][section]
                    require(receipt["encoded_h264_aac_mp4_sha256"]==_sha(video)
                            and receipt["original_wav_sha256"]==_sha(wav)
                            and len(receipt["actual_encoded_independent_pixel_samples"])==3
                            and receipt["entire_slide_source_approved"] is False,
                            "Publisher academic conditions PCM/encoded pixel proof invalid")
                else:
                    receipt=more["original_source_math_clips"][f"{section}_slide{slide}"]
                    require(receipt["encoded_mp4_sha256"]==_sha(video)
                            and receipt["original_narration_wav_sha256"]==_sha(wav)
                            and len(receipt["independent_decoded_samples"])==2,
                            "Original additional worked example pixel/PCM proof invalid")
                accepted_element=True
            else:
                # Render authentic untouched source PDF slide with genuine
                # original physical PCM; NO synthetic highlight/approval.
                image=out/f"source_{section}_slide{slide:02d}_original.png"
                video=out/f"source_{section}_slide{slide:02d}_UNAPPROVED_static.mp4"
                require(not image.exists() and not video.exists(),
                        "Never overwrite a previous unreviewed original source QA clip")
                with pymupdf.open(original/"slides.pdf") as pdf:
                    require(len(pdf)==meta["slides"],
                            f"Original slide count drifted for section {section}")
                    pdf[slide-1].get_pixmap(matrix=pymupdf.Matrix(2,2),
                                            alpha=False).save(str(image))
                output=subprocess.run([ff,"-hide_banner","-loglevel","error",
                    "-loop","1","-framerate","10","-i",str(image),
                    "-i",str(wav),"-vf","scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-c:v","libx264","-preset","veryfast","-crf","19",
                    "-pix_fmt","yuv420p","-c:a","aac","-ar","24000",
                    "-b:a","128k","-t",f"{seconds:.6f}","-shortest",
                    "-movflags","+faststart",str(video)],
                    capture_output=True,text=True,timeout=135)
                require(output.returncode==0 and video.is_file() and
                        video.stat().st_size>9000,
                        f"Original static real PCM render failed §{section} slide{slide}: "+
                        output.stderr[-700:])
                accepted_element=False
            duration=_media_seconds(video)
            require(abs(duration-seconds)<.15,
                    f"Original section {section} audio vs encoded slide{slide} drift")
            actual[slide]={"source_wav_sha256":_sha(wav),
                "mp4_sha256":_sha(video),"mp4":video,
                "real_pcm_s":seconds,"actual_mp4_s":duration,
                "at_least_one_source_proved_element":accepted_element}
        sections=split_slides(
            [actual[i]["actual_mp4_s"] for i in sorted(actual)],
            limit=MAX_DURATION)
        products=[]
        for part_num,slides in enumerate(sections,1):
            playlist=out/f"source_{section}_part{part_num:02d}.txt"
            mp4=out/f"THOMAS_{section}_ORIGINAL_SOURCE_QA_part{part_num:02d}.mp4"
            require(not playlist.exists() and not mp4.exists(),
                    "Refuse overwrite original source multipart video outputs")
            playlist.write_text("".join(
                "file '"+str(actual[i]["mp4"]).replace("\\","/")+"'\n"
                for i in slides),encoding="utf8")
            result=subprocess.run([ff,"-hide_banner","-loglevel","error",
                "-f","concat","-safe","0","-i",str(playlist),
                "-c","copy","-movflags","+faststart",str(mp4)],
                capture_output=True,text=True,timeout=140)
            require(result.returncode==0 and mp4.is_file()
                    and mp4.stat().st_size>30000,
                    f"Original §{section} full source video concat failed "+
                    result.stderr[-650:])
            observed=_media_seconds(mp4)
            expected=sum(actual[i]["actual_mp4_s"] for i in slides)
            require(observed<600 and abs(observed-expected)<1.9,
                    "Whole original lecture part not strictly under 600 or loses PCM")
            products.append({"part":part_num,"slides":slides,
                "real_h264_aac_encoded_duration_s":observed,
                "expected_component_duration_s":round(expected,3),
                "sha256":_sha(mp4),"student_publication_authorized":False})
        require([n for product in products for n in product["slides"]]==
                list(range(1,meta["slides"]+1)),
                "Missing a real publisher slide in complete multipart source QA video")
        require(before=={str(p):_sha(p) for p in physical},
                "Original publisher/slide/WAV source changed by QA render")
        summaries[section]={"original_publisher_sha256":_sha(original/"source.pdf"),
            "original_slides_pdf_sha256":_sha(original/"slides.pdf"),
            "original_slide_count":meta["slides"],
            "original_slide_audio_source_receipts":{
                str(i):{"original_wav_sha256":x["source_wav_sha256"],
                       "video_source_sha256":x["mp4_sha256"],
                       "real_source_pcm_s":x["real_pcm_s"],
                       "actual_encoded_s":x["actual_mp4_s"],
                       "at_least_one_verified_math_element":
                           x["at_least_one_source_proved_element"]}
                for i,x in actual.items()},
            "source_verified_highlight_slide_numbers":sorted(FOCUS[section]),
            "unapproved_element_slides":[i for i in actual if i not in FOCUS[section]],
            "actual_original_encoded_parts":products,
            "all_figures_and_math_source_correspondence_accepted":False,
            "full_production_release_accepted":False}
    receipt={"status":STATUS,"sections":summaries,
        "both_full_original_slide_audio_qa_previews_encoded":True,
        "both_sections_complete_academic_acceptance":False,
        "all_source_element_highlights_time_correct":False,
        "student_publication_authorized":False}
    with (out/"ORIGINAL_85_86_COMPLETE_MULTIPART_SOURCE_QA_NOT_STUDENTS.json").open(
            "x",encoding="utf8") as f:
        json.dump(receipt,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,
        "sections":{k:{"original_slides":v["original_slide_count"],
            "highlight_scenes":len(v["source_verified_highlight_slide_numbers"]),
            "parts":[{"n":p["part"],"seconds":p["real_h264_aac_encoded_duration_s"]}
                     for p in v["actual_original_encoded_parts"]]}
            for k,v in summaries.items()}}))
    return receipt


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("root","checkpoint","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args(argv)
    build(root=a.root,checkpoint=a.checkpoint,out=a.out)
if __name__=="__main__":
    main()
