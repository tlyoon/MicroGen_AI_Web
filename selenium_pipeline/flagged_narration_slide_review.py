"""Review-only source-bound Math/WAV/slide snapshots for flagged TTS clips.

Uses EXISTING historic recognition records only. No new ASR, TTS, network
calls, academic signoff or changes to any original lecture or review file.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import tempfile

try:
    import pymupdf
except ImportError:  # older installed PyMuPDF builds
    import fitz as pymupdf

from .recover_frozen_highlight_review import (
    PreservedReviewRecoveryError, file_sha, json_file, need, preflight,
)
from .source_bound_narration_review_packet import _read_exact_offline


def _assert_destination(dest: Path, originals: tuple[Path, ...]) -> None:
    need(not dest.exists() and not dest.is_symlink()
         and dest.parent.is_dir() and not dest.parent.is_symlink(),
         "A new isolated review output folder is required")
    final = dest.resolve(strict=False)
    for item in originals:
        need(not item.is_symlink(), "Original source/review symlink forbidden")
        real = item.resolve(strict=True)
        boundary = real if real.is_dir() else real.parent
        need(not final.is_relative_to(boundary)
             and not boundary.is_relative_to(final),
             "Refuse writing flagged packet inside or above original evidence")


def build(*, source: Path, slides: Path, authored: Path, frozen: Path,
          synthesis_receipt: Path, refined_screen: Path,
          offline_receipts: Path, destination: Path) -> dict:
    """Create page images + original WAVs and both transcripts; all unapproved.

    Fail-closed before output creation on any historic-record or source mismatch.
    """
    originals = tuple(Path(p) for p in
        (source,slides,authored,frozen,synthesis_receipt,
         refined_screen,offline_receipts))
    dest = Path(destination).absolute()
    _assert_destination(dest,originals)
    bound = preflight(source=source, slides=slides, authored=authored,
                      frozen=frozen, synthesis_receipt=synthesis_receipt)
    plan = json_file(Path(authored))
    gem = json_file(Path(refined_screen))
    need(gem.get("status") == "QUALITY_SCREEN_REVIEW_ONLY"
         and gem.get("total_clips") == bound["audio_elements"]
         and gem.get("human_listening_complete") is False
         and gem.get("academic_approved") is False
         and gem.get("production_approved") is False,
         "Gemini historic screen is not a valid unapproved source-bound QA record")
    clips = gem.get("clips")
    need(isinstance(clips,list) and len(clips)==bound["audio_elements"],
         "Gemini QA does not cover the original recorded audio")
    gby = {}
    for clip in clips:
        name=clip.get("wav") if isinstance(clip,dict) else None
        need(isinstance(name,str) and name not in gby,
             "Gemini historical WAV identity missing/duplicated")
        gby[name]=clip
    per_wav={name:(path,sha) for name,path,sha in bound["bindings"]}
    names=set(per_wav)
    need(set(gby)==names,"Gemini QA includes missing or extraneous clips")
    offline=_read_exact_offline(Path(offline_receipts),names)
    source_utterances={}
    for part in plan["parts"]:
        for slide in part["slides"]:
            for el in slide["elements"]:
                name=el["wav"]
                need(name not in source_utterances,
                     "Duplicate source-bound narration WAV")
                source_utterances[name] = (slide["slide"],el["spoken_text"])
    need(set(source_utterances)==names,"Narration plan lacks source WAV coverage")
    entries=[]
    for name,record in gby.items():
        history=offline[name]
        slide_number,original_spoken=source_utterances[name]
        original_text_sha=hashlib.sha256(original_spoken.encode("utf8")).hexdigest()
        wavpath,wavsha=per_wav[name]
        need(record.get("wav_sha256")==history.get("wav_sha256")==wavsha
             and record.get("reference_sha256")==
                 history.get("reference_sha256")==original_text_sha
             and record.get("human_listening_approved") is False,
             "Gemini/offline speech evidence cannot be bound to current lecture")
        gs=record.get("asr_status")
        hs=history.get("status")
        need(gs in ("machine_transcript_consistent","transcript_mismatch",
                    "pending_independent_asr")
             and hs in ("machine_asr_consistent_not_certified",
                        "speech_review_required"),
             "Unexpected historic speech QA status")
        flagged=(gs=="transcript_mismatch" or hs=="speech_review_required")
        if not flagged:
            continue
        entries.append({
            "wav":name,
            "slide":slide_number,
            "source_expected_spoken":original_spoken,
            "original_wav_sha256":wavsha,
            "original_text_sha256":original_text_sha,
            "gemini_status":gs,
            "gemini_transcript":record.get("transcript") or "",
            "gemini_word_error_rate":record.get("word_error_rate"),
            "gemini_flags":record.get("review_flags") or [],
            "offline_status":hs,
            "offline_transcript":history.get("transcript") or "",
            "offline_word_error_rate":(history.get("metrics") or {}).get("wer"),
            "historic_statuses_not_human_signoff":True,
            "human_listening_approved":False,
            "spoken_mathematics_correct":False,
            "figure_semantics_approved":False,
            "student_published":False,
            "_wavpath":wavpath,
        })
    need(bool(entries),"No flagged source-bound clips — no reviewer packet needed")
    entries.sort(key=lambda e:(e["slide"],e["wav"]))
    # Verify the PDF really is current and contains all reference slides,
    # before creating any output. Extracted glyph text is non-authoritative
    # for radicals, visual figure panels or fraction formatting.
    with pymupdf.open(str(slides)) as pdf:
        need(len(pdf)==len({s["slide"] for p in plan["parts"]
                            for s in p["slides"]}),
             "The bound slides PDF page count changed")
        for e in entries:
            index=e["slide"]-1
            need(index in range(len(pdf)),"Narrated slide PDF page missing")
            e["extracted_slide_text_non_authoritative"]=pdf[index].get_text(
                sort=True)[:12000]
    # Only the output directory is new. Stage it in the same volume and
    # rename at the end, so a partial render never becomes a review packet.
    scratch = Path(tempfile.mkdtemp(
        prefix="."+dest.name+".pending.",dir=dest.parent))
    try:
        audio=scratch/"audio"
        slide_png=scratch/"slides"
        audio.mkdir()
        slide_png.mkdir()
        with pymupdf.open(str(slides)) as pdf:
            for slide_number in sorted({e["slide"] for e in entries}):
                pdf[slide_number-1].get_pixmap(
                    matrix=pymupdf.Matrix(1.7,1.7),alpha=False).save(
                        str(slide_png/f"slide_{slide_number:02d}.png"))
        for e in entries:
            name=e["wav"]
            dest_wav=audio/name
            with e["_wavpath"].open("rb") as src, dest_wav.open("xb") as out:
                shutil.copyfileobj(src,out)
            need(file_sha(dest_wav)==e["original_wav_sha256"],
                 "A source-bound original review WAV changed during copying")
            e.pop("_wavpath")
        out_html=[
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
            "<title>Flagged calculus narration: math and speech review</title>",
            "<style>body{font:16px system-ui,sans-serif;max-width:1000px;"
            "margin:25px auto;padding:0 15px;color:#17212e}article{"
            "border-top:2px solid #d6d9df;padding:18px 0}img{display:block;"
            "width:100%;height:auto;border:1px solid #ddd}pre{white-space:"
            "pre-wrap;overflow-wrap:anywhere;background:#f1f3f6;padding:12px}"
            "audio{width:100%}small{color:#58616e}</style></head><body>",
            "<h1>Flagged original calculus TTS — source slide review</h1>",
            "<p><strong>REVIEW ONLY.</strong> Machine transcript notation may "
            "convert spoken numbers and signs into glyphs, but it cannot "
            "certify the audio. Every expression, sign, denominator, square root, "
            "inverse-trig branch, figure panel and spoken word needs human "
            "listening and visible-source confirmation.</p>"
        ]
        for e in entries:
            def para(title,text):
                return "<p><small>"+html.escape(title)+"</small></p><pre>"+html.escape(
                    str(text))+"</pre>"
            out_html.extend([
                f"<article><h2>{html.escape(e['wav'])} — slide {e['slide']}</h2>",
                f"<audio controls preload='none' src='audio/{html.escape(e['wav'])}'></audio>",
                f"<img src='slides/slide_{e['slide']:02d}.png' "
                f"alt='Actual source-bound lecture slide {e['slide']}'>",
                para("Exact expected original narration",e["source_expected_spoken"]),
                para("Existing Gemini recognition (unapproved)",e["gemini_transcript"]),
                para("Existing offline recognition (unapproved)",e["offline_transcript"]),
                para("Prior machine review flags",json.dumps(e["gemini_flags"])),
                "<p><strong>Reviewer must verify</strong>: Listen to this "
                "specific WAV, match all numbers/signs/branches and identify "
                "the intended element on the visible slide. Neither transcript "
                "is an academic/voice approval.</p></article>"
            ])
        out_html.append("</body></html>")
        (scratch/"index.html").write_text("\n".join(out_html),encoding="utf8")
        report={
            "schema_version":1,
            "status":"ORIGINAL_SPEECH_AND_SLIDE_MATH_REVIEW_PENDING",
            "source_sha256":bound["source_sha256"],
            "slides_sha256":bound["slides_sha256"],
            "authored_plan_sha256":bound["plan_sha256"],
            "all_original_recorded_wav_count":len(names),
            "flagged_wav_count":len(entries),
            "flagged_clips":entries,
            "all_original_QA_records_source_bound":True,
            "rendered_slide_previews_non_authoritative_for_math":True,
            "no_new_asr_or_paid_tts":True,
            "human_listening_approved":False,
            "academic_approval":False,
            "original_figures_and_subpanels_approved":False,
            "production_approved":False,
            "student_published":False,
        }
        with (scratch/"evidence.json").open("x",encoding="utf8") as f:
            json.dump(report,f,indent=2,ensure_ascii=False)
            f.write("\n")
        need(not dest.exists() and not dest.is_symlink(),
             "Refuse a collision with a previously created reviewer packet")
        scratch.rename(dest)
        return report
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


def main(argv: list[str] | None=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source","slides","authored","frozen","synthesis-receipt",
                 "refined-screen","offline-receipts","destination"):
        parser.add_argument("--"+name,required=True,type=Path)
    opt=parser.parse_args(argv)
    result=build(source=opt.source,slides=opt.slides,
                 authored=opt.authored,frozen=opt.frozen,
                 synthesis_receipt=opt.synthesis_receipt,
                 refined_screen=opt.refined_screen,
                 offline_receipts=opt.offline_receipts,
                 destination=opt.destination)
    print(json.dumps({"status":result["status"],
                      "flagged_wav_count":result["flagged_wav_count"],
                      "flagged_clips":[x["wav"] for x in result["flagged_clips"]],
                      "academic_approval":result["academic_approval"]},
                     indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
