"""Complete original source -> explicit review -> unpaid Flash Lite TTS handoff.

Only actual reviewer selections can become TTS requests. This module is
strictly cost-free and never authorizes incomplete academic coverage.
"""
from __future__ import annotations
from pathlib import Path
from .figure_source_identity import require,_sha
from .source_review_packet_bridge import validate_signed_review_packet
from .incremental_chunk_tts_requests import prepare_chunk_jobs,save_unpaid_job_manifest

def stage_reviewed_unpaid_audio_jobs(*,folder:Path,packet:dict,
                                    destination:Path|None=None)->dict:
    folder=Path(folder).absolute()
    review=validate_signed_review_packet(folder=folder,packet=packet)
    validated=review["source_bound_validated_choices"]
    require(validated["tts_billing_authorized"] is False
            and validated["student_publication_authorized"] is False,
            "Review provenance must not supply paid execution permission")
    source,slides,script=(folder/n for n in ("source.pdf","slides.pdf","script.txt"))
    result=prepare_chunk_jobs(source=source,slides=slides,script=script,reviewed=validated)
    require(result["job_count"]==review["reviewed_utterances"]
            and result["original_narration_utterances_unreviewed"]==review["unreviewed_utterances"]
            and result["voice"]=="Kore"
            and result["model"]=="gemini-3.8-flash-lite-tts"
            and result["paid_tts_execution_authorized"] is False,
            "Exact reviewed-scope, primary TTS model or voice changed")
    out={"status":"UNPAID_SOURCE_ATTESTED_ELEMENT_AUDIO_WORKLIST",
         "candidate_tts_jobs":result,
         "original_utterances":review["reviewed_utterances"]+review["unreviewed_utterances"],
         "attested_utterances":review["reviewed_utterances"],
         "unresolved_utterances":review["unreviewed_utterances"],
         "all_segments_eligible_for_audio":review["unreviewed_utterances"]==0,
         "physical_audio_chunks_generated":0,
         "paid_tts_execution_authorized":False,
         "cloud_fallback_authorized":False,
         "same_voice_required":True,
         "production_speech_sync_verified":False,
         "student_publication_authorized":False}
    if destination is not None:
        destination=Path(destination).absolute()
        require(destination.parent.is_dir() and not destination.exists()
                and destination.suffix==".json"
                and not destination.is_relative_to(folder),
                "Unpaid manifests must be staged as new independent JSON only")
        save_unpaid_job_manifest(result,output=destination,original_folder=folder)
    require(all(_sha(folder/k)==result[sha] for k,sha in (
        ("source.pdf","source_sha256"),("slides.pdf","slides_sha256"),
        ("script.txt","script_sha256"))),
        "Original source mutated during unpaid TTS request preparation")
    return out
