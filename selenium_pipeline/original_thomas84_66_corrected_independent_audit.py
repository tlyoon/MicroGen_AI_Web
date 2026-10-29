"""Second-pass independent real H264/AAC/PCM/PDF audit after ten math fixes.

Each corrected original-source focus must be recreated from original PDF
blocks. Unchanged 96 physical clips must match the prior independently
audited source. Neither pass certifies full spoken-math semantic meaning.
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
from .original_thomas84_66_selective_math_reencode import (
    STATUS as CORRECTED_STATUS,physically_exact_source_composite)
from .original_thomas84_66_full_review import REVIEW_STATUS as OLD_STATUS
from .original_thomas84_composite_source_semantic_corrections import (
    STATUS as MATH_STATUS)
from .original_thomas84_slide6_pcm_review import _source_visual
from .offline_original_thomas84_two_part_real_review import _video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

STATUS="TWO_ACTUAL_CORRECTED_ORIGINAL_8_4_MP4S_INDEPENDENT_PHYSICAL_AUDIT_RELEASE_BLOCKED"

def existing_file(path:str,allowed:Path)->Path:
    require(isinstance(path,str) and bool(path),"No actual source file path")
    x=Path(path)
    require(x.is_absolute() and x.is_file() and not x.is_symlink()
            and x.resolve().is_relative_to(allowed.resolve()),
            "Physical audio/PDF/MP4 file missing or outside approved source bundle")
    return x

def audit_corrected(*,original:Path,corrected_review:Path,
                    prior_review:Path,prior_independent_audit:Path,
                    math_corrections:Path,original_plan:Path,out:Path)->dict:
    root=Path(original).resolve()
    files=[Path(f).resolve() for f in
           (corrected_review,prior_review,prior_independent_audit,
            math_corrections,original_plan)]
    destination=Path(out).absolute()
    require(root.is_dir() and all(p.is_file() and not p.is_symlink()
            for p in files) and destination.parent.is_dir()
            and not destination.exists()
            and not destination.is_relative_to(root.parent),
            "Protected actual original/media receipts or exclusive output missing")
    cp,pp,ap,mp,sp=files
    corrected,old,audit,math,plan=[
        json.loads(p.read_text(encoding="utf8")) for p in files]
    require(corrected.get("status")==CORRECTED_STATUS
            and old.get("status")==OLD_STATUS
            and math.get("status")==MATH_STATUS
            and audit.get("status")==
                "TWO_REAL_66_CUE_H264_AAC_MP4S_PHYSICALLY_INDEPENDENTLY_VERIFIED_NO_RELEASE"
            and corrected.get("original_source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and corrected.get("source_pr348_real_mp4_receipt_sha256")==file_hash(pp)
            and corrected.get("source_pr349_independent_real_media_audit_sha256")==file_hash(ap)
            and corrected.get("source_pr350_mathematical_corrections_sha256")==file_hash(mp)
            and math.get("original_66_source_cue_plan_sha256")==file_hash(sp)
            and audit.get("pr348_render_receipt_sha256")==file_hash(pp)
            and old.get("original_pcm_plan_sha256")==file_hash(sp)
            and corrected.get("actually_reencoded_original_source_composite_corrections")==10
            and corrected.get("physically_unchanged_other_real_source_clips_reused")==96
            and corrected.get("actual_real_H264_final_source_frames_decoded")==106
            and all(r.get("student_publication_authorized") is False
                    for r in (corrected,old,audit,math,plan))
            and corrected.get("student_release_accepted_videos")==0
            and corrected.get("academic_source_math_66_spoken_elements_approved") is False
            and math.get("source_mathematical_equivalence_for_all_66_approved") is False,
            "Untrusted input or false academic-release promotion")
    original_hashes=old["source_original_hashes"]
    require(original_hashes["source.pdf"]==EXPECTED_SOURCE_SHA
            and all(file_hash(root/name)==sha for name,sha in original_hashes.items()),
            "Original protected PDF/script/WAV/media changed")
    require(len(old["parts"])==len(corrected["parts"])==2
            and [r["part"] for r in corrected["parts"]]==[1,2],
            "Original two complete movies missing")
    corrections={(p["slide"],p["sentence_index"]):p
                 for p in math["corrected_original_pdf_composite_focuses"]}
    require(len(corrections)==10,"Original composite focus math correction inventory drift")
    historic={s["slide"]:s for s in plan["source_historical_slides"]}
    require(set(historic)==set(range(1,18))-{4},
            "Original protected 16 PCM WAV source inventory changed")
    media_dir=cp.parent
    original_review_dir=pp.parent
    ffmpeg=ffmpeg_executable()
    summary=[]
    changed_count=unchanged_count=source_frames=0
    full_wavs=set()
    corrected_keys=set()
    slide4_count=0
    with pymupdf.open(root/"slides.pdf") as deck:
        require(len(deck)==17 and file_hash(root/"slides.pdf")==
                plan["original_slides_pdf_sha256"],
                "Protected source slide PDF changed")
        for part,baseline in zip(corrected["parts"],old["parts"]):
            index=part["part"]
            movie=existing_file(part["actual_mp4_file"],media_dir)
            require(file_hash(movie)==part["actual_mp4_sha256"],
                    "Actual corrected full MP4 hash differs from receipt")
            duration=_mp4_duration(movie,ffmpeg=ffmpeg)
            require(0<duration<600 and
                    abs(duration-part["actual_encoded_duration_s"])<.09,
                    "Corrected actual MP4 duration drift or >=600s")
            decoded=subprocess.run(
                [ffmpeg,"-nostdin","-v","error","-i",str(movie),
                 "-map","0:a:0","-f","null","NUL"],
                timeout=120,capture_output=True)
            require(decoded.returncode==0,"Corrected complete AAC audio decoder failed")
            current=part["all_real_source_clip_records"]
            previous=baseline["original_pdf_real_source_clips"]
            saved=part["actual_decoded_source_pdf_frame_checks"]
            require(len(current)==len(previous)==len(saved)>10,
                    "Corrected H264 source clips or sampled PDF frames missing")
            sources={}
            slide_cursors={}
            visual_cursor=0.0
            for rowno,(item,oldrow,receipt) in enumerate(zip(current,previous,saved)):
                slide=item["source_slide"]
                changed=item["physically_original_composite_corrected"] is True
                require(item["semantics_approved"] is False
                        and oldrow["semantics_approved"] is False
                        and slide==oldrow["source_slide"]
                        and item["source_first_pcm_sample"]==
                            oldrow["source_first_pcm_sample"]
                        and item["source_last_pcm_sample_exclusive"]==
                            oldrow["source_last_pcm_sample_exclusive"]
                        and item["existing_real_slide4_corrected"]==
                            oldrow["existing_real_slide4_corrected"],
                        "Actual source audio sample index, clip order, semantics drift")
                if slide==4:
                    # The five genuinely corrected source clips were reused
                    # from immutable PR333, not the PR348 video directory.
                    # Require that exact source bundle identity, and compare
                    # all file hashes against independently audited PR348.
                    oldclip=Path(oldrow["clip_file"])
                    require(not changed and
                            oldclip.parents[2].name==
                            "20261028_PR333_TWO_REAL_THOMAS84_WORD_TIMED_FOUR_PROVISIONAL_PDF_HIGHLIGHTS_REVIEW",
                            "Slide4 correction clip is not original PR333 media")
                    allowed=oldclip.parents[2]
                else:
                    allowed=media_dir if changed else original_review_dir
                clip=existing_file(item["clip_file"],allowed)
                visual=existing_file(item["image_file"],allowed)
                require(file_hash(clip)==item["actual_clip_sha256"]
                        and file_hash(visual)==item["actual_image_sha256"],
                        "Physical corrected/unchanged source clip or original image drift")
                if changed:
                    original_id=item["candidate_target_id"]
                    require(slide!=4 and original_id.startswith(
                            f"s{slide:03d}.composite_source_math_fix."),
                            "Corrected source PDF video segment misidentified")
                    n=int(original_id.rsplit(".",1)[-1])
                    key=(slide,n)
                    require(key in corrections and key not in corrected_keys,
                            "Original source math correction missing/duplicated")
                    fix=corrections[key]
                    require(oldrow["candidate_target_id"]==
                            fix["superseded_review_only_pdf_element_id"],
                            "Wrong-context source PDF original cue not actually replaced")
                    rect=physically_exact_source_composite(deck[slide-1],fix)
                    expected_image=_source_visual(deck[slide-1],rect)
                    with Image.open(visual) as saved_image:
                        require(saved_image.size==expected_image.size
                                and ImageChops.difference(
                                    saved_image.convert("RGB"),expected_image
                                ).getbbox() is None,
                                "Corrected mathematical source focus image not original-PDF-pixel reproducible")
                    corrected_keys.add(key)
                    changed_count+=1
                else:
                    require(item["clip_file"]==oldrow["clip_file"]
                            and item["image_file"]==oldrow["image_file"]
                            and item["actual_clip_sha256"]==
                                oldrow["actual_clip_sha256"]
                            and item["actual_image_sha256"]==
                                oldrow["actual_image_sha256"]
                            and file_hash(clip)==oldrow["actual_clip_sha256"],
                            "Unchanged clip was re-encoded or replaced without authorization")
                    unchanged_count+=1
                if slide==4:
                    require(not changed and index==1,"Corrected Slide4 WAV must be preserved")
                    slide4_count+=1
                else:
                    require(slide in historic,"Original source historic slide missing")
                    if slide not in sources:
                        historical=root/f"slide{slide}.wav"
                        require(file_hash(historical)==historic[slide]["source_wav_sha256"],
                                "Actual protected historical WAV SHA mismatch")
                        with wave.open(str(historical),"rb") as origin:
                            require(origin.getnchannels()==1
                                    and origin.getsampwidth()==2
                                    and origin.getframerate()==24000
                                    and origin.getcomptype()=="NONE",
                                    "Original real WAV not PCM16/24k mono")
                            sources[slide]=origin.readframes(origin.getnframes())
                    first=item["source_first_pcm_sample"]
                    last=item["source_last_pcm_sample_exclusive"]
                    require(type(first) is int and type(last) is int
                            and first==slide_cursors.get(slide,0)
                            and first<last<=historic[slide]["original_source_PCM_total_samples"],
                            "Corrected media has dropped/reordered audio source PCM")
                    slide_cursors[slide]=last
                    chunk=sources[slide][2*first:2*last]
                    oldclip=Path(oldrow["clip_file"])
                    piece=oldclip.stem.rsplit("piece",1)[-1]
                    require(piece.isdigit(),"Prior actual source PCM chip identifier drift")
                    wav=original_review_dir/f"part_{index:02d}"/"actual_source_pcm_chunks"/(
                        f"slide{slide:02d}_part{int(piece):02d}.wav")
                    require(wav.is_file() and not wav.is_symlink()
                            and file_hash(wav)==item["original_or_split_audio_sha256"]
                            and item["original_or_split_audio_sha256"]==
                                oldrow["original_or_split_audio_sha256"],
                            "Original correction lost exact protected WAV sample chip")
                    with wave.open(str(wav),"rb") as audio:
                        require(audio.getnchannels()==1
                            and audio.getsampwidth()==2
                            and audio.getframerate()==24000
                            and audio.readframes(audio.getnframes())==chunk,
                            "Physical actual corrected clip audio not exact original source sample bytes")
                when=visual_cursor+min(.5,item["encoded_clip_duration_s"]*.5)
                pixel_error=_video_sample_error(exe=ffmpeg,movie=movie,
                                                at=when,reference_png=visual)
                require(float(pixel_error)<1.5
                    and receipt["source_slide"]==slide
                    and receipt["source_candidate_id"]==item["candidate_target_id"]
                    and receipt["source_composite_corrected"] is changed
                    and abs(float(receipt["actual_decoded_PDF_source_frame_error"])-
                            float(pixel_error))<.2,
                    "Actual corrected final MP4 H264 frame not independently reproducible")
                visual_cursor+=item["encoded_clip_duration_s"]
                source_frames+=1
            for slide,last in slide_cursors.items():
                require(last==historic[slide]["original_source_PCM_total_samples"],
                        "Entire original historic WAV not represented in corrected media")
                full_wavs.add(slide)
            require(file_hash(Path(baseline["actual_mp4_file"]))==
                    baseline["actual_mp4_sha256"],
                    "Former independently audited MP4 corrupted during correction")
            summary.append({
                "part":index,"independent_actual_duration_seconds":duration,
                "actual_corrected_full_mp4_sha256":file_hash(movie),
                "physical_media_clips_checked":len(current),
                "independently_decoded_final_source_PDF_frames":len(saved),
                "whole_actual_AAC_audio_stream_decoded":True,
            })
    require(changed_count==10 and unchanged_count==96
            and len(corrected_keys)==10 and source_frames==106
            and len(full_wavs)==16 and slide4_count==5
            and all(file_hash(root/name)==sha
                    for name,sha in original_hashes.items()),
            "Corrected full source video audit failed original sample/source preservation")
    result={
      "schema_version":1,"status":STATUS,
      "source_original_pdf_sha256":EXPECTED_SOURCE_SHA,
      "corrected_review_receipt_sha256":file_hash(cp),
      "prior_independently_audited_media_receipt_sha256":file_hash(ap),
      "original_math_source_composite_corrections_sha256":file_hash(mp),
      "sixteen_original_WAVs_PCM_exactly_reverified":True,
      "physically_corrected_source_math_clips":changed_count,
      "unchanged_verified_prior_source_clips":unchanged_count,
      "corrected_existing_slide4_source_clips_preserved":slide4_count,
      "original_pdf_frames_independently_decoded":source_frames,
      "actual_MP4_parts_independently_verified":summary,
      "complete_academic_source_math_semantic_equivalence_accepted":False,
      "all_original_66_utterances_academically_approved":False,
      "release_eligible":False,"student_publication_authorized":False,
      "student_release_accepted_videos":0,
    }
    with destination.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for field in ("original","corrected_review","prior_review",
                  "prior_independent_audit","math_corrections",
                  "original_plan","out"):
        p.add_argument("--"+field.replace("_","-"),type=Path,required=True)
    r=audit_corrected(**vars(p.parse_args()))
    print(json.dumps(r,indent=2))
if __name__=="__main__":main()
