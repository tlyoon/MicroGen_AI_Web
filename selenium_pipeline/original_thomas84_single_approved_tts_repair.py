"""One source-locked routine Gemini Flash-Lite TTS audition for corrected §8.4.

One authorized provider request, no automatic retry, no fallback or claim
that audio pronounces every mathematical word without independent QA.
Never touch original protected textbook, WAVs or video.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import wave

from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_paired_question_source_fix import (
    STATUS as PAIRED_STATUS,CORRECTED_NARRATION)
from .original_corrected_kore_candidate_batch import (
    _single_gemini_key_environment)
from .gemini38_tts_interactions import (
    APPROVED_VOICE,require_modern_tts_sdk,generate_3_8_kore_wav)

MODEL="gemini-3.8-flash-lite-tts"
STATUS="NEW_ONE_SHOT_CORRECTED_SLIDE17_GEMINI_KORE_PCM_AWAITS_INDEPENDENT_VOICE_QA"

def source_preflight(*,original:Path,bundle:Path,out:Path)->dict:
    root=Path(original).resolve()
    b=Path(bundle).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and b.is_dir()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent)
            and not dest.is_relative_to(b),
            "Only external exclusive one-shot TTS candidate output allowed")
    r=json.loads((b/"PAIR_SOURCE_PROOF_NO_AUDIO.json").read_text(encoding="utf8"))
    tts=json.loads((b/"script_tts.json").read_text(encoding="utf8"))
    require(r.get("status")==PAIRED_STATUS
            and r.get("source_original_narration_slide")==17
            and r.get("exact_changed_source_original_sentence_indices")==[2]
            and r.get("real_synthesized_replacement_WAV_available") is False
            and r.get("student_publication_authorized") is False
            and tts["slides"][16]["tts_text"].count(CORRECTED_NARRATION)==1
            and file_hash(b/"slides.tex")==r["corrected_tex_sha256"]
            and file_hash(b/"slides.pdf")==r["corrected_pdf_sha256"]
            and file_hash(b/"script_tts.json")==r["corrected_script_tts_sha256"]
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Corrected source question or TTS audio text source is unverifiable")
    return r

def one_approved_correction(*,original:Path,bundle:Path,out:Path,
                            dispatch_single_routine_tts:bool=False)->dict:
    root=Path(original).resolve()
    b=Path(bundle).resolve()
    dest=Path(out).absolute()
    source=source_preflight(original=root,bundle=b,out=dest)
    require(dispatch_single_routine_tts,
            "Provider dispatch needs explicit authorized routine-TTS flag")
    require_modern_tts_sdk()
    # Existing environment/cost guard validates owner-permitted TTS and loads
    # credentials without printing/logging or retaining the key.
    env=_single_gemini_key_environment()
    import google.genai as genai
    require(bool(env.get("GEMINI_API_KEY_1")),
            "No owner-authorized voice credentials")
    from .tts_flexible_pronunciation_contract import QA_VERSION
    originals={name:file_hash(root/name) for name in (
        "source.pdf","slides.tex","slides.pdf","script_tts.json",
        "slide17.wav","slide11.wav")}
    dest.mkdir()
    started={"status":"SINGLE_ROUTINE_PAID_FLASH_LITE_TTS_DISPATCH_STARTED",
             "model_requested":MODEL,"voice_requested":APPROVED_VOICE,
             "text_sha256":__import__("hashlib").sha256(
                 CORRECTED_NARRATION.encode("utf8")).hexdigest(),
             "paired_source_proof_sha256":file_hash(b/"PAIR_SOURCE_PROOF_NO_AUDIO.json"),
             "original_textbook_sha256":EXPECTED_SOURCE_SHA,
             "requests_permitted":1,"automatic_retry_count":0,
             "provider_dispatch_submitted":True,
             "student_publication_authorized":False}
    with (dest/"ATTEMPT_STARTED_DO_NOT_RETRY.json").open("x",encoding="utf8") as f:
        json.dump(started,f,indent=2);f.write("\n")
    observation={}
    try:
        with genai.Client(api_key=env["GEMINI_API_KEY_1"]) as client:
            raw=generate_3_8_kore_wav(
                client,CORRECTED_NARRATION,MODEL,APPROVED_VOICE,
                request_observation=observation)
        candidate=dest/"slide17_sentence02_corrected_Kore_original_math.wav"
        with candidate.open("xb") as f:
            f.write(raw)
        with wave.open(str(candidate),"rb") as wav:
            require(wav.getnchannels()==1 and wav.getsampwidth()==2
                    and wav.getframerate()==24000
                    and 2<wav.getnframes()/24000<100,
                    "New Gemini 3.8 audio must be real mono 24k PCM16")
            seconds=wav.getnframes()/24000
        require(all(file_hash(root/name)==digest
                    for name,digest in originals.items()),
                "Protected original source modified during paid TTS attempt")
        result={"schema_version":1,"status":STATUS,
            "requested_provider":MODEL,"requested_voice":APPROVED_VOICE,
            "owner_routine_tts_authorization_guard_passed":True,
            "new_actual_pcm_file":str(candidate),
            "new_actual_pcm_sha256":file_hash(candidate),
            "new_actual_pcm_duration_s":seconds,
            "spoken_source_exact_text":CORRECTED_NARRATION,
            "text_hash":started["text_sha256"],
            "actual_paid_provider_request_count":1,
            "local_auto_retry_count":0,
            "provider_request_id":observation.get("provider_request_id"),
            "independent_acoustic_correct_pronunciation_accepted":False,
            "all_historical_source_math_audio_approved":False,
            "student_publication_authorized":False,
            "source_originals_modified":False}
        with (dest/"SUCCESS_CANDIDATE_NOT_VOICE_APPROVED.json").open(
                "x",encoding="utf8") as f:
            json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
        return result
    except Exception as error:
        with (dest/"FAILED_DO_NOT_AUTO_RETRY.json").open("x",encoding="utf8") as f:
            json.dump({"status":"SINGLE_AUTHORIZED_TTS_ATTEMPT_FAILED",
                       "error_class":type(error).__name__,
                       "safe_error":str(error)[:450],
                       "manual_or_explicit_retry_required":True,
                       "automatic_retry_count":0,
                       "student_publication_authorized":False},f,indent=2)
            f.write("\n")
        raise

def main():
    p=argparse.ArgumentParser()
    for name in ("original","bundle","out"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--dispatch-single-routine-tts",action="store_true")
    result=one_approved_correction(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in result.items()
                      if k!="spoken_source_exact_text"},indent=2))
if __name__=="__main__":main()
