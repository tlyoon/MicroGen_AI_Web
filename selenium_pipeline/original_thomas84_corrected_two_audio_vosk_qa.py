"""Unprompted offline Vosk QA on genuine Flash-Lite/Kore corrected slides 6/17.

Original textbook/17-slide corrected source hashes, exact new provider WAV
hashes, unfed original WAVs, and official pre-verified offline Vosk archive
must agree. Do not use ASR reference vocabulary prompting. Owner's flexible
phonetic contract governs screen; no WER-only automatic replacement and no
false voice/academic/video/publication approval.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from .figure_source_identity import require,_sha
from .runner import blocks
from .original_thomas84_corrected_tts_batch import STATUS,SUCCESS,SLOTS
from .tts_flexible_pronunciation_contract import evaluate_tts_soundalike
from .tts_offline_vosk_fidelity import unprompted_audio_review

def known_math_mismatch_in_audio_asr(slide:int,recognized:str)->bool:
    import re
    heard=recognized.casefold()
    if slide==6:
        return bool(re.search(r"\bvertical\s+asymptot",heard)
                    and re.search(r"\barc\s*tangent|arctangent",heard))
    if slide==17:
        return bool(re.search(r"strict\w*.*?sine\s+and\s+tangent",heard)
                    or re.search(r"strict\w*.*?tangent\s+and\s+sine",heard))
    return False


def review(*,original:Path,corrected:Path,tts_output:Path,
           vosk_model:Path,vosk_packages:Path,out:Path)->dict:
    original,corrected,tts_output,vosk_model,vosk_packages,out=(
        Path(p).absolute() for p in
        (original,corrected,tts_output,vosk_model,vosk_packages,out))
    require(out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(original)
            and not out.is_relative_to(tts_output),
            "Source-independent exclusive QA report required")
    pending=tts_output/"SOURCE_LOCKED_PENDING_TTS.json"
    proof=tts_output/"REAL_TWO_WAVS_PENDING_ACOUSTIC_QA.json"
    inputs=[pending,proof,corrected/"script.txt",corrected/"slides.pdf",
            original/"source.pdf",*[original/f"slide{n}.wav" for n in SLOTS],
            *[tts_output/f"corrected_original_slide{n}.wav" for n in SLOTS]]
    require(all(p.is_file() and not p.is_symlink() for p in inputs),
            "Original/corrected/genuine provider PCM files missing")
    hashes={str(f):_sha(f) for f in inputs}
    job=json.loads(pending.read_text(encoding="utf8"))
    audio=json.loads(proof.read_text(encoding="utf8"))
    require(job["status"]==STATUS and audio["status"]==SUCCESS
            and job["slide_numbers"]==list(SLOTS)
            and audio["source_pinned_job_sha256"]==_sha(pending)
            and job["source_pdf_sha256"]==_sha(original/"source.pdf")
            and job["corrected_slides_sha256"]==_sha(corrected/"slides.pdf")
            and job["corrected_full_narration_sha256"]==_sha(corrected/"script.txt")
            and audio["effective_provider_voice"]["voice"]=="Kore"
            and audio["effective_provider_voice"]["model"]==
                "gemini-3.8-flash-lite-tts"
            and audio["student_publication_authorized"] is False,
            "Unapproved source/provider/voice identity")
    scripts=dict(blocks((corrected/"script.txt").read_text(encoding="utf8")))
    os.environ["MICROGEN_TTS_QA_VOSK_MODEL"]=str(vosk_model)
    os.environ["MICROGEN_TTS_QA_VOSK_PACKAGES"]=str(vosk_packages)
    observations={}
    for n in SLOTS:
        wav=tts_output/f"corrected_original_slide{n}.wav"
        require(_sha(wav)==audio["physical_new_wavs"][str(n)]["sha256"]
                and _sha(original/f"slide{n}.wav")==job["original_wav_sha256"][str(n)]
                and _sha(wav)!=_sha(original/f"slide{n}.wav"),
                "Stale original speech or unidentified corrected PCM included")
        asr=unprompted_audio_review(wav,scripts[n])
        contract=evaluate_tts_soundalike(scripts[n],asr["transcript"])
        heard=asr["transcript"].casefold()
        explicit_error=known_math_mismatch_in_audio_asr(n,heard)
        # Vosk is imperfect; positive phrase evidence is advisory unless
        # independently audible. Explicitly wrong concepts block promotion.
        must_have=(("horizontal","asymptotes") if n==6 else
                   ("sine","tangent","endpoints"))
        matched=[word for word in must_have if word in heard]
        observations[str(n)]={
            "source_slide_number":n,
            "corrected_script_sha256":job["source_bound_full_slide_text_sha256"][str(n)],
            "new_real_pcm_sha256":_sha(wav),
            "pcm_metrics":asr["offline_vosk_pcm_audit"],
            "unprompted_offline_vosk_transcript":asr["transcript"],
            "flexible_phonetic_qa":contract,
            "targeted_math_terms_found_in_actual_recording_asr":matched,
            "explicit_original_wrong_mathematics_suspected":bool(explicit_error),
            "passes_automated_phonetic_screen":bool(
                contract["tts_qa_soundalike_pass"] and not explicit_error),
            "independent_faithful_mathematical_audio_certified":False,
            "independent_voice_identity_certified":False,
            "automatic_tts_regeneration_from_imperfect_asr":False}
    require({str(f):_sha(f) for f in inputs}==hashes,
            "Original source/corrected narration/provider WAV changed during QA")
    accept=all(v["passes_automated_phonetic_screen"]
               for v in observations.values())
    result={"schema_version":1,
        "status":("TWO_CORRECTED_ORIGINAL_KORE_WAVS_OFFLINE_PHONETIC_SCREEN_PASS"
                  if accept else
                  "TWO_CORRECTED_ORIGINAL_KORE_WAVS_TARGETED_REVIEW_REQUIRED"),
        "original_source_pdf_sha256":_sha(original/"source.pdf"),
        "corrected_script_sha256":_sha(corrected/"script.txt"),
        "provider_physical_evidence_sha256":_sha(proof),
        "source_slide_audio_observations":observations,
        "all_corrected_wavs_phonetic_screen_pass":accept,
        "independent_complete_scientific_audio_accepted":False,
        "full_original_lecture_video_accepted":False,
        "student_publication_authorized":False}
    with out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write("\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("original","corrected","tts-output","vosk-model",
              "vosk-packages","out"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args(argv)
    r=review(original=a.original,corrected=a.corrected,
             tts_output=a.tts_output,vosk_model=a.vosk_model,
             vosk_packages=a.vosk_packages,out=a.out)
    print(json.dumps({"status":r["status"],
        "slides":[(k,v["flexible_phonetic_qa"]["tts_qa_decision"],
                  v["flexible_phonetic_qa"]["phonetic_token_similarity"],
                  v["explicit_original_wrong_mathematics_suspected"])
                  for k,v in r["source_slide_audio_observations"].items()]}))
if __name__=="__main__":
    main()
