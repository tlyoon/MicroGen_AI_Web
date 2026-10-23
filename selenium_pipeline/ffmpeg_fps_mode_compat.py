"""Version-checked video sync options for modern and FFmpeg 4 encoders.

Choosing -vsync vfr/cfr for FFmpeg <5 is the documented historical FFmpeg
equivalent of per-stream -fps_mode. Fail closed on unknown executables, not
silently alter H.264 timing, slide counts, frame emphasis or audio alignment.
"""
from __future__ import annotations
import re,subprocess

class FfmpegSyncOptionError(ValueError):
    pass

def fps_mode_flags(ffmpeg_exe:str,mode:str)->list[str]:
    if type(ffmpeg_exe) is not str or not ffmpeg_exe.strip() or mode not in ("cfr","vfr"):
        raise FfmpegSyncOptionError("Require bounded FFmpeg executable and CFR/VFR mode")
    try:
        result=subprocess.run([ffmpeg_exe,"-hide_banner","-version"],
            capture_output=True,text=True,errors="replace",timeout=15)
    except (FileNotFoundError,OSError,subprocess.TimeoutExpired) as exc:
        raise FfmpegSyncOptionError("FFmpeg capability could not be safely determined") from exc
    if result.returncode:
        raise FfmpegSyncOptionError("FFmpeg version probe failed")
    match=re.search(r"(?im)^ffmpeg version\s+(?:n)?(\d+)(?:\.|\s|[-+])",
                    result.stdout[:1200])
    if not match:
        raise FfmpegSyncOptionError("Unrecognized FFmpeg version; refuse frame-timing assumption")
    major=int(match.group(1))
    if major<3 or major>15:
        raise FfmpegSyncOptionError("Unsupported untested FFmpeg major version")
    return ["-fps_mode",mode] if major>=5 else ["-vsync",mode]
