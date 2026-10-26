"""Strict offline intake of five actual WAV candidates, NEVER voice/text approval.

Audio waveform cannot prove words spoken, voice identity, or Gemini provenance.
Every candidate is quarantined until independent content/review acceptance.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,wave
from .offline_corrected_bundle_verify import verify_original_five_bundle,strict_json,need

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()

def inspect_corrected_five_pcm(*,original:Path,bundle:Path,audio_dir:Path)->dict:
    verified=verify_original_five_bundle(original=original,bundle=bundle)
    original=Path(original).absolute();audio_dir=Path(audio_dir).absolute()
    need(audio_dir.is_dir() and not audio_dir.is_symlink()
         and not audio_dir.is_relative_to(original),
         "Candidate WAV folder must be separate from protected original media")
    doc=strict_json(Path(bundle)/"FIVE_CORRECTED_SEGMENTS_UNAPPROVED.json")
    historical={sha(p) for p in original.glob("slide*.wav")}
    need(len(historical)>0,"Missing protected historical audio inventory")
    expected={u["tts_audio_relative_path_expected"] for u in
              doc["source_verified_tts_highlight_units"]}
    present={p.name for p in audio_dir.iterdir() if p.is_file() and p.suffix.lower()==".wav"}
    need(not (present-expected),"Unknown extra WAV inserted in the corrected batch")
    rows=[]
    for unit in doc["source_verified_tts_highlight_units"]:
        name=unit["tts_audio_relative_path_expected"]
        path=audio_dir/name
        if not path.exists():
            rows.append({"utterance_id":unit["original_utterance_id"],
                         "text_sha256":unit["corrected_tts_text_sha256"],
                         "waveform_present":False,"voice_approved":False})
            continue
        need(path.is_file() and not path.is_symlink()
             and 10000<=path.stat().st_size<=30000000,
             "Invalid, linked or unbounded replacement WAV")
        digest=sha(path)
        need(digest not in historical,
             "Historic slide WAV disguised as corrected five-utterance speech")
        try:
            with wave.open(str(path),"rb") as wav:
                rate=wav.getframerate();frames=wav.getnframes()
                need(wav.getnchannels()==1 and wav.getsampwidth()==2
                     and wav.getcomptype()=="NONE" and 16000<=rate<=48000
                     and .25<=frames/rate<150,
                     "Expected bounded uncompressed mono 16-bit speech")
                # Nonzero samples only establish the bytes are not digital silence.
                raw=wav.readframes(frames)
                need(any(raw),"Digital silence is not a genuine speech candidate")
        except (wave.Error,EOFError,OSError) as e:
            raise ValueError("WAV cannot be decoded as PCM") from e
        rows.append({"utterance_id":unit["original_utterance_id"],
                     "text_sha256":unit["corrected_tts_text_sha256"],
                     "wav_sha256":digest,"duration_s":round(frames/rate,4),
                     "waveform_present":True,
                     "provider_attested":False,"same_voice_Kore_verified":False,
                     "actual_spoken_words_match_text_verified":False,
                     "independent_source_math_accepted":False})
    got=sum(bool(u["waveform_present"]) for u in rows)
    return {"status":("OFFLINE_FIVE_PCM_CANDIDATES_ONLY_UNAPPROVED" if got==5
                      else "WAITING_FOR_FIVE_ACTUAL_CORRECTED_PCM_SEGMENTS"),
            "verified_original_preview_count":verified["verified_image_count"],
            "candidate_audio_count":got,"expected_audio_count":5,"units":rows,
            "same_voice_approved":False,"spoken_content_approved":False,
            "independent_mathematics_approved":False,"tts_replacement_eligible":False,
            "synchronized_video_approved":False,"student_publication_authorized":False}
