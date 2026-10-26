"""Prove original Slide-4 WAV byte provenance, never corrected speech fidelity.

Read-only. This existing per-slide WAV contains the historical erroneous script;
measuring its samples does not create five independently narrated TTS receipts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import wave

from .figure_source_identity import _sha,require
from .ai_academic_web_review import build_review_job

_SOURCE_SHA="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
_HISTORICAL_SLIDE4_WAV_SHA="2b95cc22bc097c53eb5c55f82a0e086b0c661530be97dfa4622cdc1e9bb25106"

def inspect_original_slide4_pcm(*,folder:Path)->dict:
    root=Path(folder).absolute()
    original=tuple(_sha(root/f) for f in ("source.pdf","slides.pdf","script.txt"))
    require(original[0]==_SOURCE_SHA,"Not immutable original textbook source")
    wav_path=root/"slide4.wav"
    require(wav_path.is_file() and not wav_path.is_symlink()
            and _sha(wav_path)==_HISTORICAL_SLIDE4_WAV_SHA,
            "Historical Slide4 audio evidence missing or changed")
    job=build_review_job(folder=root,slide_numbers=[4])
    require(job["utterance_count"]==5 and
            (job["source_sha256"],job["slides_sha256"],
             job["script_sha256"])==original,
            "Historical audio cannot be detached from exact five original narrations")
    with wave.open(str(wav_path),"rb") as stream:
        rate=stream.getframerate()
        count=stream.getnframes()
        channels=stream.getnchannels()
        sample_width=stream.getsampwidth()
        data=stream.readframes(count)
    require(rate==24000 and channels==1 and sample_width==2
            and count==1087088 and len(data)==count*2,
            "Historical 24kHz PCM sample rate/frames/channels changed")
    # Nonzero samples are necessary for voiced content, NOT proof of any words.
    require(any(data[i:i+2]!=b"\x00\x00" for i in range(0,len(data),2)),
            "Historical audio is silent")
    require(_sha(wav_path)==_HISTORICAL_SLIDE4_WAV_SHA
            and tuple(_sha(root/f) for f in
                      ("source.pdf","slides.pdf","script.txt"))==original,
            "Protected historical WAV/source changed during QA")
    return {
        "status":"GENUINE_ORIGINAL_SLIDE4_PCM_MEASURED_CORRECTION_AUDIO_NOT_YET_DELIVERED",
        "source_sha256":original[0],
        "slides_sha256":original[1],
        "script_sha256":original[2],
        "original_historical_wav_sha256":_HISTORICAL_SLIDE4_WAV_SHA,
        "sample_rate":rate,"pcm_channels":channels,
        "pcm_sample_width_bytes":sample_width,
        "pcm_frame_count":count,"measured_original_slide4_audio_duration_s":count/rate,
        "has_nonzero_pcm_samples":True,
        "five_corrected_individual_WAVs_exists":False,
        "original_speech_content_acoustically_verified":False,
        "old_WAV_valid_for_corrected_narration":False,
        "per_utterance_speech_timestamps_verified":False,
        "highlight_to_speech_synchronization_verified":False,
        "actual_corrected_student_mp4_encoded":False,
        "final_under_600s_release_approved":False,
        "source_and_historical_WAV_modified":False,
        "new_provider_request_sent":False,
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    out=args.out.absolute();original=args.folder.absolute()
    require(out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(original),
            "Exclusive new external PCM receipt required")
    result=inspect_original_slide4_pcm(folder=original)
    with out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True);f.write("\n")
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":
    main()
