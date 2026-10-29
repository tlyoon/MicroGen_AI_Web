"""Selectively re-encode ten real §8.4 original-PDF composite math focus clips.

Reuse unchanged, independently audited PR348 source audio/visual media
for other timeline units. Exactly ten original 24k PCM source chips get
re-encoded with corrected, physically original PDF composite rectangles.
All complete videos stay REVIEW ONLY, NEVER student approved.
"""
from __future__ import annotations
import argparse
import json
import wave
from pathlib import Path
import pymupdf

from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_composite_source_semantic_corrections import STATUS as CORRECTION_STATUS
from .original_thomas84_66_full_review import REVIEW_STATUS as ORIGINAL_VIDEO_STATUS
from .original_thomas84_66_source_cue_pcm_plan import STATUS as ORIGINAL_PLAN_STATUS
from .original_thomas84_slide6_pcm_review import _source_visual
from .offline_original_thomas84_two_part_real_review import FPS,ff,_video_sample_error
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

STATUS="TWO_REAL_SOURCE_66_CUE_MP4S_TEN_CORRECTED_COMPOSITE_MATH_FOCUS_REVIEW_ONLY"

def locate_original_source_clip(rows:list[dict],*,slide:int,
                                old_target:str,first:int,last:int)->int:
    """Require one real original PCM interval; never guess the same-word target."""
    hits=[i for i,r in enumerate(rows)
          if r["source_slide"]==slide
          and r["candidate_target_id"]==old_target
          and r.get("existing_real_slide4_corrected") is False
          and r["source_first_pcm_sample"]<=first
          and r["source_last_pcm_sample_exclusive"]>=last]
    require(len(hits)==1,
            "Acoustic word-to-old-source clip interval ambiguous/missing")
    return hits[0]

def physically_exact_source_composite(page,proof:dict)->list[float]:
    """Reconstruct exact original block set and enclosing visible PDF geometry."""
    physical=[]
    for element in proof["original_pdf_source_blocks"]:
        index=element["original_pdf_block_index"]
        blocklist=page.get_text("blocks")
        require(index>=0 and index<len(blocklist) and blocklist[index][6]==0,
                "Missing source-visible mathematical PDF block")
        block=blocklist[index]
        actual=" ".join(str(block[4]).split())
        expected=element["original_pdf_text"]
        bounds=element["original_pdf_bbox_pt"]
        require(actual==expected and len(bounds)==4 and
                all(abs(float(block[j])-bounds[j])<=.12
                    for j in range(4)),
                "Source PDF source mathematical text or geometry changed")
        physical.append(bounds)
    rect=[min(b[0] for b in physical),min(b[1] for b in physical),
          max(b[2] for b in physical),max(b[3] for b in physical)]
    claimed=proof["original_pdf_visual_union_rect_pt"]
    require(all(abs(rect[i]-claimed[i])<=.12 for i in range(4)),
            "Untrusted composite mathematical original PDF rectangle")
    return rect

def selectively_reencode(*,original:Path,full_review_receipt:Path,
                         source_plan_receipt:Path,independent_media_receipt:Path,
                         corrected_math_receipt:Path,out:Path)->dict:
    root=Path(original).resolve()
    video=Path(full_review_receipt).resolve()
    oldplan=Path(source_plan_receipt).resolve()
    audited=Path(independent_media_receipt).resolve()
    corrections=Path(corrected_math_receipt).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and all(x.is_file() and not x.is_symlink()
            for x in (video,oldplan,audited,corrections))
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent)
            and not dest.is_relative_to(video.parent),
            "Source and original video receipts required; external new output only")
    v=json.loads(video.read_text(encoding="utf8"))
    p=json.loads(oldplan.read_text(encoding="utf8"))
    a=json.loads(audited.read_text(encoding="utf8"))
    c=json.loads(corrections.read_text(encoding="utf8"))
    require(v.get("status")==ORIGINAL_VIDEO_STATUS
            and p.get("status")==ORIGINAL_PLAN_STATUS
            and c.get("status")==CORRECTION_STATUS
            and a.get("status")==
                "TWO_REAL_66_CUE_H264_AAC_MP4S_PHYSICALLY_INDEPENDENTLY_VERIFIED_NO_RELEASE"
            and c.get("original_66_source_cue_plan_sha256")==file_hash(oldplan)
            and c.get("independent_real_video_audit_sha256")==file_hash(audited)
            and a.get("pr348_render_receipt_sha256")==file_hash(video)
            and v.get("original_pcm_plan_sha256")==file_hash(oldplan)
            and v.get("source_pdf_sha256")==EXPECTED_SOURCE_SHA
            and c.get("protected_original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and a.get("source_original_pdf_sha256")==EXPECTED_SOURCE_SHA
            and a.get("source_pdf_reverified_provisional_cue_events")==66
            and c.get("incomplete_or_wrong_context_original_cues_corrected")==10
            and all(z.get("student_publication_authorized") is False
                    for z in (v,p,a,c)),
            "Original protected source + real media audit chain missing")
    before=v["source_original_hashes"]
    require(before["source.pdf"]==EXPECTED_SOURCE_SHA and
            all(file_hash(root/key)==sha for key,sha in before.items()),
            "Original protected source PDF/WAV/MP4 changed")
    source_plan={(s["slide"],x["sentence_index"]):(s,x)
                 for s in p["source_historical_slides"]
                 for x in s["physical_original_pdf_source_targets"]}
    source_slide_index={s["slide"]:s for s in p["source_historical_slides"]}
    previous_parts=v["parts"]
    require(len(previous_parts)==2 and
            [x["original_slide_span"] for x in previous_parts]==[[1,8],[9,17]],
            "Exactly two SHA-bound complete original review MP4 parts required")
    correction_index={}
    for k in c["corrected_original_pdf_composite_focuses"]:
        key=(k["slide"],k["sentence_index"])
        require(key in source_plan and key not in correction_index
                and source_plan[key][1]["narration_source_sha256"]==
                    k["original_narration_fragment_sha256"]
                and source_plan[key][1]["physical_original_pdf_element_id"]==
                    k["superseded_review_only_pdf_element_id"],
                "Correction not bound to the actual original source sentence")
        correction_index[key]=k
    require(len(correction_index)==10,
            "Ten independent source-PDF composite corrections required")
    planned_changes={}
    for key,fix in correction_index.items():
        slide,sentence=key
        parent,original_cue=source_plan[key]
        source_segment=next(x for x in parent["source_pcm_sample_exact_timeline"]
                     if x["sentence_index"]==sentence)
        part=previous_parts[0] if slide<=8 else previous_parts[1]
        idx=locate_original_source_clip(
            part["original_pdf_real_source_clips"],slide=slide,
            old_target=original_cue["physical_original_pdf_element_id"],
            first=source_segment["first_pcm_sample"],
            last=source_segment["last_pcm_sample_exclusive"])
        identity=(part["part"],idx)
        require(identity not in planned_changes,
                "Two mathematical corrections unexpectedly share one audio clip")
        planned_changes[identity]=fix
    require(len(planned_changes)==10,
            "Cannot uniquely identify ten physically original audio clip windows")
    exe=ffmpeg_executable()
    dest.mkdir()
    image_root=dest/"corrected_original_pdf_composite_focuses";image_root.mkdir()
    results=[]
    corrected_count=0
    all_checked=0
    with pymupdf.open(root/"slides.pdf") as pdf:
        require(len(pdf)==17 and file_hash(root/"slides.pdf")==
                p["original_slides_pdf_sha256"],
                "Protected original source full slide PDF changed")
        for original_part in previous_parts:
            part_no=original_part["part"]
            section=dest/f"part_{part_no:02d}";section.mkdir()
            changed_clips=section/"original_pcm_corrected_encoded_clips"
            changed_clips.mkdir()
            rows=[]
            clips=[]
            for i,old in enumerate(original_part["original_pdf_real_source_clips"]):
                row=dict(old)
                correction=planned_changes.get((part_no,i))
                if correction is not None:
                    slide=correction["slide"]
                    rect=physically_exact_source_composite(pdf[slide-1],correction)
                    image=image_root/f"slide{slide:02d}_sentence{correction['sentence_index']:02d}_ORIGINAL_COMPOSITE_REVIEW.png"
                    _source_visual(pdf[slide-1],rect).save(image)
                    # PR348 audio sample chip is an exact immutable
                    # original-source segment, independently audited in PR349.
                    oldclip=Path(old["clip_file"])
                    require(oldclip.is_file() and oldclip.is_relative_to(video.parent),
                            "Original reference media clip is missing/foreign")
                    name=oldclip.stem
                    suffix=name.rsplit("piece",1)[-1]
                    require(suffix.isdigit(),"Saved original clip piece has changed name")
                    audio=video.parent/f"part_{part_no:02d}"/"actual_source_pcm_chunks"/(
                        f"slide{slide:02d}_part{int(suffix):02d}.wav")
                    require(audio.is_file() and file_hash(audio)==
                            old["original_or_split_audio_sha256"],
                            "Corrected visual source lacks matching exact original PCM")
                    with wave.open(str(audio),"rb") as sourceaudio:
                        require(sourceaudio.getframerate()==24000
                            and sourceaudio.getnchannels()==1
                            and sourceaudio.getsampwidth()==2,
                            "Source exact audio chip format changed")
                        duration=sourceaudio.getnframes()/24000
                    movie=changed_clips/f"corrected_slide{slide:02d}_sentence{correction['sentence_index']:02d}.mp4"
                    ff(exe,["-n","-loop","1","-framerate",str(FPS),
                        "-i",str(image),"-i",str(audio),
                        "-map","0:v:0","-map","1:a:0",
                        "-c:v","libx264","-preset","ultrafast","-crf","23",
                        "-pix_fmt","yuv420p","-r",str(FPS),
                        "-c:a","aac","-b:a","96k",
                        "-t",f"{duration:.8f}","-shortest",
                        "-movflags","+faststart",str(movie)],timeout=180)
                    encoded=_mp4_duration(movie,ffmpeg=exe)
                    require(0<encoded<180 and abs(encoded-duration)<.2,
                            "Original real PCM clip duration changed during corrective render")
                    row.update({
                        "clip_file":str(movie),"image_file":str(image),
                        "actual_clip_sha256":file_hash(movie),
                        "actual_image_sha256":file_hash(image),
                        "encoded_clip_duration_s":encoded,
                        "candidate_target_id":
                            f"s{slide:03d}.composite_source_math_fix.{correction['sentence_index']:02d}",
                        "physically_original_composite_corrected":True,
                        "source_math_semantics_approved":False,
                        "student_publication_authorized":False})
                    corrected_count+=1
                else:
                    require(Path(old["clip_file"]).is_file()
                        and file_hash(Path(old["clip_file"]))==old["actual_clip_sha256"]
                        and file_hash(Path(old["image_file"]))==old["actual_image_sha256"],
                        "Unmodified real source reference clip/image provenance changed")
                    row["physically_original_composite_corrected"]=False
                clips.append(Path(row["clip_file"]))
                rows.append(row)
            order=section/"full_source_clips_ordered.txt"
            with order.open("x",encoding="utf8") as f:
                for clip in clips:
                    f.write("file '"+clip.as_posix()+"'\n")
            final=section/f"Thomas_8_4_part{part_no:02d}_TEN_MATH_SOURCE_CORRECTED_REVIEW_ONLY.mp4"
            ff(exe,["-n","-f","concat","-safe","0","-i",str(order),
                    "-c","copy","-movflags","+faststart",str(final)],timeout=240)
            length=_mp4_duration(final,ffmpeg=exe)
            require(0<length<600,"Two physical source-corrected videos must remain <600s")
            cursor=0.
            visual_checks=[]
            for row in rows:
                time=cursor+min(.5,row["encoded_clip_duration_s"]*.5)
                error=_video_sample_error(exe=exe,movie=final,at=time,
                                          reference_png=Path(row["image_file"]))
                visual_checks.append({"source_slide":row["source_slide"],
                    "source_candidate_id":row["candidate_target_id"],
                    "source_composite_corrected":
                        row["physically_original_composite_corrected"],
                    "decoded_MP4_time_s":round(time,4),
                    "actual_decoded_PDF_source_frame_error":float(error)})
                cursor+=row["encoded_clip_duration_s"]
                all_checked+=1
            results.append({"part":part_no,
                "source_original_slide_span":original_part["original_slide_span"],
                "actual_mp4_file":str(final),"actual_mp4_sha256":file_hash(final),
                "actual_encoded_duration_s":length,
                "all_real_source_clip_records":rows,
                "actual_decoded_source_pdf_frame_checks":visual_checks,
                "student_publication_authorized":False})
            print("ACTUAL_CORRECTED_SOURCE_MP4_PART",part_no,
                  "duration",length,"clips",len(rows),"decoded",len(visual_checks),
                  flush=True)
    require(corrected_count==10 and all_checked==106
            and all(file_hash(root/key)==sha for key,sha in before.items())
            and all(file_hash(Path(part["actual_mp4_file"]))==
                    part["actual_mp4_sha256"] for part in previous_parts),
            "Ten source math corrections did not preserve original media/input")
    result={"schema_version":1,"status":STATUS,
        "original_source_pdf_sha256":EXPECTED_SOURCE_SHA,
        "source_pr348_real_mp4_receipt_sha256":file_hash(video),
        "source_pr349_independent_real_media_audit_sha256":file_hash(audited),
        "source_pr350_mathematical_corrections_sha256":file_hash(corrections),
        "actually_reencoded_original_source_composite_corrections":corrected_count,
        "physically_unchanged_other_real_source_clips_reused":all_checked-corrected_count,
        "actual_real_H264_final_source_frames_decoded":all_checked,
        "all_66_original_source_cue_events_retained":True,
        "academic_source_math_66_spoken_elements_approved":False,
        "student_release_accepted_videos":0,
        "student_publication_authorized":False,"parts":results}
    with (dest/"PR351_TEN_ORIGINAL_SOURCE_CORRECTED_TWO_PART_MP4_REVIEW.json").open(
            "x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    parser=argparse.ArgumentParser()
    for key in ("original","full_review_receipt","source_plan_receipt",
                "independent_media_receipt","corrected_math_receipt","out"):
        parser.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    a=selectively_reencode(**vars(parser.parse_args()))
    print(json.dumps({k:v for k,v in a.items() if k!="parts"},indent=2))
if __name__=="__main__":main()
