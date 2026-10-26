"""Accurately transcode original encoded lessons into external REVIEW_ONLY MP4 clips.

This is an infrastructure/encoding proof, NOT corrected narration or synced
highlighted production media. Splits use approximate original WAV clock and
original historical video, and never overwrite a historical file.
"""
from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .production_video_contract import _mp4_duration
from .video_ffmpeg import ffmpeg_executable

class OfflineClipError(ValueError):pass
def require(ok,message):
    if not ok:raise OfflineClipError(message)
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def encode_six_original_review_clips(*,chapter:Path,output_dir:Path,
                                     encoder:str|None=None)->dict:
    original=Path(chapter).absolute()
    out=Path(output_dir).absolute()
    require(original.is_dir() and not original.is_symlink()
            and out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(original),
            "REVIEW_ONLY external exclusive output directory required")
    exe=encoder or ffmpeg_executable()
    prepared=[]
    for topic in ("8.4","8.5","8.6"):
        folder=original/topic
        plan=inspect_original_slide_wav_plan(folder)
        mp4=folder/"slides.mp4"
        require(mp4.is_file() and not mp4.is_symlink(),"Historical video missing")
        historical_sha=sha(mp4)
        encoded_length=_mp4_duration(mp4,ffmpeg=exe)
        require(encoded_length>600,"No known historical overlong video")
        durations=[row["duration_s"] for row in plan["wav_evidence"]]
        parts=plan["proposed_parts"]
        require(len(parts)==2,"Genuine original scoped three-section two-part plan changed")
        windows=[]
        for i,part in enumerate(parts):
            start=sum(durations[:part["slide_start"]-1])
            # Last part includes any original encoding tail, never cuts it off.
            end=(encoded_length if i==len(parts)-1 else
                 sum(durations[:part["slide_end"]]))
            require(0<=start<end<=encoded_length+.0001 and end-start<540,
                    "Source segment duration or boundary unsafe")
            windows.append((start,end))
        prepared.append((topic,mp4,historical_sha,plan,windows))
    out.mkdir()
    encoded=[]
    for topic,mp4,historical_sha,plan,windows in prepared:
        for i,(start,end) in enumerate(windows,1):
            target=out/f"REVIEW_ONLY_HISTORICAL_{topic.replace('.','_')}_part_{i:02d}.mp4"
            cmd=[exe,"-hide_banner","-nostdin","-loglevel","error","-n",
                 "-ss",f"{start:.4f}","-i",str(mp4),
                 "-t",f"{end-start:.4f}","-map","0:v:0","-map","0:a:0",
                 "-c:v","libx264","-preset","ultrafast","-crf","30",
                 "-pix_fmt","yuv420p","-c:a","aac","-b:a","80k",
                 "-movflags","+faststart",str(target)]
            run=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
            require(run.returncode==0 and target.is_file() and target.stat().st_size>2000,
                    "FFmpeg historical preview transcode failed: "+run.stderr[-320:])
            actual=_mp4_duration(target,ffmpeg=exe)
            require(0<actual<600 and abs(actual-(end-start))<1.2,
                    "Actual transcoded duration is not aligned with requested original window")
            encoded.append({"section":topic,"part_id":f"part_{i:02d}",
                            "path":str(target),"sha256":sha(target),
                            "provisional_requested_original_start_s":round(start,4),
                            "provisional_requested_original_end_s":round(end,4),
                            "actual_encoded_duration_s":actual,
                            "historic_MP4_source_sha256":historical_sha,
                            "source_pdf_sha256":plan["source_sha256"],
                            "original_audio_used":True,
                            "corrected_math_or_Kore_audio_used":False,
                            "per_element_highlight_present_verified":False,
                            "student_publication_authorized":False})
    require(len(encoded)==6,"Exactly six source-media preview parts required")
    for topic,mp4,historical_sha,_,_ in prepared:
        require(sha(mp4)==historical_sha,
                "Protected original MP4 changed during remux")
    result={"schema_version":1,"status":"SIX_GENUINE_HISTORICAL_REVIEW_MP4_CLIPS_NOT_LECTURE_REPLACEMENTS",
            "clips":encoded,"clip_count":len(encoded),
            "source_video_corrected":False,"math_independently_approved":False,
            "all_clip_stream_durations_strictly_below_600":True,
            "actual_speech_to_highlight_synchronization_approved":False,
            "student_publication_authorized":False,
            "original_files_modified":False}
    with (out/"UNAPPROVED_HISTORICAL_CLIPS.json").open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2)
    return result

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chapter",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args(argv)
    r=encode_six_original_review_clips(chapter=a.chapter,output_dir=a.out)
    print(json.dumps({"status":r["status"],
                      "clip_count":r["clip_count"],
                      "durations_s":[x["actual_encoded_duration_s"] for x in r["clips"]],
                      "new_corrected_clips":0,"published":False}))
if __name__=="__main__":main()
