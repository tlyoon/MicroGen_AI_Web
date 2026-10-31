"""Produce source-witnessed ORIGINAL §8.4 slide12 radical math highlight MP4.

Only authentic source-publisher PDF, exact slide12 rendered equation geometry,
original WAV with SHA-bound independent acoustic word receipt, and complete
spoken sine/cosine substitution phrase may produce a QA-only clip.
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
from .original_thomas84_equation_provenance import audit as inspect_original_math
from .original_math_sync_video_verify import count_yellow_border

def is_complete_sine_radical_explanation(value:str)->bool:
    low=value.casefold()
    return ("nine minus nine times the sine squared of theta" in low
            and "nine times the cosine squared of theta" in low)

def _decode_media_details(mp4:Path)->float:
    info=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(mp4)],
                        capture_output=True,text=True,timeout=30).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",info)
    require(m is not None and "Video: h264" in info and "Audio: aac" in info,
            "Encoded original clip not real H.264/AAC audiovisual media")
    return int(m[1])*3600+int(m[2])*60+float(m[3])

def build(*,root:Path,word_receipt:Path,out:Path)->dict:
    root,out=(Path(x).absolute() for x in (root,out))
    folder=root/"8.4"
    inputs=[folder/name for name in
            ("source.pdf","slides.pdf","script.txt","slide12.wav")]
    source,slides,script,wav=inputs
    require(out.is_dir() and not out.is_symlink() and not out.is_relative_to(root)
            and all(p.is_file() and not p.is_symlink() for p in inputs),
            "Protected source files and exclusive external QA directory required")
    prior=[_sha(p) for p in inputs]
    witnesses=inspect_original_math(source=source,slides=slides)
    target=[e for e in witnesses["equations"] if e["slide_number"]==12]
    require(len(target)==1 and target[0]["single_original_page_candidate"]==3
            and target[0]["source_equality_chain_witnesses"][0]["source_match_kind"]
                =="source_chain_first_last_equality",
            "Complete textbook source equation endpoint geometry not witnessed")
    original=json.loads(Path(word_receipt).read_text(encoding="utf8"))
    orig_sec=next(r for r in original["sections"] if r["section"]=="8.4")
    item=orig_sec["slides"][11]
    require(item["slide"]==12 and item["wav_sha256"]==prior[-1],
            "Actual WAV differs from independently recorded word receipt")
    script_sentences,_=tokenize_reference_sentences(
        dict(blocks(script.read_text(encoding="utf-8-sig")))[12])
    spoken=item["sentence_timing_candidates"]
    require(len(spoken)==len(script_sentences)==5,
            "Original slide 12 narration sentence structure changed")
    for index,(sentence,audio) in enumerate(zip(script_sentences,spoken),start=1):
        require(sentence["narration_fragment_sha256"]==audio["narration_fragment_sha256"]
                and audio["sentence_index"]==index,
                "Original spoken text and actual word hypothesis SHA disagrees")
        matches=is_complete_sine_radical_explanation(sentence["narration_fragment"])
        require(matches==(index==3),
                "Only source-grounded third sentence describes entire 9-x² identity")
    anchor=spoken[2]
    require(anchor["word_timing_hypothesis_available"] is True
            and anchor["actual_ASR_word_anchor_fraction"]>=.85,
            "Recorded sine/cosine phrase lacks sufficiently anchored acoustic evidence")
    first,last=(anchor["first_matched_real_audio_second"],
                anchor["last_matched_real_audio_second"])
    require(all(type(x) in (float,int) and math.isfinite(x) for x in (first,last))
            and 0<first<last and 20<first<27 and last<33,
            "Unexpected source-anchored equation narration window")
    with wave.open(str(wav),"rb") as audio:
        duration=audio.getnframes()/audio.getframerate()
        require(audio.getnchannels()==1 and audio.getsampwidth()==2
                and audio.getcomptype()=="NONE" and 0<last<duration<600,
                "Actual source recording PCM unsuitable for independent sync")
    raster=out/"thomas84_slide12_original_render_qa.png"
    video=out/"thomas84_slide12_math_sync_qa.mp4"
    receipt=out/"thomas84_slide12_math_sync_provenance.json"
    require(all(not q.exists() for q in (raster,video,receipt)),
            "Never overwrite previous video or source verification")
    with pymupdf.open(slides) as deck:
        deck[11].get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False).save(str(raster))
    x0,y0,x1,y1=target[0]["rendered_slide_rect_pt"]
    visual_filter=(
        f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-4}:"
        f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+8}:"
        f"color=yellow@0.95:t=4:enable='between(t,{first:.4f},{last:.4f})',"
        "scale=trunc(iw/2)*2:trunc(ih/2)*2")
    command=[ffmpeg_executable(),"-hide_banner","-loglevel","error",
             "-loop","1","-framerate","10","-i",str(raster),"-i",str(wav),
             "-vf",visual_filter,"-c:v","libx264","-preset","veryfast",
             "-crf","19","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
             "-t",f"{duration:.6f}","-shortest","-movflags","+faststart",
             str(video)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=160)
    require(result.returncode==0 and video.is_file() and video.stat().st_size>10000,
            "Actual original-source synchronized video encoding failed: "+result.stderr[-800:])
    media_duration=_decode_media_details(video)
    require(0<media_duration<600 and abs(media_duration-duration)<.15,
            "Video duration exceeds original WAV by more than frame rounding tolerance")
    require([_sha(p) for p in inputs]==prior,
            "Original textbook/slide/narration/PCM mutated during source QA")
    proof={"status":"ORIGINAL_SLIDE12_REAL_PCM_MATH_FOCUS_PENDING_INDEPENDENT_PIXEL_QA",
           "original_source_sha256":prior[0],
           "original_slides_sha256":prior[1],
           "original_script_sha256":prior[2],
           "original_slide12_wav_sha256":prior[3],
           "original_pcm_duration_s":round(duration,4),
           "encoded_duration_s":round(media_duration,4),
           "original_source_equation_target":target[0],
           "original_narration_sentence_index":3,
           "actual_audio_anchor_fraction":anchor["actual_ASR_word_anchor_fraction"],
           "actual_equation_highlight_start_second":first,
           "actual_equation_highlight_end_second":last,
           "encoded_mp4_sha256":_sha(video),
           "original_figure_body_accepted":False,
           "full_section_production_accepted":False,
           "student_publication_authorized":False}
    with receipt.open("x",encoding="utf8") as f:
        json.dump(proof,f,indent=2)
        f.write("\n")
    return proof

def verify(*,root:Path,out:Path)->dict:
    folder=Path(root).absolute()/"8.4"
    out=Path(out).absolute()
    source=out/"thomas84_slide12_math_sync_provenance.json"
    video=out/"thomas84_slide12_math_sync_qa.mp4"
    record=json.loads(source.read_text(encoding="utf8"))
    require(_sha(video)==record["encoded_mp4_sha256"]
            and _sha(folder/"slide12.wav")==record["original_slide12_wav_sha256"]
            and _sha(folder/"source.pdf")==record["original_source_sha256"],
            "Actual original video provenance changed")
    encoded=_decode_media_details(video)
    require(encoded<600 and abs(encoded-record["original_pcm_duration_s"])<.15,
            "Encoded original slide12 duration drift")
    coords=record["original_source_equation_target"]["rendered_slide_rect_pt"]
    frames=[]
    for label,at,should in (("opening",5.0,False),("setup",15.0,False),
                            ("radical",25.0,True),("integral",37.0,False),
                            ("outro",52.0,False)):
        dst=out/f"thomas84_slide12_independent_{label}.png"
        require(not dst.exists(),"Never overwrite prior independent QA frame")
        encoded_frame=subprocess.run(
            [ffmpeg_executable(),"-hide_banner","-loglevel","error",
             "-i",str(video),"-ss",str(at),"-frames:v","1",str(dst)],
            capture_output=True,text=True,timeout=40)
        require(encoded_frame.returncode==0 and dst.is_file(),
                "Unable to independently decode actual media frame")
        probes=count_yellow_border(dst,coords)
        require((probes>=6)==should,
                f"Actual original slide12 math highlight incorrect at {at}s ({probes}/8)")
        frames.append({"second":at,"expected":should,
                       "highlight_border_probes":probes,
                       "decoded_frame_sha256":_sha(dst)})
    report={"status":"ORIGINAL_SLIDE12_INDEPENDENT_ENCODED_PIXEL_QA_PASS",
            "encoded_duration_s":round(encoded,3),
            "source_original_wav_duration_s":record["original_pcm_duration_s"],
            "independent_encoded_samples":frames,
            "full_lecture_production_accepted":False,
            "student_publication_authorized":False}
    with (out/"thomas84_slide12_independent_encoded_pixel_receipt.json").open(
            "x",encoding="utf8") as f:
        json.dump(report,f,indent=2)
        f.write("\n")
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("root","word-receipt","out"):
        p.add_argument("--"+arg,required=True,type=Path)
    a=p.parse_args(argv)
    build(root=a.root,word_receipt=a.word_receipt,out=a.out)
    report=verify(root=a.root,out=a.out)
    print(json.dumps({"status":report["status"],
                      "duration_s":report["encoded_duration_s"],
                      "pixel_samples":len(report["independent_encoded_samples"])}))
if __name__=="__main__":
    main()
