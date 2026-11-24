"""G3 original-publisher-linked OFFLINE media technical preflight.

Protect original source/slides/script identities, verify exact PDF-to-WAV slide
coverage, inspect actual separate video/audio decode and multipart timing.
Physical signal/container readiness is NOT transcription, pronunciation,
scientific accuracy, audiovisual visual-highlight acceptance or publication.
No provider/model Send, TTS generation or paid API call is performed.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import wave

import pymupdf

from .figure_source_identity import _sha,require
from .g3_multisection_autoforward_v71 import _verified_specs
from .recovery_registry import lookup_mechanism

KIND="g3_source_media_technical_preflight"
SIGNATURE="G3_MATCHED_ORIGINAL_TEXTBOOK_MEDIA_NOT_INDEPENDENTLY_TECHNICALLY_VERIFIED"
MECHANISM="CHECK_SOURCE_PINNED_WAV_AND_INDEPENDENT_VIDEO_AUDIO_DECODE_NO_RELEASE"
ROOT="g3_source_media_technical_preflight_v1"
STATUS="G3_SOURCE_MEDIA_TECHNICALLY_CHECKED_UNAPPROVED"
MAX_FILES=24
MAX_VIDEO_SECONDS=3600
MAX_WAV_SECONDS=120
MAX_DRIFT_SECONDS=4.0
MAX_PART_DRIFT_SECONDS=0.25
MP4=("slides.mp4","slides_part01.mp4","slides_part02.mp4")
SECTION={"Serway_8_2":"8.2","Serway_8_3":"8.3"}
_DURATION=re.compile(r"Duration:\s*(\d\d):(\d\d):(\d\d\.\d+)")


def _canon(data:dict)->bytes:
    return (json.dumps(data,sort_keys=True,ensure_ascii=False,
                       separators=(",",":"),allow_nan=False)+"\n").encode("utf8")


def _probe(*,path:Path,ffmpeg:str)->dict:
    """Probe/fully decode real H.264 and AAC streams separately.

    Older FFmpeg 4.0 may report 'Too many packets buffered' when decoding
    sparse lecture video and AAC together to one null muxer. This is a
    muxing artifact; independently decode each stream and require both OK.
    """
    meta=subprocess.run(
        [ffmpeg,"-hide_banner","-nostdin","-i",str(path)],
        capture_output=True,text=True,timeout=25)
    output=meta.stdout+"\n"+meta.stderr
    match=_DURATION.search(output)
    require(match is not None and "Video: h264" in output
            and "Audio: aac" in output,
            "Original MP4 missing parseable H264/AAC metadata")
    duration=3600*int(match.group(1))+60*int(match.group(2))+float(match.group(3))
    require(0.5<=duration<=MAX_VIDEO_SECONDS,
            "Original MP4 duration missing or unbounded")
    for kind,args in (
            ("video",["-map","0:v:0","-an"]),
            ("audio",["-map","0:a:0","-vn"])):
        output=subprocess.run(
            [ffmpeg,"-hide_banner","-nostdin","-v","error","-xerror",
             "-i",str(path),*args,"-f","null",os.devnull],
            capture_output=True,text=True,timeout=150)
        require(output.returncode==0 and not output.stderr.strip(),
                "Original "+kind+" MP4 stream failed full independent decode")
    return {"duration_seconds":round(duration,3),
            "video_codec":"h264","audio_codec":"aac",
            "full_video_stream_decoded":True,
            "full_audio_stream_decoded":True}


def inspect(*,spec:dict,media_root:Path,state_root:Path,
            probe=None,ffmpeg:str|None=None)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "G3 source-bound technical media preflight not executable")
    require(spec["section"] in SECTION,
            "Original G3 subsection must not be substituted")
    root=Path(state_root).absolute()
    media_root=Path(media_root).absolute()
    folder=Path(spec["source_folder"]).absolute()
    media=media_root/SECTION[spec["section"]]
    require(root.is_dir() and media_root.is_dir()
            and media.is_dir() and folder.is_dir()
            and not any(x.is_symlink()
                        for x in (root,media_root,media,folder))
            and not root.is_relative_to(media)
            and not media.is_relative_to(folder),
            "Real, separate G3 source and media folders required")
    source_hashes=spec["identity"]["source_inputs_sha256"]
    need=("source.pdf","slides.pdf","script.txt")
    require(set(source_hashes)==set(need),
            "Expected original source/slide/script identity")
    checked={}
    for name in need:
        p=media/name
        original=folder/name
        require(p.is_file() and not p.is_symlink()
                and original.is_file() and not original.is_symlink()
                and _sha(p)==_sha(original)==source_hashes[name],
                "Real G3 media source input differs from original textbook")
        checked[name]=source_hashes[name]
    with pymupdf.open(media/"slides.pdf") as pdf:
        pages=len(pdf)
    require(1<=pages<=MAX_FILES,
            "Original rendered G3 slide PDF has invalid size")
    names={x.name for x in media.iterdir()
           if x.is_file() and re.fullmatch(r"slide\d+\.wav",x.name)}
    require(names=={f"slide{i}.wav" for i in range(1,pages+1)},
            "Missing, duplicate or misnumbered G3 PCM slide WAV")
    wav_rows=[]
    total=0.0
    for i in range(1,pages+1):
        path=media/f"slide{i}.wav"
        require(not path.is_symlink(),"Redirected G3 original slide WAV")
        with wave.open(str(path),"rb") as w:
            require(w.getnchannels()==1 and w.getsampwidth()==2
                    and w.getframerate()==24000
                    and w.getcomptype()=="NONE",
                    "Unexpected original G3 WAV channel/rate/PCM format")
            dur=w.getnframes()/w.getframerate()
            require(0.1<=dur<=MAX_WAV_SECONDS,
                    "Original G3 narration WAV empty or unbounded")
        total+=dur
        wav_rows.append({"slide":i,"sha256":_sha(path),
                         "duration_seconds":round(dur,4)})
    actual=sorted(x.name for x in media.iterdir()
                  if x.is_file() and x.name.endswith(".mp4"))
    require(actual==sorted(MP4),
            "Original G3 video inventory is incomplete or unexpected")
    if probe is None:
        ffmpeg=ffmpeg or shutil.which("ffmpeg")
        require(type(ffmpeg) is str and bool(ffmpeg),
                "FFmpeg not available for full MP4 video/audio validation")
        probe=lambda path:_probe(path=path,ffmpeg=ffmpeg)
    videos=[]
    for name in MP4:
        path=media/name
        require(path.is_file() and not path.is_symlink()
                and 10000<=path.stat().st_size<=2_000_000_000,
                "Original G3 MP4 missing or too small for a real video")
        technical=probe(path)
        require(type(technical) is dict
                and technical.get("video_codec")=="h264"
                and technical.get("audio_codec")=="aac"
                and technical.get("full_video_stream_decoded") is True
                and technical.get("full_audio_stream_decoded") is True
                and type(technical.get("duration_seconds")) in (int,float)
                and 0.1<=technical["duration_seconds"]<=MAX_VIDEO_SECONDS,
                "G3 video/audio streams not independently decoded")
        videos.append({"file":name,"sha256":_sha(path),**technical})
    main=videos[0]["duration_seconds"]
    parts=sum(x["duration_seconds"] for x in videos[1:])
    require(all(x["duration_seconds"]<=600 for x in videos[1:]),
            "G3 multipart exceeded previously specified 600-second limit")
    require(abs(main-parts)<=MAX_PART_DRIFT_SECONDS
            and abs(main-total)<=MAX_DRIFT_SECONDS,
            "G3 PCM/full-video/multipart duration parity not established")
    evidence={"schema_version":1,"status":STATUS,
        "section":spec["section"],
        "original_source_inputs_sha256":checked,
        "original_slide_count":pages,
        "original_slide_wavs":wav_rows,
        "total_original_WAV_duration_seconds":round(total,3),
        "all_original_WAVs_PCM_24kHz_mono_16bit":True,
        "videos":videos,
        "full_video_duration_seconds":main,
        "multipart_total_duration_seconds":round(parts,3),
        "independent_video_audio_decoding_complete":True,
        "media_technical_integrity_is_academic_acceptance":False,
        "spoken_content_fidelity_verified":False,
        "acoustic_pronunciation_QA_complete":False,
        "scientific_source_QA_complete":False,
        "independent_video_visual_highlight_QA_complete":False,
        "second_subsection_academic_acceptance_complete":False,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "student_publication_authorized":False}
    scope=hashlib.sha256(_canon(evidence)).hexdigest()
    receipt={"scope_sha256":scope,**evidence}
    home=root/ROOT/spec["section"]
    require(not home.is_symlink(),
            "Redirected G3 original technical evidence checkpoint")
    home.mkdir(parents=True,exist_ok=True)
    dest=home/(scope+".json")
    body=_canon(receipt)
    require(not dest.is_symlink(),
            "Redirected G3 original technical receipt")
    if dest.exists():
        require(dest.is_file() and dest.read_bytes()==body,
                "Original G3 media source witness changed after checkpoint")
    else:
        with dest.open("xb") as out:
            out.write(body);out.flush();os.fsync(out.fileno())
    return {"status":STATUS,"section":spec["section"],
        "scope_sha256":scope,"receipt":str(dest),
        "slide_count":pages,"wav_duration_seconds":round(total,3),
        "video_duration_seconds":main,
        "part1_duration_seconds":videos[1]["duration_seconds"],
        "part2_duration_seconds":videos[2]["duration_seconds"],
        "stream_decode_errors":0,
        "independent_acoustic_QA_complete":False,
        "independent_video_QA_complete":False,
        "source_scientific_QA_complete":False,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "student_publication_authorized":False}


def materialize(*,manifest:Path,media_root:Path,state_root:Path,
                probe=None,ffmpeg:str|None=None)->dict:
    _,specs=_verified_specs(Path(manifest).absolute())
    require(len(specs)==2 and
            {s["section"] for s in specs}==set(SECTION),
            "G3 original Serway 8.2/8.3 source manifest required")
    results=[inspect(spec=s,media_root=media_root,
                     state_root=state_root,probe=probe,ffmpeg=ffmpeg)
             for s in specs]
    return {"status":"G3_TWO_ORIGINAL_SUBSECTIONS_MEDIA_TECHNICALLY_CHECKED_NO_RELEASE",
            "technical_subsections_checked":len(results),
            "sections":results,
            "independent_scientific_QA_complete":False,
            "independent_acoustic_QA_complete":False,
            "independent_video_QA_complete":False,
            "new_browser_sends":0,"new_paid_gemini_API_calls":0,
            "student_publication_authorized":False}


def main(argv=None)->int:
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--media-root",required=True,type=Path)
    p.add_argument("--state-dir",required=True,type=Path)
    args=p.parse_args(argv)
    print(json.dumps(materialize(manifest=args.manifest,
        media_root=args.media_root,state_root=args.state_dir),
        ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
