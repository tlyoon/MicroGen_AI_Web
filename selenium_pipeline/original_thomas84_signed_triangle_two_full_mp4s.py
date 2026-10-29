"""Rebuild §8.4 Part1 with corrected signed triangle PDF + genuine Kore WAV.

Part2 keeps the already independently proven corrected full-integral
Slide17 real MP4 BYTE-IDENTICAL. Original Slide8 sentence2 used two old
recording chunks; replace BOTH by ONE independently Vosk-screened
single 15.56s original source-registered paid Kore PCM utterance.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess,wave
from pathlib import Path
import pymupdf
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_signed_triangle_source_repair import STATUS as SOURCE_STATUS
from .original_thomas84_signed_triangle_single_kore_tts import STATUS as TTS_STATUS
from .original_thomas84_all66_independent_semantic_matrix import CURATED_BLOCKS
from .original_thomas84_slide6_pcm_review import _source_visual
from .offline_original_thomas84_two_part_real_review import FPS,ff,_video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

STATUS="TWO_FULL_TRUE_SOURCE_SLIDE8_SIGNED_TRIANGLE_SLIDE17_INTEGRAL_KORE_CORRECTED_REVIEW_MP4S"
ORIGINAL_PR351_STATUS="TWO_REAL_SOURCE_66_CUE_MP4S_TEN_CORRECTED_COMPOSITE_MATH_FOCUS_REVIEW_ONLY"
PART2_PR355_STATUS="PAIRED_MATH_CORRECTED_SLIDE17_REAL_KORE_TTS_TWO_FULL_MOVIES_REVIEW_ONLY"
PIECE_TO_SENTENCE={1:1,2:2,4:3,5:4,6:None,7:5}

def final_render(*,original:Path,paired_source:Path,new_audio:Path,
                 offline_speech_receipt:Path,pr351_video_receipt:Path,
                 pr355_video_receipt:Path,out:Path)->dict:
    root=Path(original).resolve();pair=Path(paired_source).resolve()
    voice=Path(new_audio).resolve()
    aud=Path(offline_speech_receipt).resolve()
    old=Path(pr351_video_receipt).resolve()
    later=Path(pr355_video_receipt).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and pair.is_dir() and voice.is_dir()
            and all(z.is_file() for z in (aud,old,later))
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Safe external real source corrected final video output required")
    source=json.loads((pair/"SIGNED_TRIANGLE_SOURCE_REPAIR_NO_AUDIO.json").read_text(encoding="utf8"))
    tts=json.loads((voice/"REAL_TTS_AUDIO_CANDIDATE_UNAPPROVED.json").read_text(encoding="utf8"))
    asr=json.loads(aud.read_text(encoding="utf8"))
    olddata=json.loads(old.read_text(encoding="utf8"))
    part2data=json.loads(later.read_text(encoding="utf8"))
    require(source.get("status")==SOURCE_STATUS
            and tts.get("status")==TTS_STATUS
            and olddata.get("status")==ORIGINAL_PR351_STATUS
            and part2data.get("status")==PART2_PR355_STATUS
            and source.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and source.get("new_corrected_signed_triangle_and_final_question_PDF_SHA256")==
                    file_hash(pair/"slides.pdf")
            and tts.get("paired_source_proof_sha256")==file_hash(pair/"SIGNED_TRIANGLE_SOURCE_REPAIR_NO_AUDIO.json")
            and asr.get("real_new_WAV_SHA256")==tts.get("actual_WAV_sha256")
            and asr.get("tts_soundalike_qa",{}).get("tts_qa_soundalike_pass") is True
            and not asr.get("tts_soundalike_qa",{}).get("critical_errors")
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and all(x.get("student_publication_authorized") is False
                    for x in (source,tts,olddata,part2data,asr)),
            "Only physically source-verified math and soundalike audio can be composed")
    wav=Path(tts["actual_WAV_path"])
    require(wav.is_file() and file_hash(wav)==tts["actual_WAV_sha256"]
            and wav.resolve().is_relative_to(voice),
            "New paid Kore math utterance was modified/moved")
    before={k:file_hash(root/k) for k in (
        "source.pdf","slides.pdf","slides.tex","script_tts.json",
        "slide8.wav","slide17.wav","slide11.wav")}
    exe=ffmpeg_executable()
    dest.mkdir()
    old_part=olddata["parts"][0]
    previous=old_part["all_real_source_clip_records"]
    require(len(previous)==57 and
            len([r for r in previous if r["source_slide"]==8])==7,
            "Source registered corrected Slide8 originally has seven real PCM video clips")
    final_part2_src=later.parent/"part_02"/"Thomas_8_4_part02_CORRECTED_FULL_INTEGRAL_KORE_REVIEW_ONLY.mp4"
    part2=dest/"part_02_OriginalSource_Slide17_MATH_CORRECTED_REVIEW_ONLY.mp4"
    require(final_part2_src.is_file() and file_hash(final_part2_src)==
            part2data["part2_actual_h264_aac_SHA256"],
            "Existing true source corrected full part2 movie missing")
    shutil.copy2(final_part2_src,part2)
    require(file_hash(part2)==file_hash(final_part2_src),
            "Prior real Slide17 corrected Part2 no longer bit identical")
    section=dest/"part_01";section.mkdir()
    imgdir=section/"slide8_corrected_PDF_focus";imgdir.mkdir()
    clipdir=section/"slide8_corrected_source_pcm_clips";clipdir.mkdir()
    cliplist=[];repacked=[];reused=0;recreated=0;onevoice=0
    old8=[r for r in previous if r["source_slide"]==8]
    with pymupdf.open(pair/"slides.pdf") as deck:
        page=deck[7]
        require(len(deck)==17 and "opposite = |x|" in
                " ".join(page.get_text().split()),
                "Real corrected signed triangle original source PDF absent")
        with pymupdf.open(root/"slides.pdf") as original_pdf:
            for i in range(17):
                if i not in (7,16):
                    a=original_pdf[i].get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),alpha=False)
                    b=deck[i].get_pixmap(matrix=pymupdf.Matrix(1.8,1.8),alpha=False)
                    require(a.samples==b.samples,"Unchanged original source slide pixels changed")
        for row in previous:
            slide=row["source_slide"]
            if slide!=8:
                clip=Path(row["clip_file"])
                img=Path(row["image_file"])
                require(clip.is_file() and img.is_file()
                        and file_hash(clip)==row["actual_clip_sha256"]
                        and file_hash(img)==row["actual_image_sha256"],
                        "Unchanged original part1 source/audio/video SHA differs")
                cliplist.append(clip)
                repacked.append({**row,"new_mathematics_pdf":False,
                                 "new_Kore_source_audio":False})
                reused+=1
                continue
            piece=old8.index(row)+1
            if piece==3:continue
            require(piece in PIECE_TO_SENTENCE,"Original source Slide8 clip ordering changed")
            sent=PIECE_TO_SENTENCE[piece]
            target=CURATED_BLOCKS[8][sent-1] if sent is not None else ()
            blocks=page.get_text("blocks")
            if target:
                require(all(0<=i<len(blocks) and blocks[i][6]==0 for i in target),
                        "New source PDF mathematical focus block indexing changed")
                rect=[min(blocks[i][0] for i in target),
                      min(blocks[i][1] for i in target),
                      max(blocks[i][2] for i in target),
                      max(blocks[i][3] for i in target)]
            else:rect=None
            img=imgdir/f"source_slide08_piece{piece:02d}_signed_math_correct.png"
            _source_visual(page,rect).save(img)
            realaudio=wav if piece==2 else (
                old.parent.parent/
                "20261028_PR348_TWO_REAL_FULL66_SOURCE_CUE_REVIEW_MOVIES"/
                "part_01"/"actual_source_pcm_chunks"/
                f"slide08_part{piece:02d}.wav")
            require(realaudio.is_file(),"True original sample-exact unaffected PCM WAV missing")
            if piece!=2:
                require(file_hash(realaudio)==row["original_or_split_audio_sha256"],
                        "Original preserved recorded PCM sample chunk changed")
            with wave.open(str(realaudio),"rb") as a:
                require(a.getframerate()==24000 and a.getnchannels()==1
                        and a.getsampwidth()==2,"Not original source 24k PCM16")
                length=a.getnframes()/24000
            clip=clipdir/f"source_slide08_piece{piece:02d}_SIGNED_REAL_REVIEW_ONLY.mp4"
            ff(exe,["-n","-loop","1","-framerate",str(FPS),
                    "-i",str(img),"-i",str(realaudio),
                    "-map","0:v:0","-map","1:a:0",
                    "-c:v","libx264","-preset","ultrafast","-crf","23",
                    "-pix_fmt","yuv420p","-r",str(FPS),
                    "-c:a","aac","-b:a","96k",
                    "-t",f"{length:.8f}","-shortest",
                    "-movflags","+faststart",str(clip)],timeout=180)
            require(0<_mp4_duration(clip,ffmpeg=exe)<120,
                    "New corrected original math clip unacceptable")
            changed={**row,"clip_file":str(clip),"image_file":str(img),
                 "actual_clip_sha256":file_hash(clip),
                 "actual_image_sha256":file_hash(img),
                 "original_or_split_audio_sha256":file_hash(realaudio),
                 "encoded_clip_duration_s":_mp4_duration(clip,ffmpeg=exe),
                 "source_first_pcm_sample":None if piece==2 else row["source_first_pcm_sample"],
                 "source_last_pcm_sample_exclusive":None if piece==2 else row["source_last_pcm_sample_exclusive"],
                 "actual_source_audio_file":str(realaudio),
                 "new_mathematics_pdf":True,
                 "new_Kore_source_audio":piece==2,
                 "candidate_target_id":f"s008.SIGNED_MATH_REPAIRED.{piece:02d}",
                 "student_publication_authorized":False}
            repacked.append(changed);cliplist.append(clip)
            recreated+=1;onevoice+=int(piece==2)
    require(len(repacked)==56 and reused==50 and recreated==6 and onevoice==1,
            "One previously split original source sentence was not replaced correctly")
    order=section/"true_source_clips.txt"
    with order.open("x",encoding="utf8") as f:
        for clip in cliplist:f.write("file '"+clip.as_posix()+"'\n")
    part1=section/"Thomas_8_4_part01_SIGNED_TRIANGLE_SOURCE_KORE_CORRECTED_REVIEW_ONLY.mp4"
    ff(exe,["-n","-f","concat","-safe","0","-i",str(order),"-c","copy",
            "-movflags","+faststart",str(part1)],timeout=240)
    times=[_mp4_duration(part1,ffmpeg=exe),_mp4_duration(part2,ffmpeg=exe)]
    require(all(0<t<600 for t in times)
            and abs(times[1]-313.81)<.08,
            "Strict real original two-part video duration contract violated")
    errors=[];cursor=0.
    for r in repacked:
        sample=cursor+min(.5,r["encoded_clip_duration_s"]*.5)
        value=_video_sample_error(exe=exe,movie=part1,
                                  at=sample,reference_png=Path(r["image_file"]))
        require(float(value)<1.5,
                "Final actual 8.4 mathematical PDF source frame changed/missed")
        errors.append({"source_slide":r["source_slide"],
                       "corrected_slide8":r["new_mathematics_pdf"],
                       "frame_sample_source_error":float(value)})
        cursor+=r["encoded_clip_duration_s"]
    for movie in (part1,part2):
        complete=subprocess.run([exe,"-nostdin","-v","error","-i",str(movie),
                    "-map","0:a:0","-f","null","NUL"],
                    capture_output=True,timeout=140)
        require(complete.returncode==0,"Full real corrected movie AAC cannot decode")
    require(all(file_hash(root/k)==sha for k,sha in before.items()),
            "Original protected source/previous WAV mutated during re-render")
    result={"schema_version":1,"status":STATUS,
      "original_source_pdf_sha256":EXPECTED_SOURCE_SHA,
      "real_new_source_corrected_slides_pdf_sha256":file_hash(pair/"slides.pdf"),
      "new_signed_triangle_Kore_wav_sha256":file_hash(wav),
      "new_Kore_speech_offline_QA_receipt_sha256":file_hash(aud),
      "original_16_untouched_slides_pixels_identical":True,
      "real_video_part1_sha256":file_hash(part1),
      "real_video_part2_sha256":file_hash(part2),
      "real_video_duration_seconds":times,
      "part1_original_source_PCM_visual_clips_reused":reused,
      "part1_new_real_signed_math_PDF_source_clips":recreated,
      "actual_corrected_full_part1_H264_source_frame_checks":len(errors),
      "original_two_clip_sentence_tail_replaced_with_one_genuine_new_WAV":True,
      "part2_original_corrected_full_integral_bit_identical":
        file_hash(part2)==part2data["part2_actual_h264_aac_SHA256"],
      "all_66_complete_math_semantics_accepted":False,
      "student_publication_authorized":False,"release_eligible":False,
      "actual_part1_clips":repacked,
      "part1_source_frame_checks":errors,
    }
    with (dest/"PAIRED_TWO_CORRECTED_REAL_MP4S_SIGNED_MATH_REVIEW.json").open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ("original","paired_source","new_audio","offline_speech_receipt",
                "pr351_video_receipt","pr355_video_receipt","out"):
        p.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    r=final_render(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in r.items() if k not in (
        "actual_part1_clips","part1_source_frame_checks")},indent=2))
if __name__=="__main__":main()
