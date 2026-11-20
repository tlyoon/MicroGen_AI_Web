"""Independent read-only actual MP4-decoded audio vs original recorded WAV audit.

A mathematical/voice/listening QA gate is NOT inferred from this technical
comparison. Compare first/middle/end speech waveform windows to detect wrong,
shifted, truncated, repeated or replaced audio hidden by coarse spectrum checks.
"""
from __future__ import annotations
from array import array
import hashlib,json,math,subprocess,sys,wave
from pathlib import Path
from .highlight_video_preview import ffmpeg_path, probe_mp4

class AudioTemporalAuditError(ValueError):
    pass

def _need(condition:bool,message:str):
    if not condition:raise AudioTemporalAuditError(message)

def _sha(file:Path)->str:
    h=hashlib.sha256()
    with file.open("rb") as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()

def _samples(data:bytes)->array:
    _need(len(data)%2==0,"Malformed signed 16-bit PCM samples")
    samples=array("h");samples.frombytes(data)
    if sys.byteorder!="little":samples.byteswap()
    return samples

def _window_correlation(source:array,encoded:array,*,centre:int,
                        shift:int,span:int)->float:
    # Map decoded audio sample index into reference source + one global shift.
    begin=centre-span//2;start=begin+shift
    if begin<0 or begin+span>len(encoded) or start<0 or start+span>len(source):
        return -1.0
    a=encoded[begin:begin+span];b=source[start:start+span]
    am=sum(a)/span;bm=sum(b)/span
    va=vb=dot=0.0
    for x,y in zip(a,b):
        u=x-am;v=y-bm
        dot+=u*v;va+=u*u;vb+=v*v
    if va<span*100 or vb<span*100:return -1.0
    return dot/math.sqrt(va*vb)

def _find_global_shift(src:array,enc:array,centres:list[int],
                       *,span:int,max_shift:int)->tuple[int,list[float]]:
    # Prefer single global shift over independently shifting each window.
    # Coarse scan followed by fine scan; all three windows must match.
    def evaluate(offset):
        return [_window_correlation(src,enc,centre=center,shift=offset,span=span)
                for center in centres]
    winner=None
    for lag in range(-max_shift,max_shift+1,64):
        scores=evaluate(lag)
        strength=min(scores)
        if winner is None or strength>winner[0]:winner=(strength,lag,scores)
    assert winner is not None
    for lag in range(max(-max_shift,winner[1]-80),
                     min(max_shift,winner[1]+80)+1,4):
        scores=evaluate(lag);strength=min(scores)
        if strength>winner[0]:winner=(strength,lag,scores)
    return winner[1],winner[2]

def audit_encoded_original_pcm(*,original_folder:Path,review_folder:Path,
                               ffmpeg_exe:str|None=None)->dict:
    original_folder=Path(original_folder).absolute()
    review_folder=Path(review_folder).absolute()
    _need(review_folder!=original_folder and
          not review_folder.is_relative_to(original_folder),
          "Never treat original folder as review sandbox")
    src_files={x:original_folder/x for x in ("source.pdf","slides.pdf","script.txt")}
    manifest=review_folder/"source_aware_pilot_receipt.json"
    wav=review_folder/"narration.wav"
    mp4=review_folder/"element_highlight_review.mp4"
    for path in (*src_files.values(),manifest,wav,mp4):
        _need(path.is_file() and not path.is_symlink(),
              "Missing or symlinked original/pilot evidence")
    report=json.loads(manifest.read_text(encoding="utf8"))
    _need(report.get("status")=="REAL_ORIGINAL_SINGLE_UTTERANCE_ELEMENT_HIGHLIGHT_REVIEW_ONLY"
          and report.get("student_publication_authorized") is False
          and report.get("independent_second_ai_review_pass_complete") is False
          and report.get("original_WAV_is_new_element_TTS") is False,
          "Must audit only a non-approved original WAV preview")
    original_sha=report.get("original_source_asset_sha256")
    _need(type(original_sha) is dict and all(
          original_sha.get(key)==_sha(path) for key,path in src_files.items()),
          "Original textbook/slide/narration hashes disagree with saved pilot")
    recorded=_sha(wav);encoded=_sha(mp4)
    _need(recorded==report.get("original_audio_sha256")
          and encoded==report.get("encoded_mp4_sha256"),
          "Original recorded WAV or encoded MP4 differs from saved pilot")
    with wave.open(str(wav),"rb") as audio:
        _need(audio.getnchannels()==1 and audio.getsampwidth()==2
              and audio.getframerate()==24000 and audio.getnframes()>24000,
              "Expected actual nonempty mono 16-bit 24 kHz original WAV")
        source=_samples(audio.readframes(audio.getnframes()))
    exe=ffmpeg_exe or ffmpeg_path()
    meta=probe_mp4(mp4,exe=exe)
    decode=subprocess.run([exe,"-nostdin","-hide_banner","-loglevel","error",
        "-i",str(mp4),"-map","0:a:0","-vn",
        "-ac","1","-ar","24000","-c:a","pcm_s16le","-f","s16le",
        "-t","601","pipe:1"],capture_output=True,timeout=160)
    _need(decode.returncode==0 and
          len(decode.stdout)<=601*24000*2 and len(decode.stdout)>24000*2,
          "Could not decode bounded actual MP4 audio samples")
    decoded=_samples(decode.stdout)
    _need(abs(len(source)-len(decoded))/24000<=0.15
          and abs(meta["duration_s"]-len(decoded)/24000)<=0.18,
          "Wrong, truncated or padded audio duration in encoded MP4")
    span=2048
    centres=[round((len(decoded)-1)*fraction) for fraction in (0.2,0.5,0.8)]
    _need(len(source)>max(centres)+span and min(centres)>span,
          "Original WAV too short for three independent speech windows")
    lag,scores=_find_global_shift(source,decoded,centres=centres,span=span,
                                  max_shift=1920)
    _need(max(scores)<=1.0+1e-8 and min(scores)>=0.78
          and abs(lag)/24000<=0.08,
          "Original WAV does not match actual decoded MP4 speech windows")
    # Even if all samples sound right, a provider, speech text, accent, math
    # meaning or synchronized element timing must NOT be inferred.
    return {"status":"REAL_ENCODED_ORIGINAL_WAV_TEMPORAL_FIDELITY_TECHNICAL_ONLY",
       "original_audio_sha256":recorded,
       "actual_encoded_mp4_sha256":encoded,
       "decoded_video_duration_s":meta["duration_s"],
       "wav_sample_frames":len(source),"decoded_audio_sample_frames":len(decoded),
       "global_sample_alignment_offset":lag,
       "global_alignment_offset_seconds":round(lag/24000,5),
       "three_independent_window_correlations":[round(x,5) for x in scores],
       "sample_windows":[0.2,0.5,0.8],
       "mathematical_semantics_approved":False,
       "audio_spoken_words_listening_verified":False,
       "claim_new_kore_tts":False,
       "all_elements_highlight_sync_verified":False,
       "student_publication_authorized":False}
