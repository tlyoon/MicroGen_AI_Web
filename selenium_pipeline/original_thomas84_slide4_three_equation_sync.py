"""Render three independent textbook-grounded original slide4 equation highlights.

Uses ORIGINAL publisher equation chains and genuine per-sentence acoustic word
anchors; never assumes Figure 8.2's panels/ticks are scientifically approved.
Produces a source-bound H264/AAC QA clip, then independently decodes its pixels.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import subprocess
import wave
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .video_ffmpeg import ffmpeg_executable
from .runner import blocks
from .original_thomas84_equation_provenance import audit as source_audit
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from PIL import Image


def count_source_equation_side_border(frame:Path,rect:list[float])->int:
    """Probe the vertical border MIDLINE: adjacent tightly stacked rows overlap top probes."""
    picture=Image.open(frame).convert("RGB")
    x0,y0,x1,y1=rect
    x=int(x0*2)-4
    require(0<=x<picture.width and y1>y0+4,
            "Invalid independent source math border probe geometry")
    points=[(x,int((y0+(y1-y0)*i/9)*2)) for i in range(1,9)]
    return sum(1 for px,py in points
               if 0<=py<picture.height and (
                   lambda c:c[0]>155 and c[1]>120 and c[2]<145)(
                       picture.getpixel((px,py))))

TRIG=("tangent","sine","secant")
TIMED_SENTENCES=(2,3,4)

def _source_binding(original:Path,corrected:Path,word_receipt:Path)->dict:
    source=original/"source.pdf"
    original_pdf=original/"slides.pdf"
    corrected_pdf=corrected/"slides.pdf"
    narration=original/"script.txt"
    wav=original/"slide4.wav"
    originals=[source,original_pdf,corrected_pdf,narration,wav]
    require(all(f.is_file() and not f.is_symlink() for f in originals),
            "Missing immutable publisher source/slide/narration/audio")
    before=[_sha(f) for f in originals]
    witness=source_audit(source=source,slides=original_pdf)
    equations=[e for e in witness["equations"] if e["slide_number"]==4]
    require(len(equations)==3
            and all(e["single_original_page_candidate"] in (1,2)
                    and e["whole_equation_source_pattern_verified"] for e in equations),
            "Three independent publisher equalities not proven")
    with pymupdf.open(original_pdf) as original_deck,pymupdf.open(
            corrected_pdf) as revised_deck:
        require(len(original_deck)==len(revised_deck)==17
                and original_deck[3].get_text()==revised_deck[3].get_text()
                and original_deck[3].get_pixmap(alpha=False).samples==
                    revised_deck[3].get_pixmap(alpha=False).samples,
                "Corrected academic deck altered original source slide4")
        visible=original_deck[3].get_text()
    targets={}
    for function,evidence in zip(TRIG,equations):
        phrase="For x = a "+("tan" if function=="tangent"
                             else "sin" if function=="sine" else "sec")
        require(phrase in visible
                and (("tan2" in evidence["rendered_slide_math_equation"])
                     if function=="secant" else
                     ("cos2" in evidence["rendered_slide_math_equation"])
                     if function=="sine" else
                     ("sec2" in evidence["rendered_slide_math_equation"])),
                "Slide figure/equation labels not uniquely verified")
        require(len(evidence["source_equality_chain_witnesses"])==1
                and evidence["source_equality_chain_witnesses"][0][
                    "source_match_kind"]=="source_chain_first_last_equality",
                "Not independently source-chain-grounded")
        targets[function]=evidence["rendered_slide_rect_pt"]
    actual=json.loads(Path(word_receipt).read_text(encoding="utf8"))
    section=next(s for s in actual["sections"] if s["section"]=="8.4")
    timing=section["slides"][3]
    require(timing["slide"]==4 and timing["wav_sha256"]==before[-1],
            "Real word timing is not for original slide4 source PCM")
    sentences,_=tokenize_reference_sentences(
        dict(blocks(narration.read_text(encoding="utf-8-sig")))[4])
    anchors=timing["sentence_timing_candidates"]
    require(len(sentences)==len(anchors)==5,"Original 5-sentence narration changed")
    positions={}
    for idx,name in zip(TIMED_SENTENCES,TRIG):
        spoke=sentences[idx-1]
        anchor=anchors[idx-1]
        text=spoke["narration_fragment"].casefold()
        require("for the "+name+" substitution" in text
                and anchor["narration_fragment_sha256"]==
                    spoke["narration_fragment_sha256"]
                and anchor["word_timing_hypothesis_available"] is True
                and anchor["actual_ASR_word_anchor_fraction"]>=.80,
                "Source/math speaking phrase or acoustic anchor unreliable")
        first,last=anchor["first_matched_real_audio_second"],anchor[
            "last_matched_real_audio_second"]
        require(all(type(t) in (float,int) and math.isfinite(t)
                    for t in (first,last)) and first<last,
                "No real measured source word interval")
        positions[name]=(float(first),float(last))
    require(all(positions[a][1]<positions[b][0]
                for a,b in zip(TRIG,TRIG[1:])),
            "Recorded independent algebra explanations overlap or reorder")
    with wave.open(str(wav),"rb") as audio:
        duration=audio.getnframes()/audio.getframerate()
        require(audio.getnchannels()==1 and audio.getsampwidth()==2
                and audio.getcomptype()=="NONE" and
                0<positions["secant"][1]<duration<600,
                "Wrong original PCM or duration")
    return {"originals":originals,"hashes":before,"targets":targets,
            "timings":positions,"duration":duration,"wav":wav,
            "pdf":corrected_pdf,"equations":equations}

def _encoded_duration(video:Path)->float:
    info=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(video)],
                        capture_output=True,text=True,timeout=25).stderr
    match=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",info)
    require(match is not None and "Audio: aac" in info
            and "Video: h264" in info,"No actual encoded audiovisual MP4")
    return int(match[1])*3600+int(match[2])*60+float(match[3])

def produce(*,original:Path,corrected:Path,word_receipt:Path,out:Path)->dict:
    original,corrected,out=(Path(p).absolute() for p in
                            (original,corrected,out))
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and not out.is_relative_to(corrected),
            "Use separate preexisting review output directory")
    witness=_source_binding(original,corrected,word_receipt)
    base=out/"thomas84_slide4_original_source_base.png"
    video=out/"thomas84_slide4_three_equation_sync_qa.mp4"
    receipt=out/"thomas84_slide4_source_synchronized_equations.json"
    require(all(not p.exists() for p in (base,video,receipt)),
            "Do not overwrite prior original video QA")
    with pymupdf.open(witness["pdf"]) as deck:
        deck[3].get_pixmap(matrix=pymupdf.Matrix(2,2),
                          alpha=False).save(str(base))
    filters=[]
    for name in TRIG:
        x0,y0,x1,y1=witness["targets"][name]
        a,b=witness["timings"][name]
        filters.append(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                       f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                       f"color=yellow@0.95:t=4:"
                       f"enable='between(t,{a:.4f},{b:.4f})'")
    command=[ffmpeg_executable(),"-hide_banner","-loglevel","error",
             "-loop","1","-framerate","10","-i",str(base),
             "-i",str(witness["wav"]),"-vf",",".join(filters)+
             ",scale=trunc(iw/2)*2:trunc(ih/2)*2",
             "-c:v","libx264","-preset","veryfast","-crf","19",
             "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
             "-t",f"{witness['duration']:.6f}","-shortest",
             "-movflags","+faststart",str(video)]
    encoded=subprocess.run(command,capture_output=True,text=True,timeout=150)
    require(encoded.returncode==0 and video.is_file() and video.stat().st_size>10000,
            "Real original source video rendering failed: "+encoded.stderr[-800:])
    duration=_encoded_duration(video)
    require(0<duration<600 and abs(duration-witness["duration"])<.15,
            "Real encoded MP4 differs from source PCM by too much")
    require([_sha(q) for q in witness["originals"]]==witness["hashes"],
            "Original book, corrected deck, audio or text changed during render")
    result={
        "status":"ORIGINAL_SLIDE4_THREE_SOURCE_MATH_HIGHLIGHTS_AWAIT_PIXEL_QA",
        "original_source_pdf_sha256":witness["hashes"][0],
        "original_slide_pdf_sha256":witness["hashes"][1],
        "corrected_slide_pdf_sha256":witness["hashes"][2],
        "original_script_sha256":witness["hashes"][3],
        "original_slide4_wav_sha256":witness["hashes"][4],
        "original_pcm_duration_s":round(witness["duration"],4),
        "encoded_duration_s":round(duration,4),
        "original_math_equation_source_witnesses":witness["equations"],
        "source_grounded_target_rectangles_pt":witness["targets"],
        "real_speech_word_anchor_intervals_s":witness["timings"],
        "actual_mp4_sha256":_sha(video),
        "source_figure82_panel_labels_fully_approved":False,
        "all_other_lecture_elements_approved":False,
        "student_publication_authorized":False}
    with receipt.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def verify(*,original:Path,out:Path)->dict:
    original,out=Path(original).absolute(),Path(out).absolute()
    parent=out/"thomas84_slide4_source_synchronized_equations.json"
    video=out/"thomas84_slide4_three_equation_sync_qa.mp4"
    record=json.loads(parent.read_text(encoding="utf8"))
    require(record["status"]==
            "ORIGINAL_SLIDE4_THREE_SOURCE_MATH_HIGHLIGHTS_AWAIT_PIXEL_QA"
            and _sha(video)==record["actual_mp4_sha256"]
            and _sha(original/"slide4.wav")==record["original_slide4_wav_sha256"],
            "Original source slide4 audio/video proof changed")
    seconds=_encoded_duration(video)
    require(seconds<600 and abs(seconds-record["original_pcm_duration_s"])<.15,
            "Re-decoded audiovisual duration is not real WAV duration")
    all_events=record["real_speech_word_anchor_intervals_s"]
    probes=[]
    for name,at,expected in [
        ("intro",3.,None),("tangent",12.5,"tangent"),
        ("sine",20.5,"sine"),("secant",28.0,"secant"),
        ("radical",39.,None)
    ]:
        frame=out/f"thomas84_slide4_independent_{name}.png"
        require(not frame.exists(),"Never replace old visual QA evidence")
        response=subprocess.run([ffmpeg_executable(),"-hide_banner",
            "-loglevel","error","-i",str(video),"-ss",str(at),
            "-frames:v","1",str(frame)],
            capture_output=True,text=True,timeout=45)
        require(response.returncode==0 and frame.is_file(),
                "Unable to decode REAL recorded video sample")
        scores={fn:count_source_equation_side_border(frame,rect) for fn,rect in
                record["source_grounded_target_rectangles_pt"].items()}
        require(all((score>=6)==(fn==expected)
                    for fn,score in scores.items()),
                f"Actual equation highlight wrong at {at}s: {scores}")
        if expected is not None:
            a,b=all_events[expected]
            require(a<at<b,"Visual highlight sample not in original spoken interval")
        probes.append({"name":name,"encoded_second":at,
                       "expected_source_focus":expected,
                       "observed_yellow_border_probes":scores,
                       "actual_frame_sha256":_sha(frame)})
    result={"status":"ORIGINAL_SLIDE4_THREE_MATH_EQUATIONS_INDEPENDENT_PIXEL_QA_PASS",
            "original_audio_sha256":record["original_slide4_wav_sha256"],
            "actual_mp4_sha256":_sha(video),
            "actual_decoded_sample_count":len(probes),
            "independently_verified_original_highlights":TRIG,
            "source_figure82_scientific_labels_not_approved":True,
            "full_section_production_accepted":False,
            "student_publication_authorized":False,
            "samples":probes}
    with (out/"thomas84_slide4_independent_pixel_qa.json").open(
            "x",encoding="utf8") as f:
        json.dump(result,f,indent=2);f.write("\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("original","corrected","word-receipt","out"):
        p.add_argument("--"+field,required=True,type=Path)
    a=p.parse_args(argv)
    produce(original=a.original,corrected=a.corrected,
            word_receipt=a.word_receipt,out=a.out)
    result=verify(original=a.original,out=a.out)
    print(json.dumps({"status":result["status"],
                      "source_equations":len(result["independently_verified_original_highlights"]),
                      "actual_mp4_samples":result["actual_decoded_sample_count"]}))
if __name__=="__main__":
    main()
