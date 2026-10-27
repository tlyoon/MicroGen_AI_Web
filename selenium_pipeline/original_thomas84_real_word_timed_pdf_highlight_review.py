"""Real-PCM-anchored PDF-candidate highlight review, Thomas 8.4 parts 1/2.

This OPTIONAL second pass retains the previously encoded PR331 real videos.
The genuine 16 historical slide WAVs are NEVER regenerated or overwritten.
Only FOUR read-only original PDF candidate rectangles (slides 5/6/15/17)
with actual independently decoded spoken-word timestamps are visually
emphasized. Other historic slides remain static, except genuine NEW
five-utterance source-element-synced Slide4 Flash-Lite/Kore candidates.

Every PCM split spans the exact original 24kHz sample sequence, no inferred
word speed or proportional timestamps. Rebuilt true H264/AAC MP4s are
sampled/visually compared to the original PDF source-derived frames.

PROVISIONAL original PDF lexical target does NOT prove semantic speech
mapping, academic mathematics, Kore voice identity or release; all video
frames retain REVIEW ONLY warnings.
"""
from __future__ import annotations
import argparse
from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import wave

import pymupdf
from PIL import Image,ImageDraw

from .offline_original_thomas84_two_part_real_review import (
    WIDTH,HEIGHT,FPS,MAX_SECONDS_EXCLUSIVE,need,ff,pcm_details,
    _visual_for_unit,_video_sample_error,
    plan_real_original_thomas84_two_parts,
)
from .offline_corrected_bundle_verify import strict_json
from .original_replacement_video_handoff import _sha
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable


EXPECTED_REAL_CANDIDATES={5:1,6:5,15:1,17:3}
MIN_ACOUSTIC_WORD_ANCHOR_FRACTION=.70


def _source_normalized(text:str)->str:
    return " ".join(str(text).casefold().split())


def actual_word_timed_pdf_targets(*,original:Path,receipt:Path)->dict[int,dict]:
    """Recompute PDF bbox identity, actual WAV SHA, and acoustic timing."""
    root=Path(original).absolute()
    saved=strict_json(Path(receipt).absolute())
    need(saved.get("status")==
         "REAL_HISTORICAL_16_SLIDES_ASR_TO_ORIGINAL_PDF_ELEMENT_CANDIDATES_REVIEW_ONLY"
         and saved.get("actual_historical_slides_inspected")==16
         and saved.get("audio_word_timing_hypotheses")==65
         and saved.get("independent_utterance_to_math_element_semantics_certified")
             is False
         and saved.get("student_publication_authorized") is False
         and saved.get("source_originals_modified") is False
         and saved.get("network_asr_used") is False,
         "Untrusted/misreported original sixteen-WAV semantic timing evidence")
    before={name:_sha(root/name) for name in
            ("source.pdf","slides.pdf","script.txt","script_tts.json","slides.mp4")}
    need(before==saved["source_original_hashes"],
         "Protected original PDFs/transcripts/media drift from word-timing receipt")
    historical=saved["original_historical_WAV_hashes"]
    need(set(historical)=={f"slide{i}.wav" for i in range(1,18) if i!=4},
         "Historical original sixteenth-WAV inventory changed")
    for n,sha in historical.items():
        need(_sha(root/n)==sha,
             "Saved ASR provenance no longer agrees with true historical WAV")
    candidates={}
    slide_index=saved.get("slides")
    need(isinstance(slide_index,list) and len(slide_index)==16
         and [x["slide"] for x in slide_index]==[i for i in range(1,18) if i!=4],
         "Original PDF visual candidate row order missing")
    with pymupdf.open(root/"slides.pdf") as deck:
        need(len(deck)==17,"Original PDF slide count drift")
        for record in slide_index:
            slide=int(record["slide"])
            need(record["historical_WAV_sha256"]==historical[f"slide{slide}.wav"],
                 "Original TTS audio sha mismatch in a slide")
            with wave.open(str(root/f"slide{slide}.wav"),"rb") as wav:
                wav_s=wav.getnframes()/wav.getframerate()
            need(abs(wav_s-record["actual_original_PCM_duration_s"])<.001,
                 "Historical source audio duration changed")
            viable=[]
            for sentence in record["candidate_elements"]:
                if not (sentence.get("word_timing_hypothesis_available")
                        and sentence.get("top_visual_lexical_match_unambiguous")
                        and sentence.get("original_script_tts_matches_draft_fragment")
                        and sentence.get("top_visual_id_only_candidate")
                        and sentence.get("actual_ASR_word_anchor_fraction",0)>=
                            MIN_ACOUSTIC_WORD_ANCHOR_FRACTION):
                    continue
                idx=int(sentence["sentence_index"])
                begin=sentence["first_matched_real_audio_second"]
                end=sentence["last_matched_real_audio_second"]
                need(type(begin) in (float,int) and
                     type(end) in (float,int) and
                     math.isfinite(begin) and math.isfinite(end) and
                     0<=begin<end<=wav_s+.005 and end-begin>=.35,
                     "Real original WAV acoustic timestamps invalid")
                claimed=sentence["top_visual_id_only_candidate"]
                first=(sentence.get("ranked_original_pdf_visual_candidates") or [None])[0]
                need(first is not None and first["visual_target_id"]==claimed
                     and first["is_figure_panel_ambiguous"] is False
                     and float(first["lexical_overlap_hint_not_semantic"])>=.43,
                     "Candidate original PDF geometry not unequivocally top-ranked")
                rect=[float(v) for v in first["pdf_rect_pt"]]
                need(len(rect)==4 and 0<=rect[0]<rect[2]<=deck[slide-1].rect.width
                     and 0<=rect[1]<rect[3]<=deck[slide-1].rect.height,
                     "Source PDF candidate rectangle escapes genuine slide")
                visible=first["visible_pdf_text"]
                actual_blocks=deck[slide-1].get_text("blocks")
                matches=[b for b in actual_blocks if len(b)>=5
                         and _source_normalized(b[4])==_source_normalized(visible)
                         and all(abs(float(b[k])-rect[k])<.12 for k in range(4))]
                need(len(matches)==1,
                     "Candidate lexical visual is not exactly one original PDF block")
                source_text=sentence.get("original_actual_slide_narration_fragment","")
                need(hashlib.sha256(source_text.encode("utf8")).hexdigest()==
                     sentence["narration_fragment_sha256"],
                     "ASR candidate narration is not the original TTS text hash")
                viable.append({
                    "slide":slide,"sentence_index":idx,
                    "visual_target_id":claimed,
                    "real_vosk_first_word_s":float(begin),
                    "real_vosk_last_word_s":float(end),
                    "source_bbox_pdf_pt":rect,
                    "original_pdf_visible_text":visible,
                    "spoken_expected_narration_sha256":
                        sentence["narration_fragment_sha256"],
                    "actual_anchored_word_fraction":
                        sentence["actual_ASR_word_anchor_fraction"],
                    "source_semantic_approval":False,
                })
            if viable:
                need(len(viable)==1 and slide in EXPECTED_REAL_CANDIDATES
                     and viable[0]["sentence_index"]==EXPECTED_REAL_CANDIDATES[slide],
                     "Unexpected or multiply ambiguous original PDF visual targets")
                candidates[slide]=viable[0]
    need(set(candidates)==set(EXPECTED_REAL_CANDIDATES),
         "Cannot claim four existing measured acoustic PDF highlight candidates")
    return candidates


def exact_original_pcm_word_splits(*,wav:Path,begin_s:float,end_s:float
                                   )->tuple[bytes,list[dict]]:
    """Return exact concatenated source PCM and actual 24 kHz sample spans."""
    path=Path(wav)
    with wave.open(str(path),"rb") as w:
        need(w.getnchannels()==1 and w.getsampwidth()==2
             and w.getframerate()==24000 and w.getcomptype()=="NONE",
             "Original WAV is not true canonical 24kHz mono PCM16")
        rate=w.getframerate()
        nframes=w.getnframes()
        pcm=w.readframes(nframes)
    need(len(pcm)==nframes*2 and nframes>12000,
         "Original audio frames incomplete")
    need(math.isfinite(begin_s) and math.isfinite(end_s)
         and 0<=begin_s<end_s<=nframes/rate+.005,
         "ASR word intervals are not inside actual original WAV")
    start=max(0,min(nframes,round(begin_s*rate)))
    end=max(0,min(nframes,round(end_s*rate)))
    # An under-80ms leading silence has no audible mathematical words.
    # Include it in the first candidate segment, not a tiny unplayable clip.
    if start<=round(rate*.08):
        start=0
    need(0<=start<end<=nframes and end-start>=round(rate*.30),
         "Word-timed PDF candidate has no substantial audible PCM region")
    bounds=[0,start,end,nframes]
    windows=[]
    for a,b,highlight in ((bounds[0],bounds[1],False),
                          (bounds[1],bounds[2],True),
                          (bounds[2],bounds[3],False)):
        if a==b:continue
        need(b-a>=round(rate*.20),
             "Cannot encode mathematically ungrounded tiny original PCM tail")
        content=pcm[a*2:b*2]
        windows.append({
            "source_first_pcm_sample":a,
            "source_last_pcm_sample_exclusive":b,
            "highlight_provisional_PDF_target":bool(highlight),
            "source_pcm_bytes":content,
            "real_pcm_duration_s":(b-a)/rate,
        })
    need(sum(len(w["source_pcm_bytes"]) for w in windows)==len(pcm)
         and b"".join(w["source_pcm_bytes"] for w in windows)==pcm
         and sum(bool(w["highlight_provisional_PDF_target"]) for w in windows)==1,
         "Original historical WAV sample coverage incomplete/duplicated")
    return pcm,windows


def _write_pcm_window(*,path:Path,content:bytes):
    need(len(content)>0 and len(content)%2==0,
         "Original WAV split contains invalid PCM byte boundaries")
    with path.open("xb") as raw:
        with wave.open(raw,"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
            w.writeframes(content)


def _highlight_picture(*,static:Path,target:dict,out:Path,page)->Path:
    with Image.open(static) as im:
        canvas=im.convert("RGBA")
    bounds=target["source_bbox_pdf_pt"]
    need(canvas.size==(WIDTH,HEIGHT),"Original PDF source review raster size drift")
    sx=WIDTH/page.rect.width
    sy=HEIGHT/page.rect.height
    rect=[round(bounds[0]*sx),round(bounds[1]*sy),
          round(bounds[2]*sx),round(bounds[3]*sy)]
    need(0<=rect[0]<rect[2]<WIDTH and 0<=rect[1]<rect[3]<HEIGHT,
         "Original visible PDF block rectangle outside actual raster")
    overlay=Image.new("RGBA",canvas.size,(0,0,0,0))
    draw=ImageDraw.Draw(overlay)
    draw.rounded_rectangle(rect,radius=9,fill=(255,205,0,48),
                           outline=(255,160,0,255),width=6)
    highlighted=Image.alpha_composite(canvas,overlay).convert("RGB")
    # Additional persistent red caution label: evidence is real audio timing
    # but the source mathematical semantic match remains PROVISIONAL.
    pen=ImageDraw.Draw(highlighted)
    pen.rectangle((0,39,WIDTH-1,70),fill=(120,0,0))
    pen.text((8,48),
             "PROVISIONAL WORD-TIMED PDF HIGHLIGHT - MATH SEMANTIC REVIEW MISSING",
             fill=(255,255,255))
    with out.open("xb") as f:highlighted.save(f,format="PNG")
    return out


def encode_provisional_two_part_real_original_highlights(
    *,original:Path,bundle:Path,audio_dir:Path,timing_receipt:Path,
    out:Path)->dict:
    root=Path(original).absolute()
    destination=Path(out).absolute()
    need(destination.parent.is_dir() and not destination.exists()
         and not destination.is_relative_to(root.parent)
         and not destination.is_relative_to(Path(audio_dir).absolute())
         and not destination.is_relative_to(Path(bundle).absolute()),
         "Exclusive external Dell AppData output only; cannot write originals")
    original_plan=plan_real_original_thomas84_two_parts(
        original=root,bundle=bundle,audio_dir=audio_dir)
    candidates=actual_word_timed_pdf_targets(
        original=root,receipt=timing_receipt)
    exe=ffmpeg_executable()
    destination.mkdir()
    image_root=destination/"actual_original_pdf_source_frames"
    image_root.mkdir()
    sample_receipts=[]
    original_audio_coverage=[]
    historical_highlight_count=0
    with pymupdf.open(root/"slides.pdf") as pdf:
        for section in original_plan["parts"]:
            output=destination/section["part_id"]
            output.mkdir()
            clips=output/"actual_h264_aac_clips"
            clips.mkdir()
            segmented=output/"original_pcm_exact_split_chips"
            segmented.mkdir()
            rows=[]
            for item in section["timeline_units"]:
                slide=int(item["slide"])
                if item["element_index"] is None:
                    reference=_visual_for_unit(
                        original=root,pdf=pdf,p=item,dest=image_root)
                    sections=[]
                    if slide in candidates:
                        match=candidates[slide]
                        pcm,subchunks=exact_original_pcm_word_splits(
                            wav=Path(item["audio"]["path"]),
                            begin_s=match["real_vosk_first_word_s"],
                            end_s=match["real_vosk_last_word_s"])
                        concat=b""
                        for index,window in enumerate(subchunks,1):
                            splitwav=segmented/f"slide{slide:02d}_segment{index:02d}.wav"
                            _write_pcm_window(path=splitwav,
                                              content=window["source_pcm_bytes"])
                            concat+=window["source_pcm_bytes"]
                            highlight=window["highlight_provisional_PDF_target"]
                            pic=reference
                            if highlight:
                                pic=_highlight_picture(
                                    static=reference,target=match,
                                    out=image_root/f"slide{slide:02d}_PROVISIONAL_"
                                                   f"word_timed_target.png",
                                    page=pdf[slide-1])
                                historical_highlight_count+=1
                            sections.append({
                                "audio_path":splitwav,
                                "image_path":pic,
                                "source_slide":slide,
                                "candidate_target_id":
                                    match["visual_target_id"] if highlight else None,
                                "source_sample_first":window["source_first_pcm_sample"],
                                "source_sample_end":window["source_last_pcm_sample_exclusive"],
                                "expected_pcm_duration_s":window["real_pcm_duration_s"],
                                "word_timed_highlight_semantically_approved":False,
                            })
                        need(concat==pcm,
                             "Real historical PCM split omitted actual original speech")
                        original_audio_coverage.append({
                            "slide":slide,
                            "original_historical_WAV_sha256":_sha(
                                Path(item["audio"]["path"])),
                            "all_samples_recombined_losslessly":concat==pcm,
                            "source_pcm_frames_preserved":len(concat)//2,
                            "real_word_anchor_seconds":[match["real_vosk_first_word_s"],
                                                        match["real_vosk_last_word_s"]],
                            "pdf_candidate_target":match["visual_target_id"],
                            "source_pdf_semantics_approved":False,
                        })
                    else:
                        sections=[{
                            "audio_path":Path(item["audio"]["path"]),
                            "image_path":reference,
                            "source_slide":slide,
                            "candidate_target_id":None,
                            "source_sample_first":0,
                            "source_sample_end":item["audio"]["frame_count"],
                            "expected_pcm_duration_s":item["audio"]["duration_seconds"],
                            "word_timed_highlight_semantically_approved":False,
                        }]
                else:
                    image=_visual_for_unit(
                        original=root,pdf=pdf,p=item,dest=image_root)
                    sections=[{
                        "audio_path":Path(item["audio"]["path"]),
                        "image_path":image,
                        "source_slide":slide,
                        "element_index":item["element_index"],
                        "candidate_target_id":item["source_target_id"],
                        "source_sample_first":0,
                        "source_sample_end":item["audio"]["frame_count"],
                        "expected_pcm_duration_s":item["audio"]["duration_seconds"],
                        "word_timed_highlight_semantically_approved":False,
                    }]
                for row in sections:
                    wavefile=row["audio_path"]
                    sound=pcm_details(wavefile)
                    need(abs(sound["duration_seconds"]-
                             row["expected_pcm_duration_s"])<.0001,
                         "Original-sample word-timed split is not exact PCM duration")
                    clip_path=clips/f"segment_{len(rows)+1:03d}.mp4"
                    ff(exe,["-n","-loop","1","-framerate",str(FPS),
                            "-i",str(row["image_path"]),
                            "-i",str(wavefile),
                            "-map","0:v:0","-map","1:a:0",
                            "-t",f"{sound['duration_seconds']:.8f}",
                            "-c:v","libx264","-preset","ultrafast","-crf","23",
                            "-pix_fmt","yuv420p","-r",str(FPS),
                            "-c:a","aac","-b:a","96k","-shortest",
                            "-movflags","+faststart",str(clip_path)],timeout=180)
                    actual_duration=_mp4_duration(clip_path,ffmpeg=exe)
                    need(0<actual_duration<180 and
                         abs(actual_duration-sound["duration_seconds"])<.14,
                         "Original PCM recorded clip and actual encoded audio drift")
                    rows.append({
                        **{k:v for k,v in row.items()
                           if k not in ("audio_path","image_path")},
                        "original_or_split_audio_sha256":sound["sha256"],
                        "actual_encoded_mp4_sha256":_sha(clip_path),
                        "clip_file":str(clip_path),
                        "image_file":str(row["image_path"]),
                        "candidate_visual_frame_sha256":_sha(row["image_path"]),
                        "encoded_actual_duration_s":actual_duration,
                        "real_pcm_duration_s":sound["duration_seconds"],
                        "semantic_sync_approved":False,
                    })
                    print("WORD_ANCHORED_ORIGINAL_PDF_REVIEW_CLIP",
                          section["part_id"],len(rows),
                          f"SLIDE{slide:02d}",
                          row.get("candidate_target_id") or "STATIC",
                          f"{actual_duration:.2f}s",flush=True)
            concat_list=output/"actual_reencoded_concat_sources.txt"
            with concat_list.open("x",encoding="utf8") as f:
                for row in rows:
                    f.write("file '"+Path(row["clip_file"]).as_posix()+"'\n")
            movie=output / (
                f"Thomas_8_4_{section['part_id']}_"
                "WORD_TIMED_PROVISIONAL_HIGHLIGHT_REVIEW_ONLY.mp4"
            )
            ff(exe,["-n","-f","concat","-safe","0","-i",str(concat_list),
                    "-c","copy","-movflags","+faststart",str(movie)],timeout=180)
            real_seconds=_mp4_duration(movie,ffmpeg=exe)
            need(0<real_seconds<MAX_SECONDS_EXCLUSIVE
                 and abs(real_seconds-
                         sum(r["real_pcm_duration_s"] for r in rows))<3.0,
                 "Actual encoded original two-part review video duration failed")
            checked=[]
            cursor=0.
            for row in rows:
                sample=cursor+min(.65,row["encoded_actual_duration_s"]/2)
                error=_video_sample_error(
                    exe=exe,movie=movie,at=sample,
                    reference_png=Path(row["image_file"]))
                checked.append({
                    "slide":row["source_slide"],
                    "candidate_target":row["candidate_target_id"],
                    "decoded_at_video_second":round(sample,4),
                    "actual_encoded_pdf_source_frame_error":error,
                })
                cursor+=row["encoded_actual_duration_s"]
            sample_receipts.append({
                "part_id":section["part_id"],
                "original_slide_span":[section["first_slide"],
                                       section["last_slide"]],
                "actual_h264_aac_mp4":str(movie),
                "actual_MP4_sha256":_sha(movie),
                "actual_MP4_bytes":movie.stat().st_size,
                "actual_encoded_MP4_duration_s":real_seconds,
                "strictly_less_than_ten_minutes":real_seconds<600,
                "decoded_actual_original_pdf_frame_checks":checked,
                "all_source_visual_audio_units":rows,
                "complete_element_synchronization_approved":False,
                "student_publication_authorized":False,
            })
            print("TRUE_THOMAS_84_REVIEW_PART_REENCODED",
                  section["part_id"],"DURATION",real_seconds,
                  "PIXEL_CHECKS",len(checked),flush=True)
    need(len(sample_receipts)==2 and historical_highlight_count==4
         and len(original_audio_coverage)==4,
         "Four actual original WAV word-timed PDF visual candidates missing")
    for name,digest in original_plan["source_hashes"].items():
        need(_sha(root/name)==digest,
             "Protected actual source/slide/script/history was modified")
    for part in original_plan["parts"]:
        for original_unit in part["timeline_units"]:
            need(_sha(Path(original_unit["audio"]["path"]))==
                 original_unit["audio"]["sha256"],
                 "Protected historical PCM/new corrected voice bytes changed")
    saved={
        "schema_version":1,
        "status":"TWO_REAL_ORIGINAL_8_4_VIDEOS_FOUR_MORE_ACOUSTIC_PDF_HIGHLIGHTS_REVIEW_ONLY",
        "original_source_sha256":original_plan["source_hashes"]["source.pdf"],
        "protected_original_hashes":original_plan["source_hashes"],
        "timing_receipt_sha256":_sha(Path(timing_receipt)),
        "real_parts":sample_receipts,
        "four_measured_asr_word_timed_original_PDF_highlights":
            historical_highlight_count,
        "five_corrected_slide4_actual_PCM_source_highlights":5,
        "four_lossless_original_PCM_sample_split_proofs":original_audio_coverage,
        "student_accepted_complete_video_parts":0,
        "all_remaining_original_source_elements_speech_synced":False,
        "academic_source_mathematics_two_pass_approved":False,
        "c_as_circa_tts_pronunciation_accepted":False,
        "new_tts_provider_requests_made":0,
        "original_PDFs_WAVs_and_MP4s_unchanged":True,
        "student_publication_authorized":False,
        "whisper_used":False,
        "windows_Dell_only":True,
    }
    with (destination/"PR333_REAL_FOUR_PROVISIONAL_VISUAL_ACCEPTANCE_NOT_RELEASE.json").open(
            "x",encoding="utf8") as f:
        json.dump(saved,f,indent=2,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({
        "status":saved["status"],
        "real_mp4_durations_s":[x["actual_encoded_MP4_duration_s"]
                                for x in sample_receipts],
        "actual_decoded_source_frame_checks":
            sum(len(x["decoded_actual_original_pdf_frame_checks"])
                for x in sample_receipts),
        "new_historical_PCM_word_timed_PDF_highlights":
            historical_highlight_count,
        "new_accepted_course_lecture_parts":0,
    }))
    return saved


def main(argv=None):
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--original",type=Path,required=True)
    cli.add_argument("--bundle",type=Path,required=True)
    cli.add_argument("--audio-dir",type=Path,required=True)
    cli.add_argument("--timing-receipt",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True)
    a=cli.parse_args(argv)
    encode_provisional_two_part_real_original_highlights(
        original=a.original,bundle=a.bundle,audio_dir=a.audio_dir,
        timing_receipt=a.timing_receipt,out=a.out)


if __name__=="__main__":
    main()
