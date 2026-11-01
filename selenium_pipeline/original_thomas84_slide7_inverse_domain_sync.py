"""Render original source-grounded Thomas §8.4 slide7 three inverse branches.

Original publisher page2 contains arcsine inclusive endpoints, two
principal arcsecant cases and x/a>=1 positive branch. The slide PDF,
original authored mathematics, complete source WAV SHA and independent
real Vosk spoken time intervals must all agree before the clip is encoded.
No optical mathematical recognition, guessed timing or student release.
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
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border
from .original_thomas84_multiline_math_witness import EXPECTED_SOURCE_SHA

ORIGINAL_SLIDE_SHA="a25f48be4ad532bf21663dc55cdf4caac99c4b1d1e2fb235d439b0bd269dc03d"
KINDS=("inclusive_arcsine","two_arcsecant_branches","nonnegative_tangent_radical")
# Bounded actual PDF region: first complete arcsine line; both principal
# secant branch CASES; conclusion with principal square root.
RECTS={
    "inclusive_arcsine":[32.727,82.34,349.38,103.55],
    "two_arcsecant_branches":[140.0,129.0,252.0,164.1],
    "nonnegative_tangent_radical":[32.727,173.92,348.36,198.52],
}
LATEX_WITNESSES=(
    r"\item For $x = a \sin \theta$, reversibility requires $\theta = \sin^{-1}\left(\frac{x}{a}\right)$ with $-\frac{\pi}{2} \le \theta \le \frac{\pi}{2}$.",
    r"\item For $x = a \sec \theta$, reversibility requires $\theta = \sec^{-1}\left(\frac{x}{a}\right)$ with restrictions:",
    r"\begin{cases} 0 \le \theta < \frac{\pi}{2} & \text{if } \frac{x}{a} \ge 1, \\ \frac{\pi}{2} < \theta \le \pi & \text{if } \frac{x}{a} \le -1. \end{cases}",
    r"\item Restricting $x/a \ge 1$ for the secant substitution places $\theta$ in $[0, \pi/2)$, making $\tan \theta \ge 0$ and $\sqrt{x^{2}-a^2} = a \tan \theta$ free of absolute value bars.",
)
SPOKEN_EVIDENCE=(
    ("sine substitution","arcsine","inclusively","negative pi over two"),
    ("secant substitution","arcsecant","greater than or equal to one",
     "less than or equal to negative one"),
    ("greater than or equal to one","tangent of theta",
     "without absolute value bars"),
)
STATUS="ORIGINAL_SLIDE7_BOOK_ARCSINE_ARCSECANT_DOMAIN_TIMED_CLIP_PENDING_PIXELS"

def _compact(text:str)->str:
    return re.sub(r"\s+","",text)

def prove_publisher_math(book:str,tex:str,visible:str)->dict:
    # Exact textbook identity and original authored math, not invented
    # from a similarly titled chapter / unrelated PDF.
    begin=book.find("As we know from Section 1.6")
    end=book.find("FIGURE 8.3",begin)
    require(0<=begin<end,"Publisher inverse-branch exposition missing")
    passage=book[begin:end]
    for signal in ("x = a sin u","u = sin-1","x = a sec u",
                   "u = sec-1","0 \u2026 u 6 p","p\n2 6 u \u2026 p",
                   "free of absolute values"):
        require(signal in passage,
                f"Original publisher inverse branch evidence missing: {signal}")
    authored=_compact(tex)
    for signal in LATEX_WITNESSES:
        require(_compact(signal) in authored,
                "Exact authored original source math inequality/sign drifted")
    # Distinguish the three actual slide display blocks with original
    # rendered formula symbols, not the unrelated full-source prose.
    for signal in ("sin−1","sec−1","≤θ","≥1","≤−1",
                   "√","a tan θ"):
        require(_compact(signal) in _compact(visible),
                f"Original rendered PDF inverse function/math missing: {signal}")
    # These sample points corroborate the branch convention, not a universal
    # symbolic theorem or authorization for unreviewed figure panels.
    for angle in (0.0,.4,.9,1.3):
        if angle==0:
            xratio=1.
        else:
            xratio=1/math.cos(angle)
        require(xratio>=1 and math.tan(angle)>=0
                and abs(math.sqrt(xratio*xratio-1)-math.tan(angle))<1e-9,
                "Positive-branch secant radical identity fails")
    for angle in (2.,2.5,math.pi):
        xratio=1/math.cos(angle)
        require(xratio<=-1 and math.tan(angle)<=0,
                "Negative-branch inverse secant label scientifically wrong")
    require(abs(math.asin(1)-math.pi/2)<1e-12
            and abs(math.asin(-1)+math.pi/2)<1e-12,
            "Inclusive principal inverse sine endpoints invalid")
    return {"publisher_inverse_branches_page":2,
            "original_arcsine_endpoints_inclusive":True,
            "original_arcsecant_positive_branch_halfopen":True,
            "original_arcsecant_negative_branch_halfopen":True,
            "original_positive_tangent_abs_removed_valid":True,
            "numerical_boundary_and_branch_samples_pass":True,
            "all_unrelated_book_math_accepted":False}

def _duration(mp4:Path)->float:
    r=subprocess.run([ffmpeg_executable(),"-hide_banner","-i",str(mp4)],
                     capture_output=True,text=True,timeout=30).stderr
    m=re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)",r)
    require(m and "Video: h264" in r and "Audio: aac" in r,
            "Original source inverse domains MP4 missing real AV streams")
    return int(m[1])*3600+int(m[2])*60+float(m[3])

def create(*,original:Path,corrected:Path,word_receipt:Path,out:Path)->dict:
    original,corrected,out=(Path(v).absolute()
                            for v in (original,corrected,out))
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and not out.is_relative_to(corrected),
            "Separate clean nonpublication output required")
    book=original/"source.pdf"
    deck=original/"slides.pdf"
    authored=original/"slides.tex"
    script=original/"script.txt"
    wav=original/"slide7.wav"
    revised=corrected/"slides.pdf"
    inputs=[book,deck,authored,script,wav,revised]
    require(all(p.is_file() and not p.is_symlink() for p in inputs),
            "Original textbook/voice or corrected source not present")
    checksums=[_sha(p) for p in inputs]
    require(checksums[0]==EXPECTED_SOURCE_SHA
            and checksums[1]==ORIGINAL_SLIDE_SHA,
            "Unexpected textbook/lecture source version: refuse inference")
    with pymupdf.open(book) as src,pymupdf.open(deck) as original_pdf,pymupdf.open(revised) as fixed:
        require(len(original_pdf)==len(fixed)==17
                and original_pdf[6].get_text()==fixed[6].get_text()
                and original_pdf[6].get_pixmap(alpha=False).samples==
                    fixed[6].get_pixmap(alpha=False).samples,
                "Corrected cumulative academic source changed original slide7")
        publisher=src[1].get_text()
        visible=original_pdf[6].get_text()
        page=original_pdf[6]
        for rect in RECTS.values():
            box=pymupdf.Rect(rect)
            require(not box.is_infinite and box.is_valid
                    and all(math.isfinite(v) for v in rect)
                    and page.rect.contains(box),
                    "Physical original slide7 target outside actual PDF")
            require(len(page.get_text(clip=box).strip())>=4,
                    "Original target mathematical region is physically blank")
    mathematical=prove_publisher_math(
        publisher,authored.read_text(encoding="utf8"),visible)
    real=json.loads(Path(word_receipt).read_text(encoding="utf8"))
    section=next(s for s in real["sections"] if s["section"]=="8.4")
    item=section["slides"][6]
    require(item["slide"]==7 and item["wav_sha256"]==checksums[4],
            "Recorded original audio timing references wrong WAV")
    sentences,_=tokenize_reference_sentences(
        dict(blocks(script.read_text(encoding="utf-8-sig")))[7])
    candidates=item["sentence_timing_candidates"]
    require(len(sentences)==len(candidates)==3,
            "Original source inverse branch narration changed")
    events={}
    for index,kind in enumerate(KINDS):
        rec=candidates[index]
        spoken=sentences[index]
        words=spoken["narration_fragment"].casefold()
        require(all(term in words for term in SPOKEN_EVIDENCE[index])
                and rec["narration_fragment_sha256"]==
                    spoken["narration_fragment_sha256"]
                and rec["actual_ASR_word_anchor_fraction"]>=.75
                and rec["word_timing_hypothesis_available"] is True,
                "Unverified source/mathematical speech correspondence")
        begin,end=rec["first_matched_real_audio_second"],rec[
            "last_matched_real_audio_second"]
        require(type(begin) in (float,int) and type(end) in (float,int)
                and math.isfinite(begin) and math.isfinite(end)
                and 0<=begin<end<600,"Missing trustworthy original PCM times")
        events[kind]={"rect_pt":RECTS[kind],
                      "narration_fragment_sha256":rec["narration_fragment_sha256"],
                      "real_source_word_anchor_fraction":rec[
                          "actual_ASR_word_anchor_fraction"],
                      "real_audio_start_s":float(begin),
                      "real_audio_end_s":float(end)}
    require(all(events[a]["real_audio_end_s"]<
                events[b]["real_audio_start_s"]
                for a,b in zip(KINDS,KINDS[1:])),
            "Inverse branches spoken in wrong chronological order")
    with wave.open(str(wav),"rb") as pcm:
        dur=pcm.getnframes()/pcm.getframerate()
        require(pcm.getnchannels()==1 and pcm.getsampwidth()==2
                and pcm.getcomptype()=="NONE"
                and 0<events[KINDS[-1]]["real_audio_end_s"]<dur<600,
                "Original PCM audio format/time invalid")
    image=out/"original_slide7_source.png"
    clip=out/"thomas84_slide7_inverse_domain_sync_qa.mp4"
    jsonfile=out/"thomas84_slide7_inverse_domain_provenance.json"
    require(all(not v.exists() for v in (image,clip,jsonfile)),
            "Do not overwrite genuine original source QA")
    with pymupdf.open(revised) as fixed:
        fixed[6].get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False).save(str(image))
    vf=[]
    for event in events.values():
        x0,y0,x1,y1=event["rect_pt"]
        a,b=event["real_audio_start_s"],event["real_audio_end_s"]
        vf.append(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                  f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                  f"color=yellow@0.95:t=4:enable='between(t,{a:.4f},{b:.4f})'")
    p=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel","error",
        "-loop","1","-framerate","10","-i",str(image),"-i",str(wav),
        "-vf",",".join(vf)+",scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v","libx264","-preset","veryfast","-crf","19",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
        "-t",f"{dur:.6f}","-shortest","-movflags","+faststart",str(clip)],
        capture_output=True,text=True,timeout=150)
    require(p.returncode==0 and clip.is_file() and clip.stat().st_size>10000,
            "Source-bound inverse branch H264 encode failed "+p.stderr[-850:])
    encoded=_duration(clip)
    require(0<encoded<600 and abs(encoded-dur)<.15,
            "Encoded source WAV vs MP4 length mismatched")
    require([_sha(f) for f in inputs]==checksums,
            "Original source book/slide math/audio changed")
    result={"status":STATUS,
        "original_book_pdf_sha256":checksums[0],
        "original_deck_sha256":checksums[1],
        "original_latex_sha256":checksums[2],
        "original_script_sha256":checksums[3],
        "original_slide7_wav_sha256":checksums[4],
        "source_corrected_deck_sha256":checksums[5],
        "mathematical_publisher_domain_evidence":mathematical,
        "real_original_inverse_branch_events":events,
        "original_pcm_duration_s":round(dur,4),
        "actual_encoded_mp4_duration_s":round(encoded,4),
        "encoded_mp4_sha256":_sha(clip),
        "complete_fig83_axis_labels_verified":False,
        "other_unmapped_slides_approved":False,
        "student_publication_authorized":False}
    with jsonfile.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False);f.write("\n")
    return result

def verify(*,original:Path,out:Path)->dict:
    original,out=Path(original).absolute(),Path(out).absolute()
    witness=json.loads((out/"thomas84_slide7_inverse_domain_provenance.json").read_text(encoding="utf8"))
    clip=out/"thomas84_slide7_inverse_domain_sync_qa.mp4"
    require(witness["status"]==STATUS
            and _sha(clip)==witness["encoded_mp4_sha256"]
            and _sha(original/"slide7.wav")==witness["original_slide7_wav_sha256"],
            "Original source audio/MP4 evidence not unchanged")
    cases=(("intro_before_speech",.05,None),("arcsine",6.5,KINDS[0]),
           ("arcsecant",24.,KINDS[1]),("positive",44.,KINDS[2]))
    observations=[]
    for label,t,focus in cases:
        png=out/f"original_slide7_independent_{label}.png"
        require(not png.exists(),"Do not replace independent pixel sample")
        result=subprocess.run([ffmpeg_executable(),"-hide_banner","-loglevel","error",
            "-i",str(clip),"-ss",str(t),"-frames:v","1",str(png)],
            capture_output=True,text=True,timeout=45)
        require(result.returncode==0 and png.is_file(),
                "Independently decoded original source frame missing")
        scores={k:count_source_equation_side_border(png,e["rect_pt"])
                for k,e in witness["real_original_inverse_branch_events"].items()}
        require(all((count>=6)==(name==focus) for name,count in scores.items()),
                f"Inverse domain semantic visual focus wrong at {t}s: {scores}")
        if focus is not None:
            e=witness["real_original_inverse_branch_events"][focus]
            require(e["real_audio_start_s"]<t<e["real_audio_end_s"],
                    "Selected publisher inverse branch not spoken at sample")
        observations.append({"sample_time_s":t,"expected":focus,
                             "source_math_border_probes":scores,
                             "decoded_frame_sha256":_sha(png)})
    result={"status":"ORIGINAL_SLIDE7_SOURCE_INVERSE_DOMAIN_H264_PIXEL_QA_PASS",
            "encoded_mp4_sha256":_sha(clip),
            "original_slide7_wav_sha256":witness["original_slide7_wav_sha256"],
            "actual_video_sample_count":len(observations),
            "math_inverse_branch_areas_verified":list(KINDS),
            "full_lecture_accepted":False,
            "student_publication_authorized":False,
            "observed_real_encoded_video_samples":observations}
    with (out/"thomas84_slide7_independent_pixel_qa.json").open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2);f.write("\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("original","corrected","word-receipt","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args(argv)
    create(original=a.original,corrected=a.corrected,
           word_receipt=a.word_receipt,out=a.out)
    r=verify(original=a.original,out=a.out)
    print(json.dumps({"status":r["status"],
                      "source_math_regions":len(r["math_inverse_branch_areas_verified"]),
                      "real_video_frame_samples":r["actual_video_sample_count"]}))
if __name__=="__main__":
    main()
