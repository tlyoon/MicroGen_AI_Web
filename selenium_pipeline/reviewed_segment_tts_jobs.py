"""Per-element TTS job queue ONLY after original reviewed math mapping.

No provider call is made here; this is exact reviewed input for the
existing Gemini Flash-Lite/Kore TTS client once all source proofs pass.
"""
from pathlib import Path
import json,hashlib
from .element_tts_safe_handoff import preflight,MODEL,VOICE
from .element_plan_review_bridge import promoted
from .figure_source_identity import require,_sha

def prepare(*,source:Path,slides:Path,script:Path,
            draft:Path|None=None,selection:Path|None=None)->dict:
    original=[Path(p).absolute() for p in (source,slides,script)]
    sha=[_sha(p) for p in original]
    check=preflight(source=original[0],slides=original[1],
                    script=original[2],draft=draft,selection=selection)
    require(check["original_source_sha256"]==sha[0]
            and check["original_slides_sha256"]==sha[1]
            and check["original_script_sha256"]==sha[2]
            and check["paid_tts_execution_authorized"] is False,
            "Stale or improperly approved billing state")
    rows=[]
    if check["element_mapping_prerequisite_passed"]:
        require(draft is not None and selection is not None,
                "Machine-only lexical hints are not sufficient for math figure narration")
        request=promoted(source=original[0],slides=original[1],script=original[2],
            draft_path=Path(draft),selection=Path(selection),prepare_tts=True)
        require(request["status"]=="reviewed_element_tts_request_unapproved"
                and request["tts_model"]==MODEL and request["tts_voice"]==VOICE
                and request["source_sha256"]==sha[0]
                and request["slides_sha256"]==sha[1]
                and request["script_sha256"]==sha[2],
                "Provider job not source/voice-bound")
        used=set()
        for part in request["parts"]:
            for slide in part["slides"]:
                for element in slide["elements"]:
                    name=element["wav"]
                    require(isinstance(name,str) and name.endswith(".wav")
                            and name not in used and len(name)<180
                            and not any(c in name for c in "/\\:"),
                            "Untrusted element-WAV target path")
                    used.add(name)
                    rows.append({"wav":name,"slide":slide["slide"],
                       "element_id":element.get("element_id"),
                       "verbatim_script_text":element["spoken_text"],
                       "tts_model":MODEL,"voice":VOICE,
                       "exact_encoded_pcm_duration_verified":False,
                       "source_mathematics_reviewed":True})
    require([_sha(p) for p in original]==sha,"Source changed while preparing jobs")
    return {"schema_version":1,
        "status":("REVIEWED_ELEMENT_TTS_JOBS_PREPARED_NOT_SENT"
                  if rows else "ELEMENT_TTS_SOURCE_MAPPING_NOT_READY"),
        "source_sha256":sha[0],"slides_sha256":sha[1],
        "script_sha256":sha[2],"effective_model":MODEL,"effective_voice":VOICE,
        "jobs":rows,"job_count":len(rows),
        "primary_gemini_flash_lite":True,
        "same_effective_voice_across_all_wavs":True,
        "cloud_fallback_only_after_three_real_failures":True,
        "paid_provider_call_performed":False,
        "tts_audio_generated":False,
        "encoded_element_highlights_verified":False,
        "student_publication_authorized":False}

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser()
    for x in ("source","slides","script"):p.add_argument("--"+x,type=Path,required=True)
    for x in ("draft","selection","out"):p.add_argument("--"+x,type=Path)
    a=p.parse_args(argv)
    data=prepare(source=a.source,slides=a.slides,script=a.script,
                 draft=a.draft,selection=a.selection)
    if a.out:
        dest=a.out.absolute()
        require(not dest.exists() and dest.parent.is_dir()
                and not dest.is_relative_to(a.source.absolute().parent),
                "New non-production TTS job manifest destination required")
        with dest.open("x",encoding="utf8") as f:json.dump(data,f,indent=2,sort_keys=True)
    print(json.dumps({"status":data["status"],"job_count":data["job_count"],
                      "tts_audio_generated":False},indent=2))
    return 2
if __name__=="__main__":raise SystemExit(main())
