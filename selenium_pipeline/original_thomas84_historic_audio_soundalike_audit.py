"""Source-hash-locked flexible audio QA for all 16 original §8.4 WAVs.

Existing *unprompted offline* Vosk transcripts are independently
screened under the owner's tolerant sound-alike contract. ASR-only
phonetic differences DO NOT establish a confirmed mispronunciation.
Confirmed wrong spoken C->circa and math signs remain HARD FAILS,
when actual audio evidence corroborates them. Not a student release.
"""
from __future__ import annotations
import argparse
import json
import re
import wave
from pathlib import Path
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_offline_word_pdf_timing import (
    HISTORIC_SLIDES,tokenize_reference_sentences)
from .tts_flexible_pronunciation_contract import (
    QA_VERSION,evaluate_tts_soundalike,
)
from .original_thomas84_66_corrected_independent_audit import (
    STATUS as CORRECTED_REAL_AUDIT_STATUS,
)

STATUS="ALL_16_HISTORIC_REAL_PCM_FLEXIBLE_PHONETIC_QA_ASR_IS_NOT_AUDIO_PROOF"
MATH_SAFETY_FLAGS={
    "LETTER_C_INCORRECTLY_EXPANDED_TO_CIRCA",
    "EXPLICIT_MATHEMATICAL_SIGN_OR_DEGENERACY_REVERSAL",
    "EXPLICIT_TRIGONOMETRIC_FUNCTION_CHANGED",
    "EXPLICIT_TRIANGLE_SIDE_ROLE_CHANGED",
    "EXPLICIT_SPOKEN_NUMBER_CHANGED",
    "EXPLICIT_MATHEMATICAL_RELATION_DIRECTION_CHANGED",
}
def classify_asr_screen(*,qa:dict,reference:str,recognized:str)->str:
    """Distinguish independent word-recognition suspicion from audible proof."""
    require(bool(reference.strip()) and isinstance(recognized,str),
            "Actual original spoken script or transcript missing")
    require(qa.get("contract_version")==QA_VERSION,
            "Must use current owner's relaxed phonetic QA requirements")
    errors=set(qa.get("critical_errors",[]))
    require(not (errors-MATH_SAFETY_FLAGS),
            "Unclassified severe math-voice observation requires review")
    if errors:
        return "TARGETED_INDEPENDENT_AUDIO_CHECK_REQUIRED_MATH_OR_CIRCA"
    if qa.get("tts_qa_soundalike_pass") is True:
        return "ACCEPTABLE_PHONETIC_SIMILARITY_ASR_SCREEN_ONLY"
    return "TARGETED_INDEPENDENT_AUDIO_CHECK_REQUIRED_LOW_ASR_AGREEMENT"

def audit_real_historic_audio(*,original:Path,asr_receipt:Path,
                              final_media_audit:Path,out:Path)->dict:
    root=Path(original).resolve()
    source=Path(asr_receipt).resolve()
    video=Path(final_media_audit).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and source.is_file() and video.is_file()
            and not source.is_symlink() and not video.is_symlink()
            and dest.parent.is_dir() and not dest.exists()
            and not dest.is_relative_to(root.parent),
            "Immutable source-recorded PCM, independent ASR and safe receipt required")
    asr=json.loads(source.read_text(encoding="utf8"))
    final=json.loads(video.read_text(encoding="utf8"))
    require(asr.get("status")==
            "REAL_HISTORICAL_16_SLIDES_ASR_TO_ORIGINAL_PDF_ELEMENT_CANDIDATES_REVIEW_ONLY"
            and asr.get("actual_historical_slides_inspected")==16
            and asr.get("source_original_hashes",{}).get("source.pdf")==
                 EXPECTED_SOURCE_SHA
            and asr.get("student_publication_authorized") is False
            and asr.get("whisper_used") is False
            and asr.get("network_asr_used") is False
            and asr.get("provider_synthesis_requests_sent")==0
            and final.get("status")==CORRECTED_REAL_AUDIT_STATUS
            and final.get("source_original_pdf_sha256")==EXPECTED_SOURCE_SHA
            and final.get("sixteen_original_WAVs_PCM_exactly_reverified") is True
            and final.get("student_publication_authorized") is False
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA,
            "Historic audio provenance or independent corrected-video QA missing")
    historical_hashes=asr["original_historical_WAV_hashes"]
    require(set(historical_hashes)=={f"slide{i}.wav" for i in HISTORIC_SLIDES},
            "Unexpected original historic WAV track roster")
    tts=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    require([r["slide"] for r in tts["slides"]]==list(range(1,18)),
            "Source-TTS script changed ordering")
    required_rows=asr["slides"]
    require([x["slide"] for x in required_rows]==list(HISTORIC_SLIDES),
            "Historic offline ASR inventory drift")
    rows=[]
    counts={"similarity_acceptable":0,"targeted_audio_review":0}
    for old in required_rows:
        slide=old["slide"]
        path=root/f"slide{slide}.wav"
        require(file_hash(path)==historical_hashes[path.name]
                and file_hash(path)==old["historical_WAV_sha256"],
                "Protected original actual recorded WAV SHA mismatch")
        with wave.open(str(path),"rb") as recorded:
            require(recorded.getframerate()==24000
                    and recorded.getnchannels()==1
                    and recorded.getsampwidth()==2
                    and recorded.getcomptype()=="NONE"
                    and abs(recorded.getnframes()/24000-
                            old["actual_original_PCM_duration_s"])<.1,
                    "Historic actual original WAV PCM layout/duration drift")
        clauses,_=tokenize_reference_sentences(
            tts["slides"][slide-1]["tts_text"])
        units=old["candidate_elements"]
        require(len(clauses)==len(units) and
                all(a["sentence_index"]==b["sentence_index"]
                    and a["narration_fragment_sha256"]==b["narration_fragment_sha256"]
                    and a["narration_fragment"]==
                        b["original_actual_slide_narration_fragment"]
                    for a,b in zip(clauses,units)),
                "Independent original TTS script/ASR source sentence mismatch")
        transcript=old["asr_transcript"]
        qa=evaluate_tts_soundalike(
            tts["slides"][slide-1]["tts_text"],transcript,
            source_audio_is_genuine_pcm=True,source_text_identity_verified=True)
        decision=classify_asr_screen(qa=qa,
                     reference=tts["slides"][slide-1]["tts_text"],
                     recognized=transcript)
        if decision=="ACCEPTABLE_PHONETIC_SIMILARITY_ASR_SCREEN_ONLY":
            counts["similarity_acceptable"]+=1
        else:
            counts["targeted_audio_review"]+=1
        rows.append({
            "slide":slide,
            "protected_actual_source_WAV_sha256":file_hash(path),
            "source_script_sha256":file_hash(root/"script_tts.json"),
            "original_narrated_sentences":len(clauses),
            "unprompted_ASR_input_sha256":file_hash(source),
            "owner_relaxed_tts_contract":QA_VERSION,
            "genuine_recording_phonetic_screen":decision,
            "offline_asr_canonical_similarity":qa["phonetic_token_similarity"],
            "offline_asr_math_critical_suspicions":qa["critical_errors"],
            "source_AAC_PCM_audio_preservation_verified":True,
            "audible_independent_pronunciation_confirmed":False,
            "full_math_voice_release_accepted":False,
        })
    require(len(rows)==16 and sum(counts.values())==16
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and all(file_hash(root/name)==sha
                    for name,sha in historical_hashes.items()),
            "Protected recording changed during flexible QA")
    result={"schema_version":1,"status":STATUS,
            "source_textbook_SHA256":EXPECTED_SOURCE_SHA,
            "independent_real_media_audit_sha256":file_hash(video),
            "unprompted_offline_Vosk_source_receipt_SHA256":file_hash(source),
            "owner_flexible_tts_qa_contract":QA_VERSION,
            "real_original_historic_WAVs_screened":len(rows),
            "genuine_PCM_mathematical_source_narration_soundalike_screen_pass":
                counts["similarity_acceptable"],
            "targeted_voice_math_pronunciation_review_required":
                counts["targeted_audio_review"],
            "ASR_only_suspicions_are_NOT_confirmed_audio_errors":True,
            "explicit_C_to_circa_if_actually_heard_is_always_hard_fail":True,
            "confirmed_narration_content_and_voice_accepted":False,
            "full_academic_math_semantics_accepted":False,
            "student_publication_authorized":False,
            "release_eligible":False,"slides":rows}
    with dest.open("x",encoding="utf8") as output:
        json.dump(result,output,indent=2,ensure_ascii=False)
        output.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ("original","asr_receipt","final_media_audit","out"):
        p.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    report=audit_real_historic_audio(**vars(p.parse_args()))
    print(json.dumps({k:v for k,v in report.items() if k!="slides"},indent=2))
if __name__=="__main__":main()
