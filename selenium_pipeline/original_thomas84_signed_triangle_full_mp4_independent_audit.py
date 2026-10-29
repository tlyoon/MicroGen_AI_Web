"""Independent second pass of the FINAL two source-corrected 8.4 movies.

Check real source-PDF slide8 corrected math, existing slide17 full integral,
old source 24k PCM sample bytes, new Kore speech, all H264 source PDF
frames, full AAC decoding, length strictly <600 and original immutable
textbook artifacts. Not automatic declaration of full academic review.
"""
from __future__ import annotations
import argparse,json,subprocess,wave
from pathlib import Path
import pymupdf
from PIL import Image,ImageChops
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_signed_triangle_two_full_mp4s import STATUS as VIDEO_STATUS,PIECE_TO_SENTENCE
from .original_thomas84_signed_triangle_source_repair import STATUS as SOURCE_STATUS
from .original_thomas84_signed_triangle_single_kore_tts import STATUS as KORE_STATUS
from .original_thomas84_slide6_pcm_review import _source_visual
from .original_thomas84_all66_independent_semantic_matrix import CURATED_BLOCKS
from .offline_original_thomas84_two_part_real_review import _video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

STATUS="INDEPENDENT_TWO_ACTUAL_SOURCE_8_4_MP4S_BOTH_MATH_REPAIRS_PHYSICAL_PASS"
def second_pass(*,original:Path,paired:Path,kore:Path,
                final_video_receipt:Path,prior_video_receipt:Path,
                out:Path)->dict:
    root=Path(original).resolve()
    pair=Path(paired).resolve();voice=Path(kore).resolve()
    media=Path(final_video_receipt).resolve()
    prior=Path(prior_video_receipt).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and pair.is_dir() and voice.is_dir()
            and media.is_file() and prior.is_file()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Real source and new exclusive independent movie audit required")
    m=json.loads(media.read_text(encoding="utf8"))
    old=json.loads(prior.read_text(encoding="utf8"))
    source=json.loads((pair/"SIGNED_TRIANGLE_SOURCE_REPAIR_NO_AUDIO.json").read_text(encoding="utf8"))
    tts=json.loads((voice/"REAL_TTS_AUDIO_CANDIDATE_UNAPPROVED.json").read_text(encoding="utf8"))
    require(m.get("status")==VIDEO_STATUS
            and source.get("status")==SOURCE_STATUS
            and tts.get("status")==KORE_STATUS
            and m.get("original_source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and source.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and m.get("real_new_source_corrected_slides_pdf_sha256")==file_hash(pair/"slides.pdf")
            and source.get("new_corrected_signed_triangle_and_final_question_PDF_SHA256")==file_hash(pair/"slides.pdf")
            and m.get("new_signed_triangle_Kore_wav_sha256")==tts["actual_WAV_sha256"]
            and m.get("part2_original_corrected_full_integral_bit_identical") is True
            and m.get("original_two_clip_sentence_tail_replaced_with_one_genuine_new_WAV") is True
            and m.get("actual_corrected_full_part1_H264_source_frame_checks")==56
            and m.get("student_publication_authorized") is False,
            "Actual final corrected source/voice video source proof broken")
    part1=media.parent/"part_01"/"Thomas_8_4_part01_SIGNED_TRIANGLE_SOURCE_KORE_CORRECTED_REVIEW_ONLY.mp4"
    part2=media.parent/"part_02_OriginalSource_Slide17_MATH_CORRECTED_REVIEW_ONLY.mp4"
    require(part1.is_file() and part2.is_file()
            and file_hash(part1)==m["real_video_part1_sha256"]
            and file_hash(part2)==m["real_video_part2_sha256"],
            "Actual final full genuine videos are not source-registered")
    original_wav=root/"slide8.wav"
    with wave.open(str(original_wav),"rb") as a:
        require(a.getframerate()==24000 and a.getnchannels()==1
                and a.getsampwidth()==2,"Original protected Slide8 recording changed format")
        historic=a.readframes(a.getnframes())
    paidwav=Path(tts["actual_WAV_path"])
    require(paidwav.is_file() and file_hash(paidwav)==tts["actual_WAV_sha256"],
            "New corrected one-shot Kore WAV missing")
    with wave.open(str(paidwav),"rb") as a:
        newpcm=a.readframes(a.getnframes())
    rows=m["actual_part1_clips"];priorrows=old["parts"][0]["all_real_source_clip_records"]
    require(len(rows)==56 and len(priorrows)==57 and len(m["part1_source_frame_checks"])==56,
            "Actual source interval inventory changed")
    old8=[r for r in priorrows if r["source_slide"]==8]
    new8=[r for r in rows if r["source_slide"]==8]
    require(len(old8)==7 and len(new8)==6,
            "Two old source sentence chunks were not replaced with one")
    exe=ffmpeg_executable()
    old_prior={(r["clip_file"],r["actual_clip_sha256"]) for r in priorrows
               if r["source_slide"]!=8}
    reused=0
    source_frames=0
    genuine_paid=0
    cursor=0.
    with pymupdf.open(pair/"slides.pdf") as pdf:
        require(len(pdf)==17 and "opposite = |x|" in pdf[7].get_text()
                and "For I =" in pdf[16].get_text(),
                "Both original mathematical slide repairs missing")
        page=pdf[7]
        for r in rows:
            image=Path(r["image_file"]);clip=Path(r["clip_file"])
            require(image.is_file() and clip.is_file()
                    and file_hash(image)==r["actual_image_sha256"]
                    and file_hash(clip)==r["actual_clip_sha256"],
                    "Actual source PDF reference frame or H264 chip changed")
            if r["source_slide"]!=8:
                require((r["clip_file"],r["actual_clip_sha256"]) in old_prior,
                        "Unchanged original historical source 8.4 clip changed")
                reused+=1
            else:
                source_frames+=1
                part=int(Path(r["clip_file"]).stem.split("piece")[-1][:2])
                require(part in PIECE_TO_SENTENCE,
                        "Actual corrected Slide8 math clip order changed")
                sentence=PIECE_TO_SENTENCE[part]
                blocks=CURATED_BLOCKS[8][sentence-1] if sentence is not None else ()
                found=page.get_text("blocks")
                rect=([min(found[i][0] for i in blocks),
                      min(found[i][1] for i in blocks),
                      max(found[i][2] for i in blocks),
                      max(found[i][3] for i in blocks)] if blocks else None)
                expected=_source_visual(page,rect)
                with Image.open(image) as actual:
                    require(actual.size==expected.size and
                            ImageChops.difference(actual.convert("RGB"),
                                                 expected.convert("RGB")).getbbox() is None,
                            "Full corrected PDF math source focus image cannot be reproduced")
                audiopath=Path(r["actual_source_audio_file"])
                require(audiopath.is_file() and
                        file_hash(audiopath)==r["original_or_split_audio_sha256"],
                        "Source original PCM chip source missing")
                with wave.open(str(audiopath),"rb") as a:
                    payload=a.readframes(a.getnframes())
                if part==2:
                    require(payload==newpcm
                            and r["new_Kore_source_audio"] is True,
                            "Paid corrected math words not used in new video source")
                    genuine_paid+=1
                else:
                    first=r["source_first_pcm_sample"]
                    last=r["source_last_pcm_sample_exclusive"]
                    require(type(first) is int and type(last) is int
                            and payload==historic[first*2:last*2],
                            "Unchanged original PCM source samples differ")
            error=_video_sample_error(exe=exe,movie=part1,
                   at=cursor+min(.5,r["encoded_clip_duration_s"]*.5),
                   reference_png=image)
            require(float(error)<1.5,
                    "Independently decoded full H264 source mathematical source image mismatch")
            cursor+=r["encoded_clip_duration_s"]
    require(reused==50 and source_frames==6 and genuine_paid==1,
            "Full corrected original source element/voice exact roster incomplete")
    lengths=[_mp4_duration(z,ffmpeg=exe) for z in (part1,part2)]
    require(all(0<x<600 for x in lengths)
            and abs(lengths[0]-426.89)<.08
            and abs(lengths[1]-313.81)<.08,
            "Strict less than 600s multi-part video rule failed")
    for movie in (part1,part2):
        result=subprocess.run([exe,"-nostdin","-loglevel","error",
               "-i",str(movie),"-map","0:a:0","-f","null","NUL"],
                capture_output=True,timeout=150)
        require(result.returncode==0,
                "Actual full final corrected video AAC audio stream undecodable")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Protected original textbook mutated")
    result={
      "schema_version":1,"status":STATUS,
      "original_textbook_sha256":EXPECTED_SOURCE_SHA,
      "new_real_corrected_source_pdf_sha256":file_hash(pair/"slides.pdf"),
      "full_2part_actual_H264_AAC_sha256":[file_hash(part1),file_hash(part2)],
      "full_actual_video_seconds":lengths,
      "source_corrected_slide8_and_slide17_present":True,
      "part1_independently_redecoded_source_pdf_H264_frames":len(rows),
      "real_corrected_slide8_source_images_independently_reconstructed":source_frames,
      "unaltered_50_original_source_MP4_clips_bytedecoded":reused,
      "new_actual_one_source_math_Kore_PCM_byte_exact":True,
      "old_sentence_two_PCM_tail_removed":True,
      "part2_original_source_full_integral_sha_preserved":True,
      "both_actual_full_AAC_audio_streams_decoded":True,
      "strict_video_duration_less_than_600":True,
      "all_66_spoken_source_mathematics_independently_accepted":False,
      "student_publication_authorized":False,"release_eligible":False}
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result
def main():
    p=argparse.ArgumentParser()
    for name in ("original","paired","kore","final_video_receipt",
                 "prior_video_receipt","out"):
        p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    r=second_pass(**vars(p.parse_args()))
    print(json.dumps(r,indent=2))
if __name__=="__main__":main()
