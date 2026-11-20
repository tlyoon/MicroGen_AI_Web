"""Prepare exact, cost-uncommitted Flash-Lite/Kore chunk requests from reviewed elements.

The provider cannot run from this manifest alone; a separate authorized
runtime billing guard and fresh source recheck are required before any API/UI
calls. Never infer spoken timings from legacy whole-slide WAV pauses.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from .figure_source_identity import require,_sha

DEFAULT_MODEL="gemini-3.8-flash-lite-tts"
DEFAULT_VOICE="Kore"

def prepare_chunk_jobs(*,source:Path,slides:Path,script:Path,reviewed:dict)->dict:
    originals=[Path(p).absolute() for p in (source,slides,script)]
    hashes=[_sha(f) for f in originals]
    require(type(reviewed) is dict
            and reviewed.get("status")=="EXPLICIT_NONLITERAL_ELEMENT_SELECTIONS_SOURCE_BOUND"
            and [reviewed.get(k) for k in ("source_sha256","slides_sha256","script_sha256")]==hashes
            and reviewed.get("tts_billing_authorized") is False
            and reviewed.get("student_publication_authorized") is False
            and type(reviewed.get("selected_segments")) is list,
            "Fresh validated source-bound reviewed utterance map required")
    jobs=[];names=set()
    for item in reviewed["selected_segments"]:
        require(type(item) is dict
                and item.get("reviewer_attestation_present") is True
                and item.get("independently_proven_spoken_audio_fidelity") is False
                and type(item.get("spoken_text")) is str
                and bool(item["spoken_text"].strip())
                and type(item.get("spoken_text_sha256")) is str
                and hashlib.sha256(item["spoken_text"].encode("utf8")).hexdigest()
                    ==item["spoken_text_sha256"]
                and type(item.get("slide")) is int
                and 1<=item["slide"]<=500
                and type(item.get("bbox_pdf_pt")) is list
                and len(item["bbox_pdf_pt"])==4,
                "Reviewed narration segment is stale or unproven")
        name=item["utterance_id"]
        require(type(name) is str
                and re.fullmatch(r"s[0-9]{3}\.utterance\.[0-9]{3}",name)
                and name not in names,
                "Invalid duplicate or unsafe stable source utterance ID")
        names.add(name)
        jobs.append({
            "job_id":name,
            "original_spoken_text":item["spoken_text"],
            "spoken_text_sha256":item["spoken_text_sha256"],
            "target_slide_index":item["slide"],
            "target_element_id":item["target_id"],
            "target_pdf_page_bbox_pt":item["bbox_pdf_pt"],
            "source_page":item["original_source_page"],
            "voice_id":DEFAULT_VOICE,
            "tts_model":DEFAULT_MODEL,
            "proposed_wav_filename":name.replace(".","_")+".wav",
            "tts_generated":False,
            "audio_fidelity_to_script_verified":False,
            "speaker_timing_verified":False,
        })
    require(all(_sha(f)==digest for f,digest in zip(originals,hashes)),
            "Original TTS source was modified while preparing requests")
    return {"status":"REVIEWED_ELEMENT_CHUNK_REQUESTS_NOT_YET_DISPATCHED",
            "source_sha256":hashes[0],"slides_sha256":hashes[1],
            "script_sha256":hashes[2],
            "model":DEFAULT_MODEL,"voice":DEFAULT_VOICE,
            "job_count":len(jobs),"chunk_jobs":jobs,
            "original_narration_utterances_unreviewed":
                reviewed["unreviewed_utterance_count"],
            "primary_gemini_flash_lite_attempts_required":True,
            "cloud_fallback_without_three_failed_primary_attempts":False,
            "paid_tts_execution_authorized":False,
            "all_segments_physically_generated":False,
            "actual_highlight_spoken_timing_verified":False,
            "student_publication_authorized":False}

def save_unpaid_job_manifest(job:dict,*,output:Path,original_folder:Path)->Path:
    output=Path(output).absolute()
    original_folder=Path(original_folder).absolute()
    require(job.get("status")=="REVIEWED_ELEMENT_CHUNK_REQUESTS_NOT_YET_DISPATCHED"
            and job.get("paid_tts_execution_authorized") is False
            and job.get("student_publication_authorized") is False
            and output.suffix.lower()==".json" and output.parent.is_dir()
            and not output.is_relative_to(original_folder),
            "Only new external reviewed no-billing manifests can be staged")
    with output.open("x",encoding="utf8") as h:
        json.dump(job,h,indent=2,ensure_ascii=False)
        h.write("\n")
    return output
