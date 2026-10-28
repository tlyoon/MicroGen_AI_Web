"""Independent, fail-closed physical audit of two complete §8.4 review MP4s.

Reopen original 16 WAVs, compare all original source PCM slices bytewise,
reconstruct final original-PDF raster visuals from genuine page geometry,
rehash all encoded clip/video data, decode both complete AAC streams and
independently sample actual final H264 frames. NEVER approve semantics.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import wave
from pathlib import Path

import pymupdf
from PIL import Image,ImageChops

from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_slide6_pcm_review import _source_visual
from .original_thomas84_29_full_review import REVIEW_STATUS
from .offline_original_thomas84_two_part_real_review import _video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

def _within(pathstr:str,allowed:Path)->Path:
    require(isinstance(pathstr,str) and bool(pathstr),"Missing actual media path")
    p=Path(pathstr)
    require(p.is_absolute() and p.is_file() and not p.is_symlink()
            and p.resolve().is_relative_to(allowed.resolve()),
            "Media path outside actual saved source review directory")
    return p

def audit_full_real_review(*,original:Path,review_receipt:Path,
                           sample_receipt:Path,candidate_receipt:Path,
                           old_review_receipt:Path,out:Path)->dict:
    root=Path(original).resolve()
    receipt=Path(review_receipt).resolve()
    sample=Path(sample_receipt).resolve()
    candidate=Path(candidate_receipt).resolve()
    earlier=Path(old_review_receipt).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and all(p.is_file() and not p.is_symlink()
            for p in (receipt,sample,candidate,earlier))
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Genuine source, reviews or external exclusive output missing")
    live=json.loads(receipt.read_text(encoding="utf8"))
    plan=json.loads(sample.read_text(encoding="utf8"))
    candidates=json.loads(candidate.read_text(encoding="utf8"))
    previous=json.loads(earlier.read_text(encoding="utf8"))
    require(live.get("status")==REVIEW_STATUS
            and live.get("schema_version")==1
            and live.get("historical_visual_candidate_count")==29
            and live.get("corrected_slide4_real_pcm_visual_count")==5
            and live.get("student_publication_authorized") is False
            and live.get("full_mathematics_and_source_semantics_approved") is False
            and live.get("all_utterance_element_synchronization_approved") is False
            and live.get("student_release_accepted_mp4_count")==0
            and live.get("new_tts_provider_requests")==0
            and live.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and live.get("original_pcm_plan_sha256")==file_hash(sample)
            and live.get("prior_four_candidate_review_sha256")==file_hash(earlier)
            and plan.get("actual_source_pdf_acoustic_candidates")==29
            and plan.get("student_publication_authorized") is False
            and candidates.get("student_publication_authorized") is False
            and previous.get("student_publication_authorized") is False,
            "False release or incompatible original source evidence")
    protected=live["source_original_hashes"]
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and all(file_hash(root/name)==h for name,h in protected.items()),
            "Protected original textbook/audio/video changed")
    actual_source = {s["slide"]:s for s in plan["historical_slides"]}
    require(set(actual_source)==set(range(1,18))-{4},
            "Sixteen historical PCM original slide receipts missing")
    target_rect={}
    candidate_utterances=0
    for slide in candidates["slides"]:
        for row in slide["candidate_segments"]:
            if row.get("unique_target_review_priority"):
                item=row["candidate_targets"][0]
                key=(slide["slide"],item["original_pdf_element_id"])
                rect=item["source_pdf_rect_pt"]
                require(key not in target_rect or target_rect[key]==rect,
                        "The same real PDF block was assigned conflicting rectangles")
                target_rect[key]=rect
                candidate_utterances+=1
    # Multiple acoustic utterances can legitimately highlight the SAME
    # visible PDF block; 29 is a count of sentence candidates, not boxes.
    require(candidate_utterances==29 and 15<=len(target_rect)<=29,
            "29 acoustically timed original PDF sentence candidates are missing")
    movie_parts=live.get("parts")
    require(type(movie_parts) is list and len(movie_parts)==2
            and [part.get("original_slide_span") for part in movie_parts]==[[1,8],[9,17]],
            "Exactly two original two-part real videos required")
    actual_receipt_dir=receipt.parent
    prior_dir=earlier.parent
    exe=ffmpeg_executable()
    candidate_count=0
    corrected_count=0
    verified_pcm_slides=set()
    actual_clips=0
    actual_decoded=0
    summaries=[]
    with pymupdf.open(root/"slides.pdf") as deck:
        require(len(deck)==17, "Original full PDF pages altered")
        for part in movie_parts:
            movie=_within(part["actual_mp4_file"],actual_receipt_dir)
            require(file_hash(movie)==part["actual_mp4_sha256"],
                    "Actually encoded final MP4 SHA mismatch")
            duration=_mp4_duration(movie,ffmpeg=exe)
            require(0<duration<600
                    and abs(duration-part["actual_encoded_duration_s"])<=.08,
                    "Real encoded media duration stale or >600s")
            decoded_aac=subprocess.run(
                [exe,"-nostdin","-v","error","-i",str(movie),
                 "-map","0:a:0","-f","null","NUL"],
                capture_output=True,timeout=120)
            require(decoded_aac.returncode==0,
                    "Real final MP4 AAC stream undecodable")
            rows=part["original_pdf_real_source_clips"]
            recorded=part["actual_decoded_pdf_source_frame_checks"]
            require(type(rows) is list and type(recorded) is list
                    and len(rows)==len(recorded)>10,
                    "Real media visual chip/frame inventory incomplete")
            scan_cursor=0.
            current_slide=part["original_slide_span"][0]
            per_slide_sample_cursor={}
            source_chunks={}
            for i,(row,claim) in enumerate(zip(rows,recorded),1):
                slide=row["source_slide"]
                require(current_slide<=slide<=part["original_slide_span"][1],
                        "Real video source slide out of original order")
                current_slide=slide
                corrected=bool(row["existing_real_slide4_corrected"])
                folder=prior_dir if corrected else actual_receipt_dir
                clip=_within(row["clip_file"],folder)
                picture=_within(row["image_file"],folder)
                require(file_hash(clip)==row["actual_clip_sha256"]
                        and file_hash(picture)==row["actual_image_sha256"]
                        and row["semantics_approved"] is False,
                        "Actual encoded source media clip/image untrusted")
                cand=row["candidate_target_id"]
                if corrected:
                    require(slide==4 and cand and
                            part["part"]==1,"Wrong corrected historic Slide4 re-use")
                    corrected_count+=1
                else:
                    require(slide!=4 and slide in actual_source,
                            "Incorrect original source historical slide number")
                    first=row["source_first_pcm_sample"]
                    last=row["source_last_pcm_sample_exclusive"]
                    cursor=per_slide_sample_cursor.get(slide,0)
                    require(type(first) is int and type(last) is int
                            and first==cursor and first<last
                            and last<=actual_source[slide]["original_pcm_total_samples"],
                            "Actual original PCM source samples missing or reordered")
                    per_slide_sample_cursor[slide]=last
                    if slide not in source_chunks:
                        originalwav=root/f"slide{slide}.wav"
                        require(file_hash(originalwav)==actual_source[slide][
                            "original_pcm_sha256"],
                            "Historical original WAV SHA changed")
                        with wave.open(str(originalwav),"rb") as sourcewave:
                            require(sourcewave.getframerate()==24000
                                and sourcewave.getnchannels()==1
                                and sourcewave.getsampwidth()==2,
                                "Actual old WAV has wrong PCM layout")
                            source_chunks[slide]=sourcewave.readframes(
                                sourcewave.getnframes())
                    originalpcm=source_chunks[slide]
                    segment=originalpcm[2*first:2*last]
                    pcm_folder=actual_receipt_dir/f"part_{part['part']:02d}"/"actual_source_pcm_chunks"
                    index=sum(1 for earlier_row in rows[:i]
                              if earlier_row["source_slide"]==slide and
                              not earlier_row["existing_real_slide4_corrected"])
                    chipfile=pcm_folder/f"slide{slide:02d}_part{index:02d}.wav"
                    require(chipfile.is_file() and not chipfile.is_symlink()
                            and file_hash(chipfile)==row["original_or_split_audio_sha256"],
                            "Actual physical PCM chip absent/stale")
                    with wave.open(str(chipfile),"rb") as chip:
                        require(chip.getframerate()==24000
                            and chip.getnchannels()==1
                            and chip.getsampwidth()==2
                            and chip.readframes(chip.getnframes())==segment,
                            "Actual source original PCM chip does not match byte-for-byte")
                    # independently reconstruct original PDF pixels for each
                    # visible element; no OCR, semantic inference or repaint.
                    rect=target_rect.get((slide,cand)) if cand is not None else None
                    require(cand is None or rect is not None,
                            "Provisional rectangle not in real original source evidence")
                    recomputed=_source_visual(deck[slide-1],rect)
                    with Image.open(picture) as refimage:
                        require(refimage.size==recomputed.size and
                            ImageChops.difference(refimage.convert("RGB"),
                                                 recomputed).getbbox() is None,
                            "Visual pixel frame cannot be recreated from original PDF")
                    candidate_count+=bool(cand is not None)
                sample_time=scan_cursor+min(.5,
                    row["encoded_clip_duration_s"]*.5)
                actual_error=_video_sample_error(
                    exe=exe,movie=movie,at=sample_time,
                    reference_png=picture)
                require(float(actual_error)<1.5
                    and claim["source_slide"]==slide
                    and claim["candidate_target_id"]==cand
                    and abs(float(claim["decoded_original_pdf_pixel_error"])-
                            float(actual_error))<.20,
                    "Re-decoded actual final H264 frame does not match source PDF")
                scan_cursor+=row["encoded_clip_duration_s"]
                actual_clips+=1
                actual_decoded+=1
            for slide,frames in per_slide_sample_cursor.items():
                require(frames==actual_source[slide]["original_pcm_total_samples"],
                        "Full original protected WAV not covered by source PCM chips")
                verified_pcm_slides.add(slide)
            summaries.append({"part":part["part"],"duration_s":duration,
                "mp4_sha256":part["actual_mp4_sha256"],
                "physical_real_encoded_clips":len(rows),
                "independent_final_decoded_pdf_frames":len(recorded),
                "real_aac_stream_decodable":True})
    require(candidate_count==29 and corrected_count==5
            and len(verified_pcm_slides)==16
            and actual_clips==actual_decoded
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and all(file_hash(root/name)==h for name,h in protected.items()),
            "Original multimedia source full-coverage or protected hashes changed")
    result={"schema_version":1,
        "status":"TWO_REAL_FULL_8_4_MP4S_29_CANDIDATES_INDEPENDENTLY_REAUDITED_NO_RELEASE",
        "original_source_sha256":EXPECTED_SOURCE_SHA,
        "source_review_receipt_sha256":file_hash(receipt),
        "all_16_original_PCM_WAVs_byte_verified":True,
        "real_provisional_original_pdf_highlights_reverified":candidate_count,
        "real_new_corrected_slide4_highlights_reverified":corrected_count,
        "actual_encoded_video_clips_rehashed":actual_clips,
        "actual_final_mp4_source_pdf_frames_independently_decoded":actual_decoded,
        "verified_original_mp4_parts":summaries,
        "full_academic_source_math_review_approved":False,
        "full_spoken_element_synchronization_approved":False,
        "student_publication_authorized":False,
        "student_release_accepted_videos":0}
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    a=argparse.ArgumentParser()
    for k in ("original","review_receipt","sample_receipt","candidate_receipt",
              "old_review_receipt","out"):
        a.add_argument("--"+k.replace("_","-"),type=Path,required=True)
    result=audit_full_real_review(**vars(a.parse_args()))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
