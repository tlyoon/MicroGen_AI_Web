"""Original publisher-backed outline topics, with actual offline Vosk word times.

No guessed equal-duration subdivisions: all five original topic intervals are
derived from actual unprompted offline ASR word timestamps, checked against
unchanged original narration and source book + rendered slide PDF. Two Vosk
misrecognitions are NOT silently rewritten into recognized words.
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
from .original_thomas84_offline_word_pdf_timing import (
    _real_local_vosk_transcribe,tokenize_reference_sentences)
from .original_thomas84_slide4_three_equation_sync import (
    count_source_equation_side_border)
from .original_thomas84_multiline_math_witness import EXPECTED_SOURCE_SHA

# Exact slide2 text and visible PDF rectangles from original physical PDF.
OUTLINE={
  1:("Introduction to Trigonometric Substitutions",[32.7,109.6,233.5,122.4],
     ["will","examine","how","these","transformations","help","simplify","complex"],
     None),
  2:("Reference Right Triangles and Algebraic Forms",[32.7,125.5,249.,139.],
     ["review","the","necessary","reference","right","triangles","and","algebraic","forms"],
     None),
  3:("Reversibility and Inverse Function Domain Restrictions",[32.7,142.,284.5,156.],
     ["discuss","the","importance","of"],
     ["inverse","function","domain","restrictions"]),
  4:("Procedure for Trigonometric Substitution",[32.7,158.5,223.5,172.5],
     ["the","step","by","step","procedure"],None),
  5:("Worked Examples and Applications",[32.7,175.,196.,189.],
     ["work","through","several","detailed","examples","and","applications"],None),
}
STATUS="FIVE_ORIGINAL_PUBLISHER_OUTLINE_WORD_ACOUSTIC_EVENTS_ENCODED_PIXEL_QA_PASS"


def _phrase(words:list[dict],sequence:list[str])->tuple[int,int]:
    require(len(sequence)>=4,"No single isolated word token can certify a topic")
    normalized=[row["word"].casefold() for row in words]
    candidates=[i for i in range(len(normalized)-len(sequence)+1)
                if normalized[i:i+len(sequence)]==sequence]
    require(len(candidates)==1,
            f"Required actual unprompted spoken phrase not uniquely present: {sequence}")
    return candidates[0],candidates[0]+len(sequence)-1


def _proof(pages:list[str],visible:str,narration:str)->dict:
    require(len(pages)>=4,
            "Original textbook chapter pages incomplete")
    checks=[
      ("8.4 Trigonometric Substitutions",pages[0]),
      ("reference right triangles in Figure 8.2",pages[0]),
      ("For reversibility,",pages[1]),
      ("Procedure for a Trigonometric Substitution",pages[1]),
      ("EXAMPLE 1",pages[1]),
    ]
    require(all(term in page for term,page in checks),
            "Five original §8.4 textbook topic sources not all independently located")
    for label,_,_,_ in OUTLINE.values():
        require(visible.count(label)==1,
                "Original rendered outline has a missing/ambiguous topic label")
    phrases=("transformations help simplify complex integrals",
             "reference right triangles and algebraic forms",
             "reversibility and inverse function domain restrictions",
             "step by step procedure",
             "several detailed examples and applications")
    spoken=narration.casefold()
    require(all(s in spoken for s in phrases),
            "Original authored spoken five-topic narration does not match PDF outline")
    return {"original_book_page1_and_page2_with_example1":True,
            "five_distinct_rendered_outline_topics_verified":True,
            "exact_original_narration_topics_present":True,
            "all_textbook_figure_axis_labels_verified":False}


def _mp4_duration(video:Path)->float:
    info=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(video)],
                        capture_output=True,text=True,timeout=30).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",info)
    require(m and "Video: h264" in info and "Audio: aac" in info,
            "Actual outline video missing genuine H264/AAC streams")
    return int(m[1])*3600+int(m[2])*60+float(m[3])


def produce(*,original:Path,corrected:Path,model_path:Path,
            word_receipt:Path,out:Path)->dict:
    original,corrected,model_path,out=(Path(x).absolute()
                                      for x in (original,corrected,model_path,out))
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and model_path.is_dir() and not model_path.is_symlink(),
            "Original source and offline ASR model must be on Dell Windows")
    publisher=original/"source.pdf"
    old=original/"slides.pdf"
    revised=corrected/"slides.pdf"
    script=original/"script.txt"
    wav=original/"slide2.wav"
    files=[publisher,old,revised,script,wav]
    require(all(p.is_file() and not p.is_symlink() for p in files),
            "Physical publisher/source/source speech absent")
    hashes={str(q):_sha(q) for q in files}
    require(hashes[str(publisher)]==EXPECTED_SOURCE_SHA,
            "Not original publisher Thomas Calculus §8.4")
    narr=dict(blocks(script.read_text(encoding="utf-8-sig")))[2]
    sentences,_=tokenize_reference_sentences(narr)
    require(len(sentences)==2,"Not original two-sentence outline narration")
    original_timing=json.loads(Path(word_receipt).read_text(encoding="utf8"))
    data=next(x for x in original_timing["sections"] if x["section"]=="8.4")[
        "slides"][1]
    require(data["wav_sha256"]==_sha(wav)
            and data["sentence_timing_candidates"][1][
                "actual_ASR_word_anchor_fraction"]>=.90
            and sentences[1]["narration_fragment_sha256"]==
                data["sentence_timing_candidates"][1]["narration_fragment_sha256"],
            "The original source outline narrated sentence lacks genuine word evidence")
    with pymupdf.open(publisher) as book,pymupdf.open(old) as original_pdf,pymupdf.open(revised) as final:
        require(len(original_pdf)==len(final)==17
                and original_pdf[1].get_text()==final[1].get_text()
                and original_pdf[1].get_pixmap(alpha=False).samples==
                    final[1].get_pixmap(alpha=False).samples,
                "Cumulative corrected PDF altered original outline unexpectedly")
        visible=original_pdf[1].get_text()
        proof=_proof([p.get_text() for p in book],visible,narr)
        for name,rect,*_ in OUTLINE.values():
            box=pymupdf.Rect(rect)
            require(box.is_valid and not box.is_infinite
                    and original_pdf[1].rect.contains(box)
                    and name in original_pdf[1].get_text(clip=box),
                    f"Original physical publisher outline rectangle not visible: {name}")
    try:
        import vosk
    except ImportError:
        require(False,"Offline actual word timestamps need authorized Vosk, no guess fallback")
    vosk.SetLogLevel(-1)
    recognized,unprompted=_real_local_vosk_transcribe(
        model=vosk.Model(str(model_path)),exe=ffmpeg_executable(),audio_path=wav)
    require(len(recognized)>42 and
            all(0<=row["start"]<=row["end"]<30
                and math.isfinite(row["start"]) and math.isfinite(row["end"])
                for row in recognized),
            "Original spoken words not genuinely decoded")
    events={}
    previous_end=-1.
    for i,(title,rect,start_phrase,end_phrase) in OUTLINE.items():
        j,k=_phrase(recognized,start_phrase)
        if end_phrase:
            m,n=_phrase(recognized,end_phrase)
            require(k<m,"Actual multi-phrase topic3 order wrong")
            k=n
        a,b=recognized[j]["start"],recognized[k]["end"]
        require(previous_end<a<b<27,
                f"Real spoken outline topic order/time {i} not independently proven")
        previous_end=b
        events[str(i)]={"actual_rendered_title":title,
            "original_pdf_rect_pt":rect,
            "unprompted_real_asr_start_s":float(a),
            "unprompted_real_asr_end_s":float(b),
            "actual_vosk_first_word":recognized[j]["word"],
            "actual_vosk_last_word":recognized[k]["word"],
            "source_book_pdf_topic_witness":True,
            "actual_pcm_spoken_word_timestamp_verified":True}
    # Explicitly record actual two ASR deficiencies. Do not silently
    # relabel 'enter girls' as 'integrals' or 'reverse ability' as 'reversibility'.
    require("enter girls" in unprompted and "reverse ability" in unprompted,
            "Original ASR transcript changed: source expression needs revalidation")
    with wave.open(str(wav),"rb") as wf:
        duration=wf.getnframes()/wf.getframerate()
        require(wf.getnchannels()==1 and wf.getsampwidth()==2
                and wf.getcomptype()=="NONE" and
                events["5"]["unprompted_real_asr_end_s"]<duration<600,
                "Original PCM format/duration mismatched real source audio")
    source_png=out/"original_slide2_outline.png"
    video=out/"thomas84_slide2_real_word_source_focus.mp4"
    receipt=out/"original_slide2_real_word_source_pixel_qa.json"
    require(all(not p.exists() for p in (source_png,video,receipt)),
            "Never overwrite existing original QA evidence")
    with pymupdf.open(revised) as deck:
        deck[1].get_pixmap(matrix=pymupdf.Matrix(2,2),
                          alpha=False).save(str(source_png))
    masks=[]
    for event in events.values():
        x0,y0,x1,y1=event["original_pdf_rect_pt"]
        a=event["unprompted_real_asr_start_s"]
        b=event["unprompted_real_asr_end_s"]
        masks.append(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
             f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
             f"color=yellow@0.95:t=4:enable='between(t,{a:.4f},{b:.4f})'")
    encoded=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel","error",
        "-loop","1","-framerate","10","-i",str(source_png),"-i",str(wav),
        "-vf",",".join(masks)+",scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v","libx264","-preset","veryfast","-crf","19",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
        "-t",f"{duration:.6f}","-shortest","-movflags","+faststart",
        str(video)],capture_output=True,text=True,timeout=135)
    require(encoded.returncode==0 and video.is_file()
            and video.stat().st_size>10000,
            "Failed actual source word video rendering: "+encoded.stderr[-600:])
    length=_mp4_duration(video)
    require(abs(length-duration)<.15 and length<600,
            "Actual original outline PCM/video duration drift")
    probes=[]
    for step,time,focused in ([("intro",.1,None)] +
         [(f"topic{i}",(e["unprompted_real_asr_start_s"]+
                 e["unprompted_real_asr_end_s"])/2,str(i))
          for i,e in events.items()]):
        image=out/f"real_outline_independent_{step}.png"
        require(not image.exists(),"Do not replace prior recorded QA pixels")
        decode=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
            "error","-i",str(video),"-ss",f"{time:.3f}",
            "-frames:v","1",str(image)],
            capture_output=True,text=True,timeout=40)
        require(decode.returncode==0 and image.is_file(),
                "Unable to independently decode real original outline frame")
        values={i:count_source_equation_side_border(image,e["original_pdf_rect_pt"])
                for i,e in events.items()}
        require(all((score>=6)==(i==focused)
                    for i,score in values.items()),
                f"Independent outline spoken-word focus not exclusive: {values}")
        probes.append({"real_encoded_second":round(time,3),
                       "expected_source_topic":focused,
                       "actual_yellow_probe_counts":values,
                       "independent_decoded_frame_sha256":_sha(image)})
    require({str(q):_sha(q) for q in files}==hashes,
            "Original source, corrected PDF or WAV mutated")
    report={"status":STATUS,
        "publisher_original_source_sha256":_sha(publisher),
        "original_pdf_sha256":_sha(old),
        "corrected_pdf_sha256":_sha(revised),
        "original_slide2_wav_sha256":_sha(wav),
        "original_script_sha256":_sha(script),
        "original_publisher_five_outline_topic_evidence":proof,
        "real_unprompted_asr_transcript":unprompted,
        "actual_vosk_misrecognitions_not_source_truth":["enter girls","reverse ability"],
        "real_original_word_anchor_topic_events":events,
        "physical_original_pcm_duration_s":round(duration,4),
        "real_encoded_h264_aac_duration_s":round(length,4),
        "actual_encoded_mp4_sha256":_sha(video),
        "independent_decoded_pixel_samples":probes,
        "student_publication_authorized":False,
        "all_lecture_math_and_figures_verified":False}
    with receipt.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps({"status":STATUS,"original_topics":len(events),
          "independent_actual_frame_samples":len(probes)}))
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original","corrected","model-path","word-receipt","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args(argv)
    produce(original=a.original,corrected=a.corrected,
            model_path=a.model_path,word_receipt=a.word_receipt,out=a.out)

if __name__=="__main__":
    main()
