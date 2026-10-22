"""Independently decode muxed MP4 audio and compare source PCM spectral features.

Validates existence and approximate audio identity at each event time. It
cannot verify that the decoded audio speaks a mathematical utterance.
"""
from __future__ import annotations
import subprocess,wave
from pathlib import Path
import numpy as np
from .figure_source_identity import require
from .highlight_video_preview import ffmpeg_path,probe_mp4

def audit_muxed_audio_segment_fingerprints(*,mp4:Path,wavs:list[Path],
                                             score_threshold:float=.65)->dict:
    mp4=Path(mp4).absolute()
    wavs=[Path(x).absolute() for x in wavs]
    require(mp4.is_file() and type(score_threshold) is float
            and .5<=score_threshold<=.95
            and 2<=len(wavs)<=40 and len(set(wavs))==len(wavs),
            "Independently addressable original PCM chunks required")
    signals=[];rate=None;durations=[]
    for f in wavs:
        require(f.is_file() and not f.is_symlink() and f.suffix.lower()==".wav",
                "Original external WAV missing")
        with wave.open(str(f),"rb") as w:
            require(w.getnchannels()==1 and w.getsampwidth()==2
                    and w.getcomptype()=="NONE","Only original PCM16 mono is supported")
            require(rate is None or rate==w.getframerate(),"Inconsistent sample rate")
            rate=w.getframerate()
            data=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype(np.float64)
            require(.3*rate<=len(data)<120*rate,"Audio segment is not independently inspectable")
            signals.append(data)
            durations.append(len(data))
    exe=ffmpeg_path()
    probe=probe_mp4(mp4,exe=exe)
    require(0<probe["duration_s"]<600 and abs(probe["duration_s"]-sum(durations)/rate)<.4,
            "Actual encoded audiovisual duration must match original PCM clock")
    ff=subprocess.run([exe,"-hide_banner","-loglevel","error","-nostdin",
                       "-i",str(mp4),"-map","0:a:0","-ac","1","-ar",str(rate),
                       "-f","s16le","-"],capture_output=True,timeout=120)
    require(ff.returncode==0 and len(ff.stdout)>=sum(durations)*2*.9,
            "Actual encoded MP4 audio cannot be decoded to original sample clock")
    decoded=np.frombuffer(ff.stdout[:len(ff.stdout)//2*2],dtype="<i2").astype(np.float64)
    window=int(.18*rate)
    scores=[];cursor=0
    for source,nframes in zip(signals,durations):
        sample=source[(nframes-window)//2:(nframes+window)//2]
        a=np.abs(np.fft.rfft(sample*np.hanning(len(sample))))
        require(float(np.linalg.norm(a))>100,
                "Original verified element audio is spectrally empty")
        center=cursor+nframes//2
        best=-1.
        for offset in range(-int(.08*rate),int(.08*rate)+1,max(1,int(.015*rate))):
            start=center-window//2+offset
            if start<0 or start+window>len(decoded):continue
            x=decoded[start:start+window]
            b=np.abs(np.fft.rfft(x*np.hanning(len(x))))
            den=float(np.linalg.norm(a)*np.linalg.norm(b))
            if den>0:best=max(best,float(a@b/den))
        require(best>=score_threshold,
                "Independently decoded MP4 PCM spectrum disagrees with timed source element WAV")
        scores.append(round(best,4));cursor+=nframes
    return {"status":"INDEPENDENT_MUXED_PCM_SEGMENT_AUDIO_PRESENT_AND_TIMED",
            "source_element_count":len(signals),"spectral_similarity":scores,
            "audio_segments_are_real_spoken_words_verified":False,
            "source_mathematical_meaning_verified":False,
            "student_publication_authorized":False}
