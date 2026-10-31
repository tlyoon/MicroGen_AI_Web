"""Two genuine corrected Thomas §8.4 slide/voice synchronized QA videos.

Source-bound visual regions:
  Slide 6: corrected one-to-one statement, tangent source equation and
  *top* arctangent panel of original Figure 8.3, independently mapped
  against textbook source operator/curves in PR399.
  Slide 17: corrected inclusive arcsine/strict tangent entire review question.

Genuine Vosk unprompted word timestamps drive intervals. Rendered original
17-slide *corrected* PDF and freshly generated Flash-Lite/Kore audio (PR404),
not the wrong earlier slide6.wav / slide17.wav. Independently decode encoded
MP4 frames to prove timed border appears and disappears as expected.

Never imply source axis tick correctness or finished full lecture acceptance.
"""
from __future__ import annotations
import argparse
from difflib import SequenceMatcher
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import wave
import pymupdf

from .figure_source_identity import require,_sha
from .runner import blocks
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_corrected_tts_batch import STATUS as JOB_STATUS,SUCCESS
from .original_math_sync_video_verify import count_yellow_border
from .video_ffmpeg import ffmpeg_executable
from .tts_offline_vosk_fidelity import approved_assets,recognizer_model
from .original_thomas84_cumulative_academic_repairs import CORRECT_REVIEW_SPEECH

MATCH_REQUIRED=.70
SLIDES=(6,17)

def words(value:str)->list[str]:
    return re.findall(r"[a-z]+|[0-9]+",value.casefold())

def match_actual_sentences(texts:list[str],events:list[dict])->list[dict]:
    require(type(texts) is list and 2<=len(texts)<=8
            and type(events) is list and len(events)>=15
            and all(type(e.get("word")) is str
                    and type(e.get("start")) in (int,float)
                    and type(e.get("end")) in (int,float)
                    and e["end"]>e["start"]>=0
                    for e in events),
            "Real time-stamped, unprompted ASR words required")
    flat=[]
    bounds=[]
    for sentence in texts:
        start=len(flat)
        flat.extend(words(sentence))
        bounds.append((start,len(flat)))
    asr=[event["word"].casefold() for event in events]
    pairs=[(block.a+i,block.b+i)
           for block in SequenceMatcher(
               None,flat,asr,autojunk=False).get_matching_blocks()
           for i in range(block.size)]
    report=[]
    for i,(first,last) in enumerate(bounds,1):
        matched=[j for k,j in pairs if first<=k<last]
        fraction=len(matched)/max(1,last-first)
        require(matched and fraction>=MATCH_REQUIRED,
                f"Actual sentence {i} acoustic words are insufficiently matched")
        low=float(events[min(matched)]["start"])
        high=float(events[max(matched)]["end"])
        require(math.isfinite(low) and math.isfinite(high) and high>low,
                "No real finite source-aligned time window")
        report.append({"sentence_index":i,
                       "actual_matched_word_fraction":round(fraction,5),
                       "real_earliest_matched_word_s":round(low,5),
                       "real_last_matched_word_s":round(high,5),
                       "actual_matched_words":len(matched),
                       "source_word_count":last-first})
    require(all(a["real_last_matched_word_s"]<
                b["real_earliest_matched_word_s"]+.25
                for a,b in zip(report,report[1:])),
            "Source speech sentence order overlaps or changed")
    return report

def recognized_words(wav:Path,model)->list[dict]:
    from vosk import KaldiRecognizer
    decoded=subprocess.run([
        ffmpeg_executable(),"-nostdin","-v","error",
        "-i",str(wav),"-ac","1","-ar","16000",
        "-f","s16le","pipe:1"],
        capture_output=True,timeout=90)
    require(decoded.returncode==0 and len(decoded.stdout)>=16000,
            "Actual corrected PCM failed real audio decoding")
    rec=KaldiRecognizer(model,16000)
    rec.SetWords(True)
    rows=[]
    for k in range(0,len(decoded.stdout),8000):
        if rec.AcceptWaveform(decoded.stdout[k:k+8000]):
            rows+=json.loads(rec.Result()).get("result",[])
    rows+=json.loads(rec.FinalResult()).get("result",[])
    require(len(rows)>=15,"Source WAV lacks independently decoded words")
    return rows

def union(rects:list)->list[float]:
    require(bool(rects),"No original corrected slide mathematical geometry")
    r=pymupdf.Rect(rects[0])
    for box in rects[1:]:
        r|=pymupdf.Rect(box)
    require(r.is_valid and not r.is_empty,"Invalid original PDF region")
    return [round(float(v),4) for v in r]

def original_visual_targets(*,pdf:Path,figure_proof:dict)->dict[int,list[dict]]:
    require(figure_proof.get("status")==
            "ORIGINAL_FIGURE83_THREE_VERTICAL_PANEL_CURVES_AND_INVERSE_GLYPHS_CORROBORATED"
            and figure_proof.get(
                "three_source_printed_inverse_glyphs_uniquely_matched_to_slide") is True
            and figure_proof.get("student_publication_authorized") is False,
            "Original textbook arctangent panel identity evidence required")
    with pymupdf.open(pdf) as deck:
        require(len(deck)==17,"Missing full corrected original 17-slide PDF")
        page6,page17=deck[5],deck[16]
        blocks6=[b for b in page6.get_text("blocks") if b[6]==0]
        blocks17=[b for b in page17.get_text("blocks") if b[6]==0]
        full_review=" ".join(b[4] for b in blocks17)
        require("Restrict trigonometric functions" in blocks6[3][4]
                and "For x = a tan" in blocks6[4][4]
                and "for tangent" in full_review
                and "for sine" in full_review,
                "Original source correction mathematical blocks changed")
        images=[q for q in page6.get_image_info(xrefs=True)
                if q["width"]>=100 and q["height"]>=100]
        require(len(images)==1 and images[0]["width"]==232
                and images[0]["height"]==480,
                "Original Figure8.3 actual bitmap missing/ambiguous")
        figure=images[0]
        row=figure_proof["curve_and_inverse_operator_evidence"][0]
        require(row["panel_index"]==1
                and row["verified_source_function_name"]=="tangent",
                "Arctangent panel label source identity changed")
        top,bottom=row["original_slide_bitmap_vertical_panel_y_pixels"]
        require(0<=top<bottom<480,"Source-pinned figure panel layout invalid")
        bbox=pymupdf.Rect(figure["bbox"])
        rect_fig=[round(bbox.x0,4),
                  round(bbox.y0+bbox.height*top/480,4),
                  round(bbox.x1,4),
                  round(bbox.y0+bbox.height*bottom/480,4)]
        visual={
            6:[
                {"sentence_index":2,"focus":"corrected_branch_restriction",
                 "rect_pt":union([blocks6[3][:4]])},
                {"sentence_index":3,"focus":"source_matched_tangent_inverse",
                 "rect_pt":union([b[:4] for b in blocks6[4:9]])},
                {"sentence_index":4,"focus":"source_verified_arctangent_top_graph",
                 "rect_pt":rect_fig}
            ],
            17:[
                {"sentence_index":3,"focus":"corrected_tangent_vs_sine_interval",
                 "rect_pt":union([b[:4] for b in blocks17
                                  if 125<=b[1] and b[3]<210])}
            ]}
        for n,regions in visual.items():
            page=deck[n-1]
            for r in regions:
                box=pymupdf.Rect(r["rect_pt"])
                require(box.is_valid and not box.is_empty
                        and page.rect.contains(box),
                        "Source-matched mathematical visual region outside corrected page")
        return visual

def checked_inputs(*,original:Path,corrected:Path,tts:Path,
                   qa:Path,figure:Path)->dict:
    jobs=json.loads((tts/"SOURCE_LOCKED_PENDING_TTS.json").read_text(encoding="utf8"))
    done=json.loads((tts/"REAL_TWO_WAVS_PENDING_ACOUSTIC_QA.json").read_text(encoding="utf8"))
    audit=json.loads(qa.read_text(encoding="utf8"))
    fig=json.loads(figure.read_text(encoding="utf8"))
    paired=json.loads((corrected/
           "original_two_slides_source_corrected_audio_stale.json").read_text(encoding="utf8"))
    require(jobs.get("status")==JOB_STATUS and done.get("status")==SUCCESS
            and jobs.get("slide_numbers")==list(SLIDES)
            and jobs.get("source_pdf_sha256")==_sha(original/"source.pdf")
            and jobs.get("corrected_slides_sha256")==_sha(corrected/"slides.pdf")
            and jobs.get("corrected_full_narration_sha256")==_sha(corrected/"script.txt")
            and done.get("source_pinned_job_sha256")==_sha(tts/"SOURCE_LOCKED_PENDING_TTS.json")
            and audit.get("status")==
                "TWO_CORRECTED_ORIGINAL_KORE_WAVS_OFFLINE_PHONETIC_SCREEN_PASS"
            and audit.get("all_corrected_wavs_phonetic_screen_pass") is True
            and audit.get("provider_physical_evidence_sha256")==
                _sha(tts/"REAL_TWO_WAVS_PENDING_ACOUSTIC_QA.json")
            and paired.get("only_corrected_slides")==list(SLIDES)
            and paired.get("old_original_wavs_reuse_prohibited")==list(SLIDES)
            and paired.get("student_publication_authorized") is False
            and fig.get("source_pdf_sha256")==_sha(original/"source.pdf"),
            "Original source-bound paired TTS and evidence disagree")
    script=dict(blocks((corrected/"script.txt").read_text(encoding="utf8")))
    require(CORRECT_REVIEW_SPEECH in script[17],
            "Corrected arcsine domain speech text missing")
    for n in SLIDES:
        require(done["physical_new_wavs"][str(n)]["sha256"]==
                _sha(tts/f"corrected_original_slide{n}.wav")
                and audit["source_slide_audio_observations"][str(n)][
                    "passes_automated_phonetic_screen"] is True
                and audit["source_slide_audio_observations"][str(n)][
                    "explicit_original_wrong_mathematics_suspected"] is False
                and paired["stale_original_wav_sha256"][str(n)]==
                    _sha(original/f"slide{n}.wav"),
                "Original stale WAV or unproved corrected speech cannot be synchronized")
    return {"job":jobs,"done":done,"audit":audit,"figure":fig,
            "paired":paired,"script":script}

def encode_one(*,slide:int,corrected:Path,tts:Path,
               focus:list[dict],sentences:list[dict],out:Path)->dict:
    wav=tts/f"corrected_original_slide{slide}.wav"
    with wave.open(str(wav),"rb") as voice:
        duration=voice.getnframes()/voice.getframerate()
        require(voice.getnchannels()==1 and voice.getsampwidth()==2
                and 0<duration<600,
                "Original corrected math WAV not valid mono PCM16")
    clip=out/f"corrected_thomas84_slide{slide}_real_sync.mp4"
    background=out/f"corrected_thomas84_slide{slide}_pdf.png"
    receipt=out/f"corrected_thomas84_slide{slide}_real_sync.json"
    require(not any(p.exists() for p in (clip,background,receipt)),
            "Never overwrite existing original corrected audio/video QA")
    with pymupdf.open(corrected/"slides.pdf") as doc:
        doc[slide-1].get_pixmap(matrix=pymupdf.Matrix(2,2),
                                alpha=False).save(str(background))
    filters=[]
    events=[]
    for visual in focus:
        anchor=sentences[visual["sentence_index"]-1]
        begin=float(anchor["real_earliest_matched_word_s"])
        end=float(anchor["real_last_matched_word_s"])
        require(0<begin<end<duration+.01
                and anchor["actual_matched_word_fraction"]>=MATCH_REQUIRED,
                "Real corrected source sentence lacks genuine acoustic coverage")
        x0,y0,x1,y1=visual["rect_pt"]
        filters.append(
            f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-4}:"
            f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+8}:"
            f"color=yellow@0.95:t=4:enable='between(t,{begin:.4f},{end:.4f})'")
        events.append({**visual,"source_bound_speech_start_s":begin,
                             "source_bound_speech_end_s":end,
                             "actual_matched_word_fraction":
                                 anchor["actual_matched_word_fraction"]})
    filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
    result=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel","error",
        "-loop","1","-framerate","10","-i",str(background),
        "-i",str(wav),"-vf",",".join(filters),
        "-c:v","libx264","-preset","veryfast","-crf","19",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
        "-t",f"{duration:.6f}","-shortest","-movflags","+faststart",
        str(clip)],capture_output=True,text=True,timeout=160)
    require(result.returncode==0 and clip.is_file() and clip.stat().st_size>20000,
            "Authentic corrected element highlight encoding failed: "+
            result.stderr[-600:])
    info=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(clip)],
                        capture_output=True,text=True,timeout=20).stderr
    match=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",info)
    actual=(int(match[1])*3600+int(match[2])*60+float(match[3])) if match else 0
    require("Video: h264" in info and "Audio: aac" in info
            and actual<600 and abs(actual-duration)<.15,
            "Encoded corrected MP4 duration/audio/video stream invalid")
    manifest={"status":"ORIGINAL_SOURCE_CORRECTED_ELEMENT_FOCUS_MP4_PENDING_FRAME_QA",
              "original_source_slide_number":slide,
              "real_audio_sha256":_sha(wav),"corrected_pdf_sha256":
                  _sha(corrected/"slides.pdf"),
              "actual_wav_duration_s":round(duration,5),
              "encoded_mp4_duration_s":actual,"encoded_mp4_sha256":_sha(clip),
              "actual_ASR_word_aligned_sentences":sentences,
              "source_grounded_visual_event_targets":events,
              "all_math_figures_release_approved":False,
              "full_lecture_production_accepted":False,
              "student_publication_authorized":False}
    with receipt.open("x",encoding="utf8") as f:
        json.dump(manifest,f,indent=2,ensure_ascii=False)
        f.write("\n")
    return manifest

def independent_encoded_frames(*,slide:int,out:Path)->dict:
    source=out/f"corrected_thomas84_slide{slide}_real_sync.json"
    clip=out/f"corrected_thomas84_slide{slide}_real_sync.mp4"
    record=json.loads(source.read_text(encoding="utf8"))
    require(record["encoded_mp4_sha256"]==_sha(clip),
            "Encoded original math video changed after generation")
    events=record["source_grounded_visual_event_targets"]
    samples=[("intro",1.,None)]
    for item in events:
        middle=(item["source_bound_speech_start_s"]+
                item["source_bound_speech_end_s"])/2
        samples.append((item["focus"],middle,item["focus"]))
    tail=min(record["encoded_mp4_duration_s"]-.3,
             events[-1]["source_bound_speech_end_s"]+.15)
    if tail>events[-1]["source_bound_speech_end_s"]+.09:
        samples.append(("outro",tail,None))
    verified=[]
    for name,time,which in samples:
        frame=out/f"corrected_thomas84_slide{slide}_decoded_{name}.png"
        require(not frame.exists(),"Never overwrite original independent QA evidence")
        decoded=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel",
            "error","-i",str(clip),"-ss",f"{time:.4f}",
            "-frames:v","1",str(frame)],capture_output=True,text=True,timeout=45)
        require(decoded.returncode==0 and frame.is_file(),
                "Could not independently decode real corrected audio sync frame")
        probes={x["focus"]:count_yellow_border(frame,x["rect_pt"])
                for x in events}
        require(all((p>=6)==(k==which) for k,p in probes.items()),
                f"Actual corrected MP4 focus pixels wrong at {time}: {probes}")
        verified.append({"sample":name,"actual_encoded_second":round(time,4),
                         "expected_focus":which,"observed_focus_border_probes":probes,
                         "decoded_frame_sha256":_sha(frame)})
    result={"status":"ORIGINAL_SOURCE_CORRECTED_MATH_SYNCHRONIZED_ENCODED_PIXEL_QA_PASS",
            "original_slide_number":slide,
            "actual_encoded_mp4_sha256":_sha(clip),
            "source_audio_pcm_duration_s":record["actual_wav_duration_s"],
            "verified_samples":verified,
            "original_figure_full_axis_semantics_accepted":False,
            "full_original_section_production_accepted":False,
            "student_publication_authorized":False}
    with (out/f"corrected_thomas84_slide{slide}_independent_pixel_qa.json").open(
            "x",encoding="utf8") as f:
        json.dump(result,f,indent=2)
        f.write("\n")
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("original","corrected","tts","speech-qa","figure",
                 "vosk-model","vosk-packages","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args(argv)
    original,corrected,tts,out=(Path(x).absolute() for x in
                                (a.original,a.corrected,a.tts,a.out))
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and not out.is_relative_to(corrected)
            and not out.is_relative_to(tts),
            "Original math/audio immutable and external exclusive QA output needed")
    prove=checked_inputs(original=original,corrected=corrected,tts=tts,
                         qa=a.speech_qa,figure=a.figure)
    figure_regions=original_visual_targets(pdf=corrected/"slides.pdf",
                                            figure_proof=prove["figure"])
    os.environ["MICROGEN_TTS_QA_VOSK_MODEL"]=str(a.vosk_model)
    os.environ["MICROGEN_TTS_QA_VOSK_PACKAGES"]=str(a.vosk_packages)
    model_dir,site_dir=approved_assets()
    model=recognizer_model(str(model_dir),str(site_dir))
    old={str(q):_sha(q) for q in
         [original/"source.pdf",corrected/"slides.pdf",corrected/"script.txt",
          *[original/f"slide{x}.wav" for x in SLIDES],
          *[tts/f"corrected_original_slide{x}.wav" for x in SLIDES]]}
    outcomes=[]
    for n in SLIDES:
        source_text=prove["script"][n]
        raw_sents,_=tokenize_reference_sentences(source_text)
        words_in_pcm=recognized_words(tts/f"corrected_original_slide{n}.wav",model)
        timings=match_actual_sentences(
            [x["narration_fragment"] for x in raw_sents],words_in_pcm)
        encoded=encode_one(slide=n,corrected=corrected,tts=tts,
                           focus=figure_regions[n],sentences=timings,out=out)
        qa=independent_encoded_frames(slide=n,out=out)
        outcomes.append({"slide":n,"duration":encoded["actual_wav_duration_s"],
                         "math_visual_events":len(encoded[
                             "source_grounded_visual_event_targets"]),
                         "independent_pixel_samples":len(qa["verified_samples"])})
    require(all(_sha(Path(p))==h for p,h in old.items()),
            "Protected original source/WAV or genuine new provider audio mutated")
    summary={"status":"TWO_REAL_SOURCE_CORRECTED_TIMED_MP4S_PASS_QA_NOT_SECTION_RELEASE",
             "original_textbook_sha256":_sha(original/"source.pdf"),
             "corrected_pdf_sha256":_sha(corrected/"slides.pdf"),
             "repaired_voice_source_sha256":_sha(corrected/"script.txt"),
             "slide_results":outcomes,
             "whole_17_slide_video_accepted":False,
             "student_publication_authorized":False}
    with (out/"TWO_REAL_CORRECTED_SYNC_QA_SUMMARY.json").open(
        "x",encoding="utf8") as f:
        json.dump(summary,f,indent=2)
        f.write("\n")
    print(json.dumps(summary))
if __name__=="__main__":
    main()
