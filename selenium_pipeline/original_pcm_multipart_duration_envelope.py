"""Strict-duration planning using ORIGINAL source-bound PCM and full acoustic QA.

This is a production precursor, NOT a video or a valid element-highlight plan.
Both original source PDF and corrected slides/scripts stay immutable; every
slide duration is measured from decoded PCM headers, never inferred from
narration strings or assumed page display times. Final MP4s require an
independent H264/AAC and decoded pixel/element QA; this file cannot approve them.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import wave
from pathlib import Path

from .runner import blocks

class MultipartEnvelopeError(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise MultipartEnvelopeError(message)

def sha(path:Path)->str:
    require(path.is_file() and not path.is_symlink(),f"Missing/unsafe original: {path}")
    digest=hashlib.sha256()
    with path.open("rb") as data:
        for chunk in iter(lambda:data.read(1048576),b""):
            digest.update(chunk)
    return digest.hexdigest()

def bound_audio_seconds(path:Path)->float:
    require(path.is_file() and not path.is_symlink(),
            f"Missing original recorded slide WAV: {path}")
    try:
        with wave.open(str(path),"rb") as wav:
            sample_rate=wav.getframerate()
            duration=wav.getnframes()/max(1,sample_rate)
            require(wav.getnchannels()==1 and wav.getsampwidth()==2
                    and wav.getcomptype()=="NONE"
                    and 16000<=sample_rate<=48000
                    and .2<duration<300,
                    f"Not genuine supported mono PCM16 source speech: {path.name}")
    except (wave.Error,EOFError,OSError) as exc:
        raise MultipartEnvelopeError(
            f"Cannot decode PCM WAV duration for {path.name}") from exc
    return duration

def build(*,source:Path,slides:Path,script:Path,
          audio_qa:Path,max_payload_seconds:float=540.0,
          per_slide_overhead_seconds:float=1.5,
          final_duration_limit_seconds:float=600.0)->dict:
    paths=[Path(v).absolute() for v in (source,slides,script,audio_qa)]
    require(all(p.parent==paths[0].parent for p in paths),
            "Original source/slides/script/audio QA must live together")
    require(120<=max_payload_seconds<=540
            and 0<=per_slide_overhead_seconds<=8
            and final_duration_limit_seconds==600
            and max_payload_seconds<final_duration_limit_seconds,
            "Never relax the strictly shorter-than-600s video contract")
    proof={x.name:sha(x) for x in paths}
    from pymupdf import open as open_pdf
    with open_pdf(paths[0]) as textbook,open_pdf(paths[1]) as deck:
        require(len(textbook)>0 and 1<=len(deck)<=500,
                "Genuine original textbook and complete slide PDF required")
        pages=len(deck)
    statements=blocks(paths[2].read_text(encoding="utf8"))
    require(len(statements)==pages,
            "Real source slide/page/script count mismatch")
    try:
        report=json.loads(paths[3].read_text(encoding="utf8"))
        rows=report["slides"]
        summary=report["summary"]
    except (OSError,ValueError,TypeError,KeyError) as exc:
        raise MultipartEnvelopeError("Missing genuine complete TTS QA report") from exc
    require(isinstance(rows,list) and len(rows)==pages
            and summary.get("passed")==pages
            and summary.get("review")==0
            and summary.get("blocking_failures")==0,
            "Actual original-source WAV screen has not passed all slides")
    envelopes=[];current=[];duration=0.0;part_no=1
    observed_files=set()
    for (number,spoken),entry in zip(statements,rows):
        file=f"slide{number}.wav"
        require(entry.get("slide")==number
                and entry.get("audio_file")==file
                and entry.get("status")=="pass"
                and entry.get("ground_truth")==spoken,
                f"Slide{number} QA result/source speech/number identity drift")
        require(file not in observed_files,"Repeated original WAV identity")
        observed_files.add(file)
        wav=paths[0].parent/file
        seconds=bound_audio_seconds(wav)
        if "duration_seconds" in entry:
            require(abs(seconds-float(entry["duration_seconds"]))<=.01,
                    f"Slide{number} QA duration differs from actual original PCM")
        contribution=seconds+per_slide_overhead_seconds
        require(contribution<max_payload_seconds,
                f"Slide{number} longer than one safe part: must split genuine speech")
        if current and duration+contribution>=max_payload_seconds:
            envelopes.append({"part_index":part_no,
                    "slides":current,
                    "projected_pcm_and_transition_seconds":round(duration,3),
                    "encoded_duration_verified":False})
            part_no+=1;duration=0;current=[]
        current.append({
            "slide":number,
            "wav":file,
            "wav_sha256":sha(wav),
            "actual_pcm_seconds":round(seconds,4),
            "tts_qa_pass":True})
        duration+=contribution
    if current:
        envelopes.append({"part_index":part_no,
                "slides":current,
                "projected_pcm_and_transition_seconds":round(duration,3),
                "encoded_duration_verified":False})
    require(all(p["projected_pcm_and_transition_seconds"]<max_payload_seconds
                for p in envelopes),
            "Strict available time budget cannot accommodate original audio")
    require([entry["slide"] for p in envelopes for entry in p["slides"]]
            ==list(range(1,pages+1)),
            "Original slides missing or out of order")
    require(all(sha(p)==digest for p in paths for name,digest in proof.items()
                if p.name==name),
            "Original media source changed while calculating part envelope")
    return {
        "schema_version":1,
        "status":"ORIGINAL_PCM_QA_LOCKED_MULTIPART_DURATION_ENVELOPE_ONLY",
        "source_pdf_sha256":proof[paths[0].name],
        "slides_pdf_sha256":proof[paths[1].name],
        "script_sha256":proof[paths[2].name],
        "real_audio_qa_sha256":proof[paths[3].name],
        "source_slide_count":pages,
        "all_original_slide_wavs_passed_acoustic_qa":True,
        "part_count":len(envelopes),
        "part_max_projected_seconds":max(p["projected_pcm_and_transition_seconds"]
                                         for p in envelopes),
        "max_payload_seconds":max_payload_seconds,
        "final_encoded_duration_limit_seconds_exclusive":600,
        "minimum_duration_slack_seconds":round(
            600-max(p["projected_pcm_and_transition_seconds"] for p in envelopes),3),
        "parts":envelopes,
        "mathematical_visual_element_mapping_verified":False,
        "real_mp4_duration_verified":False,
        "pixel_highlight_synchronization_verified":False,
        "production_video_approved":False,
        "student_publication_authorized":False,
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    root=args.folder.absolute()
    dest=args.output.absolute()
    require(dest.parent.is_dir() and not dest.exists() and not dest.is_symlink()
            and not dest.is_relative_to(root),
            "New immutable sidecar outside original source folder required")
    result=build(source=root/"source.pdf",slides=root/"slides.pdf",
                 script=root/"script.txt",
                 audio_qa=root/"tts_fidelity_report.json")
    with dest.open("x",encoding="utf8") as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    print(json.dumps({k:result[k] for k in (
        "source_slide_count","part_count","part_max_projected_seconds",
        "minimum_duration_slack_seconds","real_mp4_duration_verified")}))
    return 0
if __name__=="__main__":raise SystemExit(main())
