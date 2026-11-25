"""Checkpoint-safe narrated lecture split on slide time boundaries (<600 s).

Automatic post-render repair. Never edits source PDF, narration or WAV. A
complete original video is archived before replacement, and all parts are
decoded and hashed before publication. No API calls or highlight claims.
"""
from __future__ import annotations
import hashlib,json,os,re,shutil,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
from .video_ffmpeg import ffmpeg_executable

CAP_SECONDS=600.0
PLAN_SECONDS=570.0
def sha(p:Path)->str:
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def jsonread(p:Path)->dict:
    return json.loads(p.read_text(encoding="utf8"))
def atomic_json(p:Path,obj:dict)->None:
    tmp=p.with_name("."+p.name+".pending")
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    os.replace(tmp,p)
def duration(exe:str,p:Path)->float:
    r=subprocess.run([exe,"-hide_banner","-i",str(p)],
        capture_output=True,text=True,errors="replace",timeout=60)
    s=r.stdout+r.stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)",s)
    if not m:raise ValueError(f"Unable to inspect duration: {p}")
    return round(int(m[1])*3600+int(m[2])*60+float(m[3]),3)
def verify_media(exe:str,p:Path)->float:
    d=duration(exe,p)
    if not 0<d<CAP_SECONDS:raise ValueError(f"Video part outside 600s: {p}: {d}")
    r=subprocess.run([exe,"-hide_banner","-nostdin","-v","error",
        "-i",str(p),"-f","null",os.devnull],capture_output=True,
        text=True,errors="replace",timeout=900)
    if r.returncode or r.stderr.strip():raise RuntimeError(f"Decoded media error {p}: {r.stderr[-500:]}")
    return d
def plan(wavs:list[float],maximum:float=PLAN_SECONDS)->list[tuple[int,int,float,float]]:
    if not wavs or any(not 0<x<maximum for x in wavs):
        raise ValueError("Missing, invalid, or individually oversized source slide duration")
    sections=[];start=0;elapsed=0.0;total=0.0
    for i,seconds in enumerate(wavs):
        if elapsed and elapsed+seconds+0.35*(i-start+1)>maximum:
            sections.append((start,i,total-elapsed,total))
            start=i;elapsed=0.0
        elapsed+=seconds;total+=seconds
    sections.append((start,len(wavs),total-elapsed,total))
    return sections
def _preflight(folder:Path):
    names=("source.pdf","slides.pdf","script.txt","slides.mp4","slide_narration_sync.json","tts_fidelity_report.json")
    if not all((folder/n).is_file() for n in names):
        raise FileNotFoundError("Missing final narrated source/video chain")
    from .slide_narration_sync import verify
    verify(folder)
    q=jsonread(folder/"tts_fidelity_report.json")
    s=q.get("summary",{})
    sync=jsonread(folder/"slide_narration_sync.json")
    if s.get("slides")!=sync.get("pages") or s.get("passed")!=s.get("slides") or s.get("blocking_failures") or s.get("review"):
        raise ValueError("Acoustic QA is not passing for all source slides")
    wav=sync.get("wav",[])
    if len(wav)!=s.get("slides"):
        raise ValueError("WAV and slide counts disagree")
    durations=[]
    for i,a in enumerate(wav,1):
        f=folder/f"slide{i}.wav"
        if not f.is_file() or sha(f)!=a.get("sha256"):
            raise ValueError(f"Slide {i} WAV source changed")
        durations.append(float(a["duration_s"]))
    return durations
def enforce(folder:Path)->dict:
    folder=Path(folder)
    wavs=_preflight(folder)
    exe=ffmpeg_executable()
    src=folder/"slides.mp4"
    manifestfile=folder/"lecture_parts_manifest.json"
    if manifestfile.exists():
        old=jsonread(manifestfile)
        if (old.get("status")=="technical_length_control_passed"
          and old.get("source_sha256")==sha(folder/"source.pdf")
          and old.get("slides_sha256")==sha(folder/"slides.pdf")
          and old.get("script_sha256")==sha(folder/"script.txt")
          and all((folder/p["filename"]).is_file() and
             sha(folder/p["filename"])==p["sha256"] and
             0<float(p["duration_seconds"])<600
             for p in old.get("parts",[]))):
            return {"status":"existing_verified","parts":len(old["parts"])}
        raise RuntimeError("Conflicting/stale part manifest; do not overwrite")
    if list(folder.glob("slides_part*.mp4")):
        raise RuntimeError("Unexpected preexisting multipart MP4 without manifest")
    full=duration(exe,src)
    sections=plan(wavs)
    if full<CAP_SECONDS:
        sections=[(0,len(wavs),0.0,sum(wavs))]
    else:
        if len(sections)<2:raise RuntimeError("Overlong video with unsplittable slide groups")
    scale=full/sum(wavs)
    if not 0.96<=scale<=1.04:
        raise ValueError("Encoded video timing differs substantially from source WAV timing")
    stage=folder/".microgen_length_stage_v1"
    if stage.exists():
        raise RuntimeError("Existing length stage may represent interrupted process; reconcile first")
    stage.mkdir()
    names=["slides.mp4" if i==0 else f"slides_part{i+1:02d}.mp4" for i in range(len(sections))]
    parts=[]
    full_hash=sha(src)
    try:
        for n,(first,last,start,end) in enumerate(sections):
            name=names[n]
            target=stage/name
            begin=round(start*scale,3)
            stop=round(end*scale,3) if n<len(sections)-1 else full
            if len(sections)==1:
                shutil.copy2(src,target)
            else:
                result=subprocess.run([exe,"-hide_banner","-nostdin","-loglevel","error",
                    "-ss",f"{begin:.3f}","-i",str(src),
                    "-t",f"{max(.01,stop-begin):.3f}",
                    "-map","0:v:0","-map","0:a:0",
                    "-c:v","libx264","-preset","fast","-crf","19","-pix_fmt","yuv420p",
                    "-c:a","aac","-b:a","192k","-movflags","+faststart",
                    "-y",str(target)],capture_output=True,text=True,errors="replace",timeout=1200)
                if result.returncode:raise RuntimeError(f"Part encode failed: {result.stderr[-600:]}")
            sec=verify_media(exe,target)
            parts.append({"filename":name,"sha256":sha(target),"duration_seconds":sec,
                 "slide_start":first+1,"slide_end":last,"slide_count":last-first,
                 "source_video_time_start":begin,"source_video_time_end":stop,
                 "decoded_all_frames":True})
            print(f"[length-control] validated part {n+1}/{len(sections)}: {sec:.2f}s slides {first+1}-{last}",flush=True)
        if sum(p["slide_count"] for p in parts)!=len(wavs):
            raise RuntimeError("Part list misses source slide")
        if len(sections)>1:
            h=folder/".history"/("original_long_mp4_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
            h.mkdir(parents=True,exist_ok=False)
            shutil.copy2(src,h/"slides_full_original.mp4")
            if sha(h/"slides_full_original.mp4")!=full_hash:
                raise RuntimeError("Preserved full original video hash mismatch")
            receipt=folder/".microgen_completion.json"
            d=jsonread(receipt) if receipt.exists() else None
            if d is not None and d.get("final_sha256",{}).get("slides.mp4")!=full_hash:
                raise RuntimeError("Old completion receipt no longer matches original full video")
            for i,name in enumerate(names):
                os.replace(stage/name,folder/name)
            if d is not None:
                d["final_sha256"]["slides.mp4"]=parts[0]["sha256"]
                d["multipart_video_count"]=len(parts)
                d["length_control_original_sha256"]=full_hash
                atomic_json(receipt,d)
        document={"schema_version":1,"status":"technical_length_control_passed",
            "source_sha256":sha(folder/"source.pdf"),"slides_sha256":sha(folder/"slides.pdf"),
            "script_sha256":sha(folder/"script.txt"),"technical_only":True,
            "independent_visual_highlight_acceptance":"not_performed_user_skipped",
            "full_g3_release_accepted":False,"total_parts":len(parts),
            "original_video_sha256":full_hash,"original_video_preserved":len(parts)>1,
            "parts":parts,"checked_utc":datetime.now(timezone.utc).isoformat()}
        atomic_json(manifestfile,document)
        return {"status":"length_control_passed","parts":len(parts),
            "original_duration_s":full,"part_durations_s":[p["duration_seconds"] for p in parts]}
    finally:
        if stage.is_dir():
            shutil.rmtree(stage,ignore_errors=True)
def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--folder",type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(enforce(args.folder),indent=2),flush=True)
if __name__=="__main__":main()
