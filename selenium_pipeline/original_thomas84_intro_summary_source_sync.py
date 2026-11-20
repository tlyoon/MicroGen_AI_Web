"""Publisher-grounded, real-WAV synchronized §8.4 introduction/summary elements.

Only independently matched textbook statements and physically rendered source
math/text are highlighted. Title slide is NOT forced into fake word timing:
original slide1 has insufficient genuine Vosk anchors (0.25), and summary
bullet4 (generic algebra preparation) remains unapproved here.

Every encoded clip uses the ACTUAL original PCM plus independent FFmpeg
pixel OFF/ON probes. All source/corrected PDFs/scripts/WAVs are immutable.
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
from .figure_source_identity import require, _sha
from .video_ffmpeg import ffmpeg_executable
from .runner import blocks
from .original_thomas84_offline_word_pdf_timing import tokenize_reference_sentences
from .original_thomas84_slide4_three_equation_sync import count_source_equation_side_border
from .original_thomas84_multiline_math_witness import EXPECTED_SOURCE_SHA

# Each original event is a bounded, visible PDF rectangle. The index is
# ORIGINAL narration sentence, not a guessed number of seconds.
CASES = {
    3: (
        ("three_substitutions", 2, [52.0, 114.0, 104.0, 151.0],
         ("three most common substitutions", "tangent", "sine", "secant"), 12.0),
        ("three_radical_classes", 3, [32.0, 155.0, 316.0, 194.0],
         ("square root of the sum", "square root of the difference",
          "trigonometric integrals"), 23.0),
        ("right_triangle_identity", 4, [32.0, 196.0, 338.0, 225.0],
         ("algebraic identities", "right triangle geometry"), 37.0),
    ),
    16: (
        ("substitution_identity_summary", 1, [32.0, 85.0, 334.0, 112.0],
         ("trigonometric substitutions", "tangent", "sine",
          "secant", "pythagorean"), 8.0),
        ("reversible_angle_domain_summary", 2, [32.0, 115.0, 356.0, 142.0],
         ("angle domains", "inverse trigonometric", "reversible"), 22.0),
        ("reference_triangle_summary", 3, [32.0, 145.0, 353.0, 173.0],
         ("reference right triangles", "algebraic functions"), 31.0),
    ),
}
STATUS = "INTRO_AND_SUMMARY_SIX_SOURCE_MATH_EVENTS_ACTUAL_PCM_PIXEL_QA_PASS"


def _publisher_witness(pages: list[str], tex_frames: list[str]) -> dict:
    require(len(pages) >= 4 and len(tex_frames) == 17,
            "Wrong publisher or original 17-slide lecture")
    intro = pages[0]
    inverse = pages[1]
    require(all(s in intro for s in (
        "The most common substitutions are x = a tan u, x = a sin u, and",
        "x = a sec u",
        "2a2 + x2, 2a2 - x2, and 2x2 - a2",
        "come from the reference right triangles in Figure 8.2")),
        "Not the original textbook's three substitutions/radical classes")
    require(all(s in inverse for s in (
        "any substitution we use in an integration to be reversible",
        "functions in these substitutions have inverses only",
        "for selected values of u (Figure 8.3)")),
        "Publisher's original angle reversibility identity not corroborated")
    # Require the exact authored LaTeX for ALL source-grounded math,
    # including the sign/order of each radicand, not just matching prose.
    introduction = tex_frames[2]
    summary = tex_frames[15]
    exact_math = (
        r"$x = a \tan \theta$",
        r"$x = a \sin \theta$",
        r"$x = a \sec \theta$",
    )
    for expression in exact_math:
        require(expression in introduction and expression in summary,
                "Original authored basic substitution mathematics missing")
    require(all(x in introduction for x in (
        r"$\sqrt{a^{2} + x^{2}}$",
        r"$\sqrt{a^{2} - x^{2}}$",
        r"$\sqrt{x^{2} - a^{2}}$")),
        "Original rendered three radical sign classes were changed")
    require("standard right-triangle geometry" in introduction
            and "reversible" in summary
            and "Reference right triangles" in summary,
            "Publisher's geometric/domain summary no longer present")
    # Independent symbolic verification of the Pythagorean identities
    # underlying the original source chapter's three substitution classes.
    try:
        import sympy as s
    except ImportError:
        require(False, "Independent SymPy required, never assert on absent math engine")
    u = s.symbols("u", real=True)
    identities = (
        s.simplify(1 + s.tan(u)**2 - s.sec(u)**2),
        s.simplify(1 - s.sin(u)**2 - s.cos(u)**2),
        s.simplify(s.sec(u)**2 - 1 - s.tan(u)**2),
    )
    require(all(q == 0 for q in identities),
            "Independent source Pythagorean trig identity invalid")
    return {
        "original_textbook_page_intro": 1,
        "original_textbook_page_reversibility": 2,
        "original_three_substitutions_and_radicals_verified": True,
        "independent_three_trig_identity_residuals": ["0", "0", "0"],
        "source_angle_reversibility_and_reference_triangle_statements": True,
        "algebra_preparation_summary_fourth_bullet_approved": False,
        "title_slide_word_alignment_approved": False,
    }


def _encoded_media_seconds(video: Path) -> float:
    info = subprocess.run(
        [ffmpeg_executable(), "-hide_banner", "-i", str(video)],
        capture_output=True, text=True, timeout=30).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", info)
    require(m is not None and "Video: h264" in info and "Audio: aac" in info,
            "Original source video does not contain H264 and AAC")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def create(*, original: Path, corrected: Path,
           timings: Path, out: Path) -> dict:
    original, corrected, out = (Path(x).absolute()
                                for x in (original, corrected, out))
    require(out.is_dir() and not out.is_symlink()
            and not out.is_relative_to(original)
            and not out.is_relative_to(corrected),
            "Source-separated clean original mathematical QA dir required")
    book, tex, slides, script, fixed = (
        original/"source.pdf", original/"slides.tex", original/"slides.pdf",
        original/"script.txt", corrected/"slides.pdf")
    sources = [book, tex, slides, script, fixed]
    sources += [original/f"slide{n}.wav" for n in CASES]
    require(all(p.is_file() and not p.is_symlink() for p in sources),
            "Missing physical source publisher PDF, original slide or PCM")
    before = {str(p): _sha(p) for p in sources}
    require(_sha(book) == EXPECTED_SOURCE_SHA,
            "Publisher source PDF is not pinned original Thomas §8.4")
    raw = tex.read_text(encoding="utf8")
    frames = re.findall(r"\\begin\{frame\}.*?\\end\{frame\}", raw, re.S)
    with pymupdf.open(book) as publisher:
        proof = _publisher_witness([page.get_text() for page in publisher], frames)
    narratives = dict(blocks(script.read_text(encoding="utf-8-sig")))
    records = json.loads(Path(timings).read_text(encoding="utf8"))
    section = next(s for s in records["sections"] if s["section"] == "8.4")
    outputs = {}
    with pymupdf.open(slides) as original_pdf, pymupdf.open(fixed) as final_pdf:
        require(len(original_pdf) == len(final_pdf) == 17,
                "Changed complete original 17-slide deck")
        for index, targets in CASES.items():
            old, new = original_pdf[index-1], final_pdf[index-1]
            require(old.get_text() == new.get_text()
                    and old.get_pixmap(alpha=False).samples ==
                        new.get_pixmap(alpha=False).samples,
                    f"Changed academically unreviewed original slide {index}")
            wav = original/f"slide{index}.wav"
            row = section["slides"][index-1]
            require(row["slide"] == index and row["wav_sha256"] == _sha(wav),
                    "Wrong original audio time receipt / wav checksum")
            with wave.open(str(wav), "rb") as wf:
                duration = wf.getnframes()/wf.getframerate()
                require(wf.getnchannels() == 1 and wf.getsampwidth() == 2
                        and wf.getcomptype() == "NONE" and duration < 600,
                        "Unsupported nonoriginal PCM format/time")
            sentences, _ = tokenize_reference_sentences(narratives[index])
            times = row["sentence_timing_candidates"]
            require(len(sentences) == len(times) == (4 if index in CASES else 0),
                    "Original section's real source narration sentence count drifted")
            events = []
            for name, sentence_index, rect, terms, on in targets:
                original_sentence = sentences[sentence_index-1]
                real = times[sentence_index-1]
                require(real["narration_fragment_sha256"] ==
                            original_sentence["narration_fragment_sha256"]
                        and real["word_timing_hypothesis_available"] is True
                        and real["actual_ASR_word_anchor_fraction"] >= .74
                        and all(term in original_sentence["narration_fragment"].casefold()
                                for term in terms),
                        f"Source proof and actual word time disconnected: {index}/{name}")
                a,b = real["first_matched_real_audio_second"], real[
                    "last_matched_real_audio_second"]
                require(all(isinstance(q, (int,float)) and math.isfinite(q)
                            for q in (a,b)) and 0 <= a < on < b < duration,
                        "No genuine source spoken interval covering visual probe")
                box = pymupdf.Rect(rect)
                require(box.is_valid and not box.is_infinite
                        and new.rect.contains(box)
                        and len(new.get_text(clip=box).strip()) >= 6,
                        "Original source mathematical visual target blank/invalid")
                events.append({"name": name, "original_sentence_number": sentence_index,
                    "real_audio_start_s": float(a), "real_audio_end_s": float(b),
                    "actual_ASR_anchor_fraction": real["actual_ASR_word_anchor_fraction"],
                    "original_narration_sha256": real["narration_fragment_sha256"],
                    "actual_source_slide_rect_pt": rect,
                    "source_math_or_text_matching_proved": True,
                    "probe_time_s": on})
            require(all(a["real_audio_end_s"] <
                        b["real_audio_start_s"] for a,b in zip(events, events[1:])),
                    "Overlapping or out of order original audio sentence sources")
            base = out/f"thomas84_slide{index}_original_source.png"
            video = out/f"thomas84_slide{index}_three_verified_focus.mp4"
            require(not base.exists() and not video.exists(),
                    "Preserve prior original-source preview artifacts")
            new.get_pixmap(matrix=pymupdf.Matrix(2,2),
                           alpha=False).save(str(base))
            vf = []
            for item in events:
                x0,y0,x1,y1 = item["actual_source_slide_rect_pt"]
                a,b = item["real_audio_start_s"],item["real_audio_end_s"]
                vf.append(f"drawbox=x={int(x0*2)-4}:y={int(y0*2)-1}:"
                    f"w={int((x1-x0)*2)+8}:h={int((y1-y0)*2)+2}:"
                    f"color=yellow@0.95:t=4:"
                    f"enable='between(t,{a:.4f},{b:.4f})'")
            proc = subprocess.run([ffmpeg_executable(),"-hide_banner",
                "-loglevel","error","-loop","1","-framerate","10",
                "-i",str(base),"-i",str(wav),"-vf",
                ",".join(vf)+",scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:v","libx264","-preset","veryfast","-crf","19",
                "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
                "-t",f"{duration:.6f}","-shortest",
                "-movflags","+faststart",str(video)],
                capture_output=True,text=True,timeout=150)
            require(proc.returncode == 0 and video.is_file() and
                    video.stat().st_size > 10000,
                    f"Real publisher-source slide {index} encode failed "+
                    proc.stderr[-600:])
            encoded = _encoded_media_seconds(video)
            require(abs(encoded-duration) < .15 and encoded < 600,
                    "Genuine WAV / video durations changed")
            # Independent encoded-frame sample: sampled DURING each original
            # spoken focus AND before any source sentence begins.
            frames_qa = []
            for name, at, expected in (
                [("pre_first_word",.05,None)] +
                [(item["name"],item["probe_time_s"],item["name"])
                 for item in events]):
                image = out/f"slide{index}_independent_{name}.png"
                require(not image.exists(),"Do not overwrite real pixel QA evidence")
                result = subprocess.run([ffmpeg_executable(),"-hide_banner",
                    "-loglevel","error","-i",str(video),"-ss",str(at),
                    "-frames:v","1",str(image)],
                    capture_output=True,text=True,timeout=40)
                require(result.returncode == 0 and image.is_file(),
                        "Cannot independently decode video pixel proof")
                counts = {item["name"]:
                    count_source_equation_side_border(
                        image,item["actual_source_slide_rect_pt"])
                    for item in events}
                require(all((n>=6)==(name_event==expected)
                            for name_event,n in counts.items()),
                        f"Real independently decoded wrong active slide {index}: {counts}")
                frames_qa.append({
                    "actual_second":at,"expected":expected,
                    "yellow_border_probes":counts,
                    "decoded_frame_sha256":_sha(image),
                })
            outputs[str(index)] = {
                "original_pcm_sha256":_sha(wav),
                "actual_h264_aac_mp4_sha256":_sha(video),
                "original_pcm_duration_s":round(duration,4),
                "encoded_media_duration_s":round(encoded,4),
                "source_verified_element_events":events,
                "independently_decoded_real_pixels":frames_qa,
                "unreviewed_slide_elements_accepted":False,
            }
    require(before == {str(p):_sha(p) for p in sources},
            "Original publisher/source math/PCM changed during QA")
    report = {
        "status":STATUS,"schema_version":1,
        "publisher_source_sha256":_sha(book),
        "original_tex_sha256":_sha(tex),
        "original_slide_pdf_sha256":_sha(slides),
        "corrected_slide_pdf_sha256":_sha(fixed),
        "original_source_justification":proof,
        "original_highlighted_slides":[3,16],
        "verified_events_count":sum(len(v["source_verified_element_events"])
                                    for v in outputs.values()),
        "source_bound_original_video_clips":outputs,
        "intro_title_slide_word_timing_claimed":False,
        "summary_fourth_bullet_source_certified":False,
        "full_section_accepted":False,
        "student_publication_authorized":False,
    }
    with (out/"INTRO_SUMMARY_SOURCE_VIDEO_AND_PIXEL_QA.json").open(
            "x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original","corrected","word-receipt","out"):
        parser.add_argument("--"+name,required=True,type=Path)
    args = parser.parse_args(argv)
    result = create(original=args.original,corrected=args.corrected,
                    timings=args.word_receipt,out=args.out)
    print(json.dumps({"status":result["status"],
        "original_highlighted_slides":result["original_highlighted_slides"],
        "verified_events":result["verified_events_count"]}))


if __name__ == "__main__":
    main()
