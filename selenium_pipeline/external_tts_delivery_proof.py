"""Independently validate provider audio identity without claiming listening QA."""
from __future__ import annotations
import re,math,wave
from pathlib import Path
from .figure_source_identity import require,_sha
from .incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE

def verify_external_tts_delivery(*,job:dict,delivery:dict,original_folder:Path)->dict:
    require(type(job) is dict and type(delivery) is dict
            and delivery.get("job_id")==job.get("job_id")
            and delivery.get("spoken_text_sha256")==job.get("spoken_text_sha256")
            and delivery.get("model")==DEFAULT_MODEL
            and delivery.get("voice")==DEFAULT_VOICE
            and delivery.get("provider_receipt_present") is True
            and type(delivery.get("execution_id")) is str
            and re.fullmatch(r"[A-Za-z0-9_.:-]{8,128}",delivery["execution_id"]),
            "Actual Flash-Lite identity and provider execution proof required")
    folder=Path(original_folder).absolute()
    path=Path(delivery.get("pcm_wav_path","")).absolute()
    require(path.is_file() and path.suffix.lower()==".wav"
            and not path.is_symlink() and not path.is_relative_to(folder)
            and _sha(path)==delivery.get("wav_sha256"),
            "External unique WAV must not overwrite original teaching sources")
    with wave.open(str(path),"rb") as w:
        frames=w.getnframes();rate=w.getframerate()
        require(w.getnchannels()==1 and w.getsampwidth()==2
                and w.getcomptype()=="NONE" and 8000<=rate<=96000
                and .15<=frames/rate<120,"Audio format/duration outside review encoder contract")
    require(_sha(path)==delivery["wav_sha256"],"WAV modified during receipt check")
    return {"status":"EXTERNAL_PROVIDER_ATTESTED_PCM_BYTES_CHECKED",
            "job_id":job["job_id"],"provider_execution_id":delivery["execution_id"],
            "original_spoken_text_sha256":job["spoken_text_sha256"],
            "wav_sha256":delivery["wav_sha256"],"sample_rate":rate,
            "sample_frames":frames,"measured_duration_s":frames/rate,
            "audio_actually_speaks_requested_text_verified":False,
            "voice_identity_acoustically_verified":False,
            "student_publication_authorized":False}
