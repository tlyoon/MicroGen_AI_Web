"""Encode two complete real Thomas §8.4 PDF/PCM REVIEW MP4s with 29 candidates.

Existing five corrected Slide4 clips are re-used by exact SHA/physical
path; all 16 old slide WAVs are split from original PCM samples only.
Every frame warns REVIEW ONLY. No semantic acceptance or publication.
"""
from __future__ import annotations
import argparse
import json
import wave
from pathlib import Path

import pymupdf
from .element_plan_autodraft import file_hash
from .original_thomas84_all_historical_pcm_plan import STEM,require
from .original_thomas84_slide6_pcm_review import _source_visual
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA
from .offline_original_thomas84_two_part_real_review import WIDTH,HEIGHT,FPS,ff,_video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

REVIEW_STATUS="TWO_REAL_FULL_8_4_VIDEOS_29_HISTORIC_PDF_CANDIDATES_REVIEW_ONLY"
PR333_STATUS="TWO_REAL_ORIGINAL_8_4_VIDEOS_FOUR_MORE_ACOUSTIC_PDF_HIGHLIGHTS_REVIEW_ONLY"

def stabilized_windows(rows:list[dict])->list[dict]:
    """Merge tiny front silent span into first highlight without losing a sample."""
    r=[dict(x) for x in rows]
    require(bool(r) and r[0]["first_pcm_sample"]==0,
            "Missing actual first sample")
    if len(r)>1 and r[0]["provisional_pdf_target"] is None and (
        r[0]["last_pcm_sample_exclusive"]-r[0]["first_pcm_sample"]<4800):
        r[1]["first_pcm_sample"]=0
        r[1]["includes_unmapped_leading_samples"]=True
        r.pop(0)
    require(all(a["last_pcm_sample_exclusive"]==b["first_pcm_sample"]
                for a,b in zip(r,r[1:])), "Stabilized original PCM boundaries overlap")
    return r

def _safe_file(name:str,root:Path)->Path:
    p=Path(name)
    require(p.is_absolute() and p.is_file() and not p.is_symlink()
            and p.resolve().is_relative_to(root.resolve()),
            "Old real review asset is absent or outside protected review bundle")
    return p

def encode_two_review_parts(*,original:Path,plan_receipt:Path,
                            old_review_receipt:Path,out:Path)->dict:
    root=Path(original).resolve(); plan_path=Path(plan_receipt).resolve()
    oldpath=Path(old_review_receipt).resolve(); dest=Path(out).absolute()
    require(root.is_dir() and plan_path.is_file() and oldpath.is_file()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent)
            and not dest.is_relative_to(oldpath.parent),
            "External exclusive output; preserve all old media/originals")
    plan=json.loads(plan_path.read_text(encoding="utf8"))
    old=json.loads(oldpath.read_text(encoding="utf8"))
    require(plan.get("status")==STEM
            and plan.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and plan.get("actual_source_pdf_acoustic_candidates")==29
            and plan.get("student_publication_authorized") is False
            and plan.get("full_lecture_semantics_approved") is False
            and old.get("status")==PR333_STATUS
            and old.get("student_publication_authorized") is False
            and old.get("five_corrected_slide4_actual_PCM_source_highlights")==5
            and old.get("original_source_sha256")==EXPECTED_SOURCE_SHA,
            "Original complete source or visual plan not proven")
    expected=old["protected_original_hashes"]
    require(len(expected)>0 and all(file_hash(root/name)==sha
            for name,sha in expected.items())
            and expected["source.pdf"]==EXPECTED_SOURCE_SHA
            and plan["original_slides_pdf_sha256"]==file_hash(root/"slides.pdf"),
            "Protected PDF/script/video assets changed")
    previous_parts=old["real_parts"]
    require(len(previous_parts)==2 and
            [p["original_slide_span"] for p in previous_parts]==[[1,8],[9,17]],
            "Not the two genuine original review partitions")
    original_slide4=[
        p for p in previous_parts[0]["all_source_visual_audio_units"]
        if p["source_slide"]==4]
    require(len(original_slide4)==5
            and all(p.get("candidate_target_id") for p in original_slide4),
            "Five corrected original Slide4 source pieces absent")
    old_root=oldpath.parent
    for p in original_slide4:
        _safe_file(p["clip_file"],old_root)
        _safe_file(p["image_file"],old_root)
        require(file_hash(Path(p["clip_file"]))==p["actual_encoded_mp4_sha256"]
            and file_hash(Path(p["image_file"]))==p["candidate_visual_frame_sha256"],
            "Existing genuine corrected Slide4 encoded media was changed")
    all_hist={s["slide"]:s for s in plan["historical_slides"]}
    require(set(all_hist)==set(range(1,18))-{4},
            "Original sixteen historical slide plan incomplete")
    exe=ffmpeg_executable()
    dest.mkdir()
    pics=dest/"original_pdf_review_images"
    pics.mkdir()
    final_parts=[]
    count=0
    with pymupdf.open(root/"slides.pdf") as deck:
        require(len(deck)==17,"Original PDF slide count changed")
        for part_no,(first,last) in enumerate(((1,8),(9,17)),1):
            section=dest/f"part_{part_no:02d}"
            section.mkdir()
            clips=section/"actual_source_encoded_clips";clips.mkdir()
            wavs=section/"actual_source_pcm_chunks";wavs.mkdir()
            source_row=[]
            clip_seq=[]
            for slide in range(first,last+1):
                if slide==4:
                    for source in original_slide4:
                        source_row.append({
                            "source_slide":4,
                            "audio_file":source.get("source_pcm_file","CORRECTED_SLIDE4_REAL_WAV"),
                            "clip_file":source["clip_file"],
                            "image_file":source["image_file"],
                            "candidate_target_id":source["candidate_target_id"],
                            "source_first_pcm_sample":source["source_sample_first"],
                            "source_last_pcm_sample_exclusive":source["source_sample_end"],
                            "original_or_split_audio_sha256":source["original_or_split_audio_sha256"],
                            "actual_clip_sha256":source["actual_encoded_mp4_sha256"],
                            "actual_image_sha256":source["candidate_visual_frame_sha256"],
                            "encoded_clip_duration_s":source["encoded_actual_duration_s"],
                            "semantics_approved":False,
                            "existing_real_slide4_corrected":True})
                        clip_seq.append(Path(source["clip_file"]))
                    continue
                info=all_hist[slide]
                originalwav=root/f"slide{slide}.wav"
                require(file_hash(originalwav)==info["original_pcm_sha256"],
                        "Historical original WAV changed during encoding")
                with wave.open(str(originalwav),"rb") as h:
                    require(h.getframerate()==24000 and h.getnchannels()==1
                            and h.getsampwidth()==2 and h.getcomptype()=="NONE",
                            "Original PCM format changed")
                    pcm=h.readframes(h.getnframes())
                require(len(pcm)==info["original_pcm_total_samples"]*2,
                        "Real original PCM incomplete")
                timeline=stabilized_windows(info["sample_exact_timeline"])
                sourcepix=deck[slide-1]
                static=pics/f"slide{slide:02d}_original_STATIC_REVIEW_ONLY.png"
                _source_visual(sourcepix).save(static)
                pix={None:static}
                for fragment in timeline:
                    target=fragment["provisional_pdf_target"]
                    if target is None or target in pix:
                        continue
                    # Source box identified via the exact candidate ledger,
                    # never OCR or fabricated image coordinates.
                    source_candidates=Path(plan_path).parent/"20261028_PR335_REAL_THOMAS84_PDF_SEMANTIC_TARGET_WORKLIST_UNAPPROVED_V2.json"
                    require(source_candidates.is_file() and
                            file_hash(source_candidates)==plan["source_candidate_receipt_sha256"],
                            "Source-PDF candidate receipt changed or absent")
                    cand=json.loads(source_candidates.read_text(encoding="utf8"))
                    source_segment=next(x for t in cand["slides"] if t["slide"]==slide
                        for x in t["candidate_segments"]
                        if x["unique_target_review_priority"]
                        and x["candidate_targets"][0]["original_pdf_element_id"]==target)
                    rect=source_segment["candidate_targets"][0]["source_pdf_rect_pt"]
                    picture=pics/f"slide{slide:02d}_{target.replace('.','_')}_PROVISIONAL.png"
                    _source_visual(sourcepix,rect).save(picture)
                    pix[target]=picture
                cursor=0
                for idx,row in enumerate(timeline,1):
                    start=row["first_pcm_sample"]
                    finish=row["last_pcm_sample_exclusive"]
                    require(start==cursor and start<finish<=len(pcm)//2,
                            "Actual full original WAV samples missing/overlapping")
                    soundbytes=pcm[start*2:finish*2]
                    outwav=wavs/f"slide{slide:02d}_part{idx:02d}.wav"
                    with wave.open(str(outwav),"wb") as chip:
                        chip.setnchannels(1);chip.setsampwidth(2)
                        chip.setframerate(24000);chip.writeframes(soundbytes)
                    clip=clips/f"source_slide{slide:02d}_piece{idx:02d}.mp4"
                    ff(exe,["-n","-loop","1","-framerate",str(FPS),
                        "-i",str(pix[row["provisional_pdf_target"]]),
                        "-i",str(outwav),"-map","0:v:0","-map","1:a:0",
                        "-c:v","libx264","-preset","ultrafast","-crf","23",
                        "-pix_fmt","yuv420p","-r",str(FPS),
                        "-c:a","aac","-b:a","96k",
                        "-t",f"{len(soundbytes)/48000:.8f}",
                        "-shortest","-movflags","+faststart",str(clip)],timeout=180)
                    encoded=_mp4_duration(clip,ffmpeg=exe)
                    require(0<encoded<180 and abs(encoded-len(soundbytes)/48000)<.2,
                            "True audio source chip H264/AAC duration drift")
                    item={"source_slide":slide,"clip_file":str(clip),
                        "image_file":str(pix[row["provisional_pdf_target"]]),
                        "candidate_target_id":row["provisional_pdf_target"],
                        "source_first_pcm_sample":start,
                        "source_last_pcm_sample_exclusive":finish,
                        "actual_clip_sha256":file_hash(clip),
                        "actual_image_sha256":file_hash(pix[row["provisional_pdf_target"]]),
                        "original_or_split_audio_sha256":file_hash(outwav),
                        "encoded_clip_duration_s":encoded,
                        "semantics_approved":False,
                        "existing_real_slide4_corrected":False}
                    source_row.append(item)
                    clip_seq.append(clip)
                    cursor=finish
                    count+=bool(row["provisional_pdf_target"] is not None)
                require(cursor==info["original_pcm_total_samples"]
                        and file_hash(originalwav)==info["original_pcm_sha256"],
                        "Source WAV audio not preserved through all sample splits")
            concat=section/"source_order.txt"
            with concat.open("x",encoding="utf8") as fh:
                for clip in clip_seq:
                    fh.write("file '"+clip.as_posix()+"'\n")
            movie=section/f"Thomas_8_4_part{part_no:02d}_29_PDF_HIGHLIGHTS_REAL_REVIEW_ONLY.mp4"
            ff(exe,["-n","-f","concat","-safe","0","-i",str(concat),
                    "-c","copy","-movflags","+faststart",str(movie)],timeout=240)
            seconds=_mp4_duration(movie,ffmpeg=exe)
            require(0<seconds<600,"Real two-part source media must be <600s")
            verified=[]
            cursor_time=0.0
            for item in source_row:
                sample=cursor_time+min(.5,item["encoded_clip_duration_s"]*.5)
                error=_video_sample_error(exe=exe,movie=movie,at=sample,
                                          reference_png=Path(item["image_file"]))
                verified.append({"source_slide":item["source_slide"],
                    "candidate_target_id":item["candidate_target_id"],
                    "final_video_second":round(sample,4),
                    "decoded_original_pdf_pixel_error":float(error)})
                cursor_time+=item["encoded_clip_duration_s"]
            final_parts.append({"part":part_no,"original_slide_span":[first,last],
                "actual_mp4_file":str(movie),"actual_mp4_sha256":file_hash(movie),
                "actual_encoded_duration_s":seconds,
                "original_pdf_real_source_clips":source_row,
                "actual_decoded_pdf_source_frame_checks":verified,
                "student_publication_authorized":False})
            print("ACTUAL_REAL_29_CANDIDATE_REVIEW_PART",part_no,
                  "duration",seconds,"sourceclips",len(source_row),
                  "decoded",len(verified),flush=True)
    require(count==29 and len(final_parts)==2
            and sum(len(x["actual_decoded_pdf_source_frame_checks"])
                    for x in final_parts)>29,
            "Source PCM/visual candidate coverage not physically encoded")
    for name,sha in expected.items():
        require(file_hash(root/name)==sha,"G original protected source modified")
    result={"schema_version":1,"status":REVIEW_STATUS,
        "source_pdf_sha256":EXPECTED_SOURCE_SHA,
        "source_original_hashes":expected,
        "original_pcm_plan_sha256":file_hash(plan_path),
        "prior_four_candidate_review_sha256":file_hash(oldpath),
        "historical_visual_candidate_count":count,
        "corrected_slide4_real_pcm_visual_count":5,
        "student_release_accepted_mp4_count":0,
        "full_mathematics_and_source_semantics_approved":False,
        "all_utterance_element_synchronization_approved":False,
        "student_publication_authorized":False,
        "new_tts_provider_requests":0,
        "parts":final_parts}
    with (dest/"PR342_29_REAL_PDF_ACOUSTIC_REVIEW_ONLY.json").open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":REVIEW_STATUS,"video_lengths_s":
        [p["actual_encoded_duration_s"] for p in final_parts],
        "highlight_candidates":count,"released":0}))
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ("original","plan_receipt","old_review_receipt","out"):
        p.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    encode_two_review_parts(**vars(p.parse_args()))
if __name__=="__main__":main()
