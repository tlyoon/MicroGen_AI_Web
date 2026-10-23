"""Independent actual decoded audio acceptance on real source-bound MP4 parts."""
from array import array
from pathlib import Path
import subprocess,sys
from .independent_encoded_audio_temporal_audit import _samples,_find_global_shift,AudioTemporalAuditError
from .highlight_video_preview import ffmpeg_path,probe_mp4

def _pcm(exe:str,path:Path,*,encoded:bool)->array:
    if not path.is_file() or path.is_symlink():
        raise AudioTemporalAuditError("Actual original WAV or encoded MP4 missing")
    options=["-map","0:a:0"] if encoded else ["-map","0:a:0"]
    cmd=[exe,"-nostdin","-hide_banner","-v","error","-i",str(path),*options,
         "-ac","1","-ar","24000","-acodec","pcm_s16le","-f","s16le","-t","599","pipe:1"]
    try:
        out=subprocess.run(cmd,capture_output=True,timeout=160)
    except (OSError,subprocess.TimeoutExpired) as e:
        raise AudioTemporalAuditError("Actual audio decode failed") from e
    if out.returncode!=0 or len(out.stdout)%2 or not 48000<=len(out.stdout)<599*48000:
        raise AudioTemporalAuditError("Corrupted, empty or overlong audio stream")
    return _samples(out.stdout)

def verify_encoded_part_audio(*,mp4:Path,wav:Path,ffmpeg_exe:str|None=None)->dict:
    mp4,wav=Path(mp4).absolute(),Path(wav).absolute()
    exe=ffmpeg_exe or ffmpeg_path()
    from .independent_encoded_audio_temporal_audit import _need
    meta=probe_mp4(mp4,exe=exe)
    _need(0<meta["duration_s"]<600,"Actual video not shorter than 600 seconds")
    source=_pcm(exe,wav,encoded=False)
    decoded=_pcm(exe,mp4,encoded=True)
    _need(abs(len(source)-len(decoded))/24000<=.15,
          "Actual encoded audio missing, truncated or padded")
    duration=len(decoded)/24000
    _need(abs(duration-meta["duration_s"])<=.2,
          "MP4 audio and video container durations disagree")
    span=2048
    centres=[round(len(decoded)*x) for x in (.2,.5,.8)]
    _need(min(centres)>span and max(centres)+span<len(source),
          "Real per-part audio too short for independent temporal windows")
    lag,scores=_find_global_shift(source,decoded,centres=centres,span=span,max_shift=1920)
    _need(abs(lag)<=1920 and min(scores)>=.78 and max(scores)<=1.000001,
          "Actual encoded MP4 audio fails original WAV temporal waveform fidelity")
    return {"status":"ACTUAL_DECODED_PART_AUDIO_TEMPORAL_INTEGRITY",
            "decoded_audio_duration_s":duration,"video_container_duration_s":meta["duration_s"],
            "window_correlations":[round(n,5) for n in scores],
            "global_shift_pcm_samples":lag,
            "mathematical_or_listening_approved":False,
            "student_publication_authorized":False}
