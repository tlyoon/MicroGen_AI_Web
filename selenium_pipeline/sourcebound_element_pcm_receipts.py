"""Verify genuine separately supplied PCM element chunks for an unbilled review plan.

The verified WAV bytes, original spoken text and claimed TTS voice are distinct
evidence: a waveform alone cannot prove that someone spoke the script or
that a provider actually used the declared voice. Never promote to published.
"""
from __future__ import annotations
import math,wave
from pathlib import Path
from .figure_source_identity import require,_sha
from .incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE

def inspect_supplied_element_wavs(*,folder:Path,jobs:dict,receipts:list[dict])->dict:
    folder=Path(folder).absolute()
    require(folder.is_dir() and not folder.is_symlink()
            and type(jobs) is dict
            and jobs.get("status")=="REVIEWED_ELEMENT_CHUNK_REQUESTS_NOT_YET_DISPATCHED"
            and jobs.get("paid_tts_execution_authorized") is False
            and jobs.get("student_publication_authorized") is False
            and jobs.get("model")==DEFAULT_MODEL and jobs.get("voice")==DEFAULT_VOICE
            and type(jobs.get("chunk_jobs")) is list
            and jobs.get("job_count")==len(jobs["chunk_jobs"])
            and type(receipts) is list and len(receipts)==len(jobs["chunk_jobs"])
            and 1<=len(receipts)<=40,
            "Real reviewed element TTS jobs and every distinct audio receipt required")
    before={k:_sha(folder/name) for k,name in (
        ("source_sha256","source.pdf"),("slides_sha256","slides.pdf"),
        ("script_sha256","script.txt"))}
    require(all(jobs.get(k)==digest for k,digest in before.items()),
            "Original textbook/slide/script changed since TTS preparation")
    clips=[];uids=set();paths=set();spec=None;total_frames=0
    for job,entry in zip(jobs["chunk_jobs"],receipts):
        require(type(job) is dict and type(entry) is dict
                and entry.get("job_id")==job.get("job_id")
                and entry.get("original_spoken_text_sha256")==job.get("spoken_text_sha256")
                and entry.get("claimed_voice")==DEFAULT_VOICE
                and entry.get("claimed_model")==DEFAULT_MODEL
                and entry.get("provider_output_not_verified_acoustically") is True
                and job.get("tts_generated") is False
                and job.get("audio_fidelity_to_script_verified") is False,
                "Declaring actual TTS generation or voice identity as proof is prohibited")
        uid=job["job_id"]
        path=Path(entry.get("wav_path","")).absolute()
        require(uid not in uids and path not in paths
                and path.is_file() and not path.is_symlink()
                and not path.is_relative_to(folder) and path.suffix.lower()==".wav"
                and _sha(path)==entry.get("wav_sha256"),
                "Source WAV modification/reuse, identity mismatch or unsafe input")
        uids.add(uid);paths.add(path)
        with wave.open(str(path),"rb") as audio:
            fmt=(audio.getnchannels(),audio.getsampwidth(),audio.getframerate(),
                 audio.getcomptype())
            frames=audio.getnframes()
            require(fmt[0]==1 and fmt[1]==2 and fmt[3]=="NONE"
                    and 8000<=fmt[2]<=96000 and (spec is None or fmt==spec)
                    and .15<=frames/fmt[2]<120,
                    "PCM format/rate/duration inconsistent or incompatible with encoder")
            spec=fmt;total_frames+=frames
            data=audio.readframes(frames)
            require(any(data[i:i+2]!=b"\x00\x00" for i in range(0,len(data),2)),
                    "Silent original audio cannot silently count as narrated element")
        clips.append({"job_id":uid,"wav_path":str(path),
                      "voice_id":DEFAULT_VOICE,"wav_sha256":entry["wav_sha256"]})
    require(total_frames/spec[2]<540
            and all(_sha(folder/name)==before[k] for k,name in (
                ("source_sha256","source.pdf"),("slides_sha256","slides.pdf"),
                ("script_sha256","script.txt"))),
            "WAV output exceeds safe part or source changed")
    return {"status":"EXTERNALLY_SUPPLIED_PCM_ELEMENT_WAV_BYTES_VERIFIED_REVIEW_ONLY",
            "source_sha256":before["source_sha256"],
            "slides_sha256":before["slides_sha256"],
            "script_sha256":before["script_sha256"],
            "audio_clip_count":len(clips),"measured_pcm_duration_s":total_frames/spec[2],
            "encoder_clip_inputs":clips,
            "actual_audio_text_fidelity_independently_verified":False,
            "claimed_voice_acoustically_independently_verified":False,
            "tts_provider_execution_authorized_by_this_check":False,
            "source_semantics_academically_verified":False,
            "student_publication_authorized":False}
