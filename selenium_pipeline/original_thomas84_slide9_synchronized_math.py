"""Original §8.4 slide9: independent textbook algebra + actual WAV synchronized MP4.

A second, genuinely rendered original-source pilot, not a template example.
Requires full equality-chain source witness on textbook page 2 and genuine
original PCM word-timed sentence 3. No paid TTS or source mutation.
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
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_equation_provenance import audit as equation_audit
from .original_math_sync_video_verify import count_yellow_border

def is_complete_example1_explanation(text:str)->bool:
    low=text.casefold()
    return ("four plus four times the tangent squared" in low
            and "four times the secant squared" in low)


def create(*,root:Path,timing_receipt:Path,output_dir:Path)->dict:
    root,output_dir=Path(root).absolute(),Path(output_dir).absolute()
    folder=root/"8.4"
    require(output_dir.is_dir() and not output_dir.is_symlink()
            and not output_dir.is_relative_to(root),
            "External isolated output folder required")
    inputs=[folder/x for x in ("source.pdf","slides.pdf","script.txt","slide9.wav")]
    source,slides,script,wav=inputs
    before=[_sha(p) for p in inputs]
    evidence=equation_audit(source=source,slides=slides)
    witness=[e for e in evidence["equations"]
             if e["slide_number"]==9]
    require(len(witness)==1
            and witness[0]["single_original_page_candidate"]==2
            and all(h["source_match_kind"]=="complete_textbook_algebraic_chain"
                    for h in witness[0]["source_equality_chain_witnesses"]),
            "Original example1 algebraic identity not source-proven")
    authored=dict(blocks(script.read_text(encoding="utf-8-sig")))
    sentences,_=tokenize_reference_sentences(authored[9])
    actual=json.loads(Path(timing_receipt).read_text(encoding="utf8"))
    acoustic=next(x for x in actual["sections"] if x["section"]=="8.4")["slides"][8]
    require(acoustic["slide"]==9 and acoustic["wav_sha256"]==before[-1]
            and len(sentences)==len(acoustic["sentence_timing_candidates"])==3,
            "Original recorded slide9 timed narration identity mismatch")
    timed=[]
    for idx,(sentence,anchor) in enumerate(zip(
        sentences,acoustic["sentence_timing_candidates"]),1):
        require(anchor["sentence_index"]==idx
                and sentence["narration_fragment_sha256"]==anchor["narration_fragment_sha256"],
                "Original spoken text differs from acoustic analysis")
        text=sentence["narration_fragment"]
        is_chain=is_complete_example1_explanation(text)
        require(is_chain==(idx==3),
                "Entire original example1 math explanation must be exactly sentence3")
        if is_chain:
            require(anchor["word_timing_hypothesis_available"] is True
                    and anchor["actual_ASR_word_anchor_fraction"]>=.70,
                    "Insufficient actual acoustic alignment for equation")
            a,b=anchor["first_matched_real_audio_second"],anchor["last_matched_real_audio_second"]
            require(type(a) in (float,int) and type(b) in (float,int)
                    and math.isfinite(a) and math.isfinite(b) and 0<a<b,
                    "No real source-bound timing for original mathematical phrase")
            timed.append((float(a),float(b)))
    require(len(timed)==1 and timed[0][0]>20 and timed[0][1]<55,
            "Unexpected recorded mathematical sentence timing")
    with wave.open(str(wav),"rb") as sound:
        duration=sound.getnframes()/sound.getframerate()
        require(sound.getnchannels()==1 and sound.getsampwidth()==2
                and .1<duration<600 and timed[0][1]<duration,
                "Original lecture PCM duration/format invalid")
    frame=output_dir/"original_thomas84_slide9_source_math_base.png"
    video=output_dir/"original_thomas84_slide9_math_sync_qa.mp4"
    receipt=output_dir/"original_thomas84_slide9_math_sync_qa.json"
    require(all(not p.exists() for p in (frame,video,receipt)),
            "Never overwrite earlier original-source math QA")
    with pymupdf.open(slides) as deck:
        deck[8].get_pixmap(matrix=pymupdf.Matrix(2,2),
                           alpha=False).save(str(frame))
    x0,y0,x1,y1=witness[0]["rendered_slide_rect_pt"]
    a,b=timed[0]
    filt=(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-4}:"
          f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+8}:"
          f"color=yellow@0.95:t=4:enable='between(t,{a:.4f},{b:.4f})',"
          "scale=trunc(iw/2)*2:trunc(ih/2)*2")
    ffmpeg=ffmpeg_executable()
    result=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error",
        "-loop","1","-framerate","10","-i",str(frame),
        "-i",str(wav),"-vf",filt,"-c:v","libx264","-preset","veryfast",
        "-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
        "-t",f"{duration:.6f}","-shortest","-movflags","+faststart",
        str(video)],capture_output=True,text=True,timeout=150)
    require(result.returncode==0 and video.stat().st_size>10000,
            "Failed to encode real timed math highlight: "+result.stderr[-700:])
    require([_sha(p) for p in inputs]==before,
            "Original textbook/slides/narration/PCM mutated during rendering")
    report={
        "status":"SOURCE_MATH_PROVEN_ORIGINAL_SLIDE9_VIDEO_PIXEL_QA_REQUIRED",
        "source_pdf_sha256":before[0],"original_slides_sha256":before[1],
        "original_narration_sha256":before[2],"original_pcm_sha256":before[3],
        "real_pcm_duration_s":round(duration,4),
        "source_chain_witness":witness[0],
        "source_narration_sentence_index":3,
        "actual_word_timing_fraction":acoustic["sentence_timing_candidates"][2]["actual_ASR_word_anchor_fraction"],
        "measured_equation_highlight_interval_s":list(timed[0]),
        "encoded_mp4_sha256":_sha(video),
        "full_lecture_accepted":False,
        "student_publication_authorized":False}
    with receipt.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
        f.write("\n")
    return report

def verify(*,root:Path,output_dir:Path)->dict:
    folder=Path(root).absolute()/"8.4"
    output_dir=Path(output_dir).absolute()
    video=output_dir/"original_thomas84_slide9_math_sync_qa.mp4"
    receipt=output_dir/"original_thomas84_slide9_math_sync_qa.json"
    record=json.loads(receipt.read_text(encoding="utf8"))
    require(_sha(video)==record["encoded_mp4_sha256"]
            and _sha(folder/"slide9.wav")==record["original_pcm_sha256"],
            "Source-bound encoded video/audio hash changed after encoding")
    ffmpeg=ffmpeg_executable()
    details=subprocess.run([ffmpeg,"-hide_banner","-i",str(video)],
                            capture_output=True,text=True,timeout=20).stderr
    match=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",details)
    encoded_duration=(int(match[1])*3600+int(match[2])*60+float(match[3])) if match else 0
    require("Video: h264" in details and "Audio: aac" in details
            and 0<encoded_duration<600
            and abs(encoded_duration-record["real_pcm_duration_s"])<.15,
            "Encoded video/audio missing or duration exceeds frame quantization tolerance")
    rect=record["source_chain_witness"]["rendered_slide_rect_pt"]
    checked=[]
    for label,t,expected in (("intro",5.0,False),
                             ("substitution",16.0,False),
                             ("algebra",37.0,True),
                             ("closing",47.0,False)):
        output=output_dir/f"original_thomas84_slide9_decoded_{label}.png"
        require(not output.exists(),"Never overwrite independent decoded frame evidence")
        decoded=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error",
            "-i",str(video),"-ss",str(t),"-frames:v","1",str(output)],
            capture_output=True,text=True,timeout=45)
        require(decoded.returncode==0 and output.is_file(),
                "Cannot independently decode real MP4 frame")
        count=count_yellow_border(output,rect)
        require((count>=6)==expected,
                f"Incorrect source-equation highlighted pixel at {t}s: {count}/8")
        checked.append({"time_s":t,"expected":expected,
                        "yellow_border_probes":count,
                        "frame_sha256":_sha(output)})
    result={"status":"ORIGINAL_SOURCE_SLIDE9_ENCODED_PIXEL_SAMPLES_PASS",
            "real_pcm_duration_s":record["real_pcm_duration_s"],
            "decoded_sample_count":len(checked),"samples":checked,
            "all_original_input_sha256_verified":True,
            "full_section_accepted":False,"student_publication_authorized":False}
    out=output_dir/"original_thomas84_slide9_independent_pixel_qa.json"
    with out.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("root","timing-receipt","output-dir"):
        p.add_argument("--"+field,required=True,type=Path)
    a=p.parse_args(argv)
    create(root=a.root,timing_receipt=a.timing_receipt,output_dir=a.output_dir)
    proof=verify(root=a.root,output_dir=a.output_dir)
    print(json.dumps({"status":proof["status"],
        "duration_s":proof["real_pcm_duration_s"],
        "decoded_samples":proof["decoded_sample_count"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
