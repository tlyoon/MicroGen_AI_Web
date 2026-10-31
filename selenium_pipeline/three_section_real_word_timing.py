"""Read-only genuine PCM word-timing evidence for all original lecture slides.

ASR timing is a candidate only: neither mathematical alignment nor encoded
highlighting is approved by this utility.
"""
from __future__ import annotations
import argparse
import json
import wave
from pathlib import Path
from .runner import blocks
from .original_thomas84_offline_word_pdf_timing import (
    tokenize_reference_sentences, real_word_anchor_candidates,
    _real_local_vosk_transcribe,
)
from .offline_vosk_corrected_math_speech_qa import MODEL_NAME, MODEL_ZIP_SHA256
from .figure_source_identity import require, _sha
from .video_ffmpeg import ffmpeg_executable

def inspect(*, root:Path, model_dir:Path)->dict:
    from vosk import Model, SetLogLevel
    root, model_dir = Path(root).absolute(), Path(model_dir).absolute()
    archive=model_dir.parent/(MODEL_NAME+".zip")
    require(model_dir.is_dir() and model_dir.name==MODEL_NAME
            and not model_dir.is_symlink() and archive.is_file()
            and _sha(archive)==MODEL_ZIP_SHA256,
            "Offline ASR model identity must be verified before any reading")
    SetLogLevel(-1)
    model=Model(str(model_dir))
    ffmpeg=ffmpeg_executable()
    sections=[]
    for section in ("8.4","8.5","8.6"):
        folder=root/section
        inputs=[folder/x for x in ("source.pdf","slides.pdf","script.txt")]
        require(all(p.is_file() and not p.is_symlink() for p in inputs),
                "Missing original source-bound input")
        hashes=[_sha(p) for p in inputs]
        spoken=blocks(inputs[2].read_text(encoding="utf-8-sig"))
        rows=[]
        for index, speech in spoken:
            require(index==len(rows)+1,"Narration slide number or order drift")
            wav=folder/f"slide{index}.wav"
            require(wav.is_file() and not wav.is_symlink(),"Missing genuine original slide WAV")
            wav_sha=_sha(wav)
            with wave.open(str(wav),"rb") as f:
                duration=f.getnframes()/f.getframerate()
                require(f.getnchannels()==1 and f.getsampwidth()==2
                        and f.getcomptype()=="NONE" and 1<duration<600,
                        "Invalid original PCM narration format")
            words, heard=_real_local_vosk_transcribe(model=model,exe=ffmpeg,audio_path=wav)
            sentences, expected=tokenize_reference_sentences(speech)
            anchors=real_word_anchor_candidates(expected,words,sentences)
            require(_sha(wav)==wav_sha,"Original WAV mutated during offline alignment")
            rows.append({"slide":index,"wav_sha256":wav_sha,
                         "wav_duration_s":round(duration,4),
                         "actual_recognized_word_count":len(words),
                         "actual_timed_sentence_candidates":sum(
                             bool(a["word_timing_hypothesis_available"]) for a in anchors),
                         "sentence_count":len(sentences),
                         "sentence_timing_candidates":anchors,
                         "audio_semantics_verified":False,
                         "visual_element_synchronized":False})
        require([_sha(p) for p in inputs]==hashes,"Source files changed during audit")
        sections.append({"section":section,"source_sha256":hashes[0],
                         "slides_sha256":hashes[1],"script_sha256":hashes[2],
                         "slide_count":len(rows),"slides":rows})
    return {"schema_version":1,
            "status":"REAL_ASR_WORD_TIMING_CANDIDATES_ONLY",
            "total_slides":sum(s["slide_count"] for s in sections),
            "sections":sections,
            "mathematical_correspondence_verified":False,
            "synchronized_video_accepted":False,
            "student_publication_authorized":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("root","model-dir","out"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args(argv)
    out=a.out.absolute()
    require(out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(a.root.absolute()),
            "External exclusive sidecar only; source may not be overwritten")
    result=inspect(root=a.root,model_dir=a.model_dir)
    with out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    print(json.dumps({"slides":result["total_slides"],"status":result["status"],
                      "timed_sentence_candidates":sum(
                         row["actual_timed_sentence_candidates"]
                         for sec in result["sections"] for row in sec["slides"])}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
