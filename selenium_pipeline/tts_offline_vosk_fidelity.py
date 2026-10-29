"""Independent, unprompted *offline* Vosk WAV-QA fallback on Windows.

The owner-approved relaxed sound-alike contract is checked by the
existing evaluate_slide/evaluate_tts_soundalike pipeline. Offline Vosk
is evidence from genuine decoded audio, NOT a guarantee of exact words
or human-acoustic certification. Only select with explicit per-device
MICROGEN_TTS_QA_BACKEND=offline_vosk and verified local official model.
No Gemini QA API, Whisper, download, remote service or auto-publication.
"""
from __future__ import annotations
import array
import hashlib
import json
import os
import subprocess
import sys
import wave
from functools import lru_cache
from pathlib import Path

_MODEL_ZIP_SHA256="30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498"
_MODEL_NAME="vosk-model-small-en-us-0.15"

def sha_file(path:Path)->str:
    digest=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):
            digest.update(chunk)
    return digest.hexdigest()

def approved_assets()->tuple[Path,Path]:
    model=Path(os.environ.get("MICROGEN_TTS_QA_VOSK_MODEL","")).expanduser()
    packages=Path(os.environ.get("MICROGEN_TTS_QA_VOSK_PACKAGES","")).expanduser()
    if (not model.is_dir() or model.is_symlink()
            or model.name!=_MODEL_NAME
            or not (model/"am"/"final.mdl").is_file()
            or not packages.is_dir() or packages.is_symlink()):
        raise RuntimeError("Offline Vosk model/packages not explicitly installed on Dell; no QA pass")
    archive=model.parent/(_MODEL_NAME+".zip")
    if not archive.is_file() or sha_file(archive)!=_MODEL_ZIP_SHA256:
        raise RuntimeError("Offline speech model ZIP SHA-256 not official verified artifact")
    return model.resolve(),packages.resolve()

@lru_cache(maxsize=1)
def recognizer_model(model_dir:str,packages_dir:str):
    # Add previously verified isolated local package, not an untrusted
    # model-generated package or a network-downloaded dependency.
    if packages_dir not in sys.path:
        sys.path.insert(0,packages_dir)
    from vosk import Model,SetLogLevel
    SetLogLevel(-1)
    return Model(model_dir)

def check_pcm(audio:Path)->dict:
    if not audio.is_file() or audio.is_symlink():
        raise RuntimeError("Missing or symlinked source WAV")
    with wave.open(str(audio),"rb") as wav:
        rate=wav.getframerate();frames=wav.getnframes()
        if not (wav.getnchannels()==1 and wav.getsampwidth()==2
                and wav.getcomptype()=="NONE" and 16000<=rate<=48000
                and 0.25<frames/rate<180):
            raise RuntimeError("Invalid PCM16 speech parameters/duration")
        samples=array.array("h",wav.readframes(frames))
    if sys.byteorder!="little":
        samples.byteswap()
    if not samples:
        raise RuntimeError("Empty actual speech frames")
    magnitude=sum(abs(n) for n in samples)/len(samples)
    clip_ratio=sum(abs(n)>=32760 for n in samples)/len(samples)
    if magnitude<80:
        raise RuntimeError("Audio near silence; Vosk cannot approve")
    if clip_ratio>0.015:
        raise RuntimeError("Audio clipping prevents speech approval")
    return {"pcm_mean_abs_amplitude":round(magnitude,3),
            "pcm_clipping_fraction":round(clip_ratio,7),
            "duration_seconds":round(frames/rate,3)}

def unprompted_audio_review(audio:Path,reference_script:str)->dict:
    # Callers independently compute exact soundalike acceptance and
    # math-critical tokens from the returned genuine heard transcript.
    if not reference_script.strip():
        raise ValueError("Missing original narration")
    model_dir,pkg_dir=approved_assets()
    pcm=check_pcm(audio)
    model=recognizer_model(str(model_dir),str(pkg_dir))
    from vosk import KaldiRecognizer
    from .video_ffmpeg import ffmpeg_executable
    audio16=subprocess.run(
        [ffmpeg_executable(),"-nostdin","-v","error","-i",str(audio),
         "-ac","1","-ar","16000","-f","s16le","pipe:1"],
        capture_output=True,timeout=90,check=False)
    if audio16.returncode!=0 or len(audio16.stdout)<16000:
        raise RuntimeError("Offline Vosk cannot decode genuine audio")
    worker=KaldiRecognizer(model,16000)
    worker.SetWords(True)
    segments=[]
    for i in range(0,len(audio16.stdout),8000):
        if worker.AcceptWaveform(audio16.stdout[i:i+8000]):
            segments.append(json.loads(worker.Result()))
    segments.append(json.loads(worker.FinalResult()))
    heard=" ".join(word.get("word","") for segment in segments
                   for word in segment.get("result",[])).strip()
    if len(heard.split())<3:
        raise RuntimeError("Offline actual waveform has insufficient recognizable speech")
    return {
        "transcript":heard,
        "pronunciation_issues":[],
        "critical_token_issues":[],
        "audio_defects":[],
        "notes":("OFFLINE_VOSK_UNPROMPTED_REAL_WAV; model SHA verified; "
                 "transcript subject to soundalike/critical-math checks; "
                 "not an independent human listening/voice certification"),
        "offline_vosk_pcm_audit":pcm,
        "offline_vosk_audio_sha256":sha_file(audio),
        "offline_vosk_model_zip_sha256":_MODEL_ZIP_SHA256,
        "human_voice_certified":False,
    }
