"""Second-pass real source/PDF/Kore/WAV/H264 audit of corrected §8.4 pair.

The original slide17 source sentence was two PCM source chunks:
verify both old pieces replaced by the ONE new genuine source-matched
Kore WAV. Recheck all 48 actual final Part2 H264 frames independently.
Technical PASS does not claim audible math accuracy or student release.
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
from .original_thomas84_paired_sl17_video_repair import STATUS as NEW_MEDIA_STATUS
from .original_thomas84_66_selective_math_reencode import STATUS as OLD_MEDIA_STATUS
from .original_thomas84_slide6_pcm_review import _source_visual
from .offline_original_thomas84_two_part_real_review import _video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

STATUS="PAIRED_CORRECTED_MATH_SLIDE17_NEW_KORE_REAL_MP4_INDEPENDENT_MEDIA_PASS_NO_STUDENT_RELEASE"

def audit_paired_new_video(*,original:Path,new_video_receipt:Path,
                           prior_video_receipt:Path,paired_source:Path,
                           corrected_voice:Path,out:Path)->dict:
    root=Path(original).resolve()
    receipt=Path(new_video_receipt).resolve()
    prior=Path(prior_video_receipt).resolve()
    pair=Path(paired_source).resolve()
    voice=Path(corrected_voice).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and receipt.is_file() and prior.is_file()
            and pair.is_dir() and voice.is_dir()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Require physical paired source/audio/media and exclusive external audit")
    new=json.loads(receipt.read_text(encoding="utf8"))
    old=json.loads(prior.read_text(encoding="utf8"))
    tts=json.loads((voice/"SUCCESS_CANDIDATE_NOT_VOICE_APPROVED.json").read_text(encoding="utf8"))
    source=json.loads((pair/"PAIR_SOURCE_PROOF_NO_AUDIO.json").read_text(encoding="utf8"))
    require(new.get("status")==NEW_MEDIA_STATUS
            and old.get("status")==OLD_MEDIA_STATUS
            and new.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and new.get("prior_full_source_movie_receipt_sha256")==file_hash(prior)
            and new.get("corrected_pair_receipt_sha256")==file_hash(pair/"PAIR_SOURCE_PROOF_NO_AUDIO.json")
            and new.get("corrected_genuine_gemini_wav_sha256")==tts.get("new_actual_pcm_sha256")
            and new.get("corrected_versioned_slide_pdf_sha256")==file_hash(pair/"slides.pdf")
            and source.get("corrected_pdf_sha256")==file_hash(pair/"slides.pdf")
            and source.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and source.get("other_16_original_PDF_page_pixels_bit_identical") is True
            and new.get("old_source_sentence_two_tail_removed_no_duplicate") is True
            and tts.get("independent_acoustic_correct_pronunciation_accepted") is False
            and new.get("independent_new_sentence_pronunciation_verified") is False
            and new.get("student_publication_authorized") is False,
            "Actual source/voice/media proof mismatch or false release")
    part1=receipt.parent/"Thomas_8_4_part01_original_unmodified_source_REVIEW_ONLY.mp4"
    part2=receipt.parent/"part_02"/"Thomas_8_4_part02_CORRECTED_FULL_INTEGRAL_KORE_REVIEW_ONLY.mp4"
    require(part1.is_file() and part2.is_file()
            and file_hash(part1)==new["part1_preserved_bytedecoded_original_SHA256"]
            and file_hash(part1)==old["parts"][0]["actual_mp4_sha256"]
            and file_hash(part2)==new["part2_actual_h264_aac_SHA256"],
            "Actual encoded full source movies missing or changed")
    realwav=Path(tts["new_actual_pcm_file"])
    require(realwav.is_file() and file_hash(realwav)==tts["new_actual_pcm_sha256"],
            "Paid source-matched one-shot PCM WAV altered")
    with wave.open(str(realwav),"rb") as audio:
        require(audio.getframerate()==24000 and audio.getsampwidth()==2
                and audio.getnchannels()==1
                and abs(audio.getnframes()/24000-15.48)<.03,
                "Paid corrected source audio is not full intact 15.48s mono PCM16")
        newpcm=audio.readframes(audio.getnframes())
    samples=[]
    oldrows=old["parts"][1]["all_real_source_clip_records"]
    newrows=new["part2_source_clips"]
    require(len(oldrows)==49 and len(newrows)==48
            and len(new["part2_source_frame_checks"])==48,
            "Physical clip replacement did not remove one old source-sentence tail")
    old_slide17=[x for x in oldrows if x["source_slide"]==17]
    new_slide17=[x for x in newrows if x["source_slide"]==17]
    require(len(old_slide17)==6 and len(new_slide17)==5,
            "Expected replacement of TWO old source audio pieces by ONE new model piece")
    voice_count=0
    exactly_reused=0
    new_slide_frames=0
    ffmpeg=ffmpeg_executable()
    with pymupdf.open(root/"slides.pdf") as original_pdf,pymupdf.open(pair/"slides.pdf") as new_pdf:
        require(len(original_pdf)==len(new_pdf)==17,
                "Paired source deck must have same 17 pages")
        for i in range(16):
            oldpix=original_pdf[i].get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),alpha=False)
            newpix=new_pdf[i].get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),alpha=False)
            require(oldpix.samples==newpix.samples,
                    "One original non-target slide changed actual pixels")
        page=new_pdf[16]
        from .original_thomas84_paired_sl17_video_repair import rebuilt_slide17_bounds
        originwav=root/"slide17.wav"
        require(originwav.is_file(),"Original source historical slide17 WAV missing")
        with wave.open(str(originwav),"rb") as origin:
            historicpcm=origin.readframes(origin.getnframes())
        cursor=0.
        j=0
        for idx,row in enumerate(newrows):
            oldrow=None
            if row["source_slide"]!=17:
                oldrow=oldrows[idx]
            clip=Path(row["clip_file"])
            picture=Path(row["image_file"])
            require(clip.is_file() and picture.is_file()
                    and file_hash(clip)==row["actual_clip_sha256"]
                    and file_hash(picture)==row["actual_image_sha256"],
                    "Actual source clip or exact PDF focus frame altered")
            if row["source_slide"]==17:
                j+=1
                piece={1:1,2:2,3:4,4:5,5:6}[j]
                if piece==2:
                    voice_count+=1
                    require(row["correction_audio_new"] is True
                            and row["source_first_pcm_sample"] is None
                            and row["source_last_pcm_sample_exclusive"] is None
                            and row["actual_source_audio_sha256"]==file_hash(realwav),
                            "Corrected complete mathematical sentence did not use new genuine Kore PCM")
                    with wave.open(str(row["actual_source_audio_file"]),"rb") as a:
                        require(a.readframes(a.getnframes())==newpcm,
                                "New paid source audio WAV bytes do not equal video-chip source")
                else:
                    first=row["source_first_pcm_sample"]
                    end=row["source_last_pcm_sample_exclusive"]
                    require(type(first) is int and type(end) is int
                            and first<end and end<=len(historicpcm)//2,
                            "Unchanged original slide17 speech PCM samples lost")
                    with wave.open(str(row["actual_source_audio_file"]),"rb") as a:
                        chunk=a.readframes(a.getnframes())
                        require(chunk==historicpcm[first*2:end*2],
                                "Unchanged historic original slide17 source samples changed")
                target_rect=rebuilt_slide17_bounds(page,row["candidate_target_id"],piece)
                target_frame=_source_visual(page,target_rect)
                with Image.open(picture) as candidate:
                    require(candidate.size==target_frame.size and
                            ImageChops.difference(
                                candidate.convert("RGB"),target_frame).getbbox() is None,
                            "Paired corrected source PDF frame not independently reproducible")
                new_slide_frames+=1
            else:
                require(oldrow is not None
                        and row["clip_file"]==oldrow["clip_file"]
                        and row["actual_clip_sha256"]==oldrow["actual_clip_sha256"]
                        and row["image_file"]==oldrow["image_file"]
                        and row["actual_image_sha256"]==oldrow["actual_image_sha256"],
                        "Historical original non-target media clip silently replaced")
                exactly_reused+=1
            at=cursor+min(.5,row["encoded_clip_duration_s"]*.5)
            err=_video_sample_error(exe=ffmpeg,movie=part2,at=at,
                                     reference_png=picture)
            require(float(err)<1.5,
                    "Final actual H264 frame source PDF differs from source-reconstructed PNG")
            cursor+=row["encoded_clip_duration_s"]
            samples.append(float(err))
    require(voice_count==1 and exactly_reused==43
            and new_slide_frames==5 and len(samples)==48,
            "Original real PDF clip/voice replacement inventory inconsistent")
    lengths=[_mp4_duration(movie,ffmpeg=ffmpeg) for movie in (part1,part2)]
    require(all(0<length<600 for length in lengths)
            and abs(lengths[0]-421.91)<.08
            and abs(lengths[1]-313.81)<.08,
            "Genuine video part duration outside original <600 contract")
    for movie in (part1,part2):
        p=subprocess.run([ffmpeg,"-nostdin","-v","error",
                          "-i",str(movie),"-map","0:a:0",
                          "-f","null","NUL"],
                         capture_output=True,timeout=120)
        require(p.returncode==0,
                "Actual full corrected H264/AAC audio stream undecodable")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and file_hash(root/"slide17.wav")!=file_hash(realwav)
            and file_hash(pair/"slides.pdf")==source["corrected_pdf_sha256"],
            "Protected original textbook or new math/audio source identity changed")
    result={
      "schema_version":1,"status":STATUS,
      "original_textbook_sha256":EXPECTED_SOURCE_SHA,
      "corrected_math_source_slide_pdf_sha256":file_hash(pair/"slides.pdf"),
      "corrected_new_actual_Kore_PCM_WAV_sha256":file_hash(realwav),
      "original_full_part1_bit_identical_sha256":file_hash(part1),
      "new_corrected_full_part2_sha256":file_hash(part2),
      "real_final_MP4_durations_s":lengths,
      "existing_real_original_untouched_PDF_slides_pixel_identical":16,
      "independent_actual_final_H264_PDF_frame_checks":len(samples),
      "actual_corrected_source_pdf_slide17_frames_reverified":new_slide_frames,
      "actual_untouched_source_audio_visual_clips_reused":exactly_reused,
      "old_sentence_two_audio_tail_removed":True,
      "one_new_original_format_Kore_PCM_audio_verified":True,
      "new_Kore_spoken_math_pronunciation_independently_approved":False,
      "source_all_66_academic_semantics_accepted":False,
      "student_publication_authorized":False,"release_eligible":False,
      "student_release_accepted_videos":0,
    }
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ("original","new_video_receipt","prior_video_receipt",
                "paired_source","corrected_voice","out"):
        p.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    r=audit_paired_new_video(**vars(p.parse_args()))
    print(json.dumps(r,indent=2))
if __name__=="__main__":main()
