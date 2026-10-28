"""Independently replay the original §8.4 slide11 genuine WAV through Vosk.

Correct observed ASR orthography 'co sign' -> spoken cosine ONLY when
actual math script expects cosine; never conceal a true sine/cosine
swap, numerical change or C spoken 'circa'. ASR remains advisory.
"""
from __future__ import annotations
import argparse,hashlib,json,subprocess,sys,wave
from pathlib import Path
from .element_plan_autodraft import file_hash
from .original_thomas84_semantic_mapping_review import EXPECTED_SOURCE_SHA,require
from .original_thomas84_new_kore_offline_audio_qa import (
 OFFICIAL_MODEL_NAME,OFFICIAL_MODEL_SHA,screen_speech)
from .tts_flexible_pronunciation_contract import canonical_phonetic_tokens
from .video_ffmpeg import ffmpeg_executable
STATUS="ORIGINAL_SLIDE11_INDEPENDENT_UNPROMPTED_WAV_PHONETIC_TRIG_CHECK_NO_AUDIBLE_CERTIFICATION"

def check_original_11(*,original:Path,asr_provenance:Path,
                      model_dir:Path,packages_dir:Path,
                      out:Path)->dict:
    root=Path(original).resolve(); earlier=Path(asr_provenance).resolve()
    model=Path(model_dir).resolve(); packages=Path(packages_dir).resolve()
    dest=Path(out).absolute()
    require(root.is_dir() and earlier.is_file() and model.is_dir()
            and packages.is_dir() and dest.parent.is_dir()
            and not dest.exists() and not dest.is_relative_to(root.parent),
            "Actual immutable source and verified model required")
    old=json.loads(earlier.read_text(encoding="utf8"))
    slide=next(x for x in old["slides"] if x["slide"]==11)
    require(old["source_original_hashes"]["source.pdf"]==EXPECTED_SOURCE_SHA
            and file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and file_hash(root/"slide11.wav")==slide["historical_WAV_sha256"]
            and old.get("whisper_used") is False
            and old.get("network_asr_used") is False
            and old.get("student_publication_authorized") is False,
            "Actual old math narration or original source SHA drift")
    archive=model.parent/(OFFICIAL_MODEL_NAME+".zip")
    require(model.name==OFFICIAL_MODEL_NAME and
            archive.is_file() and file_hash(archive)==OFFICIAL_MODEL_SHA
            and (model/"am"/"final.mdl").is_file(),
            "Cannot compare with genuinely authenticated offline model")
    with wave.open(str(root/"slide11.wav"),"rb") as a:
        require(a.getframerate()==24000 and a.getnchannels()==1
                and a.getsampwidth()==2,
                "Original genuine recorded audio format changed")
    actual_tts=json.loads((root/"script_tts.json").read_text(encoding="utf8"))
    expected=actual_tts["slides"][10]["tts_text"]
    require("sine two u equals two sine u cosine u" in expected,
            "Original source mathematical trig equality is not present")
    sys.path.insert(0,str(packages))
    from vosk import KaldiRecognizer,Model,SetLogLevel
    exe=ffmpeg_executable()
    pcm=subprocess.run([exe,"-nostdin","-v","error",
         "-i",str(root/"slide11.wav"),"-ar","16000","-ac","1",
         "-f","s16le","-c:a","pcm_s16le","pipe:1"],
         capture_output=True,timeout=50)
    require(pcm.returncode==0 and len(pcm.stdout)>16000,
            "Actual source recording cannot be independently decoded")
    SetLogLevel(-1); recognizer=KaldiRecognizer(Model(str(model)),16000)
    recognizer.SetWords(True); pieces=[]
    for i in range(0,len(pcm.stdout),8000):
        if recognizer.AcceptWaveform(pcm.stdout[i:i+8000]):
            pieces.append(json.loads(recognizer.Result()))
    pieces.append(json.loads(recognizer.FinalResult()))
    heard=" ".join(q.get("word","") for p in pieces for q in p.get("result",[]))
    require(heard.strip() and
            heard.casefold()==slide["asr_transcript"].casefold(),
            "Independent playback changed actual source slide11 recognizer result")
    basic_expected,phonetic=canonical_phonetic_tokens(expected,heard)
    res=screen_speech(expected,heard)
    require("cosine" in basic_expected
            and "cosine" in phonetic
            and "co sign you" in heard
            and res["phonetic_soundalike_screen_pass"] is True
            and res["source_ASR_suspected_math_disagreement_codes"]==[],
            "Source Vosk orthographic sine/cosine discrepancy not reconciled")
    result={
       "schema_version":1,"status":STATUS,
       "original_textbook_sha256":EXPECTED_SOURCE_SHA,
       "real_original_slide11_wav_sha256":file_hash(root/"slide11.wav"),
       "authentic_offline_recognizer_SHA256":OFFICIAL_MODEL_SHA,
       "historic_independent_unprompted_transcript_identical":True,
       "source_expected_trig_math_phrase":"sine two u equals two sine u cosine u",
       "unprompted_ASR_recognized_trig_phrase":
         "sign to you equals to sign you co sign you",
       "phonetic_resolution":"co sign you=cosine u; sign you=sine u; to=two",
       "trig_function_changed_in_ASR_after_safe_phonetic_normalization":False,
       "phonetic_source_consistency_pass":res["phonetic_soundalike_screen_pass"],
       "phonetic_similarity":res["unprompted_asr_phonetic_similarity"],
       "independently_aurally_listened_and_confirmed":False,
       "all_66_spoken_math_semantics_accepted":False,
       "student_publication_authorized":False,
       "source_recording_modified":False}
    require(file_hash(root/"source.pdf")==EXPECTED_SOURCE_SHA
            and file_hash(root/"slide11.wav")==slide["historical_WAV_sha256"],
            "Protected real original changed during acoustic screening")
    with dest.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("original","asr_provenance","model_dir","packages_dir","out"):
        p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    r=check_original_11(**vars(p.parse_args()))
    print(json.dumps(r,indent=2))
if __name__=="__main__":main()
