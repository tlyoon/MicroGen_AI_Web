"""One original-source-verified Kore math TTS for corrected signed triangle.

Reuses existing owner-approved routine paid TTS cost and credential
guards, one single provider attempt, source script SHA, no original
modification, and no false phonetic pass from provider metadata.
"""
from __future__ import annotations
import argparse,hashlib,json,wave
from pathlib import Path
from .element_plan_autodraft import file_hash
from .original_thomas84_signed_triangle_source_repair import (
    STATUS as SOURCE_STATUS,CORRECTED_SPOKEN)
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_corrected_kore_candidate_batch import _single_gemini_key_environment
from .gemini38_tts_interactions import (
    require_modern_tts_sdk,generate_3_8_kore_wav,APPROVED_VOICE)
MODEL="gemini-3.8-flash-lite-tts"
STATUS="REAL_GENUINE_CORRECTED_SLIDE8_KORE_PCM_ONE_REQUEST_AWAITING_OFFLINE_QA"
def generate(*,original:Path,corrected_source:Path,out:Path,
             dispatch_single_routine_tts:bool=False)->dict:
    root=Path(original).resolve()
    pair=Path(corrected_source).resolve();dest=Path(out).absolute()
    require(root.is_dir() and pair.is_dir() and
            dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent)
            and not dest.is_relative_to(pair),
            "One safe new destination for protected TTS audio")
    proof=json.loads((pair/"SIGNED_TRIANGLE_SOURCE_REPAIR_NO_AUDIO.json").read_text(encoding="utf8"))
    script=json.loads((pair/"script_tts.json").read_text(encoding="utf8"))
    require(proof.get("status")==SOURCE_STATUS
            and proof.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and proof.get("changed_actual_narration_sentence_indices")==[2]
            and proof.get("corrected_spoken_math_text")==CORRECTED_SPOKEN
            and file_hash(pair/"script_tts.json")==proof["new_corrected_exact_TTS_script_sha256"]
            and file_hash(pair/"slides.pdf")==proof[
              "new_corrected_signed_triangle_and_final_question_PDF_SHA256"]
            and script["slides"][7]["tts_text"].count(CORRECTED_SPOKEN)==1
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and proof.get("student_publication_authorized") is False,
            "Corrected exact source math/voice not verified")
    require(dispatch_single_routine_tts,
            "Never dispatch paid TTS without owner's existing routine authorization flag")
    require_modern_tts_sdk()
    env=_single_gemini_key_environment()
    require(bool(env.get("GEMINI_API_KEY_1")),"No authorized billing credentials")
    before={name:file_hash(root/name) for name in (
        "source.pdf","slides.pdf","slides.tex","script_tts.json",
        "slide8.wav","slide17.wav")}
    dest.mkdir()
    started={"status":"SINGLE_VERIFIED_SLIDE8_KORE_REQUEST_STARTED",
      "requested_voice":APPROVED_VOICE,"model":MODEL,
      "source_pdf_sha256":EXPECTED_SOURCE_SHA,
      "corrected_source_proof_sha256":file_hash(pair/"SIGNED_TRIANGLE_SOURCE_REPAIR_NO_AUDIO.json"),
      "tts_math_text_sha256":hashlib.sha256(CORRECTED_SPOKEN.encode("utf8")).hexdigest(),
      "provider_attempt_budget":1,"automatic_retry_allowed":False,
      "student_publication_authorized":False}
    with (dest/"ATTEMPT_STARTED_DO_NOT_RETRY.json").open("x",encoding="utf8") as f:
        json.dump(started,f,indent=2);f.write("\n")
    observation={}
    try:
        import google.genai as genai
        with genai.Client(api_key=env["GEMINI_API_KEY_1"]) as client:
            actual=generate_3_8_kore_wav(
                client,CORRECTED_SPOKEN,MODEL,APPROVED_VOICE,
                request_observation=observation)
        wav=dest/"slide08_sentence02_signed_reference_triangle_Kore.wav"
        with wav.open("xb") as f:f.write(actual)
        with wave.open(str(wav),"rb") as a:
            require(a.getframerate()==24000
                    and a.getnchannels()==1 and a.getsampwidth()==2
                    and a.getcomptype()=="NONE"
                    and 5<a.getnframes()/24000<90,
                    "Actual new paid math audio not genuine 24k mono 16bit PCM")
            duration=a.getnframes()/24000
        require(all(file_hash(root/name)==sha for name,sha in before.items()),
                "Protected original course media changed")
        result={"schema_version":1,"status":STATUS,
          "requested_model":MODEL,"requested_voice":APPROVED_VOICE,
          "original_textbook_sha256":EXPECTED_SOURCE_SHA,
          "actual_WAV_path":str(wav),"actual_WAV_sha256":file_hash(wav),
          "actual_WAV_duration_seconds":duration,
          "corrected_narration_text":CORRECTED_SPOKEN,
          "corrected_narration_text_sha256":started["tts_math_text_sha256"],
          "paired_source_proof_sha256":started["corrected_source_proof_sha256"],
          "actual_provider_calls":1,"automatic_retries":0,
          "provider_request_id":observation.get("provider_request_id"),
          "independent_offline_math_pronunciation_accepted":False,
          "full_66_source_math_semantics_accepted":False,
          "student_publication_authorized":False,"originals_modified":False}
        with (dest/"REAL_TTS_AUDIO_CANDIDATE_UNAPPROVED.json").open("x",encoding="utf8") as f:
            json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
        return result
    except Exception as exc:
        with (dest/"FAIL_STOP_NO_AUTO_RETRY.json").open("x",encoding="utf8") as f:
            json.dump({"status":"TTS_PROVIDER_ATTEMPT_FAILED_NO_RETRY",
                       "error_class":type(exc).__name__,
                       "safe_error":str(exc)[:340],
                       "student_publication_authorized":False},f,indent=2)
        raise
def main():
    p=argparse.ArgumentParser()
    for name in ("original","corrected_source","out"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    p.add_argument("--dispatch-single-routine-tts",action="store_true")
    r=generate(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in r.items() if k!="corrected_narration_text"},indent=2))
if __name__=="__main__":main()
