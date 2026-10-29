"""AI source-reviewed utterances -> real Gemini Flash-Lite/Kore element WAV QA.

No automatic paid requests; actual external PCM WAV receipts are required.
PCM energy/clipping checks never claim speech-transcript or speaker proof.
"""
from __future__ import annotations
import wave
from pathlib import Path
import numpy as np
from .figure_source_identity import require,_sha
from .incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE
from .external_tts_delivery_proof import verify_external_tts_delivery

def prepare_original_ai_tts_jobs(*,folder:Path,job:dict,consensus:dict)->dict:
    folder=Path(folder).absolute()
    require(consensus.get("status")=="AI_DOUBLE_PASS_SOURCE_WITNESSED_ELEMENT_REVIEW"
        and consensus.get("source_sha256")==job.get("source_sha256")
        and consensus.get("slides_sha256")==job.get("slides_sha256")
        and consensus.get("script_sha256")==job.get("script_sha256")
        and consensus.get("original_utterance_count")==job.get("utterance_count"),
        "Only exact original fully reconciled AI review evidence permitted")
    for f,k in (("source.pdf","source_sha256"),("slides.pdf","slides_sha256"),
                ("script.txt","script_sha256")):
        require(_sha(folder/f)==job[k],"Original files changed")
    index={x["utterance_id"]:x for x in consensus["items"]}
    ready=[];pending=[]
    for slide in job["slides"]:
        for original in slide["utterances"]:
            choice=index.get(original["id"])
            require(choice and choice["spoken_sha256"]==original["spoken_sha256"],
                    "Original narration unit missing from AI consensus")
            if not choice["ai_double_pass_source_witnessed"]:
                pending.append(original["id"]);continue
            require(choice["target_id"] and len(choice["target_bbox_pdf_pt"])==4,
                    "A real visual source target is mandatory")
            ready.append({"job_id":original["id"],"spoken_text_sha256":original["spoken_sha256"],
                          "spoken_text":original["spoken_text"],"target_slide_index":slide["slide"],
                          "target_pdf_page_bbox_pt":choice["target_bbox_pdf_pt"],
                          "target_id":choice["target_id"],"model":DEFAULT_MODEL,"voice":DEFAULT_VOICE})
    return {"status":"AI_SOURCE_WITNESSED_ELEMENT_AUDIO_JOBS_NON_BILLED",
            "source_sha256":job["source_sha256"],"slides_sha256":job["slides_sha256"],
            "script_sha256":job["script_sha256"],"model":DEFAULT_MODEL,"voice":DEFAULT_VOICE,
            "job_count":len(ready),"jobs":ready,"unresolved":pending,
            "provider_requests_performed":0,"student_publication_authorized":False}

def inspect_genuine_tts_wav_deliveries(*,folder:Path,jobs:dict,receipts:list[dict])->dict:
    require(jobs.get("status")=="AI_SOURCE_WITNESSED_ELEMENT_AUDIO_JOBS_NON_BILLED"
            and jobs.get("model")==DEFAULT_MODEL and jobs.get("voice")==DEFAULT_VOICE
            and type(receipts) is list and len(receipts)==len(jobs["jobs"])>0,
            "Every independent original element requires actual provider delivery")
    seen=set();samples=[];issues=[];rate=None
    for j,r in zip(jobs["jobs"],receipts):
        p=Path(r.get("pcm_wav_path","")).absolute()
        require(p not in seen,"One WAV cannot stand in for several different utterances")
        seen.add(p)
        proven=verify_external_tts_delivery(job=j,delivery=r,original_folder=folder)
        with wave.open(str(p),"rb") as f:
            require(rate is None or f.getframerate()==rate,"Mixed sample rates")
            rate=f.getframerate()
            pcm=np.frombuffer(f.readframes(f.getnframes()),dtype="<i2").astype("float64")/32768
        rms=float(np.sqrt(np.mean(pcm*pcm)))
        clipping=float(np.mean(np.abs(pcm)>.998))
        silence=float(np.mean(np.abs(pcm)<.001))
        if rms<.004 or clipping>.02 or silence>.92:
            issues.append({"job_id":j["job_id"],"reason":"silence/clipping/energy"})
        samples.append({"job_id":j["job_id"],"wav_path":str(p),
                        "wav_sha256":proven["wav_sha256"],
                        "sample_rate":proven["sample_rate"],"sample_frames":proven["sample_frames"],
                        "rms":round(rms,5),"clipping_fraction":round(clipping,5),
                        "silence_fraction":round(silence,5)})
    return {"status":"ACTUAL_ELEMENT_PCM_SIGNAL_QA_PASS" if not issues else
                     "ELEMENT_PCM_NEEDS_REPAIR",
            "wav_samples_checked":len(samples),"actual_wav_receipts":samples,
            "signal_errors":issues,"spoken_content_fidelity_verified":False,
            "claimed_voice_acoustically_verified":False,"student_publication_authorized":False}
