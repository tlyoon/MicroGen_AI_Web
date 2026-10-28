"""Render ONE genuine source/PCM word-timed Slide6 proof-of-concept.

Exactly four numbered procedural original PDF blocks, measured genuine Vosk
word starts, original unmodified slide6.wav, H264/AAC and decoded frame audit.
Always REVIEW ONLY: lexical/physical agreement is not semantic approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import wave
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw
from .element_plan_autodraft import file_hash
from .original_thomas84_pdf_math_risk import physical_matches, require
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA
from .offline_original_thomas84_two_part_real_review import (
    WIDTH,HEIGHT,FPS,ff,_video_sample_error,
)
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

STEP_SENTENCES = ((2,"1 Substitute:"),(4,"2 Transform:"),
                  (5,"3 Integrate:"),(6,"4 Reverse:"))

def windows_for_steps(real_seconds: float, timed: list[tuple[float,float, int]]
                      ) -> list[tuple[float,float,int|None]]:
    """Timeline with no holes/overlap; tiny gaps may join prior highlight."""
    require(real_seconds > 10 and len(timed)==4,"Four measured procedure steps needed")
    cursor=0.0
    pieces=[]
    for index,(begin,end,step) in enumerate(timed):
        require(0 <= cursor <= begin < end <= real_seconds+.003 and
                step in (1,2,3,4),"Bad original acoustic timing or overlap")
        if begin-cursor >= .15:
            pieces.append((cursor,begin,None))
        elif pieces:
            a,_,old=pieces[-1]
            pieces[-1]=(a,begin,old)  # <=150ms inter-utterance gap
        else:
            require(begin==0,"Invalid first acoustic gap")
        pieces.append((begin,end,step))
        cursor=end
    if real_seconds-cursor>=.15:
        pieces.append((cursor,real_seconds,None))
    else:
        a,_,old=pieces[-1]
        pieces[-1]=(a,real_seconds,old)
    require(all(b>a for a,b,_ in pieces) and
            abs(pieces[0][0])<1e-8 and
            abs(pieces[-1][1]-real_seconds)<1e-6 and
            all(abs(pieces[i][1]-pieces[i+1][0])<1e-8
                for i in range(len(pieces)-1)) and
            [s for _,_,s in pieces if s is not None]==[1,2,3,4],
            "Wrong original audio sample coverage")
    return pieces

def _source_visual(pdf_page, bbox=None)->Image.Image:
    zoom=2.0
    pix=pdf_page.get_pixmap(matrix=pymupdf.Matrix(zoom,zoom),
                           colorspace=pymupdf.csRGB,alpha=False)
    image=Image.frombytes("RGB",[pix.width,pix.height],pix.samples)
    image=image.resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
    if bbox is not None:
        sx=WIDTH/pdf_page.rect.width; sy=HEIGHT/pdf_page.rect.height
        rect=[round(v*(sx if i%2==0 else sy))
              for i,v in enumerate(bbox)]
        overlay=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0))
        pen=ImageDraw.Draw(overlay)
        pen.rectangle(rect,fill=(255,210,0,65),outline=(255,165,0,255),width=6)
        image=Image.alpha_composite(image.convert("RGBA"),overlay).convert("RGB")
    pen=ImageDraw.Draw(image)
    pen.rectangle((0,0,WIDTH-1,42),fill=(120,0,0))
    pen.text((15,12),"REVIEW ONLY - ACOUSTIC PDF CANDIDATE - NOT SEMANTICALLY APPROVED",
             fill=(255,255,255))
    return image

def render_real_slide6(*,original:Path,candidate_receipt:Path,
                       destination:Path)->dict:
    root=Path(original).resolve()
    receipt=Path(candidate_receipt).resolve()
    out=Path(destination).absolute()
    require(root.is_dir() and receipt.is_file() and out.parent.is_dir()
            and not out.exists() and not out.is_relative_to(root.parent),
            "Only exclusive external output allowed")
    ledger=json.loads(receipt.read_text(encoding="utf8"))
    require(ledger.get("status")==
            "REAL_SOURCE_PDF_ACOUSTIC_VISUAL_WORKLIST_NOT_SEMANTICALLY_APPROVED"
            and ledger.get("student_publication_authorized") is False
            and ledger.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA,
            "Unapproved original acoustic/PDF receipt needed")
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Not real original textbook")
    slide=next(x for x in ledger["slides"] if x["slide"]==6)
    original_wav=root/"slide6.wav"
    require(file_hash(original_wav)==slide["source_wav_sha256"],
            "Original slide6 PCM changed")
    with wave.open(str(original_wav),"rb") as sound:
        require(sound.getnchannels()==1 and sound.getsampwidth()==2
                and sound.getframerate()==24000
                and sound.getcomptype()=="NONE",
                "Not original 24-kHz uncompressed PCM16")
        total=sound.getnframes()
        pcm=sound.readframes(total)
    require(len(pcm)==total*2,"Original PCM frames incomplete")
    timed=[]
    targets={}
    with pymupdf.open(root/"slides.pdf") as deck:
        page=deck[5]
        require(len(deck)==17,"Original full slide deck drift")
        for step,(sentence,leading) in enumerate(STEP_SENTENCES,1):
            match=next(x for x in slide["candidate_segments"]
                       if x["sentence_index"]==sentence)
            require(match["unique_target_review_priority"] is True and
                    match["speech_to_visible_math_semantics_approved"] is False and
                    match["eligible_for_final_student_highlight"] is False,
                    "Not unapproved measured word-timed PDF element")
            target=match["candidate_targets"][0]
            require(target["actual_visible_original_pdf_text"].lstrip().startswith(leading)
                    and physical_matches(page,target),
                    "Actual original numbered step not exactly visible in PDF")
            begin=match["actual_recorded_word_start_second"]
            end=match["actual_recorded_word_end_second"]
            require(isinstance(begin,(float,int)) and isinstance(end,(float,int))
                    and 0<=begin<end<=total/24000+.003,
                    "Actual word timestamp not inside WAV")
            timed.append((float(begin),float(end),step))
            targets[step]=target
        intervals=windows_for_steps(total/24000,timed)
        out.mkdir()
        pics=out/"original_pdf_frames";pics.mkdir()
        clips=out/"source_pcm_clips";clips.mkdir()
        static=pics/"original_slide6_STATIC_REVIEW_ONLY.png"
        _source_visual(page).save(static)
        images={None:static}
        for step,target in targets.items():
            path=pics/f"source_step{step:02d}_PROVISIONAL_REVIEW_ONLY.png"
            _source_visual(page,target["source_pdf_rect_pt"]).save(path)
            images[step]=path
        exe=ffmpeg_executable()
        clip_receipts=[]
        reconstructed=bytearray()
        for n,(begin,end,step) in enumerate(intervals,1):
            start=int(round(begin*24000)); finish=int(round(end*24000))
            require(0<=start<finish<=total and
                    (not clip_receipts or start==
                     clip_receipts[-1]["source_last_sample_exclusive"]),
                    "PCM cut contains duplicate/missing source sample")
            chunk=pcm[start*2:finish*2]
            reconstructed.extend(chunk)
            wavpath=clips/f"source_pcm_piece{n:02d}.wav"
            with wave.open(str(wavpath),"wb") as cut:
                cut.setnchannels(1);cut.setsampwidth(2)
                cut.setframerate(24000);cut.writeframes(chunk)
            movie=clips/f"real_source_pcm_piece{n:02d}.mp4"
            ff(exe,["-n","-loop","1","-framerate",str(FPS),
                    "-i",str(images[step]),"-i",str(wavpath),
                    "-c:v","libx264","-preset","ultrafast","-crf","23",
                    "-pix_fmt","yuv420p","-r",str(FPS),
                    "-c:a","aac","-b:a","96k",
                    "-t",f"{(finish-start)/24000:.8f}",
                    "-shortest","-movflags","+faststart",str(movie)],timeout=180)
            clip_receipts.append({
                "clip_file":str(movie),
                "actual_clip_sha256":file_hash(movie),
                "visual_png":str(images[step]),
                "visual_png_sha256":file_hash(images[step]),
                "source_first_sample":start,
                "source_last_sample_exclusive":finish,
                "source_pcm_sha256":hashlib.sha256(chunk).hexdigest(),
                "provisional_step":step,
                "encoded_duration_s":_mp4_duration(movie,ffmpeg=exe),
                "semantics_approved":False,
            })
        require(bytes(reconstructed)==pcm
                and clip_receipts[-1]["source_last_sample_exclusive"]==total,
                "Original slide6 PCM not preserved sample-exact")
        concat=out/"ordered_original_clips.txt"
        with concat.open("x",encoding="utf8") as f:
            for item in clip_receipts:
                f.write("file '"+Path(item["clip_file"]).as_posix()+"'\n")
        final=out/"Thomas_8_4_Slide6_REAL_PCM_FOUR_STEP_PROVISIONAL_REVIEW_ONLY.mp4"
        ff(exe,["-n","-f","concat","-safe","0","-i",str(concat),
                "-c","copy","-movflags","+faststart",str(final)],timeout=180)
        seconds=_mp4_duration(final,ffmpeg=exe)
        require(0<seconds<600 and abs(seconds-total/24000)<2.0,
                "Final real encoded review-only pilot duration drift")
        checks=[]
        cursor=0.0
        for item in clip_receipts:
            sample=cursor+min(.5,item["encoded_duration_s"]*.5)
            error=_video_sample_error(
                exe=exe,movie=final,at=sample,
                reference_png=Path(item["visual_png"]))
            checks.append({"source_pcm_first_sample":item["source_first_sample"],
                           "provisional_step":item["provisional_step"],
                           "decoded_video_second":round(sample,4),
                           "decoded_original_PDF_frame_error":error})
            cursor+=item["encoded_duration_s"]
        evidence={
            "schema_version":1,
            "status":"REAL_SLIDE6_FOUR_STEP_PROVISIONAL_PDF_WAV_REVIEW_ONLY",
            "source_pdf_sha256":EXPECTED_SOURCE_SHA,
            "original_slide6_wav_sha256":file_hash(original_wav),
            "original_slide6_pcm_samples":total,
            "all_original_samples_recombined_identically":True,
            "actual_encoded_mp4":str(final),
            "actual_encoded_mp4_sha256":file_hash(final),
            "actual_encoded_duration_s":seconds,
            "original_pdf_provisional_step_highlights":4,
            "source_audio_visual_clips":clip_receipts,
            "decoded_source_PDF_frame_checks":checks,
            "semantics_math_approved":False,
            "entire_lecture_full_element_sync_approved":False,
            "student_publication_authorized":False,
            "paid_TTS_calls":0,
        }
        with (out/"SOURCE_PDF_PCM_STEP6_REVIEW_RECEIPT.json").open("x",encoding="utf8") as f:
            json.dump(evidence,f,indent=2,ensure_ascii=False);f.write("\n")
    require(file_hash(original_wav)==slide["source_wav_sha256"]
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Original source/media changed during preview encode")
    return evidence

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--candidates",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    data=render_real_slide6(original=a.original,candidate_receipt=a.candidates,
                            destination=a.out)
    print(json.dumps({k:v for k,v in data.items()
                      if k not in ("source_audio_visual_clips",
                                   "decoded_source_PDF_frame_checks")},indent=2))
if __name__=="__main__":main()
