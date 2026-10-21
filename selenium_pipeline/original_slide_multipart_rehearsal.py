"""Combine already-recorded original slide/WAV rehearsal clips into real multipart review.

Whole-slide transition timing is measured, not narration-to-element timing.
All teaching inputs are read-only. A review MP4 is NOT a replacement.
"""
from __future__ import annotations
import json,subprocess
from pathlib import Path
from .figure_source_identity import require,_sha
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .original_slide_pcm_rehearsal import rehearse_original_slide
from .highlight_video_preview import ffmpeg_path,probe_mp4

def rehearse_contiguous_original_slides(*,folder:Path,slide_start:int,
                                        slide_end:int,destination:Path)->dict:
    folder,destination=Path(folder).absolute(),Path(destination).absolute()
    require(type(slide_start) is int and type(slide_end) is int
            and 1<=slide_start<=slide_end and slide_end-slide_start<=30
            and destination.parent.is_dir() and not destination.exists()
            and not destination.is_relative_to(folder),
            "Only an independent new original slide-range rehearsal is allowed")
    original=inspect_original_slide_wav_plan(folder)
    evidence=original["wav_evidence"]
    require(slide_end<=len(evidence),"Slide range beyond genuine WAV inventory")
    wav_sum=sum(x["duration_s"] for x in evidence[slide_start-1:slide_end])
    require(0<wav_sum<540,"Original audio window must leave margin below 600")
    hashes={name:_sha(folder/name) for name in ("source.pdf","slides.pdf","script.txt")}
    destination.mkdir()
    rows=[]
    for i in range(slide_start,slide_end+1):
        receipt=rehearse_original_slide(folder=folder,slide_number=i,
                                        destination=destination/f"slide_{i:03d}")
        rows.append(receipt)
    playlist=destination/"original_slides.ffconcat"
    with playlist.open("x",encoding="utf8") as stream:
        stream.write("ffconcat version 1.0\n")
        for i in range(slide_start,slide_end+1):
            stream.write(f"file 'slide_{i:03d}/original_slide_technical_rehearsal.mp4'\n")
    output=destination/"whole_slide_multipart_review.mp4"
    exe=ffmpeg_path()
    result=subprocess.run([exe,"-hide_banner","-loglevel","error",
        "-nostdin","-f","concat","-safe","0","-i",str(playlist),
        "-c","copy","-y",str(output)],
        capture_output=True,timeout=180)
    require(result.returncode==0 and output.is_file(),
            "Could not concatenate genuine independent audio slides")
    probe=probe_mp4(output,exe=exe)
    require(0<probe["duration_s"]<600
            and abs(probe["duration_s"]-wav_sum)<.75,
            "Real concatenated MP4 duration drift or ten-minute breach")
    require(all(_sha(folder/n)==digest for n,digest in hashes.items())
            and all(_sha(folder/x["relative_name"])==x["sha256"]
                    for x in evidence[slide_start-1:slide_end]),
            "Source or original WAV mutated during review encoding")
    receipt={"status":"GENUINE_WHOLE_SLIDE_MULTIPART_REVIEW_ONLY",
        "original_file_sha256":hashes,
        "slide_range":[slide_start,slide_end],
        "independently_encoded_whole_slide_count":len(rows),
        "original_pcm_sum_s":round(wav_sum,4),
        "actual_encoded_mp4_duration_s":probe["duration_s"],
        "mp4_sha256":_sha(output),
        "individual_original_wav_sha256":[r["original_wav_sha256"] for r in rows],
        "element_level_highlight_verified":False,
        "actual_words_on_screen_timing_verified":False,
        "student_publication_authorized":False}
    with (destination/"multipart_receipt.json").open("x",encoding="utf8") as out:
        json.dump(receipt,out,indent=2)
        out.write("\n")
    return receipt
