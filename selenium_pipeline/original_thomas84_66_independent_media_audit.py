"""Independent physical re-audit of both real 66-cue source-PDF §8.4 MP4s.

Reopen original 16 source WAVs, all actual source sample split chips,
both final MP4 AAC streams, and every saved original PDF video frame.
Technical evidence is not semantic source/math acceptance or release.
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
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA, require
from .original_thomas84_66_full_review import REVIEW_STATUS as REAL66_STATUS
from .original_thomas84_66_source_cue_pcm_plan import STATUS as ORIGINAL66_STATUS
from .original_thomas84_slide6_pcm_review import _source_visual
from .offline_original_thomas84_two_part_real_review import _video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

STATUS="TWO_REAL_66_CUE_H264_AAC_MP4S_PHYSICALLY_INDEPENDENTLY_VERIFIED_NO_RELEASE"

def physical_asset(pathstr:str,inside:Path)->Path:
    require(type(pathstr) is str and bool(pathstr),"Empty encoded-media path")
    path=Path(pathstr)
    require(path.is_absolute() and path.is_file()
            and not path.is_symlink()
            and path.resolve().is_relative_to(inside.resolve()),
            "Saved video or reference PDF image outside genuine source bundle")
    return path

def candidate_geometry(plan:dict)->dict:
    visual={}
    total=0
    for slide in plan["source_historical_slides"]:
        number=slide["slide"]
        for evidence in slide["physical_original_pdf_source_targets"]:
            key=(number,evidence["physical_original_pdf_element_id"])
            record=(evidence["physical_source_pdf_text"],
                    evidence["physical_original_pdf_rect_pt"])
            require(key not in visual or visual[key]==record,
                    "Same source PDF ID points to inconsistent math geometry")
            visual[key]=record
            total+=1
    require(total==66 and 30<=len(visual)<=66,
            "Original 66 distinct event count or physical PDF keys not preserved")
    return visual

def audit_two_actual_real_parts(*,original:Path,
                                full_review_receipt:Path,
                                source_plan_receipt:Path,
                                old_corrected_receipt:Path,
                                out:Path)->dict:
    root=Path(original).resolve();source=Path(full_review_receipt).resolve()
    plan_path=Path(source_plan_receipt).resolve()
    corrected_path=Path(old_corrected_receipt).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and all(p.is_file() and not p.is_symlink()
            for p in (source,plan_path,corrected_path))
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "No original source, original evidence, or safe external report destination")
    media=json.loads(source.read_text(encoding="utf8"))
    plan=json.loads(plan_path.read_text(encoding="utf8"))
    corrected=json.loads(corrected_path.read_text(encoding="utf8"))
    require(media.get("status")==REAL66_STATUS
            and plan.get("status")==ORIGINAL66_STATUS
            and media.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and plan.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and media.get("original_pcm_plan_sha256")==file_hash(plan_path)
            and media.get("prior_four_candidate_review_sha256")==
                file_hash(corrected_path)
            and media.get("historical_provisional_source_cue_count")==66
            and media.get("historic_provisional_65_measured_plus_1_title_source_cues") is True
            and media.get("student_release_accepted_mp4_count")==0
            and media.get("student_publication_authorized") is False
            and media.get("full_mathematics_and_source_semantics_approved") is False
            and media.get("all_utterance_element_synchronization_approved") is False
            and plan.get("full_math_source_semantic_verification_approved") is False
            and plan.get("release_eligible") is False
            and plan.get("real_original_WAV_measured_word_intervals")==65
            and plan.get("whole_original_title_WAV_single_utterance_unanchored")==1
            and corrected.get("student_publication_authorized") is False,
            "Contradictory review source or false publication acceptance")
    before=media["source_original_hashes"]
    require(before["source.pdf"]==EXPECTED_SOURCE_SHA
            and all(file_hash(root/name)==sha for name,sha in before.items()),
            "Original protected textbook or lecture material changed")
    visual=candidate_geometry(plan)
    allhist={s["slide"]:s for s in plan["source_historical_slides"]}
    require(set(allhist)==set(range(1,18))-{4},
            "Protected real source WAV inventory must have sixteen")
    corrected_rows=[
        x for x in corrected["real_parts"][0]["all_source_visual_audio_units"]
        if x["source_slide"]==4]
    require(len(corrected_rows)==5,"Five corrected genuine old WAV visual pieces missing")
    corrected_pairs={(x["clip_file"],x["actual_encoded_mp4_sha256"]):x
                     for x in corrected_rows}
    actual_parts=media.get("parts")
    require(type(actual_parts) is list and len(actual_parts)==2
            and [p["original_slide_span"] for p in actual_parts]==[[1,8],[9,17]],
            "Missing source full two-part originals")
    exe=ffmpeg_executable()
    scans=[]
    complete_wavs=set()
    clip_count=0
    frame_count=0
    visual_event_count=0
    slide4_count=0
    media_dir=source.parent
    old_media_dir=corrected_path.parent
    with pymupdf.open(root/"slides.pdf") as deck:
        require(len(deck)==17 and file_hash(root/"slides.pdf")==
                plan["original_slides_pdf_sha256"],
                "Source PDF itself changed")
        for part in actual_parts:
            number=part["part"]
            movie=physical_asset(part["actual_mp4_file"],media_dir)
            require(file_hash(movie)==part["actual_mp4_sha256"],
                    "Real full encoded MP4 checksum differs from PR348 evidence")
            seconds=_mp4_duration(movie,ffmpeg=exe)
            require(0<seconds<600
                    and abs(seconds-part["actual_encoded_duration_s"])<.08,
                    "Encoded real full MP4 is too long or has drifted")
            actual_aac=subprocess.run(
                [exe,"-nostdin","-v","error","-i",str(movie),
                 "-map","0:a:0","-f","null","NUL"],
                capture_output=True,timeout=120)
            require(actual_aac.returncode==0,
                    "Complete encoded H264 MP4 AAC audio stream fails to decode")
            rows=part["original_pdf_real_source_clips"]
            samples=part["actual_decoded_pdf_source_frame_checks"]
            require(type(rows) is list and type(samples) is list
                    and len(rows)==len(samples)>15,
                    "Original source visual/audio encoded clips/frame receipts absent")
            slide_cursor={}
            originals={}
            timestamp=0.
            previously=part["original_slide_span"][0]
            for index,(entry,saved) in enumerate(zip(rows,samples),1):
                slide=entry["source_slide"]
                require(previously<=slide<=part["original_slide_span"][1],
                        "Real source slides not encoded in original order")
                previously=slide
                corrected_slide4=entry["existing_real_slide4_corrected"]
                bundle=old_media_dir if corrected_slide4 else media_dir
                clip=physical_asset(entry["clip_file"],bundle)
                picture=physical_asset(entry["image_file"],bundle)
                require(file_hash(clip)==entry["actual_clip_sha256"]
                        and file_hash(picture)==entry["actual_image_sha256"]
                        and entry["semantics_approved"] is False,
                        "Actual encoded clip, visual or approval status drift")
                target=entry["candidate_target_id"]
                if corrected_slide4:
                    require(slide==4 and number==1
                        and (str(clip),entry["actual_clip_sha256"]) in corrected_pairs,
                        "Previously corrected Slide4 source element was substituted")
                    slide4_count+=1
                else:
                    require(slide!=4 and slide in allhist,
                            "Wrong original protected source historical audio")
                    wav=allhist[slide]
                    if slide not in originals:
                        path=root/f"slide{slide}.wav"
                        require(file_hash(path)==wav["source_wav_sha256"],
                                "Original historic source WAV SHA changed")
                        with wave.open(str(path),"rb") as wavefile:
                            require(wavefile.getframerate()==24000
                                and wavefile.getnchannels()==1
                                and wavefile.getsampwidth()==2
                                and wavefile.getcomptype()=="NONE",
                                "Actual historic source WAV is not required PCM16")
                            originals[slide]=wavefile.readframes(wavefile.getnframes())
                    first=entry["source_first_pcm_sample"]
                    last=entry["source_last_pcm_sample_exclusive"]
                    require(type(first) is int and type(last) is int
                            and first==slide_cursor.get(slide,0)
                            and first<last<=wav["original_source_PCM_total_samples"],
                            "Protected original audio source sample loss, duplication or order error")
                    slide_cursor[slide]=last
                    actual_samples=originals[slide][first*2:last*2]
                    section=media_dir/f"part_{number:02d}"/"actual_source_pcm_chunks"
                    ix=sum(1 for older in rows[:index]
                           if older["source_slide"]==slide
                           and not older["existing_real_slide4_corrected"])
                    physical_wav=section/f"slide{slide:02d}_part{ix:02d}.wav"
                    require(physical_wav.is_file() and not physical_wav.is_symlink()
                            and file_hash(physical_wav)==
                                entry["original_or_split_audio_sha256"],
                            "Actual saved split WAV is missing or mutated")
                    with wave.open(str(physical_wav),"rb") as piece:
                        require(piece.getframerate()==24000
                            and piece.getsampwidth()==2
                            and piece.getnchannels()==1
                            and piece.readframes(piece.getnframes())==actual_samples,
                            "Real encoded clip WAV audio is not exact original PCM samples")
                    rect=None
                    if target is not None:
                        require((slide,target) in visual,
                                "Video highlights nonphysical source PDF target")
                        text,rect=visual[(slide,target)]
                        matches=[b for b in deck[slide-1].get_text("blocks")
                            if b[6]==0 and " ".join(str(b[4]).split())==
                                    " ".join(text.split()) and
                            all(abs(float(b[j])-rect[j])<.12 for j in range(4))]
                        require(len(matches)==1,
                                "Highlighted mathematical text rectangle lost source provenance")
                        visual_event_count+=1
                    recomputed=_source_visual(deck[slide-1],rect)
                    with Image.open(picture) as im:
                        require(im.size==recomputed.size and
                                ImageChops.difference(im.convert("RGB"),recomputed)
                                .getbbox() is None,
                                "Review highlight frame not pixel-matched to original PDF")
                sample_time=timestamp+min(.5,entry["encoded_clip_duration_s"]*.5)
                pixel_error=_video_sample_error(
                    exe=exe,movie=movie,at=sample_time,
                    reference_png=picture)
                require(float(pixel_error)<1.5
                    and saved["source_slide"]==slide
                    and saved["candidate_target_id"]==target
                    and abs(saved["decoded_original_pdf_pixel_error"]-
                            pixel_error)<.20,
                    "Independently decoded original PDF frame mismatch")
                timestamp+=entry["encoded_clip_duration_s"]
                clip_count+=1
                frame_count+=1
            for slide,last in slide_cursor.items():
                require(last==allhist[slide]["original_source_PCM_total_samples"],
                        "Protected historical source WAV not fully represented")
                complete_wavs.add(slide)
            scans.append({
                "part_id":number,"original_slide_span":part["original_slide_span"],
                "actual_encoded_mp4_sha256":file_hash(movie),
                "independent_encoded_duration_s":seconds,
                "original_source_real_clip_checks":len(rows),
                "independently_decoded_final_pdf_frame_checks":len(samples),
                "actual_full_AAC_audio_decode_pass":True,
            })
    require(len(complete_wavs)==16 and visual_event_count==66
            and slide4_count==5 and clip_count==frame_count
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and all(file_hash(root/name)==sha for name,sha in before.items()),
            "Source PCM/full 66 highlight integrity or original preservation failed")
    result={
        "schema_version":1,"status":STATUS,
        "source_original_pdf_sha256":EXPECTED_SOURCE_SHA,
        "pr348_render_receipt_sha256":file_hash(source),
        "pr347_original_source_plan_sha256":file_hash(plan_path),
        "sixteen_protected_historical_source_WAVs_bytewise_verified":True,
        "source_pdf_reverified_provisional_cue_events":visual_event_count,
        "actual_old_slide4_corrected_source_media_count":slide4_count,
        "actual_H264_AAC_clips_SHA_reverified":clip_count,
        "actual_final_MP4_frames_redecoded_from_original_PDF":frame_count,
        "real_full_parts":scans,
        "full_spoken_math_semantic_equivalence_approved":False,
        "all_66_source_math_accepted":False,
        "student_publication_authorized":False,
        "student_release_accepted_videos":0,
    }
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    return result

def main():
    parser=argparse.ArgumentParser()
    for key in ("original","full_review_receipt","source_plan_receipt",
                "old_corrected_receipt","out"):
        parser.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    outcome=audit_two_actual_real_parts(**vars(parser.parse_args()))
    print(json.dumps(outcome,indent=2))
if __name__=="__main__":main()
