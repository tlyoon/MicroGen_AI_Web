"""Untrusted WAV container QA before element timing and video staging; no ASR."""
import hashlib,wave
from pathlib import Path
def inspect_pcm_wav_envelope(paths:list[Path],*,max_program_seconds:float=540)->dict:
    if (type(paths) is not list or not paths or len(paths)>1000
        or type(max_program_seconds) not in (int,float)
        or not 0<max_program_seconds<600):
        raise ValueError("Bounded PCM sub-600 program required")
    seen=set();pieces=[];total=0
    for path in paths:
        p=Path(path)
        if not p.is_file() or p.is_symlink() or p.resolve() in seen:
            raise ValueError("Every real utterance WAV must be distinct and regular")
        seen.add(p.resolve())
        with wave.open(str(p),"rb") as wav:
            ch,sw,rate,frames=wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getnframes()
            if ch!=1 or sw!=2 or rate!=24000 or frames<=0:
                raise ValueError("Require genuine nonempty mono signed-16 24kHz PCM")
            decoded=wav.readframes(frames)
            if len(decoded)!=frames*2:
                raise ValueError("Original PCM frames truncated")
        duration=frames/rate
        total+=duration
        if total>=max_program_seconds:
            raise ValueError("PCM timeline exceeds safe video-part duration")
        pieces.append({"wav_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                       "sample_frames":frames,"duration_seconds":duration})
    return {"status":"ORIGINAL_PCM_CONTAINER_AND_DURATION_PRECHECK_ONLY",
        "pcm_count":len(pieces),"total_seconds":total,"parts":pieces,
        "narration_semantics_verified":False,"single_voice_acoustically_verified":False,
        "student_publication_authorized":False}
