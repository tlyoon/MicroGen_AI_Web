"""Full 17-slide, source-corrected, strictly sub-600s private QA preview.

Real source and corrected slides 6/17, real corrected Flash-Lite Kore PCM
and 15 immutable original WAVs, plus the current independently verified
source/math highlighted clips selected in HIGHLIGHTS. Any unmapped slides
remain intact WITHOUT fabricated element highlights; these multipart MP4s
are NOT academic/media production-accepted. No publishing, no source change, no paid TTS.

The source-grounded quality gate remains closed until all slide elements and
figures are semantically matched and timing independently accepted.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import wave
import pymupdf
from PIL import Image,ImageChops,ImageStat
from .figure_source_identity import _sha,require
from .video_ffmpeg import ffmpeg_executable
from .original_thomas84_five_worked_math_sync_batch import WORKED,BATCH_STATUS
from .original_thomas84_intro_summary_source_sync import STATUS as INTRO_SUMMARY_STATUS

MAX_PART_SECONDS=570.
HIGHLIGHTS={
    2:("20261101_PR419_ORIGINAL_OUTLINE_REAL_WORDS",
       "thomas84_slide2_real_word_source_focus.mp4",
       "original_slide2_real_word_source_pixel_qa.json"),
    3:("20261101_PR417_ORIGINAL_INTRO_SUMMARY_SOURCE_MATH",
       "thomas84_slide3_three_verified_focus.mp4",
       "INTRO_SUMMARY_SOURCE_VIDEO_AND_PIXEL_QA.json"),
    4:("20261101_PR409_ORIGINAL_SLIDE4_SOURCE_MATH_SYNC_V2",
       "thomas84_slide4_three_equation_sync_qa.mp4",
       "thomas84_slide4_independent_pixel_qa.json"),
    5:("20261031_PR390_ORIGINAL_MATH_SYNC_PILOT_V2",
       "thomas84_slide5_source_math_sync_qa.mp4",
       "thomas84_slide5_independent_encoded_pixel_qa.json"),
    6:("20261101_PR407_CORRECTED_REAL_TIMED_HIGHLIGHTS",
       "corrected_thomas84_slide6_real_sync.mp4",
       "corrected_thomas84_slide6_independent_pixel_qa.json"),
    7:("20261101_PR413_ORIGINAL_SLIDE7_INVERSE_DOMAIN",
       "thomas84_slide7_inverse_domain_sync_qa.mp4",
       "thomas84_slide7_independent_pixel_qa.json"),
    8:("20261101_PR411_ORIGINAL_SOURCE_PROCEDURE_SLIDE8",
       "thomas84_slide8_four_step_sync_qa.mp4",
       "thomas84_slide8_independent_pixel_qa.json"),
    9:("20261031_PR396_SOURCE_MATH_SLIDE9_QA",
       "original_thomas84_slide9_math_sync_qa.mp4",
       "original_thomas84_slide9_independent_pixel_qa.json"),
    10:("20261101_PR415_FIVE_REAL_WORKED_MATH_CLIPS",
        "thomas84_slide10_single_verified_math.mp4",
        "FIVE_ORIGINAL_WORKED_MATH_CLIPS_INDEPENDENT_SOURCE_QA.json"),
    11:("20261101_PR415_FIVE_REAL_WORKED_MATH_CLIPS",
        "thomas84_slide11_single_verified_math.mp4",
        "FIVE_ORIGINAL_WORKED_MATH_CLIPS_INDEPENDENT_SOURCE_QA.json"),
    12:("20261031_PR398_SOURCE_MATH_SLIDE12_QA",
       "thomas84_slide12_math_sync_qa.mp4",
       "thomas84_slide12_independent_encoded_pixel_receipt.json"),
    13:("20261101_PR415_FIVE_REAL_WORKED_MATH_CLIPS",
        "thomas84_slide13_single_verified_math.mp4",
        "FIVE_ORIGINAL_WORKED_MATH_CLIPS_INDEPENDENT_SOURCE_QA.json"),
    14:("20261101_PR415_FIVE_REAL_WORKED_MATH_CLIPS",
        "thomas84_slide14_single_verified_math.mp4",
        "FIVE_ORIGINAL_WORKED_MATH_CLIPS_INDEPENDENT_SOURCE_QA.json"),
    15:("20261101_PR415_FIVE_REAL_WORKED_MATH_CLIPS",
        "thomas84_slide15_single_verified_math.mp4",
        "FIVE_ORIGINAL_WORKED_MATH_CLIPS_INDEPENDENT_SOURCE_QA.json"),
    16:("20261101_PR417_ORIGINAL_INTRO_SUMMARY_SOURCE_MATH",
        "thomas84_slide16_three_verified_focus.mp4",
        "INTRO_SUMMARY_SOURCE_VIDEO_AND_PIXEL_QA.json"),
    17:("20261101_PR407_CORRECTED_REAL_TIMED_HIGHLIGHTS",
       "corrected_thomas84_slide17_real_sync.mp4",
       "corrected_thomas84_slide17_independent_pixel_qa.json")
}
PROVENANCE={2:("FIVE_ORIGINAL_PUBLISHER_OUTLINE_WORD_ACOUSTIC_EVENTS_ENCODED_PIXEL_QA_PASS",
                "actual_encoded_mp4_sha256"),
            3:(INTRO_SUMMARY_STATUS,None),
            4:("ORIGINAL_SLIDE4_THREE_MATH_EQUATIONS_INDEPENDENT_PIXEL_QA_PASS",
                "actual_mp4_sha256"),
            5:("INDEPENDENT_REAL_ENCODED_PIXEL_SAMPLES_PASS",
                "original_clip_mp4_sha256"),
            6:("ORIGINAL_SOURCE_CORRECTED_MATH_SYNCHRONIZED_ENCODED_PIXEL_QA_PASS",
                "actual_encoded_mp4_sha256"),
            7:("ORIGINAL_SLIDE7_SOURCE_INVERSE_DOMAIN_H264_PIXEL_QA_PASS",
                "encoded_mp4_sha256"),
            8:("ORIGINAL_SLIDE8_FOUR_SOURCE_PROCEDURE_HIGHLIGHTS_PIXEL_QA_PASS",
                "actual_encoded_mp4_sha256"),
            9:("ORIGINAL_SOURCE_SLIDE9_ENCODED_PIXEL_SAMPLES_PASS",None),
            10:(BATCH_STATUS,None),
            11:(BATCH_STATUS,None),
            12:("ORIGINAL_SLIDE12_INDEPENDENT_ENCODED_PIXEL_QA_PASS",None),
            13:(BATCH_STATUS,None),
            14:(BATCH_STATUS,None),
            15:(BATCH_STATUS,None),
            16:(INTRO_SUMMARY_STATUS,None),
            17:("ORIGINAL_SOURCE_CORRECTED_MATH_SYNCHRONIZED_ENCODED_PIXEL_QA_PASS",
                 "actual_encoded_mp4_sha256")}
BLOCKERS=(
    "ORIGINAL_ALL_SEVENTEEN_SLIDE_MATH_AND_FIGURE_SOURCE_SEMANTICS_NOT_APPROVED",
    "ONE_TITLE_SLIDE_NO_CERTIFIED_WORD_LEVEL_TIMED_HIGHLIGHTS",
    "NOT_AN_AUTOMATED_STUDENT_PRODUCTION_RELEASE"
)

def split_slides(durations:list[float],limit:float=MAX_PART_SECONDS)->list[list[int]]:
    require(type(durations) is list and len(durations)>=1
            and 1<limit<600
            and all(type(x) in (int,float) and math.isfinite(x)
                    and 0<x<limit-.1 for x in durations),
            "No falsified duration, missing clip or impossible multipart schedule")
    chunks=[]
    current=[]
    seconds=0.
    for i,seconds_this in enumerate(durations,1):
        if current and seconds+seconds_this>limit:
            chunks.append(current)
            current=[]
            seconds=0.
        current.append(i)
        seconds+=seconds_this
    if current:
        chunks.append(current)
    require([n for part in chunks for n in part]==list(range(1,len(durations)+1)),
            "Automatic multipart order/coverage corrupted")
    return chunks

def _duration(media:Path)->float:
    proc=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(media)],
                        capture_output=True,text=True,timeout=25)
    details=proc.stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",details)
    require(m and "Video: h264" in details and "Audio: aac" in details,
            "Encoded MP4 missing real H264/AAC audiovisual streams")
    seconds=int(m[1])*3600+int(m[2])*60+float(m[3])
    require(0<seconds<600,"Entire source media exceeds the contract")
    return seconds

def _pcm(path:Path)->float:
    require(path.is_file() and not path.is_symlink(),
            "Actual original provider PCM missing")
    with wave.open(str(path),"rb") as w:
        require(w.getnchannels()==1 and w.getsampwidth()==2
                and w.getcomptype()=="NONE",
                "Original source slide PCM must be valid mono16")
        return w.getnframes()/w.getframerate()

def _bound_source(*,original:Path,corrected:Path,tts:Path,qa:Path)->dict:
    owner=json.loads((corrected/
               "original_two_slides_source_corrected_audio_stale.json").read_text())
    speech=json.loads(qa.read_text(encoding="utf8"))
    require(owner["status"]=="CUMULATIVE_ORIGINAL_SLIDES_6_AND_17_MATH_PAIRED_AUDIO_STALE"
            and owner["only_corrected_slides"]==[6,17]
            and owner["old_original_wavs_reuse_prohibited"]==[6,17]
            and owner["original_textbook_sha256"]==_sha(original/"source.pdf")
            and owner["corrected_slides_pdf_sha256"]==_sha(corrected/"slides.pdf")
            and owner["corrected_script_sha256"]==_sha(corrected/"script.txt")
            and speech["status"]==
                "TWO_CORRECTED_ORIGINAL_KORE_WAVS_OFFLINE_PHONETIC_SCREEN_PASS"
            and speech["all_corrected_wavs_phonetic_screen_pass"] is True
            and speech["corrected_script_sha256"]==_sha(corrected/"script.txt"),
            "Original textbook/corrected academic slides and true voice evidence invalid")
    sources={}
    for i in range(1,18):
        path=(tts/f"corrected_original_slide{i}.wav"
              if i in (6,17) else original/f"slide{i}.wav")
        seconds=_pcm(path)
        require(0<seconds<MAX_PART_SECONDS,
                "Missing valid actual PCM for lecture slide")
        if i in (6,17):
            require(_sha(path)==speech[
                "source_slide_audio_observations"][str(i)]["new_real_pcm_sha256"]
                and _sha(original/f"slide{i}.wav")
                ==owner["stale_original_wav_sha256"][str(i)],
                "Stale original WAV substituted for repaired academic audio")
        sources[i]={"wav":path,"duration":seconds,"sha":_sha(path)}
    with pymupdf.open(corrected/"slides.pdf") as deck:
        require(len(deck)==17,"Cumulative original lecture page count changed")
    return {"source":sources,"academic_revision":owner,"speech_qa":speech}

def source_highlights(*,checkpoint:Path,source_wavs:dict,
                      corrected_pdf:Path)->dict:
    witnesses={}
    for slide,(name,mp4,receipt) in HIGHLIGHTS.items():
        parent=checkpoint/name
        video=parent/mp4
        receipt_path=parent/receipt
        require(video.is_file() and receipt_path.is_file()
                and not video.is_symlink() and not receipt_path.is_symlink(),
                f"Missing real independently verified source math highlight slide{slide}")
        qa=json.loads(receipt_path.read_text(encoding="utf8"))
        state,sha_key=PROVENANCE[slide]
        require(qa["status"]==state and qa["student_publication_authorized"] is False
                and (sha_key is None or qa[sha_key]==_sha(video)),
                "Source math original MP4 not independently pixel verified")
        if slide in (4,5,7,8,9,12):
            # Source SHA is verified by each individual original producer.
            metadata=(parent/{
                4:"thomas84_slide4_source_synchronized_equations.json",
                5:"thomas84_slide5_source_math_sync_qa.json",
                7:"thomas84_slide7_inverse_domain_provenance.json",
                8:"thomas84_slide8_source_procedure_qa.json",
                9:"original_thomas84_slide9_math_sync_qa.json",
                12:"thomas84_slide12_math_sync_provenance.json"
            }[slide])
            doc=json.loads(metadata.read_text(encoding="utf8"))
            audio_hash=(doc.get("original_slide7_wav_sha256")
                        or doc.get("original_slide8_wav_sha256")
                        or doc.get("original_slide4_wav_sha256")
                        or doc.get("original_wav_sha256")
                        or doc.get("original_pcm_sha256")
                        or doc.get("original_slide12_wav_sha256"))
            require(audio_hash==source_wavs[slide]["sha"],
                    "Original referenced audio differs from verified math focus clip")
        elif slide==2:
            require(qa["publisher_original_source_sha256"] is not None
                    and qa["original_slide2_wav_sha256"]==source_wavs[2]["sha"]
                    and qa["corrected_pdf_sha256"]==_sha(corrected_pdf)
                    and len(qa["real_original_word_anchor_topic_events"])==5
                    and len(qa["independent_decoded_pixel_samples"])==6
                    and qa["all_lecture_math_and_figures_verified"] is False,
                    "Real original publisher outline PCM/source mapping not validated")
        elif slide in (3,16):
            item=qa["source_bound_original_video_clips"][str(slide)]
            require(qa["original_highlighted_slides"]==[3,16]
                    and qa["verified_events_count"]==6
                    and item["actual_h264_aac_mp4_sha256"]==_sha(video)
                    and item["original_pcm_sha256"]==source_wavs[slide]["sha"]
                    and qa["corrected_slide_pdf_sha256"]==_sha(corrected_pdf)
                    and item["unreviewed_slide_elements_accepted"] is False,
                    "Intro/summary source-bound audio/math pixels not independently proven")
        elif slide in WORKED:
            item=qa["source_verified_math_clips"][str(slide)]
            require(item["source_verified_individual_formula_highlight"] is True
                    and item["encoded_h264_aac_mp4_sha256"]==_sha(video)
                    and item["actual_original_wav_sha256"]==source_wavs[slide]["sha"]
                    and qa["corrected_pdf_sha256"]==_sha(corrected_pdf)
                    and item["all_intermediate_math_and_figure_panels_verified"] is False,
                    "Unverified original worked math/WAV or fabricated academic approval")
        else:
            report=json.loads((parent/
                f"corrected_thomas84_slide{slide}_real_sync.json").read_text())
            require(report["real_audio_sha256"]==source_wavs[slide]["sha"]
                    and report["corrected_pdf_sha256"]==_sha(corrected_pdf),
                    "Source-corrected math focus clip uses stale academic PDF/WAV")
        seconds=_duration(video)
        require(abs(seconds-source_wavs[slide]["duration"])<.15,
                f"Original true audio/MP4 mismatch on slide{slide}")
        witnesses[slide]={"video":video,"status":state,"sha":_sha(video)}
    return witnesses

def assemble(*,original:Path,corrected:Path,tts:Path,speech_qa:Path,
             checkpoint:Path,out:Path)->dict:
    original,corrected,tts,speech_qa,checkpoint,out=(Path(x).absolute()
        for x in (original,corrected,tts,speech_qa,checkpoint,out))
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and not out.is_relative_to(corrected)
            and not out.is_relative_to(tts),
            "Source-preserving distinct external QA preview directory required")
    identified=_bound_source(original=original,corrected=corrected,
                             tts=tts,qa=speech_qa)
    sources=identified["source"]
    highlights=source_highlights(
        checkpoint=checkpoint,source_wavs=sources,
        corrected_pdf=corrected/"slides.pdf")
    before={str(p):_sha(p) for p in
            [original/"source.pdf",corrected/"slides.pdf",
             corrected/"script.txt",
             *[data["wav"] for data in sources.values()]]}
    from .video_ffmpeg import ffmpeg_executable as executable
    ffmpeg=executable()
    clips={}
    with pymupdf.open(corrected/"slides.pdf") as deck:
        for i in range(1,18):
            if i in highlights:
                clips[i]=highlights[i]["video"]
                continue
            image=out/f"original_source_slide{i:02d}_qa_base.png"
            clip=out/f"original_source_slide{i:02d}_NO_ELEMENT_APPROVAL.mp4"
            require(not image.exists() and not clip.exists(),
                    "Never overwrite prior real source media QA files")
            deck[i-1].get_pixmap(matrix=pymupdf.Matrix(2,2),
                                  alpha=False).save(str(image))
            actual=sources[i]["duration"]
            result=subprocess.run([
                ffmpeg,"-hide_banner","-loglevel","error","-loop","1",
                "-framerate","10","-i",str(image),
                "-i",str(sources[i]["wav"]),
                "-vf","scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v","libx264","-preset","veryfast","-crf","19",
                "-pix_fmt","yuv420p","-c:a","aac","-ar","24000",
                "-b:a","128k","-t",f"{actual:.6f}","-shortest",
                "-movflags","+faststart",str(clip)],
                capture_output=True,text=True,timeout=140)
            require(result.returncode==0 and clip.is_file() and clip.stat().st_size>9000,
                    f"Original actual slide {i} encoded preview failed: "+
                    result.stderr[-700:])
            clips[i]=clip
    durations=[_duration(clips[i]) for i in range(1,18)]
    require(all(abs(sources[i]["duration"]-durations[i-1])<.15
                for i in range(1,18)),
            "One source slide audiovisual length incorrectly produced")
    groups=split_slides(durations)
    products=[]
    for index,slides in enumerate(groups,1):
        playlist=out/f"part{index:02d}_concat_sources.txt"
        part=out/f"THOMAS_84_SOURCE_QA_ONLY_part{index:02d}.mp4"
        require(not playlist.exists() and not part.exists(),
                "Never overwrite existing original lecture part QA")
        playlist.write_text("".join("file '"+str(clips[i]).replace("\\","/")+
                                    "'\n" for i in slides),encoding="utf8")
        command=[ffmpeg,"-hide_banner","-loglevel","error",
                 "-f","concat","-safe","0","-i",str(playlist),
                 "-c","copy","-movflags","+faststart",str(part)]
        output=subprocess.run(command,capture_output=True,text=True,timeout=125)
        require(output.returncode==0 and part.is_file(),
                "Real original source multipart QA concat failed: "+output.stderr[-650:])
        part_seconds=_duration(part)
        expected=sum(durations[i-1] for i in slides)
        require(part_seconds<600 and abs(part_seconds-expected)<1.8,
                "Encoded multipart preview fails <600s or complete media time parity")
        products.append({"part_number":index,"source_slide_numbers":slides,
                         "encoded_duration_s":part_seconds,
                         "sum_original_component_video_s":round(expected,3),
                         "mp4_path":str(part),"mp4_sha256":_sha(part),
                         "is_production_accepted":False})
    require([n for group in groups for n in group]==list(range(1,18)),
            "Original source slides omitted or duplicated across preview")
    require(all(_sha(Path(name))==digest for name,digest in before.items()),
            "Actual original/corrected source or PCM mutated during QA assembly")
    result={"status":"FULL_17_SLIDE_TWO_PART_SOURCE_CORRECTED_QA_PREVIEW_NOT_PRODUCTION",
            "original_source_sha256":_sha(original/"source.pdf"),
            "corrected_academic_pdf_sha256":_sha(corrected/"slides.pdf"),
            "corrected_narration_sha256":_sha(corrected/"script.txt"),
            "source_slide_count":17,"all_original_pcm_streams_present":True,
            "replaced_stale_wav_original_slide_numbers":[6,17],
            "source_verified_element_highlight_slide_numbers":sorted(highlights),
            "remaining_plain_slide_numbers":[n for n in range(1,18)
                                               if n not in highlights],
            "multipart_contract_max_duration_exclusive":600,
            "automatic_split_planning_limit_s":MAX_PART_SECONDS,
            "part_count":len(products),"parts":products,
            "original_audio_duration_sum_s":round(
                sum(z["duration"] for z in sources.values()),5),
            "full_academic_and_element_highlight_acceptance":False,
            "remaining_release_blockers":list(BLOCKERS),
            "student_publication_authorized":False}
    manifest=out/"MULTIPART_SOURCE_CORRECTED_QA_NOT_FOR_STUDENTS.json"
    with manifest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("original","corrected","tts","speech-qa","checkpoint","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args(argv)
    report=assemble(original=a.original,corrected=a.corrected,tts=a.tts,
                    speech_qa=a.speech_qa,checkpoint=a.checkpoint,out=a.out)
    print(json.dumps({"status":report["status"],
        "parts":[(p["source_slide_numbers"],p["encoded_duration_s"])
                 for p in report["parts"]],
        "highlighted_slides":report[
            "source_verified_element_highlight_slide_numbers"],
        "production_accepted":report[
            "full_academic_and_element_highlight_acceptance"]}))
if __name__=="__main__":
    main()
