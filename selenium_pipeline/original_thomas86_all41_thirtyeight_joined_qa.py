"""Integrate three new genuine speech-focus clips into original §8.6 source QA.

Runs independent second-pass pixel checks on all 13 truly joined §8.6
slides, all 12 source-spoken §8.6 visual slides, and all 12 new per-element
unprompted original WAV anchors. Rechecks preserved 8.4/8.5 slide+focus
source evidence without pretending a full scholarly per-token certification.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
from PIL import ImageChops,ImageStat
from .figure_source_identity import require,_sha
from .original_thomas85_86_multipart_qa_preview import (
    FOCUS,SOURCE,_media_seconds)
from .original_thomas_all41_independent_joined_qa import (
    STATUS as PREVIOUS_STATUS,_identities)
from .original_thomas84_multipart_independent_qa import _reference_slide,_decoded
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border
from .original_thomas86_remaining_realword_focus import STATUS as PILOT_STATUS,EVENTS
from .video_ffmpeg import ffmpeg_executable

PILOT_SUBDIR="20261102_PR443_THREE_SOURCE_SPOKEN_AUDIO_PIXELS"
PREVIOUS_QA_SUBDIR="20261101_PR437_FULL_85_86_NINETEEN_FOCUS_QA"
PREVIOUS_PIXEL_SUBDIR="20261101_PR437_INDEPENDENT_ALL41_35_FOCUS_QA"
NEW_FOCUS=set(EVENTS)
NEW_STATUS="ORIGINAL_THOMAS_ALL41_38_SOURCE_SPOKEN_SLIDES_47_REAL_FOCUS_EVENT_SAMPLES_NONPRODUCTION"

def verify_previous_sections(*,root:Path,checkpoint:Path,old:dict)->dict:
    """Retain original prior 8.4/8.5 physical slide/video hash witnesses."""
    original85=root/"8.5"
    m=old["sections"]["8.5"]
    require(m["original_publisher_sha256"]==_sha(original85/"source.pdf")
            and m["original_slides_pdf_sha256"]==_sha(original85/"slides.pdf")
            and m["original_slide_count"]==11
            and len(m["source_verified_highlight_slide_numbers"])==10,
            "Previously independently source-verified §8.5 original lecture changed")
    verified85=[]
    for part in m["actual_original_encoded_parts"]:
        mp4=checkpoint/PREVIOUS_QA_SUBDIR/(
            f"THOMAS_8.5_ORIGINAL_SOURCE_QA_part{part['part']:02d}.mp4")
        require(mp4.is_file() and _sha(mp4)==part["sha256"]
                and _media_seconds(mp4)<600
                and part["student_publication_authorized"] is False,
                "Publisher original §8.5 accepted joined MP4 changed")
        verified85.append({"part":part["part"],"sha256":_sha(mp4)})
    data=json.loads((checkpoint/
        "20261101_PR420_SOURCE_CORRECTED_16_HIGHLIGHT_MULTIPART_QA"/
        "MULTIPART_SOURCE_CORRECTED_QA_NOT_FOR_STUDENTS.json").read_text("utf8"))
    proof=json.loads((checkpoint/
        "20261101_PR420_INDEPENDENT_MULTIPART_FRAMES"/
        "INDEPENDENT_MULTIPART_VIDEO_FRAME_VERIFICATION_REVIEW_ONLY.json").read_text("utf8"))
    require(data["original_source_sha256"]==_sha(root/"8.4"/"source.pdf")
            and data["student_publication_authorized"] is False
            and proof["original_source_sha256"]==_sha(root/"8.4"/"source.pdf")
            and len(proof["real_joined_source_slide_samples"])==17
            and len(proof["real_joined_mathematical_highlight_samples"])==16,
            "Prior §8.4 original publisher H264 independent 17-slide QA unavailable")
    verified84=[]
    for part in data["parts"]:
        mp4=Path(part["mp4_path"])
        require(mp4.is_file() and _sha(mp4)==part["mp4_sha256"]
                and _media_seconds(mp4)<600,
                "Prior publisher-original §8.4 accepted video part missing")
        verified84.append({"sha256":_sha(mp4)})
    require(len(verified85)==1 and len(verified84)==2,
            "Original §8.4/8.5 five-part video arrangement changed")
    return {"8.4":verified84,"8.5":verified85}


def integrate(*,root:Path,checkpoint:Path,out:Path)->dict:
    root,checkpoint,out=(Path(x).absolute() for x in (root,checkpoint,out))
    pilot=checkpoint/PILOT_SUBDIR
    previous=checkpoint/PREVIOUS_QA_SUBDIR
    old_pixels=checkpoint/PREVIOUS_PIXEL_SUBDIR
    require(out.is_dir() and not out.is_symlink() and not out.is_relative_to(root)
            and pilot.is_dir() and previous.is_dir(),
            "Independent QA directory, immutable original publisher source required")
    original=root/"8.6"
    require(_sha(original/"source.pdf")==SOURCE["8.6"]["publisher_sha"]
            and _sha(original/"slides.pdf")==SOURCE["8.6"]["slides_pdf_sha"],
            "Original publisher section and author lecture modified")
    prior=json.loads((old_pixels/"INDEPENDENT_ALL41_ORIGINAL_MP4_FRAME_PIXEL_QA.json").read_text("utf8"))
    require(prior["status"]==PREVIOUS_STATUS
            and prior["actually_decoded_original_slide_samples_total"]==41
            and prior["actually_decoded_source_proven_highlight_samples_total"]==35
            and prior["full_three_section_production_gate_passed"] is False,
            "Old independently sampled authentic source-scene evidence untrusted")
    prior_video=json.loads((previous/"ORIGINAL_85_86_COMPLETE_MULTIPART_SOURCE_QA_NOT_STUDENTS.json").read_text("utf8"))
    require(prior_video["student_publication_authorized"] is False
            and len(prior_video["sections"]["8.6"]["original_slide_audio_source_receipts"])==13,
            "Original publisher thirteen-slide encoded component proof missing")
    old_section_sha_receipts=verify_previous_sections(
        root=root,checkpoint=checkpoint,old=prior_video)
    latest=json.loads((pilot/"ORIGINAL_86_THREE_GENUINE_SPOKEN_SOURCE_FOCUS_QA.json").read_text("utf8"))
    require(latest["status"]==PILOT_STATUS
            and latest["source_verified_real_spoken_highlight_slides"]==[6,11,12]
            and latest["total_real_spoken_source_highlight_events"]==12
            and latest["student_publication_authorized"] is False,
            "Three original true WAV word/pixel source pilots unverified")
    ff=ffmpeg_executable()
    parts=[]
    original_pilot_assets={}
    rows=prior_video["sections"]["8.6"]["original_slide_audio_source_receipts"]
    clips={}
    all_before={str(original/name):_sha(original/name) for name in
                ("source.pdf","slides.pdf","slides.tex","script.txt")}
    all_before.update({str(original/f"slide{i}.wav"):_sha(original/f"slide{i}.wav")
                       for i in range(1,14)})
    for slide in range(1,14):
        old=rows[str(slide)]
        wav=original/f"slide{slide}.wav"
        require(old["original_wav_sha256"]==_sha(wav),
                "Original source PCM slide WAV mismatches previously accepted corpus")
        if slide in NEW_FOCUS:
            item=latest["pilot_original_86_spoken_video_evidence"][str(slide)]
            clip=pilot/f"thomas86_original_slide{slide:02d}_realword_h264.mp4"
            require(item["original_wav_sha256"]==_sha(wav)
                    and item["encoded_original_video_sha256"]==_sha(clip)
                    and len(item["real_encoded_independent_pixel_samples"])==
                    len(EVENTS[slide])+1,
                    "Original unprompted scientifically proven math/audio/pixel clip missing")
            original_pilot_assets[str(slide)]={"sha256":_sha(clip),
                "original_wav_sha256":_sha(wav),"source_real_events":
                list(item["publisher_audio_visual_events"])}
        elif slide in FOCUS["8.6"]:
            folder,name,_=FOCUS["8.6"][slide]
            clip=checkpoint/folder/name
            require(old["at_least_one_verified_math_element"] is True
                    and old["video_source_sha256"]==_sha(clip),
                    "Prior publisher source-WAV math/figure focus clip altered")
        else:
            require(slide==1 and old["at_least_one_verified_math_element"] is False,
                    "Only a purely structural title slide may stay static")
            clip=previous/f"source_8.6_slide{slide:02d}_UNAPPROVED_static.mp4"
            require(_sha(clip)==old["video_source_sha256"],
                    "Original structural title source video changed")
        require(clip.is_file() and not clip.is_symlink()
                and _media_seconds(clip)<570 and
                abs(_media_seconds(clip)-float(old["real_source_pcm_s"]))<.15,
                "Original source PCM and accepted clip timings incompatible")
        clips[slide]=clip
    for segment in prior_video["sections"]["8.6"]["actual_original_encoded_parts"]:
        number,slides=segment["part"],segment["slides"]
        playlist=out/f"source_8.6_newpart{number:02d}.txt"
        mp4=out/f"THOMAS_8.6_38_FOCUS_SOURCE_QA_part{number:02d}.mp4"
        require(not playlist.exists() and not mp4.exists(),
                "No overwriting already-reviewed original lecture output")
        playlist.write_text("".join("file '"+str(clips[i]).replace("\\","/")+"'\n"
                                    for i in slides),encoding="utf8")
        encoded=subprocess.run([ff,"-hide_banner","-nostdin","-loglevel",
                                "error","-f","concat","-safe","0","-i",str(playlist),
                                "-c","copy","-movflags","+faststart",str(mp4)],
                               capture_output=True,text=True,timeout=160)
        require(encoded.returncode==0 and mp4.is_file()
                and mp4.stat().st_size>30000,
                "Full original publisher H264/AAC concat error: "+encoded.stderr[-500:])
        duration=_media_seconds(mp4)
        expected=sum(_media_seconds(clips[i]) for i in slides)
        require(duration<600 and abs(duration-expected)<1.9,
                "Full original lecture video part exceeds 600s or audio timing drift")
        parts.append({"part":number,"slides":slides,
                      "mp4_sha256":_sha(mp4),"real_encoded_seconds":duration,
                      "expected_component_seconds":expected,
                      "student_publication_authorized":False})
    require([i for p in parts for i in p["slides"]]==list(range(1,14)),
            "Missing original publisher source slide in final joined MP4")
    decoded=[]
    focused=[]
    for part in parts:
        mp4=out/f"THOMAS_8.6_38_FOCUS_SOURCE_QA_part{part['part']:02d}.mp4"
        elapsed=0.
        for slide in part["slides"]:
            component=clips[slide]
            secs=_media_seconds(component)
            at=elapsed+min(1.5,secs*.5)
            image=out/f"8.6_slide{slide:02d}_ACTUALLY_JOINED.png"
            actual=_decoded(mp4,at,image)
            reference=_reference_slide(original/"slides.pdf",slide)
            require(actual.size==reference.size,
                    "Joined original publisher slide raster size drift")
            delta=sum(ImageStat.Stat(ImageChops.difference(actual,reference)).mean)/3
            require(delta<12.0,
                    f"Incorrect original publisher slide {slide} pixels delta={delta}")
            decoded.append({"slide":slide,"part":part["part"],
                "actual_joined_decoded_sha256":_sha(image),
                "original_publisher_author_pdf_pixel_delta":round(delta,4)})
            if slide in NEW_FOCUS:
                approved=latest["pilot_original_86_spoken_video_evidence"][str(slide)]["publisher_audio_visual_events"]
                events=[(name,ev["publisher_original_visual_rect_pt"],
                         (ev["actual_start_s"]+ev["actual_end_s"])/2)
                        for name,ev in approved.items()]
            elif slide in FOCUS["8.6"]:
                rect,t=_identities(checkpoint=checkpoint,original=original,
                                   section="8.6",slide=slide,encoded=component)
                events=[("original_previously_verified_source_focus",rect,t)]
            else: events=[]
            for index,(label,rect,t) in enumerate(events):
                sample_at=elapsed+t
                image=out/f"8.6_slide{slide:02d}_JOINED_FOCUS{index+1:02d}.png"
                _decoded(mp4,sample_at,image)
                count=count_source_equation_side_border(image,rect)
                require(count>=6,
                        f"Actual final joined publisher math-source focus missing: {slide}/{label} {count}")
                focused.append({"slide":slide,"part":part["part"],"element":label,
                    "original_wav_s":round(t,4),
                    "final_joined_encoded_s":round(sample_at,4),
                    "independent_decoded_yellow_border_count":count,
                    "actual_decoded_source_pixel_sha256":_sha(image)})
            elapsed+=secs
        require(abs(elapsed-part["expected_component_seconds"])<0.05,
                "Final joined full source component time calculation drift")
    require(len(decoded)==13 and len(focused)==21
            and len(set(x["slide"] for x in focused))==12,
            "Original §8.6 13 PDF slides and 12 timed source slides incomplete")
    require(all_before=={p:_sha(Path(p)) for p in all_before},
            "Publisher source/author/original WAV changed during video integration")
    result={
        "status":NEW_STATUS,
        "original_source_slides_across_three_sections":41,
        "original_source_spoken_focus_slides_across_three_sections":38,
        "independently_accepted_prior_8_4_8_5_slide_samples":28,
        "independently_accepted_prior_8_4_8_5_spoken_samples":26,
        "new_actual_8_6_joined_original_slide_samples":len(decoded),
        "new_actual_8_6_joined_spoken_element_samples":len(focused),
        "total_distinct_source_spoken_element_samples_across_three_sections":47,
        "original_8_6_twelve_spoken_focus_slides":sorted(set(x["slide"] for x in focused)),
        "source_8_6_actual_joined_H264_parts":parts,
        "actual_source_slide_pixel_qa":decoded,
        "actual_original_spoken_highlight_pixel_qa":focused,
        "new_pilot_sha_bound_provenance":original_pilot_assets,
        "original_8_4_and_8_5_prior_video_sha_reverified":old_section_sha_receipts,
        "only_structural_title_pages_without_math_highlight":[
            "8.4_slide1","8.5_slide1","8.6_slide1"],
        "full_41_slide_academic_equation_figure_label_word_timing_accepted":False,
        "student_publication_authorized":False,
    }
    with (out/"ALL41_38_SOURCE_SPOKEN_JOINED_INDEPENDENT_QA.json").open(
            "x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"status":NEW_STATUS,"original_slides":41,
                      "spoken_source_slides":38,"new_86_joined_slides":13,
                      "new_86_individual_focus_samples":len(focused),
                      "parts":[round(p["real_encoded_seconds"],3) for p in parts],
                      "production":False}))
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("root","checkpoint","out"):
        p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args(argv)
    integrate(root=a.root,checkpoint=a.checkpoint,out=a.out)

if __name__=="__main__":
    main()
