"""One source-proven, actual-PCM synchronized math highlight pilot.

Limited to independently revalidated Thomas 8.4 slide 5. The original
textbook's two entire equation chains must match the rendered slide,
including every operator, after only the explicitly witnessed u/theta dummy
variable rename. No inferred mathematical identities or figure identities.
The clip is an internal QA specimen, NOT full lecture release.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import subprocess
import unicodedata
import wave
from pathlib import Path

import pymupdf
from .figure_source_identity import _sha, require
from .video_ffmpeg import ffmpeg_executable
from .source_audio_focus_worklist import inspect as inspect_original_timing
from .runner import blocks
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences


def equation_key(raw: str) -> str:
    value=unicodedata.normalize("NFKC",raw)
    value=value.replace("−","-").replace("θ","u").replace("Θ","u")
    return re.sub(r"\s+","",value).rstrip(".").casefold()


def discover_chains(*,source:Path,slides:Path,slide_number:int=5)->list[dict]:
    require(slide_number==5,"Only original source-proven pilot slide 5 supported")
    with pymupdf.open(source) as book,pymupdf.open(slides) as deck:
        require(len(book)>=1 and len(deck)>=5,"Missing original source/deck")
        source_text=[p.get_text() for p in book]
        slide=deck[slide_number-1]
        visible=slide.get_text()
        require("Substituting x = a tan θ yields:" in visible
                and "Substituting x = a sin θ yields:" in visible
                and "With x = a tan u" in source_text[0]
                and "With x = a sin u" in source_text[0],
                "Independent original dummy-variable substitution declarations missing")
        lines=[]
        for block in slide.get_text("dict")["blocks"]:
            for item in block.get("lines",[]):
                raw="".join(span["text"] for span in item["spans"])
                if raw.count("=")>=3 and ("tan" in raw or "sin" in raw):
                    lines.append((raw, list(map(float,item["bbox"]))))
        require(len(lines)==2,"Expected exactly two standalone original math chains")
        matches=[]
        for raw,rectangle in lines:
            expression=equation_key(raw)
            originals=[{"source_page":i+1,"original_equation":line}
                       for i,page in enumerate(source_text)
                       for line in page.splitlines()
                       if equation_key(line)==expression]
            require(len(originals)==1 and originals[0]["source_page"]==1,
                    "Complete original equation chain not uniquely present in textbook")
            function=("tangent" if "tan2" in expression
                      and "sec2" in expression else
                      "sine" if "sin2" in expression and "cos2" in expression
                      else None)
            require(function is not None,"Unknown or mismatched trig equation chain")
            require(0<=rectangle[0]<rectangle[2]<=slide.rect.width+1
                    and 0<=rectangle[1]<rectangle[3]<=slide.rect.height+1,
                    "Original equation is outside rendered slide")
            matches.append({"function":function,"slide_equation":raw,
                            "source_equation":originals[0]["original_equation"],
                            "source_page":1,"slide_rect_pt":rectangle,
                            "full_operator_chain_matches_textbook":True,
                            "dummy_variable_rename":"theta on slide corresponds to u in textbook"})
        require({m["function"] for m in matches}=={"tangent","sine"},
                "Both independent math source identities required")
        return matches


def _run(command:list[str])->None:
    result=subprocess.run(command,capture_output=True,text=True,timeout=150)
    require(result.returncode==0,
            "Local ffmpeg encoding/decode failure: "+result.stderr[-1300:])


def produce(*,root:Path,timing_receipt:Path,output_dir:Path)->dict:
    root,output_dir=Path(root).absolute(),Path(output_dir).absolute()
    require(output_dir.is_dir() and not output_dir.is_symlink()
            and not output_dir.is_relative_to(root),
            "Use preexisting external scratch output directory")
    originals=root/"8.4"
    source,slides,script,wav=(originals/name for name in
                                ("source.pdf","slides.pdf","script.txt","slide5.wav"))
    before=[_sha(p) for p in (source,slides,script,wav)]
    evidence=inspect_original_timing(root=root,timing_receipt=timing_receipt)
    row=evidence["sections"][0]["slides"][4]
    require(row["slide"]==5 and row["wav_sha256"]==before[-1],
            "Actual speech/source receipt must match original slide 5")
    chains=discover_chains(source=source,slides=slides)
    fragments=dict(blocks(script.read_text(encoding="utf-8-sig")))
    sentences,_=tokenize_reference_sentences(fragments[5])
    require(len(sentences)==len(row["sentences"]),"Narration sentence order drift")
    alignment={"tangent":[],"sine":[]}
    for spoken,measured in zip(sentences,row["sentences"]):
        require(spoken["narration_fragment_sha256"]==measured["source_narration_sha256"],
                "Spoken fragment does not match real original PCM")
        text=spoken["narration_fragment"].casefold()
        tangent=any(x in text for x in ("tangent","secant"))
        sine=any(x in text for x in ("sine","cosine"))
        require(not (tangent and sine),
                "Narration references both distinct source equations")
        key="tangent" if tangent else "sine" if sine else None
        if key is None:
            continue
        require(measured["real_acoustic_timing_candidate"] is True
                and measured["actual_word_anchor_fraction"]>=.65,
                "Mathematical narration lacks sufficient real acoustic word timing")
        a,b=measured["real_audio_first_second"],measured["real_audio_last_second"]
        require(isinstance(a,(float,int)) and isinstance(b,(float,int))
                and math.isfinite(a) and math.isfinite(b) and 0<=a<b,
                "Invalid source-word acoustic interval")
        alignment[key].append((float(a),float(b)))
    require(len(alignment["tangent"])==2 and len(alignment["sine"])==1
            and max(b for a,b in alignment["tangent"])<
                min(a for a,b in alignment["sine"]),
            "Actual spoken equation narration ordering is not source-supported")
    with wave.open(str(wav),"rb") as audio:
        duration=audio.getnframes()/audio.getframerate()
        require(audio.getnchannels()==1 and audio.getsampwidth()==2
                and audio.getcomptype()=="NONE" and .1<duration<599,
                "Original narrated PCM invalid or longer than contract")
    require(max(b for x in alignment.values() for a,b in x)<duration,
            "Acoustic timestamp outside original recorded audio")
    source_png=output_dir/"thomas84_slide5_original_qa.png"
    video=output_dir/"thomas84_slide5_source_math_sync_qa.mp4"
    receipt=output_dir/"thomas84_slide5_source_math_sync_qa.json"
    require(all(not p.exists() for p in (source_png,video,receipt)),
            "Never overwrite existing preview or review receipts")
    with pymupdf.open(slides) as deck:
        page=deck[4]
        pix=page.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False)
        pix.save(str(source_png))
    filters=[]
    for chain in chains:
        x0,y0,x1,y1=chain["slide_rect_pt"]
        regions=alignment[chain["function"]]
        expression="+".join(f"between(t,{a:.4f},{b:.4f})" for a,b in regions)
        filters.append(
            "drawbox=x="+str(int(x0*2)-4)+":y="+str(int(y0*2)-4)+
            ":w="+str(int((x1-x0)*2)+8)+":h="+str(int((y1-y0)*2)+8)+
            ":color=yellow@0.95:t=4:enable='"+expression+"'"
        )
    ffmpeg=ffmpeg_executable()
    command=[ffmpeg,"-y","-hide_banner","-loglevel","error",
             "-loop","1","-framerate","10","-i",str(source_png),
             "-i",str(wav),"-vf",",".join(filters)+
             ",scale=trunc(iw/2)*2:trunc(ih/2)*2",
             "-c:v","libx264","-preset","veryfast","-crf","19",
             "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
             "-t",f"{duration:.6f}","-shortest",
             "-movflags","+faststart",str(video)]
    _run(command)
    require(video.is_file() and video.stat().st_size>10_000,
            "No real encoded QA video was produced")
    require([_sha(p) for p in (source,slides,script,wav)]==before,
            "Protected original teaching content changed")
    record={
        "status":"ENCODED_ORIGINAL_MATH_SYNC_PILOT_PENDING_PIXEL_QA",
        "source_sha256":before[0],"slides_sha256":before[1],
        "narration_sha256":before[2],"original_wav_sha256":before[3],
        "original_pcm_duration_s":round(duration,4),
        "original_textbook_chains":chains,
        "actual_recorded_word_timed_highlight_intervals":alignment,
        "encoded_qa_mp4_sha256":_sha(video),
        "full_41_slide_production_accepted":False,
        "figure_panel_completeness_verified":False,
        "student_publication_authorized":False
    }
    with receipt.open("x",encoding="utf8") as fp:
        json.dump(record,fp,indent=2,ensure_ascii=False)
        fp.write("\n")
    return record


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("root","timing-receipt","output-dir"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args(argv)
    result=produce(root=a.root,timing_receipt=a.timing_receipt,output_dir=a.output_dir)
    print(json.dumps({"status":result["status"],
                      "duration":result["original_pcm_duration_s"],
                      "math_source_matches":len(result["original_textbook_chains"])}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
