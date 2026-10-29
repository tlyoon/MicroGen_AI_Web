"""Pair real corrected source slide17 + ONE new Kore TTS sentence in review MP4.

Other original source audio is byte-preserved. Both full videos <600 s.
Original slide17 sentence2 includes two old PCM clips; replace BOTH,
never retain stale speech tail. All source/media release gates stay false.
"""
from __future__ import annotations
import argparse
import json
import shutil
import wave
from pathlib import Path
import pymupdf

from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_paired_question_source_fix import STATUS as PAIR_STATUS
from .original_thomas84_single_approved_tts_repair import STATUS as TTS_STATUS
from .original_thomas84_66_selective_math_reencode import STATUS as PRIOR_MEDIA_STATUS
from .original_thomas84_slide6_pcm_review import _source_visual
from .offline_original_thomas84_two_part_real_review import FPS,ff,_video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

STATUS="PAIRED_MATH_CORRECTED_SLIDE17_REAL_KORE_TTS_TWO_FULL_MOVIES_REVIEW_ONLY"

def valid_old_clip(row:dict,prior:Path)->Path:
    clip=Path(row["clip_file"])
    require(clip.is_absolute() and clip.is_file() and not clip.is_symlink()
            and file_hash(clip)==row["actual_clip_sha256"],
            "Original SHA-bound encoded review clip unavailable")
    return clip

def rebuilt_slide17_bounds(page,old_target:str|None,
                           piece:int)->list[float]|None:
    if piece==6 or old_target is None:
        return None
    blocks=page.get_text("blocks")
    selected=( [1] if piece==1 else [2,3] if piece==2 else [4])
    require(all(i<len(blocks) and blocks[i][6]==0 for i in selected),
            "Versioned math-corrected final source slide block layout changed")
    text=[" ".join(str(blocks[i][4]).split()) for i in selected]
    if piece==2:
        require("For I =" in text[0] and "resulting trigonometric integrand" in text[1],
                "New original full integral source math is missing")
    if piece in (4,5):
        require("double-angle identities" in text[0],
                "Existing second question original mathematical meaning altered")
    rect=[min(float(blocks[i][0]) for i in selected),
          min(float(blocks[i][1]) for i in selected),
          max(float(blocks[i][2]) for i in selected),
          max(float(blocks[i][3]) for i in selected)]
    return rect

def encode_paired_slide17(*,original:Path,paired:Path,tts_candidate:Path,
                         prior_video_receipt:Path,prior_media_audit:Path,
                         out:Path)->dict:
    root=Path(original).resolve()
    pair=Path(paired).resolve()
    speech=Path(tts_candidate).resolve()
    previous=Path(prior_video_receipt).resolve()
    oldaudit=Path(prior_media_audit).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and all(p.is_file() and not p.is_symlink()
            for p in (previous,oldaudit))
            and pair.is_dir() and speech.is_dir()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Source safe external paired-MP4 output and actual evidence required")
    p=json.loads((pair/"PAIR_SOURCE_PROOF_NO_AUDIO.json").read_text(encoding="utf8"))
    t=json.loads((speech/"SUCCESS_CANDIDATE_NOT_VOICE_APPROVED.json").read_text(encoding="utf8"))
    old=json.loads(previous.read_text(encoding="utf8"))
    audit=json.loads(oldaudit.read_text(encoding="utf8"))
    require(p.get("status")==PAIR_STATUS and
            t.get("status")==TTS_STATUS and
            old.get("status")==PRIOR_MEDIA_STATUS and
            audit.get("status")==
                 "TWO_ACTUAL_CORRECTED_ORIGINAL_8_4_MP4S_INDEPENDENT_PHYSICAL_AUDIT_RELEASE_BLOCKED"
            and p.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and old.get("original_source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and audit.get("source_original_pdf_sha256")==EXPECTED_SOURCE_SHA
            and audit.get("corrected_review_receipt_sha256")==file_hash(previous)
            and p.get("real_synthesized_replacement_WAV_available") is False
            and t.get("independent_acoustic_correct_pronunciation_accepted") is False
            and t.get("source_originals_modified") is False
            and t.get("requested_voice")=="Kore"
            and t.get("requested_provider")=="gemini-3.8-flash-lite-tts"
            and p.get("corrected_pdf_sha256")==file_hash(pair/"slides.pdf")
            and t.get("text_hash")==__import__("hashlib").sha256(
                p["source_corrected_speech_text"].encode("utf8")).hexdigest()
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "One-shot paid genuine corrected voice and original source evidence mismatch")
    wav=Path(t["new_actual_pcm_file"])
    require(wav.is_file() and not wav.is_symlink()
            and wav.resolve().is_relative_to(speech)
            and file_hash(wav)==t["new_actual_pcm_sha256"],
            "New paid corrected genuine speech WAV absent or changed")
    with wave.open(str(wav),"rb") as audio:
        require(audio.getnchannels()==1 and audio.getsampwidth()==2
                and audio.getframerate()==24000
                and abs(audio.getnframes()/24000-
                        t["new_actual_pcm_duration_s"])<.001,
                "New Korean voice TTS is not true original-rate PCM")
    assert len(old["parts"])==2
    originalparts=old["parts"]
    old_source_hashes={z:file_hash(root/z) for z in (
        "source.pdf","slides.pdf","slides.tex","script_tts.json",
        "slide17.wav","slide11.wav")}
    dest.mkdir()
    first_source=Path(originalparts[0]["actual_mp4_file"])
    require(first_source.is_file() and file_hash(first_source)==
            originalparts[0]["actual_mp4_sha256"],
            "Previously independently verified whole original part1 changed")
    part1=dest/"Thomas_8_4_part01_original_unmodified_source_REVIEW_ONLY.mp4"
    shutil.copy2(first_source,part1)
    require(file_hash(part1)==file_hash(first_source),
            "Unchanged actual original part1 MP4 not bit-identically copied")
    exe=ffmpeg_executable()
    clips=dest/"part_02"/"original_math_corrected_slide17_clips"
    clips.mkdir(parents=True)
    images=dest/"part_02"/"corrected_pdf_source_frames"
    images.mkdir()
    outrows=[]
    cliplist=[]
    new_audio_count=0
    with pymupdf.open(pair/"slides.pdf") as deck:
        require(len(deck)==17,"New corrected actual PDF not 17 slides")
        page=deck[16]
        # Distinguish original raw WAV source audios vs one new
        # owner-authorized model/voice utterance. Old sentence source
        # clips #2 AND #3 must be removed, not appended/reused.
        earlier=originalparts[1]["all_real_source_clip_records"]
        slide17=[x for x in earlier if x["source_slide"]==17]
        require(len(slide17)==6,"Expected real old 6-part original slide17 source")
        keep_pieces={1,2,4,5,6}
        for row in earlier:
            slide=row["source_slide"]
            if slide!=17:
                clip=valid_old_clip(row,previous.parent)
                image=Path(row["image_file"])
                require(image.is_file() and file_hash(image)==
                        row["actual_image_sha256"],
                        "Unchanged original source visual frame changed")
                outrows.append({**row,"correction_audio_new":False,
                    "corrected_slide17_PDF":False})
                cliplist.append(clip)
                continue
            piece=slide17.index(row)+1
            if piece==3:
                continue
            require(piece in keep_pieces,"Unexpected old source WAV piece")
            actualwav=wav if piece==2 else (
                previous.parent.parent/
                "20261028_PR348_TWO_REAL_FULL66_SOURCE_CUE_REVIEW_MOVIES"/
                "part_02"/"actual_source_pcm_chunks"/
                f"slide17_part{piece:02d}.wav")
            require(actualwav.is_file(),"Missing genuine source slide17 audio")
            if piece!=2:
                require(file_hash(actualwav)==row["original_or_split_audio_sha256"],
                        "Unchanged original sample-exact slide17 WAV segment changed")
            rect=rebuilt_slide17_bounds(page,row["candidate_target_id"],piece)
            picture=images/f"slide17_piece{piece:02d}_SOURCE_CORRECTED_REVIEW_ONLY.png"
            _source_visual(page,rect).save(picture)
            clip=clips/f"source_slide17_piece{piece:02d}_PAIRED_CORRECTED_REVIEW_ONLY.mp4"
            with wave.open(str(actualwav),"rb") as rd:
                dur=rd.getnframes()/rd.getframerate()
            ff(exe,["-n","-loop","1","-framerate",str(FPS),
                    "-i",str(picture),"-i",str(actualwav),
                    "-map","0:v:0","-map","1:a:0",
                    "-c:v","libx264","-preset","ultrafast",
                    "-crf","23","-pix_fmt","yuv420p","-r",str(FPS),
                    "-c:a","aac","-b:a","96k",
                    "-t",f"{dur:.8f}","-shortest",
                    "-movflags","+faststart",str(clip)],timeout=180)
            encoded=_mp4_duration(clip,ffmpeg=exe)
            require(0<encoded<120 and abs(encoded-dur)<.20,
                    "Corrected source audio/video segment duration changed")
            updated={**row,"clip_file":str(clip),
                "image_file":str(picture),
                "actual_clip_sha256":file_hash(clip),
                "actual_image_sha256":file_hash(picture),
                "actual_source_audio_file":str(actualwav),
                "actual_source_audio_sha256":file_hash(actualwav),
                "encoded_clip_duration_s":encoded,
                "original_or_split_audio_sha256":file_hash(actualwav),
                "corrected_slide17_PDF":True,
                "correction_audio_new":piece==2,
                "source_first_pcm_sample":(
                    None if piece==2 else row["source_first_pcm_sample"]),
                "source_last_pcm_sample_exclusive":(
                    None if piece==2 else row["source_last_pcm_sample_exclusive"]),
                "candidate_target_id":(
                    "s017.corrected_complete_integral_question"
                    if piece==2 else row["candidate_target_id"]),
                "student_publication_authorized":False}
            outrows.append(updated);cliplist.append(clip)
            new_audio_count+=int(piece==2)
        require(new_audio_count==1 and
                sum(z["corrected_slide17_PDF"] for z in outrows)==5,
                "Exactly one paid corrected voice + five new PDF frame clips")
    order=dest/"part_02"/"source_order.txt"
    with order.open("x",encoding="utf8") as handle:
        for clip in cliplist:
            handle.write("file '"+clip.as_posix()+"'\n")
    part2=dest/"part_02"/"Thomas_8_4_part02_CORRECTED_FULL_INTEGRAL_KORE_REVIEW_ONLY.mp4"
    ff(exe,["-n","-f","concat","-safe","0","-i",str(order),
            "-c","copy","-movflags","+faststart",str(part2)],timeout=240)
    seconds=_mp4_duration(part2,ffmpeg=exe)
    require(0<seconds<600,"Corrected full part2 exceeds strict 600s")
    source_errors=[]
    moment=0.
    for row in outrows:
        sample=moment+min(.5,row["encoded_clip_duration_s"]*.5)
        err=_video_sample_error(exe=exe,movie=part2,
              at=sample,reference_png=Path(row["image_file"]))
        source_errors.append({"source_slide":row["source_slide"],
                             "candidate_target_id":row["candidate_target_id"],
                             "actual_decoded_frame_error":float(err),
                             "corrected_pdf":row["corrected_slide17_PDF"],
                             "new_voice":row["correction_audio_new"]})
        moment+=row["encoded_clip_duration_s"]
    require(all(file_hash(root/z)==sha for z,sha in old_source_hashes.items()),
            "Original protected source/multimedia modified")
    result={
       "schema_version":1,"status":STATUS,
       "original_textbook_sha256":EXPECTED_SOURCE_SHA,
       "corrected_versioned_slide_pdf_sha256":file_hash(pair/"slides.pdf"),
       "corrected_pair_receipt_sha256":file_hash(pair/"PAIR_SOURCE_PROOF_NO_AUDIO.json"),
       "corrected_genuine_gemini_wav_sha256":file_hash(wav),
       "prior_full_source_movie_receipt_sha256":file_hash(previous),
       "part1_preserved_bytedecoded_original_SHA256":file_hash(part1),
       "part2_actual_h264_aac_SHA256":file_hash(part2),
       "part2_encoded_duration_s":seconds,
       "part1_encoded_duration_s":_mp4_duration(part1,ffmpeg=exe),
       "actual_original_source_clips_plus_edited_source_clips":len(outrows),
       "actual_final_part2_decoded_PDF_frame_checks":len(source_errors),
       "one_new_Kore_VOICE_SPEECH_CLIP":new_audio_count,
       "old_source_sentence_two_tail_removed_no_duplicate":True,
       "other_original_WAVs_and_full_part1_preserved":True,
       "independent_new_sentence_pronunciation_verified":False,
       "complete_66_source_math_semantics_approved":False,
       "student_publication_authorized":False,"release_eligible":False,
       "part2_source_clips":outrows,
       "part2_source_frame_checks":source_errors}
    with (dest/"PAIRED_REAL_CORRECTED_SOURCE_VIDEO_REVIEW_ONLY.json").open(
            "x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ("original","paired","tts_candidate",
                "prior_video_receipt","prior_media_audit","out"):
        p.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    data=encode_paired_slide17(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in data.items()
                      if k not in ("part2_source_clips",
                                  "part2_source_frame_checks")},indent=2))
if __name__=="__main__":main()
