"""Paid TTS launch guard: validate exact source-reviewed elements first.

No invocation of a provider without complete independently validated mapping,
reviewed utterance selections and separate billing authorization.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .figure_source_identity import require,_sha
from .verbatim_element_manifest import build
from .automatic_element_narration import inspect_text_only,AutomaticElementAudioError
from .element_plan_review_bridge import promoted, PlanPromotionError

MODEL="gemini-3.8-flash-lite-tts"
VOICE="Kore"

def preflight(*,source:Path,slides:Path,script:Path,
              draft:Path|None=None,selection:Path|None=None)->dict:
    source,slides,script=(Path(x).absolute() for x in (source,slides,script))
    require((draft is None)==(selection is None),
            "Both original draft and source-reviewed selection required together")
    proposal=build(source=source,slides=slides,script=script)
    mapping="MISSING_REVIEWED_VISUAL_SELECTION"
    request=None
    strict_machine=False
    try:
        machine=inspect_text_only(source=source,slides=slides,script=script)
        strict_machine=(
            machine["status"]=="EXACT_TEXT_ONLY_ELEMENT_MATCH_TECHNICAL"
            and machine["source_sha256"]==proposal["source_sha256"]
            and machine["slides_sha256"]==proposal["slides_sha256"]
            and machine["script_sha256"]==proposal["script_sha256"])
    except (AutomaticElementAudioError,ValueError,KeyError,AssertionError,OSError):
        pass
    if draft is not None or selection is not None:
        require(draft is not None and selection is not None,
                "Both original SHA-frozen candidate draft and source-reviewed selection needed")
        try:
            request=promoted(source=source,slides=slides,script=script,
                             draft_path=Path(draft),selection=Path(selection),
                             prepare_tts=True)
            require(request["status"]=="reviewed_element_tts_request_unapproved"
                    and request["tts_model"]==MODEL
                    and request["tts_voice"]==VOICE
                    and request["source_sha256"]==proposal["source_sha256"]
                    and request["slides_sha256"]==proposal["slides_sha256"]
                    and request["script_sha256"]==proposal["script_sha256"],
                    "Source-authorized TTS model/voice mismatches source")
            mapping="FULLY_REVIEWED_SELECTION_VALIDATED"
        except (PlanPromotionError,KeyError,ValueError):
            request=None
            mapping="REVIEWED_SELECTION_MISSING_OR_INVALID"
    elif strict_machine:
        mapping="TECHNICALLY_EXACT_TEXT_ONLY_SOURCE_PLAN_AVAILABLE"
    permitted=(request is not None or strict_machine)
    return {
        "schema_version":1,
        "status":"SOURCE_ELEMENT_TTS_INPUT_VERIFIED_BILLING_CONFIRMATION_REQUIRED"
                 if permitted else "ELEMENT_TTS_BLOCKED_SOURCE_MAPPING_UNVERIFIED",
        "original_source_sha256":proposal["source_sha256"],
        "original_slides_sha256":proposal["slides_sha256"],
        "original_script_sha256":proposal["script_sha256"],
        "verbatim_original_utterance_count":proposal["original_utterance_count"],
        "source_mapping_disposition":mapping,
        "effective_tts_model":MODEL,"effective_tts_voice":VOICE,
        "element_mapping_prerequisite_passed":bool(permitted),
        "paid_tts_execution_authorized":False,
        "primary_flash_lite_required":True,
        "fallback_cloud_tts_allowed_without_3_real_failed_attempts":False,
        "all_elements_same_effective_voice_required":True,
        "no_original_teaching_asset_overwrite":True,
        "video_publishing_authorized":False,
    }

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("source","slides","script"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--draft",type=Path)
    p.add_argument("--selection",type=Path)
    args=p.parse_args(argv)
    result=preflight(source=args.source,slides=args.slides,script=args.script,
                     draft=args.draft,selection=args.selection)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 2  # Preflight never spends money or claims synthesized WAV.
if __name__=="__main__":
    raise SystemExit(main())
