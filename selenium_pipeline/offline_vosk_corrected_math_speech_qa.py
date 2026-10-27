"""Unbiased, wholly OFFLINE math narration transcription check using Vosk.

Do not constrain ASR with the expected script: compare independently decoded
free-dictation transcript to each immutable source-registered corrected text.
Vosk is NOT Whisper, does not send data to any provider, and never certifies
the audible Kore voice or mathematical source consensus by itself.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from .offline_corrected_bundle_verify import strict_json
from .original_replacement_video_handoff import _sha
from .original_slide4_real_pcm_chunk_highlight import (
    inspect_five_original_pcm_chunks,
)
from .video_ffmpeg import ffmpeg_executable


MODEL_NAME="vosk-model-small-en-us-0.15"
MODEL_ZIP_SHA256="30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498"


class OfflineMathSpeechReviewError(ValueError):
    pass


def require(ok:bool,message:str)->None:
    if not ok:
        raise OfflineMathSpeechReviewError(message)


def words(text:str)->list[str]:
    """Normalize harmless typography, NOT mathematical sign/domain terms."""
    if not isinstance(text,str):
        raise OfflineMathSpeechReviewError("Transcript must be textual")
    normalized=text.lower().replace("non-negative","nonnegative")
    normalized=normalized.replace("non negative","nonnegative")
    normalized=normalized.replace("end point","endpoint")
    normalized=normalized.replace("end-point","endpoint")
    normalized=normalized.replace("zero length","zerolength")
    normalized=normalized.replace("zero-length","zerolength")
    normalized=normalized.replace("pi/2","pi over two")
    return re.findall(r"[a-z]+|[0-9]+",normalized)


def word_error_rate(reference:str,transcript:str)->dict:
    a=words(reference)
    b=words(transcript)
    require(len(a)>0,"Expected speech narration is empty")
    prev=list(range(len(b)+1))
    for i,expected in enumerate(a,1):
        curr=[i]+[0]*len(b)
        for j,observed in enumerate(b,1):
            curr[j]=min(
                prev[j]+1,
                curr[j-1]+1,
                prev[j-1]+(expected!=observed),
            )
        prev=curr
    mismatch=prev[-1]
    return {
        "expected_token_count":len(a),
        "recognized_token_count":len(b),
        "edit_distance":mismatch,
        "word_error_rate":round(mismatch/len(a),5),
        "exact_token_agreement":mismatch==0,
    }


def lexical_math_risk_terms(expected:str,recognized:str)->dict:
    candidates=(
        "absolute","negative","nonnegative","positive","degenerate",
        "square","sqrt","secant","sine","cosine","tangent","zero",
        "opposite","adjacent","hypotenuse","interval","endpoint",
    )
    required={w for w in candidates if w in words(expected)}
    observed=set(words(recognized))
    matched=sorted(required & observed)
    missing=sorted(required-observed)
    return {
        "critical_terms_expected":sorted(required),
        "critical_terms_matched":matched,
        "critical_terms_unrecognized":missing,
        "critical_term_recall":round(len(matched)/len(required),4)
        if required else 1.0,
    }


def polarity_sequence(expected:str,recognized:str)->dict:
    """Even one altered negative/nonnegative/zero keyword must block screening."""
    risks={"absolute","negative","nonnegative","positive","zero","degenerate"}
    a=[w for w in words(expected) if w in risks]
    b=[w for w in words(recognized) if w in risks]
    return {
        "expected_math_polarity_sequence":a,
        "recognized_math_polarity_sequence":b,
        "critical_math_polarity_sequence_exact":a==b,
    }


def _real_source_and_model(*,original:Path,bundle:Path,audio_dir:Path,
                           model_dir:Path)->tuple[dict,dict,str]:
    evidence=inspect_five_original_pcm_chunks(
        original=original,bundle=bundle,audio_dir=audio_dir)
    source=strict_json(Path(bundle)/"FIVE_CORRECTED_SEGMENTS_UNAPPROVED.json")
    root=Path(model_dir).absolute()
    require(root.name==MODEL_NAME and root.is_dir() and not root.is_symlink()
            and (root/"am"/"final.mdl").is_file(),
            "Official offline English model missing; do not guess ASR result")
    archive=root.parent/(MODEL_NAME+".zip")
    require(archive.is_file() and not archive.is_symlink()
            and _sha(archive)==MODEL_ZIP_SHA256,
            "Official downloaded Vosk 0.15 model ZIP changed")
    return evidence,source,MODEL_ZIP_SHA256


def transcribe_actual_five_corrected_wavs(
    *, original:Path,bundle:Path,audio_dir:Path,
    model_dir:Path,output_receipt:Path,
)->dict:
    """Independent ASR corroboration only, NEVER final academic release."""
    root=Path(original).absolute()
    parent=Path(audio_dir).absolute()
    out=Path(output_receipt).absolute()
    require(out.parent.is_dir() and not out.parent.is_symlink()
            and not out.exists() and not out.is_relative_to(root)
            and not out.is_relative_to(parent),
            "New external exclusive ASR receipt required")
    evidence,source,model_zip_sha=_real_source_and_model(
        original=root,bundle=bundle,audio_dir=parent,model_dir=model_dir)
    try:
        from vosk import Model,KaldiRecognizer,SetLogLevel
    except (ImportError,OSError) as exc:
        raise OfflineMathSpeechReviewError(
            "Vosk local Windows offline ASR unavailable; no speech acceptance"
        ) from exc
    SetLogLevel(-1)
    model=Model(str(model_dir))
    exe=ffmpeg_executable()
    rows=[]
    actual_shas=[]
    for expected,row in zip(source["source_verified_tts_highlight_units"],
                            evidence["units"]):
        file=parent/expected["tts_audio_relative_path_expected"]
        require(_sha(file)==row["wav_sha256"],
                "New WAV identity differs from source-verified five-utterance bundle")
        decoded=subprocess.run(
            [exe,"-hide_banner","-nostdin","-loglevel","error",
             "-i",str(file),"-ar","16000","-ac","1",
             "-f","s16le","-c:a","pcm_s16le","pipe:1"],
            capture_output=True,timeout=60)
        require(decoded.returncode==0 and len(decoded.stdout)>=16000,
                "Cannot decode actual genuine new PCM WAV to offline ASR input")
        recognizer=KaldiRecognizer(model,16000)
        recognizer.SetWords(True)
        chunks=[]
        for i in range(0,len(decoded.stdout),8000):
            if recognizer.AcceptWaveform(decoded.stdout[i:i+8000]):
                chunks.append(json.loads(recognizer.Result()))
        chunks.append(json.loads(recognizer.FinalResult()))
        data=[word for piece in chunks for word in piece.get("result",[])]
        recognized=" ".join(word.get("word","") for word in data)
        expected_text=expected["corrected_tts_text"]
        metrics=word_error_rate(expected_text,recognized)
        terms=lexical_math_risk_terms(expected_text,recognized)
        polarity=polarity_sequence(expected_text,recognized)
        # Even one mismatched sign/absolute/zero/degenerate term blocks.
        # Passing still does not prove every acoustic word independently.
        good=(metrics["word_error_rate"]<=.20
              and terms["critical_term_recall"]>=.75
              and polarity["critical_math_polarity_sequence_exact"]
              and metrics["recognized_token_count"]>=15)
        rows.append({
            "utterance_id":expected["original_utterance_id"],
            "source_text_sha256":expected["corrected_tts_text_sha256"],
            "actual_genuine_pcm_sha256":row["wav_sha256"],
            "actual_pcm_start_ms":row["start_ms"],
            "actual_pcm_end_ms":row["end_ms"],
            "unbiased_offline_recognizer":"Vosk English US small 0.15",
            "recognized_verbatim":recognized,
            "recognized_words_sha256":
                hashlib.sha256(recognized.encode("utf8")).hexdigest(),
            **metrics,**terms,**polarity,
            "asr_math_words_screening_pass":good,
            "speaker_voice_identity_Kore_verified":False,
            "actual_exact_spoken_words_certified":False,
        })
        actual_shas.append(_sha(file))
        print("OFFLINE_VOSK_SOURCE_AUDIO_UTTERANCE",
              len(rows),
              "WER",metrics["word_error_rate"],
              "MATH_RECALL",terms["critical_term_recall"],
              "SCREENING_PASS",good,flush=True)
    require(len(rows)==5 and actual_shas==[r["wav_sha256"]
             for r in evidence["units"]],
            "Five ASR source-audio identities incomplete")
    report={
        "schema_version":1,
        "status":"REAL_FIVE_KORE_REQUESTED_WAVS_UNBIASED_OFFLINE_ASR_REVIEW_ONLY",
        "source_original_sha256":evidence["source_pdf_sha256"],
        "model_name":MODEL_NAME,
        "official_archive_sha256":model_zip_sha,
        "model_license":"Apache-2.0",
        "asr_input_rate_hz":16000,
        "unbiased_no_expected_script_grammar":True,
        "uses_whisper":False,
        "external_asr_api_used":False,
        "genuine_source_registered_pcm_count":len(rows),
        "source_registered_screening_pass_count":
            sum(bool(r["asr_math_words_screening_pass"]) for r in rows),
        "five_source_audio_rows":rows,
        "requested_provider_voice":"Kore",
        "voice_Kore_audibly_independently_verified":False,
        "independent_academic_math_review_two_pass":False,
        "unqualified_exact_words_verified":False,
        "accepted_corrected_student_lecture":False,
        "student_publication_authorized":False,
    }
    with out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
        f.write("\n")
    return report


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--bundle",required=True,type=Path)
    p.add_argument("--audio-dir",required=True,type=Path)
    p.add_argument("--model-dir",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args(argv)
    result=transcribe_actual_five_corrected_wavs(
        original=a.original,bundle=a.bundle,audio_dir=a.audio_dir,
        model_dir=a.model_dir,output_receipt=a.out)
    print(json.dumps({
        "status":result["status"],
        "ASR_screening_pass_count":result["source_registered_screening_pass_count"],
        "actual_utterance_count":result["genuine_source_registered_pcm_count"],
        "full_speech_acceptance":False,
        "source_academic_approval":False,
        "student_publication":False,
    }))


if __name__=="__main__":
    main()
