"""Independent physical re-audit of genuine §8.4 Slide6 review MP4.

Check protected PDF+PCM, sample-exact source splits, true MP4 SHA,
AAC decoder, visual frames decoded from final MP4 against source-PDF
raster. Never infer semantic approvals or publish.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import wave
from pathlib import Path

import pymupdf
from PIL import Image,ImageChops
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_pdf_math_risk import physical_matches
from .original_thomas84_slide6_pcm_review import (
    _source_visual,STEP_SENTENCES,
)
from .offline_original_thomas84_two_part_real_review import _video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

REVIEW_STATUS="REAL_SLIDE6_FOUR_STEP_PROVISIONAL_PDF_WAV_REVIEW_ONLY"

def within_bundle(path:str,root:Path)->Path:
    require(type(path) is str and path.strip(),"Missing physical original-media path")
    candidate=Path(path)
    require(candidate.is_absolute() and candidate.is_file()
            and not candidate.is_symlink()
            and candidate.resolve().is_relative_to(root.resolve()),
            "Media path missing/symlinked/outside exclusive review bundle")
    return candidate

def audit_real_slide6(*,original:Path,review_receipt:Path,
                      candidate_receipt:Path,output:Path)->dict:
    root=Path(original).resolve(); src=Path(review_receipt).resolve()
    candidate=Path(candidate_receipt).resolve()
    dest=Path(output).absolute()
    require(root.is_dir() and src.is_file() and candidate.is_file()
            and not src.is_symlink() and not candidate.is_symlink()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Review only original source/receipt unavailable or output unsafe")
    r=json.loads(src.read_text(encoding="utf8"))
    c=json.loads(candidate.read_text(encoding="utf8"))
    require(r.get("status")==REVIEW_STATUS and r.get("schema_version")==1
            and c.get("status")==
            "REAL_SOURCE_PDF_ACOUSTIC_VISUAL_WORKLIST_NOT_SEMANTICALLY_APPROVED"
            and c.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and r.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and r.get("semantics_math_approved") is False
            and r.get("entire_lecture_full_element_sync_approved") is False
            and r.get("student_publication_authorized") is False
            and r.get("paid_TTS_calls")==0
            and r.get("all_original_samples_recombined_identically") is True
            and r.get("original_pdf_provisional_step_highlights")==4,
            "Untrusted source MP4 receipt or false acceptance")
    originalwav=root/"slide6.wav"
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and file_hash(originalwav)==r["original_slide6_wav_sha256"],
            "Protected original textbook or WAV changed")
    wav_slide=next(x for x in c["slides"] if x["slide"]==6)
    require(wav_slide["source_wav_sha256"]==
            r["original_slide6_wav_sha256"],"Real word timeline WAV identity drift")
    with wave.open(str(originalwav),"rb") as w:
        require(w.getframerate()==24000 and w.getsampwidth()==2
                and w.getnchannels()==1,"Source PCM format invalid")
        total=w.getnframes(); original_pcm=w.readframes(total)
    require(total==r["original_slide6_pcm_samples"]
            and len(original_pcm)==total*2,
            "Original PCM frame count mismatch")
    bundle=src.parent
    mp4=within_bundle(r.get("actual_encoded_mp4"),bundle)
    require(file_hash(mp4)==r["actual_encoded_mp4_sha256"],
            "Actual final encoded H264/AAC MP4 SHA tampered")
    exe=ffmpeg_executable()
    seconds=_mp4_duration(mp4,ffmpeg=exe)
    require(0<seconds<600 and
            abs(seconds-float(r["actual_encoded_duration_s"]))<.08,
            "Genuine MP4 encoded duration too long/stale")
    # Verify actual AAC stream is decoded by FFmpeg, not merely present
    # in a JSON description or written as a misleading WAV extension.
    decode=subprocess.run([exe,"-hide_banner","-nostdin","-v","error",
                           "-i",str(mp4),"-map","0:a:0",
                           "-f","null","NUL"],
                          capture_output=True,timeout=90)
    require(decode.returncode==0,"Original MP4 AAC audio stream decode failed")
    cliprows=r.get("source_audio_visual_clips")
    checked=r.get("decoded_source_PDF_frame_checks")
    require(type(cliprows) is list and len(cliprows)==7
            and type(checked) is list and len(checked)==7,
            "Expected seven original real PCM/audio-visual windows")
    source_targets={}
    for idx,leading in STEP_SENTENCES:
        row=next(x for x in wav_slide["candidate_segments"]
                 if x["sentence_index"]==idx)
        require(row["unique_target_review_priority"] is True
                and row["speech_to_visible_math_semantics_approved"] is False,
                "Step candidate incorrectly accepted or missing")
        item=row["candidate_targets"][0]
        require(item["actual_visible_original_pdf_text"].lstrip().startswith(leading),
                "Wrong numbered PDF step target")
        source_targets[len(source_targets)+1]=item
    reassembled=bytearray()
    cursor=0
    decoded=[]
    video_cursor=0.
    with pymupdf.open(root/"slides.pdf") as slides:
        require(len(slides)==17,"Original protected slide PDF count drift")
        page=slides[5]
        for n,(item,saved) in enumerate(zip(cliprows,checked),1):
            start=item["source_first_sample"]
            finish=item["source_last_sample_exclusive"]
            require(type(start) is int and type(finish) is int
                    and start==cursor and 0<=start<finish<=total
                    and item["semantics_approved"] is False,
                    "Original WAV source segments missing/reordered/approved")
            cursor=finish
            expected=original_pcm[start*2:finish*2]
            require(hashlib.sha256(expected).hexdigest()==
                    item["source_pcm_sha256"],
                    "Segment original PCM SHA doesn't match actual source recording")
            reassembled.extend(expected)
            split=bundle/"source_pcm_clips"/f"source_pcm_piece{n:02d}.wav"
            require(split.is_file() and not split.is_symlink(),
                    "Actual split original PCM WAV missing")
            with wave.open(str(split),"rb") as seg:
                require(seg.getnchannels()==1 and seg.getsampwidth()==2
                        and seg.getframerate()==24000
                        and seg.readframes(seg.getnframes())==expected,
                        "Physical segmented WAV differs from protected original PCM")
            clip=within_bundle(item["clip_file"],bundle)
            pic=within_bundle(item["visual_png"],bundle)
            require(file_hash(clip)==item["actual_clip_sha256"]
                    and file_hash(pic)==item["visual_png_sha256"],
                    "Physical clip or source-PDF visual PNG changed")
            step=item["provisional_step"]
            require(step in (None,1,2,3,4),"Unrecognized audio-step candidate")
            target=source_targets[step] if step is not None else None
            if target is not None:
                require(physical_matches(page,target),
                        "Original PDF source-visual step geometry changed")
            generated=_source_visual(
                page,target["source_pdf_rect_pt"] if target else None)
            with Image.open(pic) as im:
                require(im.size==generated.size
                        and ImageChops.difference(im.convert("RGB"),generated)
                        .getbbox() is None,
                        "Saved highlighted frame not physically reconstructible "
                        "from original PDF")
            sample=video_cursor+min(.5,float(item["encoded_duration_s"])*.5)
            error=_video_sample_error(exe=exe,movie=mp4,at=sample,
                                      reference_png=pic)
            require(float(error)<1.5,
                    "Final H264 decoded visual frame does not match source PDF")
            require(saved["source_pcm_first_sample"]==start and
                    saved["provisional_step"]==step
                    and abs(saved["decoded_original_PDF_frame_error"]-error)<.2,
                    "Saved decoded-frame proof no longer reproducible")
            decoded.append({"step":step,"real_clip_index":n,
                            "real_final_video_second":round(sample,4),
                            "recomputed_original_pdf_pixel_error":float(error)})
            video_cursor+=float(item["encoded_duration_s"])
    require(cursor==total and bytes(reassembled)==original_pcm
            and [x["provisional_step"] for x in cliprows if
                 x["provisional_step"] is not None]==[1,2,3,4],
            "Real complete original WAV coverage/step ordering false")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and file_hash(originalwav)==r["original_slide6_wav_sha256"],
            "Protected source changed during independent audit")
    result={
        "schema_version":1,
        "status":"REAL_SLIDE6_REVERIFIED_BUT_RELEASE_BLOCKED",
        "original_source_pdf_sha256":EXPECTED_SOURCE_SHA,
        "pr339_review_receipt_sha256":file_hash(src),
        "pr335_candidate_receipt_sha256":file_hash(candidate),
        "real_original_pcm_samples_independently_verified":total,
        "source_pcm_samples_bytewise_reassembled":True,
        "real_encoded_media_sha256":file_hash(mp4),
        "real_encoded_duration_s":seconds,
        "real_AAC_audio_stream_decode_pass":True,
        "real_final_H264_decoded_PDF_frame_checks":len(decoded),
        "original_PDF_word_timed_step_highlights_provisional":4,
        "decoded_frame_checks":decoded,
        "entire_lecture_math_approved":False,
        "complete_lecture_spoken_element_sync_approved":False,
        "student_publication_authorized":False,
        "release_accepted_full_videos":0,
    }
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--review",required=True,type=Path)
    p.add_argument("--candidates",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    r=audit_real_slide6(original=a.original,review_receipt=a.review,
                        candidate_receipt=a.candidates,output=a.out)
    print(json.dumps({k:v for k,v in r.items()
                      if k!="decoded_frame_checks"},indent=2))
if __name__=="__main__":main()
