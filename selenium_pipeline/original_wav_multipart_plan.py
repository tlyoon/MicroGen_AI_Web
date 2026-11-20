"""Read-only, whole-slide WAV boundary planning for strict multipart video.

The plan never edits audio, splits a spoken phrase or claims an MP4 exists.
Actual *encoded* duration and timed element highlight validation still govern.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import wave
from pathlib import Path

import pymupdf

from .figure_source_identity import _sha, require

WAV_NAME = re.compile(r"slide([1-9][0-9]*)\.wav\Z", re.I)
DEFAULT_AUDIO_BUDGET_SECONDS = 540.0


def choose_contiguous_wav_parts(seconds:list, *, audio_budget_s:float=540.0)->list[tuple[int,int]]:
    require(type(seconds) is list and 1<=len(seconds)<=200
            and type(audio_budget_s) in (float,int) and not isinstance(audio_budget_s,bool)
            and math.isfinite(audio_budget_s) and 60<=audio_budget_s<=540,
            "Invalid bounded WAV durations or safe audio-only budget")
    for sec in seconds:
        require(type(sec) in (float,int) and not isinstance(sec,bool)
                and math.isfinite(sec) and 0<sec<=audio_budget_s,
                "Invalid, empty or unsplittable slide WAV")
    # Minimal number of parts, then minimize worst whole-part duration to
    # avoid a lopsided 530s / 100s result when two ~315s parts work.
    # All boundaries stay strictly between entire slide audio files.
    duration=[0.0]
    for x in seconds:
        duration.append(duration[-1]+float(x))
    dp=[None]*(len(seconds)+1)
    dp[0]=(0,0.0,[])
    for end in range(1,len(seconds)+1):
        best=None
        for start in range(end):
            prior=dp[start]
            span=duration[end]-duration[start]
            if prior is None or span>audio_budget_s+1e-7:
                continue
            candidate=(prior[0]+1,max(prior[1],span),prior[2]+[(start,end)])
            if best is None or (candidate[0],candidate[1],candidate[2]) < (best[0],best[1],best[2]):
                best=candidate
        dp[end]=best
    require(dp[-1] is not None and 1<=len(dp[-1][2])<=40,
            "Safe contiguous multipart audio plan cannot be built")
    return dp[-1][2]


def inspect_original_slide_wav_plan(folder:Path, *, audio_budget_s:float=540.0)->dict:
    root=Path(folder).absolute()
    for part in (root,*root.parents):
        require(not part.is_symlink()
                and not getattr(part,"is_junction",lambda:False)(),
                "Original lecture directory cannot be a linked path")
    require(root.is_dir(),"Expected original lecture folder")
    source,slides=root/"source.pdf",root/"slides.pdf"
    require(source.is_file() and slides.is_file(),
            "Original source and slides PDFs required")
    files=list(root.glob("slide*.wav"))
    require(1<=len(files)<=200, "Expected bounded slide-level WAV inventory")
    by_index={}
    for p in files:
        match=WAV_NAME.fullmatch(p.name)
        require(match is not None and p.is_file() and not p.is_symlink()
                and 44<=p.stat().st_size<=60_000_000,
                "Invalid slide-level WAV path or file size")
        index=int(match.group(1))
        require(index not in by_index,"Duplicate slide WAV index")
        by_index[index]=p
    require(set(by_index)==set(range(1,len(files)+1)),
            "Missing or out-of-sequence slide WAV; refuse partial plan")
    with pymupdf.open(slides) as deck:
        require(len(deck)==len(files) and len(deck)<=200,
                "Audio slide count does not match original rendered PDF")
    originals={str(p):_sha(p) for p in [source,slides,*by_index.values()]}
    seconds=[]
    records=[]
    for i in range(1,len(files)+1):
        p=by_index[i]
        try:
            with wave.open(str(p),"rb") as wav:
                require(wav.getcomptype()=="NONE" and wav.getframerate()>0
                        and wav.getnframes()>0,
                        "Original slide WAV must be nonempty uncompressed PCM")
                dur=wav.getnframes()/wav.getframerate()
                require(math.isfinite(dur) and dur>0,
                        "Invalid real WAV duration")
        except (wave.Error,EOFError,OSError) as exc:
            require(False,f"Invalid/unreadable slide WAV {i}: {type(exc).__name__}")
        records.append({"slide_index":i,"relative_name":p.name,
                        "sha256":originals[str(p)],
                        "duration_s":round(dur,4)})
        seconds.append(dur)
    ranges=choose_contiguous_wav_parts(seconds,audio_budget_s=audio_budget_s)
    parts=[]
    for j,(start,end) in enumerate(ranges,1):
        audio=sum(seconds[start:end])
        parts.append({
            "part_id":f"part_{j:02d}",
            "slide_start":start+1,
            "slide_end":end,
            "slide_count":end-start,
            "original_wav_duration_sum_s":round(audio,4),
            "within_audio_only_budget":audio<=audio_budget_s+1e-7,
            "encoded_MP4_duration_verified":False,
            "narrated_element_highlight_verified":False,
            "original_figure_math_verified":False,
        })
    require(all(_sha(Path(path))==digest for path,digest in originals.items()),
            "Original PDF or WAV changed during audio planning")
    return {
        "schema_version":1,
        "status":"ORIGINAL_SLIDE_WAV_MULTIPART_CANDIDATE_NOT_RENDERED",
        "source_sha256":originals[str(source)],
        "slides_sha256":originals[str(slides)],
        "audio_budget_s":audio_budget_s,
        "post_audio_margin_to_strict_600_seconds_s":600-audio_budget_s,
        "original_wav_count":len(files),
        "total_original_wav_duration_s":round(sum(seconds),4),
        "wav_evidence":records,
        "proposed_part_count":len(parts),
        "proposed_parts":parts,
        "audio_regeneration_required_for_boundary":False,
        "source_slide_or_WAV_modified":False,
        "encoded_video_part_strictly_below_600_verified":False,
        "speech_element_highlights_verified":False,
        "human_academic_listening_review_verified":False,
        "student_publication_authorized":False,
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--audio-budget-s",type=float,default=DEFAULT_AUDIO_BUDGET_SECONDS)
    a=p.parse_args(argv)
    print(json.dumps(inspect_original_slide_wav_plan(
        a.folder,audio_budget_s=a.audio_budget_s),indent=2,sort_keys=True))
    # An audio grouping is not encoded media acceptance.
    return 2


if __name__=="__main__":
    raise SystemExit(main())
