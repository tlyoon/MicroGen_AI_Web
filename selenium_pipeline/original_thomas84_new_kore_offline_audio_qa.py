"""Reusable independent offline, source-locked math-aware new Kore WAV QA.

No expected-word constrained ASR, paid API or Whisper. Source WAV, new
corrected Slide17 TTS text, immutable archived official Vosk 0.15 zip,
and actual independently audited H264/AAC full corrected media required.
ASR phonetic PASS is not independent speaker/whole math acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_paired_sl17_independent_audit import STATUS as MEDIA_STATUS
from .original_thomas84_paired_question_source_fix import (
    STATUS as PAIR_STATUS,CORRECTED_NARRATION)
from .original_thomas84_single_approved_tts_repair import STATUS as TTS_STATUS
from .tts_flexible_pronunciation_contract import (
    QA_VERSION,evaluate_tts_soundalike)
from .video_ffmpeg import ffmpeg_executable

OFFICIAL_MODEL_NAME="vosk-model-small-en-us-0.15"
OFFICIAL_MODEL_SHA="30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498"
STATUS="REAL_KORE_CORRECTED_MATH_WAV_INDEPENDENT_OFFLINE_SPEECH_SCREEN_NO_ACADEMIC_APPROVAL"

def screen_speech(expected:str,recognized:str)->dict:
    q=evaluate_tts_soundalike(expected,recognized)
    require(q["contract_version"]==QA_VERSION,
            "Must use the owner's flexible verified phonetic contract")
    # Serious speech claims need a real independent audible inspection;
    # explicit ASR math contradiction is targeted verification, NOT proof.
    needs_review=bool(q["critical_errors"]) or not q["tts_qa_soundalike_pass"]
    return {"phonetic_screen_decision":q["tts_qa_decision"],
            "phonetic_soundalike_screen_pass":not needs_review,
            "source_ASR_suspected_math_disagreement_codes":q["critical_errors"],
            "unprompted_asr_phonetic_similarity":q["phonetic_token_similarity"],
            "targeted_audible_check_required":needs_review,
            "individual_words_mathematically_verified":False,
            "original_Kore_voice_identity_verified":False}

def audit_real_corrected_kore_audio(*,original:Path,paired_source:Path,
                                    tts_candidate:Path,independent_mp4_audit:Path,
                                    model_dir:Path,packages_dir:Path|None,
                                    out:Path)->dict:
    root=Path(original).resolve()
    pair=Path(paired_source).resolve()
    voice=Path(tts_candidate).resolve()
    media=Path(independent_mp4_audit).resolve()
    model=Path(model_dir).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and pair.is_dir() and voice.is_dir()
            and media.is_file() and model.is_dir()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent)
            and not dest.is_relative_to(voice),
            "Original genuine source, private model and exclusive receipt needed")
    summary=json.loads(media.read_text(encoding="utf8"))
    proof=json.loads((pair/"PAIR_SOURCE_PROOF_NO_AUDIO.json").read_text(encoding="utf8"))
    tts=json.loads((voice/"SUCCESS_CANDIDATE_NOT_VOICE_APPROVED.json").read_text(encoding="utf8"))
    require(summary.get("status")==MEDIA_STATUS
            and summary.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and summary.get("corrected_new_actual_Kore_PCM_WAV_sha256")==
                 tts.get("new_actual_pcm_sha256")
            and summary.get("independent_actual_final_H264_PDF_frame_checks")==48
            and proof.get("status")==PAIR_STATUS
            and proof.get("original_textbook_sha256")==EXPECTED_SOURCE_SHA
            and proof.get("source_corrected_speech_text")==CORRECTED_NARRATION
            and proof.get("corrected_script_tts_sha256")==file_hash(pair/"script_tts.json")
            and tts.get("status")==TTS_STATUS
            and tts.get("text_hash")==hashlib.sha256(
                 CORRECTED_NARRATION.encode("utf8")).hexdigest()
            and tts.get("requested_voice")=="Kore"
            and tts.get("requested_provider")=="gemini-3.8-flash-lite-tts"
            and tts.get("actual_paid_provider_request_count")==1
            and tts.get("local_auto_retry_count")==0
            and tts.get("independent_acoustic_correct_pronunciation_accepted") is False
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Untrusted source text/provider/new PCM/MP4 provenance")
    wav=Path(tts["new_actual_pcm_file"])
    require(wav.is_file() and not wav.is_symlink()
            and wav.resolve().is_relative_to(voice)
            and file_hash(wav)==tts["new_actual_pcm_sha256"],
            "Not the genuine single-math-utterance provider WAV")
    with wave.open(str(wav),"rb") as w:
        require(w.getnchannels()==1 and w.getsampwidth()==2
                and w.getframerate()==24000
                and abs(w.getnframes()/24000-15.48)<.04,
                "Cannot independently inspect original-format source PCM")
    archive=model.parent/(OFFICIAL_MODEL_NAME+".zip")
    require(model.name==OFFICIAL_MODEL_NAME
            and archive.is_file() and not archive.is_symlink()
            and file_hash(archive)==OFFICIAL_MODEL_SHA
            and (model/"am"/"final.mdl").is_file(),
            "External offline recognizer is not verified historical Vosk model")
    if packages_dir is not None:
        module_root=Path(packages_dir).resolve()
        require(module_root.is_dir() and (module_root/"vosk").is_dir(),
                "Isolated offline Windows recognizer unavailable")
        sys.path.insert(0,str(module_root))
    from vosk import Model,KaldiRecognizer,SetLogLevel
    exe=ffmpeg_executable()
    decoded=subprocess.run([exe,"-nostdin","-v","error","-i",str(wav),
                            "-ar","16000","-ac","1",
                            "-f","s16le","-c:a","pcm_s16le","pipe:1"],
                           capture_output=True,timeout=40)
    require(decoded.returncode==0 and len(decoded.stdout)>16000,
            "Actual genuine paid source WAV could not be decoded offline")
    SetLogLevel(-1)
    rec=KaldiRecognizer(Model(str(model)),16000)
    rec.SetWords(True)
    pieces=[]
    for i in range(0,len(decoded.stdout),8000):
        if rec.AcceptWaveform(decoded.stdout[i:i+8000]):
            pieces.append(json.loads(rec.Result()))
    pieces.append(json.loads(rec.FinalResult()))
    actual=" ".join(z.get("word","") for item in pieces
                    for z in item.get("result",[]))
    require(actual.strip(),"Actual unprompted offline ASR could not detect speech")
    screening=screen_speech(CORRECTED_NARRATION,actual)
    result={
      "schema_version":1,"status":STATUS,
      "original_textbook_sha256":EXPECTED_SOURCE_SHA,
      "actual_new_source_waveform_sha256":file_hash(wav),
      "independently_audited_corrected_complete_mp4_receipt_sha256":file_hash(media),
      "verified_official_Vosk_zip_sha256":OFFICIAL_MODEL_SHA,
      "original_source_corrected_TTS_fragment_sha256":tts["text_hash"],
      "new_real_pcm_seconds":15.48,
      "unprompted_independent_offline_ASR_transcript":actual,
      **screening,
      "source_script_and_original_WAVs_not_modified":True,
      "all_66_spoken_visual_semantics_approved":False,
      "student_publication_authorized":False,"release_eligible":False}
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Protected source altered during independent audio audit")
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("original","paired_source","tts_candidate",
                 "independent_mp4_audit","model_dir","out"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    p.add_argument("--packages-dir",type=Path)
    data=audit_real_corrected_kore_audio(**vars(p.parse_args()))
    print(json.dumps(data,indent=2))
if __name__=="__main__":main()
