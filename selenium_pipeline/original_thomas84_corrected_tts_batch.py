"""Source-bound corrected §8.4 slide 6/17 two-voice-only TTS regeneration.

The existing production TTS queue owns its real Flash-Lite (Kore) retry
policy and observed fallback evidence. This wrapper PREVENTS submitting
original untouched WAVs, stale text or any other slide for paid speech.
Audio receipt means physically produced only; scientific pronunciation and
synchronization still require independent offline verification.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import wave
from .figure_source_identity import require,_sha
from .runner import blocks
from .original_thomas84_cumulative_academic_repairs import CORRECT_REVIEW_SPEECH
from .original_thomas84_arctangent_paired_repair import NEW_WORDS
from .tts_effective_identity import DEFAULT,verify_effective_identity

STATUS="ORIGINAL_CORRECTED_SLIDES6_17_TTS_ONLY_SOURCE_LOCKED_STAGED"
SUCCESS="CORRECTED_SLIDES6_17_REAL_TTS_PHYSICAL_ONLY_NOT_SPEECH_APPROVED"
SLOTS=(6,17)
STAGE_IDS=(1,2)

def source_bound_staging_script(items:dict[int,str])->str:
    require(set(items)>=set(SLOTS)
            and all(type(items[n]) is str and len(items[n])>100 for n in SLOTS)
            and all(word in items[6] for word in NEW_WORDS)
            and CORRECT_REVIEW_SPEECH in items[17],
            "Missing exact corrected original source lecture speech")
    return "\n\n".join(f"**Slide {stage} [60 sec]:\n{items[original_n]}"
                     for stage,original_n in zip(STAGE_IDS,SLOTS))


def prepare(*,original:Path,corrected:Path,output:Path)->dict:
    original,corrected,output=(Path(x).absolute() for x in (original,corrected,output))
    require(output.is_dir() and not output.is_symlink()
            and not output.is_relative_to(original)
            and not output.is_relative_to(corrected),
            "Separate real external TTS candidate folder needed")
    source=original/"source.pdf"
    original_wavs=[original/f"slide{n}.wav" for n in SLOTS]
    proof=corrected/"original_two_slides_source_corrected_audio_stale.json"
    revised_script=corrected/"script.txt"
    inputs=[source,*original_wavs,proof,revised_script,corrected/"slides.pdf"]
    require(all(p.is_file() and not p.is_symlink() for p in inputs),
            "Genuine original publisher/math/audio and cumulative revision missing")
    before={str(p):_sha(p) for p in inputs}
    claim=json.loads(proof.read_text(encoding="utf8"))
    require(claim["status"]=="CUMULATIVE_ORIGINAL_SLIDES_6_AND_17_MATH_PAIRED_AUDIO_STALE"
            and claim["original_textbook_sha256"]==_sha(source)
            and claim["corrected_script_sha256"]==_sha(revised_script)
            and claim["corrected_slides_pdf_sha256"]==_sha(corrected/"slides.pdf")
            and claim["fresh_faithful_tts_required"]==list(SLOTS)
            and claim["fresh_corrected_audio_verified"] is False
            and claim["student_publication_authorized"] is False
            and all(claim["stale_original_wav_sha256"][str(n)]
                    ==_sha(original/f"slide{n}.wav") for n in SLOTS),
            "Original-source script or stale-audio contract inconsistent")
    items=dict(blocks(revised_script.read_text(encoding="utf8")))
    require(len(items)==17, "Original 17 source-slide narration units required")
    staged=source_bound_staging_script(items)
    from .vendor_template_v2.script_tts_risk import analyze_script_text
    errors=[x for x in analyze_script_text(staged)["findings"]
            if x["severity"]=="blocking"]
    require(not errors,"Source corrected math narration has TTS ambiguity")
    stage_script=output/"script.txt"
    receipt=output/"SOURCE_LOCKED_PENDING_TTS.json"
    require(not any(p.exists() for p in (stage_script,receipt))
            and not list(output.glob("*.wav")),
            "Cannot overwrite earlier provider/audio attempt in this output folder")
    stage_script.write_text(staged,encoding="utf8")
    out={"schema_version":1,"status":STATUS,
         "source_pdf_sha256":_sha(source),
         "corrected_slides_sha256":_sha(corrected/"slides.pdf"),
         "corrected_full_narration_sha256":_sha(revised_script),
         "paired_revision_receipt_sha256":_sha(proof),
         "staged_two_slide_narration_sha256":_sha(stage_script),
         "slide_numbers":list(SLOTS),
         "provider_staging_ids":list(STAGE_IDS),
         "original_wav_sha256":{str(n):_sha(original/f"slide{n}.wav") for n in SLOTS},
         "source_bound_full_slide_text_sha256":{
             str(n):__import__("hashlib").sha256(items[n].encode("utf8")).hexdigest()
             for n in SLOTS},
         "requested_effective_provider":DEFAULT,
         "tts_attempts_completed":False,
         "real_corrected_voice_accepted":False,
         "student_publication_authorized":False}
    with receipt.open("x",encoding="utf8") as f:
        json.dump(out,f,indent=2)
        f.write("\n")
    require({str(p):_sha(p) for p in inputs}==before,
            "Protected source/audios mutated while staging corrected TTS")
    return out

def dispatch(*,original:Path,corrected:Path,output:Path)->dict:
    original,corrected,output=(Path(x).absolute()
                               for x in (original,corrected,output))
    receipt=output/"SOURCE_LOCKED_PENDING_TTS.json"
    require(receipt.is_file() and not receipt.is_symlink(),
            "Source-pinned corrected TTS batch not prepared")
    info=json.loads(receipt.read_text(encoding="utf8"))
    require(info.get("status")==STATUS
            and info.get("slide_numbers")==list(SLOTS)
            and info.get("provider_staging_ids")==list(STAGE_IDS)
            and info.get("requested_effective_provider")==DEFAULT
            and info.get("source_pdf_sha256")==_sha(original/"source.pdf")
            and info.get("corrected_slides_sha256")==_sha(corrected/"slides.pdf")
            and info.get("corrected_full_narration_sha256")==_sha(corrected/"script.txt")
            and info.get("staged_two_slide_narration_sha256")==_sha(output/"script.txt"),
            "Original source-bound corrected TTS inputs mutated")
    for n in SLOTS:
        require(info["original_wav_sha256"][str(n)]
                ==_sha(original/f"slide{n}.wav"),"Original stale WAV changed")
    from .tts_billing_guard import require_tts_cost_authorization
    require_tts_cost_authorization("gemini",routine_gemini=True)
    # Existing code manages observed 3-round queues, whole-batch fallback,
    # no mixed voices, immutable candidate checkpoints.
    from .tts import synthesize_folder
    from .runner import load_microvid_env
    load_microvid_env()
    synthesize_folder(output,"gemini","gemini-3.8-flash-lite-tts","Kore")
    expected=[(n,body) for n,body in blocks(
        (output/"script.txt").read_text(encoding="utf8"))]
    require([n for n,_ in expected]==list(STAGE_IDS),
            "Unexpected slide included by paid provider batch")
    manifest=json.loads((output/"tts_input_manifest.json").read_text(encoding="utf8"))
    effective=verify_effective_identity(manifest,expected)
    physical={}
    for stage,n in zip(STAGE_IDS,SLOTS):
        staged_wav=output/f"slide{stage}.wav"
        p=output/f"corrected_original_slide{n}.wav"
        require(staged_wav.is_file() and not staged_wav.is_symlink()
                and not p.exists(),
                "No original-to-stage audio identity or conflicting output")
        with staged_wav.open("rb") as source_audio,p.open("xb") as target_audio:
            import shutil
            shutil.copyfileobj(source_audio,target_audio)
        require(_sha(p)==_sha(staged_wav)
                and _sha(p)!=info["original_wav_sha256"][str(n)],
                "Original stale audio was relabeled as the corrected voice")
        with wave.open(str(p),"rb") as wav:
            require(wav.getnchannels()==1 and wav.getsampwidth()==2
                    and wav.getcomptype()=="NONE"
                    and 16000<=wav.getframerate()<=48000
                    and 2<wav.getnframes()/wav.getframerate()<600,
                    "Provider returned unapproved/empty source speech PCM")
            duration=round(wav.getnframes()/wav.getframerate(),5)
        physical[str(n)]={"sha256":_sha(p),"duration_s":duration,
                          "physical_wav_only":True,
                          "spoken_words_mathematically_approved":False}
    require(info["source_pdf_sha256"]==_sha(original/"source.pdf")
            and all(info["original_wav_sha256"][str(n)]
                    ==_sha(original/f"slide{n}.wav") for n in SLOTS),
            "Original textbook or WAV altered after TTS provider dispatch")
    result={"status":SUCCESS,
            "source_pinned_job_sha256":_sha(receipt),
            "provider_manifest_sha256":_sha(output/"tts_input_manifest.json"),
            "effective_provider_voice":effective,
            "physical_new_wavs":physical,
            "corrected_word_fidelity_accepted":False,
            "tts_voice_audition_accepted":False,
            "full_section_video_accepted":False,
            "student_publication_authorized":False}
    with (output/"REAL_TWO_WAVS_PENDING_ACOUSTIC_QA.json").open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("original","corrected","output"):
        p.add_argument("--"+arg,type=Path,required=True)
    p.add_argument("--dispatch-approved-routine-tts",action="store_true")
    a=p.parse_args(argv)
    result=(dispatch(original=a.original,corrected=a.corrected,output=a.output)
            if a.dispatch_approved_routine_tts
            else prepare(original=a.original,corrected=a.corrected,output=a.output))
    print(json.dumps({"status":result["status"],
                      "slide_numbers":result.get("slide_numbers",list(SLOTS)),
                      "real_new_audio_produced":result["status"]==SUCCESS}))
if __name__=="__main__":
    main()
