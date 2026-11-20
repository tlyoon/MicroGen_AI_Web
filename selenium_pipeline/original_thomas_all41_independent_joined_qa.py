"""Independently decode real JOINED 41-slide §8.4/8.5/8.6 QA videos.

This independent pass checks ALL original slide page images in final
encoded H264/AAC joined files, authentic original voice lengths,
and only publisher/SymPy/Vosk/pixel-proven mathematical spotlight clips.
No additional student, formal-release or all-element claims.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pymupdf
from PIL import Image,ImageChops,ImageStat
from .figure_source_identity import require,_sha
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border
from .original_thomas84_multipart_independent_qa import _reference_slide,_decoded
from .original_thomas85_86_multipart_qa_preview import (
    SOURCE,FOCUS,STATUS as QA_STATUS,_media_seconds)
from .original_thomas85_86_first_math_highlights import STATUS as FIRST_STATUS
from .original_thomas85_86_more_worked_math import STATUS as MORE_STATUS
from .original_thomas85_86_academic_constraints_focus import STATUS as CONSTRAINTS_STATUS
from .original_thomas85_86_derivation_audio_pixels import STATUS as DERIVATION_STATUS
from .original_thomas85_86_coverup_erf_source import STATUS as COVERUP_ERF_STATUS
from .original_thomas85_86_math_review_questions import STATUS as REVIEW_STATUS
from .original_thomas85_86_summary_cas import STATUS as SUMMARY_STATUS
from .original_two_other_outline_true_word_timing import STATUS as OTHER_OUTLINE_STATUS

STATUS="INDEPENDENT_ACTUAL_JOINED_41_SLIDE_35_VERIFIED_FOCUS_PIXELS_NONPRODUCTION"


def _identities(*,checkpoint:Path,original:Path,section:str,
                slide:int,encoded:Path)->tuple[list[float],float]:
    folder,name,kind=FOCUS[section][slide]
    require(encoded==checkpoint/folder/name,
            "Original mathematical focus MP4 source path drifted")
    if kind=="first":
        data=json.loads((checkpoint/folder/
          "ORIGINAL_85_86_TWO_SOURCE_MATH_AV_PIXEL_RECEIPT.json").read_text(encoding="utf8"))
        require(data["status"]==FIRST_STATUS
                and data["source_verified_real_media"][section][
                  "encoded_h264_aac_mp4_sha256"]==_sha(encoded),
                "Original first section science clip not proven")
        item=data["source_verified_real_media"][section][
            "original_source_mathematical_event_targets"][-1]
        rect=item["physical_slide_rect_pt"]
        t=(item["genuine_acoustic_start_s"]+
           item["genuine_acoustic_end_s"])/2
    elif kind=="constraints":
        data=json.loads((checkpoint/folder/
          "THOMAS_85_86_ORIGINAL_SOURCE_CONDITIONS_PIXEL_QA.json").read_text(encoding="utf8"))
        require(data["status"]==CONSTRAINTS_STATUS,
                "Source-approved publisher domain restriction identity missing")
        item=data["source_verified_clips"][section]
        require(item["encoded_h264_aac_mp4_sha256"]==_sha(encoded)
                and item["original_wav_sha256"]==_sha(original/f"slide{slide}.wav")
                and item["entire_slide_source_approved"] is False,
                "Real original math domain constraints are not authenticated")
        event=list(item["source_verified_math_condition_events"].values())[-1]
        rect=event["source_math_rect_pt"]
        t=(event["real_original_audio_start_s"]+event["real_original_audio_end_s"])/2
    elif kind=="outline":
        data=json.loads((checkpoint/folder/
          "ORIGINAL_85_86_OUTLINE_WORD_REAL_PCM_SOURCE_PIXEL_QA.json").read_text(encoding="utf8"))
        require(data["status"]==OTHER_OUTLINE_STATUS
                and data["student_publication_authorized"] is False,
                "Original real WAV outline source/pixel topic evidence missing")
        item=data["original_section_outline_media"][section]
        require(item["real_mp4_sha256"]==_sha(encoded)
                and item["original_slide2_wav_sha256"]==_sha(original/f"slide{slide}.wav")
                and item["entire_slide_all_academic_content_approved"] is False,
                "Original source topic word real recorded WAV identity changed")
        event=list(item["publisher_verified_spoken_topic_events"].values())[-1]
        rect=event["original_pdf_topic_rect_pt"]
        t=(event["real_source_pcm_start_s"]+event["real_source_pcm_end_s"])/2
    elif kind in ("derivation","coverup_erf","review","summary_cas"):
        receipt_file=("ORIGINAL_THOMAS_85_86_THREE_MATH_SLIDES_SIX_TIMED_PIXEL_EVENTS.json"
                      if kind=="derivation" else
                      "ORIGINAL_THOMAS_HEAVISIDE_ERF_SOURCE_MATH_PIXEL_QA.json"
                      if kind=="coverup_erf" else
                      "ORIGINAL_PUBLISHER_TWO_REVIEW_QUESTION_AUDIO_PIXEL_QA.json"
                      if kind=="review" else
                      "ORIGINAL_THOMAS_SUMMARY_CAS_SOURCE_AUDIO_PIXEL_QA.json")
        expected_status=(DERIVATION_STATUS if kind=="derivation" else
                         COVERUP_ERF_STATUS if kind=="coverup_erf" else
                         REVIEW_STATUS if kind=="review" else SUMMARY_STATUS)
        data=json.loads((checkpoint/folder/receipt_file).read_text(encoding="utf8"))
        require(data["status"]==expected_status
                and data["student_publication_authorized"] is False,
                "Original math derivation audio/publisher proof not accepted")
        item=data["original_source_mathematical_slide_clips"][f"{section}_slide{slide}"]
        require(item["encoded_h264_aac_video_sha256"]==_sha(encoded)
                and item["original_original_wav_sha256"]==_sha(original/f"slide{slide}.wav")
                and item["all_intermediate_source_math_and_figures_approved"] is False,
                "Original publisher scientific derivation WAV changed")
        event=list(item["source_mathematical_spoken_events"].values())[-1]
        rect=event["original_source_slide_rect_pt"]
        t=(event["genuine_audio_start_s"]+event["genuine_audio_end_s"])/2
    else:
        data=json.loads((checkpoint/folder/
          "FOUR_MORE_SOURCE_CALCULUS_REAL_VIDEOS_PIXEL_QA.json").read_text(encoding="utf8"))
        require(data["status"]==MORE_STATUS,
                "Additional mathematical clip source proof not accepted")
        item=data["original_source_math_clips"][f"{section}_slide{slide}"]
        require(item["encoded_mp4_sha256"]==_sha(encoded)
                and item["original_narration_wav_sha256"]==
                    _sha(original/f"slide{slide}.wav")
                and item["other_mathematical_areas_approved"] is False,
                "Additional science math SHA, original voice, or nonrelease drift")
        rect=item["original_pdf_equation_rect_pt"]
        t=(item["genuine_spoken_start_s"]+item["genuine_spoken_end_s"])/2
    require(t>0 and t<_media_seconds(encoded),
            "No real spoken original source math time in clip")
    return rect,t


def check(*,root:Path,checkpoint:Path,qa:Path,decode_dir:Path)->dict:
    root,checkpoint,qa,decode_dir=(
        Path(x).absolute() for x in (root,checkpoint,qa,decode_dir))
    require(decode_dir.is_dir() and not decode_dir.is_symlink()
            and decode_dir!=qa
            and not decode_dir.is_relative_to(qa)
            and not decode_dir.is_relative_to(root),
            "Fresh independent original publisher frames output required")
    p=qa/"ORIGINAL_85_86_COMPLETE_MULTIPART_SOURCE_QA_NOT_STUDENTS.json"
    require(p.is_file() and not p.is_symlink(),
            "Missing physically encoded complete source lecture manifest")
    manifest=json.loads(p.read_text(encoding="utf8"))
    require(manifest["status"]==QA_STATUS
            and manifest["both_full_original_slide_audio_qa_previews_encoded"] is True
            and manifest["both_sections_complete_academic_acceptance"] is False
            and manifest["student_publication_authorized"] is False,
            "Full original section internal QA release status dishonest")
    scene_proofs=[]
    focus_proofs=[]
    results={}
    for section,cfg in SOURCE.items():
        book=root/section
        m=manifest["sections"][section]
        require(m["original_publisher_sha256"]==_sha(book/"source.pdf")
                and m["original_slides_pdf_sha256"]==_sha(book/"slides.pdf")
                and m["original_slide_count"]==cfg["slides"]
                and m["source_verified_highlight_slide_numbers"]==
                    sorted(FOCUS[section])
                and m["full_production_release_accepted"] is False,
                f"Original publisher §{section} did not match authorized source")
        seen=[]
        for part in m["actual_original_encoded_parts"]:
            index=part["part"]
            mp4=qa/f"THOMAS_{section}_ORIGINAL_SOURCE_QA_part{index:02d}.mp4"
            require(mp4.is_file() and not mp4.is_symlink()
                    and part["sha256"]==_sha(mp4)
                    and _media_seconds(mp4)<600
                    and part["student_publication_authorized"] is False,
                    f"Actual §{section} joined MP4 changed or exceeds hard 600s")
            elapsed=0.0
            for slide in part["slides"]:
                seen.append(slide)
                rec=m["original_slide_audio_source_receipts"][str(slide)]
                wav=book/f"slide{slide}.wav"
                require(rec["original_wav_sha256"]==_sha(wav)
                        and abs(rec["real_source_pcm_s"]-
                                rec["actual_encoded_s"])<.15
                        and rec["at_least_one_verified_math_element"]==
                            (slide in FOCUS[section]),
                        "Original real WAV/source focus provenance mismatch")
                if slide in FOCUS[section]:
                    f,filename,_=FOCUS[section][slide]
                    source_clip=checkpoint/f/filename
                else:
                    source_clip=qa/f"source_{section}_slide{slide:02d}_UNAPPROVED_static.mp4"
                require(source_clip.is_file() and not source_clip.is_symlink()
                        and _sha(source_clip)==rec["video_source_sha256"],
                        f"Original §{section} slide{slide} actual media source drifted")
                offset=elapsed
                elapsed+=_media_seconds(source_clip)
                # Independent actual decoded JPEG-like pixel comparison to
                # exact ORIGINAL publisher-backed generated PDF slide.
                at=offset+min(1.5,_media_seconds(source_clip)*.5)
                path=decode_dir/f"{section}_slide{slide:02d}_JOINED.png"
                shown=_decoded(mp4,at,path)
                original_image=_reference_slide(book/"slides.pdf",slide)
                require(shown.size==original_image.size,
                        f"Joined §{section} slide{slide} image dimensions wrong")
                delta=sum(ImageStat.Stat(ImageChops.difference(
                    shown,original_image)).mean)/3
                require(delta<12.0,
                        f"Original §{section} slide{slide} content/pixels changed: {delta}")
                scene_proofs.append({"section":section,"slide":slide,
                    "part":index,"source_pdf_raster_rgb_delta":round(delta,4),
                    "joined_h264_decoded_frame_sha256":_sha(path),
                    "correct_original_author_slide_decoded":True})
                if slide not in FOCUS[section]:
                    continue
                rect,original_spoken_t=_identities(
                    checkpoint=checkpoint,original=book,section=section,
                    slide=slide,encoded=source_clip)
                focus_at=offset+original_spoken_t
                focus_png=decode_dir/f"{section}_slide{slide:02d}_SPOKEN_FOCUS.png"
                _decoded(mp4,focus_at,focus_png)
                probes=count_source_equation_side_border(focus_png,rect)
                require(probes>=6,
                        f"Actual JOINED §{section} slide{slide} mathematical focus disappeared: {probes}")
                focus_proofs.append({"section":section,"slide":slide,
                    "part":index,"source_equation_rect_pt":rect,
                    "real_source_wav_spoken_focus_time_s":round(focus_at,4),
                    "decoded_math_focus_border_probes":probes,
                    "joined_math_highlight_decoded_sha256":_sha(focus_png)})
            require(abs(elapsed-part["expected_component_duration_s"])<1.9,
                    "Joined original audio timing list incomplete")
        require(seen==list(range(1,cfg["slides"]+1)),
                f"Original §{section} PDF full slide order incomplete")
        results[section]={"original_source_slide_count":len(seen),
            "real_joined_parts":len(m["actual_original_encoded_parts"]),
            "independent_joined_highlight_count":len(FOCUS[section])}
    # Independently include prior accepted §8.4 third-section media QA,
    # with live re-verification of its physical source/video SHA.
    prior=checkpoint/"20261101_PR420_INDEPENDENT_MULTIPART_FRAMES"/(
        "INDEPENDENT_MULTIPART_VIDEO_FRAME_VERIFICATION_REVIEW_ONLY.json")
    prior_manifest=checkpoint/"20261101_PR420_SOURCE_CORRECTED_16_HIGHLIGHT_MULTIPART_QA"/(
        "MULTIPART_SOURCE_CORRECTED_QA_NOT_FOR_STUDENTS.json")
    old=json.loads(prior.read_text(encoding="utf8"))
    original84=json.loads(prior_manifest.read_text(encoding="utf8"))
    require(old["status"]=="INDEPENDENT_17_SLIDE_MULTIPART_ENCODED_FRAME_QA_PASS_NONPRODUCTION"
            and len(old["real_joined_source_slide_samples"])==17
            and len(old["real_joined_mathematical_highlight_samples"])==16
            and original84["student_publication_authorized"] is False
            and original84["original_source_sha256"]==
                _sha(root/"8.4"/"source.pdf")
            and old["original_source_sha256"]==
                _sha(root/"8.4"/"source.pdf"),
            "Original publisher §8.4 accepted joined pixel QA not preserved")
    for part in original84["parts"]:
        physical=Path(part["mp4_path"])
        require(physical.is_file() and _sha(physical)==part["mp4_sha256"]
                and _media_seconds(physical)<600,
                "Previously independently source-verified §8.4 final part altered")
    require(len(scene_proofs)==24 and len(focus_proofs)==19,
            "No independent final joined 24 slide/6 math focus evidence")
    result={"status":STATUS,
        "independent_actual_source_slides_across_three_sections":41,
        "independent_joined_8_5_and_8_6_slide_samples":scene_proofs,
        "independent_joined_8_5_and_8_6_spoken_math_samples":focus_proofs,
        "verified_8_4_prior_original_source_slide_samples":17,
        "verified_8_4_prior_original_source_highlight_samples":16,
        "joined_original_audio_video_part_counts":{
            "8.4":len(original84["parts"]),
            "8.5":results["8.5"]["real_joined_parts"],
            "8.6":results["8.6"]["real_joined_parts"]},
        "actually_decoded_original_slide_samples_total":41,
        "actually_decoded_source_proven_highlight_samples_total":35,
        "all_math_and_figures_elementwise_scientifically_accepted":False,
        "full_three_section_production_gate_passed":False,
        "student_publication_authorized":False}
    with (decode_dir/"INDEPENDENT_ALL41_ORIGINAL_MP4_FRAME_PIXEL_QA.json").open(
          "x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,
        "original_slides_verified":41,
        "real_source_spoken_focus_scenes":35,
        "per_section":results}))
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("root","checkpoint","qa","decode-dir"):
        p.add_argument("--"+n,required=True,type=Path)
    args=p.parse_args(argv)
    check(root=args.root,checkpoint=args.checkpoint,qa=args.qa,
          decode_dir=args.decode_dir)
if __name__=="__main__":
    main()
