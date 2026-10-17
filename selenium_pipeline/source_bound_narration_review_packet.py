"""Recover a source-bound, HUMAN-listening review packet from historic TTS QA.

Only reads historic QA/transcription evidence and verified real WAVs. It does
NOT invoke an ASR, cloud provider, TTS engine, scholarly judge or publisher.
All approvals are explicitly FALSE until an independent reviewer signs off.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import shutil

from .recover_frozen_highlight_review import preflight, need, file_sha, json_file


def _csv_guard(value: object) -> str:
    s = "" if value is None else str(value)
    # Quoting a CSV field does not disable spreadsheet formula execution.
    return "'" + s if s.lstrip().startswith(("=", "+", "-", "@")) else s


def _read_exact_offline(folder: Path, names: set[str]) -> dict:
    need(folder.is_dir() and not folder.is_symlink(),
         "Missing original offline recognition evidence directory")
    files = list(folder.glob("*.wav.asr.json"))
    need({p.name[:-9] for p in files} == names,
         "Offline recognition receipt coverage differs from source WAVs")
    result={}
    for path in files:
        data=json_file(path)
        name=path.name[:-9]
        need(data.get("wav") == name
             and data.get("status") in ("machine_asr_consistent_not_certified",
                                       "speech_review_required")
             and data.get("audible_word_fidelity_certified") is False
             and data.get("academic_approval") is False,
             "Offline screening contains unbound or falsely approved claims")
        result[name]=data
    return result


def make_review_packet(*, source: Path, slides: Path, authored: Path,
                       frozen: Path, synthesis_receipt: Path,
                       refined_screen: Path, offline_receipts: Path,
                       destination: Path) -> dict:
    """Create an isolated static HTML+CSV+real PCM packet, refuse old outputs."""
    originals=[Path(x) for x in (
        source,slides,authored,frozen,synthesis_receipt,refined_screen,
        offline_receipts)]
    need(not any(p.is_symlink() for p in originals),
         "Symlinked review evidence is forbidden")
    dest=Path(destination).absolute()
    need(not dest.exists() and not dest.is_symlink()
         and dest.parent.is_dir() and not dest.parent.is_symlink(),
         "Output must be a fresh isolated folder")
    resolved=dest.resolve(strict=False)
    for path in originals:
        real=path.resolve(strict=True)
        boundary=real if real.is_dir() else real.parent
        need(not (resolved==boundary or resolved.is_relative_to(boundary)
                  or boundary.is_relative_to(resolved)),
             "Never place a reviewer packet inside or above original source files")
    state=preflight(source=source,slides=slides,authored=authored,
                    frozen=frozen,synthesis_receipt=synthesis_receipt)
    expected=json_file(Path(authored))
    prior=json_file(Path(refined_screen))
    need(prior.get("status")=="QUALITY_SCREEN_REVIEW_ONLY"
         and prior.get("total_clips")==state["audio_elements"]
         and prior.get("human_listening_complete") is False
         and prior.get("academic_approved") is False
         and prior.get("production_approved") is False,
         "Earlier Gemini speech screening is not a valid unapproved 48-clip receipt")
    clips=prior.get("clips")
    need(isinstance(clips,list) and len(clips)==state["audio_elements"],
         "The historical Gemini screening must cover every narrated element")
    clips_by={}
    for row in clips:
        name=row.get("wav") if isinstance(row,dict) else None
        need(isinstance(name,str) and name not in clips_by,
             "Repeated or missing Gemini screening WAV record")
        clips_by[name]=row
    names={name for name,_,_ in state["bindings"]}
    need(set(clips_by)==names,"Gemini speech screening is not source-bound")
    offline=_read_exact_offline(Path(offline_receipts),names)
    bound={name:(path,checksum) for name,path,checksum in state["bindings"]}
    rows=[]
    for part in expected["parts"]:
        for slide in part["slides"]:
            for element in slide["elements"]:
                name=element["wav"]
                recorded=clips_by[name]
                other=offline[name]
                source_text_hash=hashlib.sha256(
                    element["spoken_text"].encode("utf-8")).hexdigest()
                need(recorded.get("wav_sha256")==bound[name][1]
                     and other.get("wav_sha256")==bound[name][1]
                     and recorded.get("reference_sha256")==source_text_hash
                     and other.get("reference_sha256")==source_text_hash
                     and recorded.get("human_listening_approved") is False,
                     f"Speech-screen version mismatch for {name}")
                gem_status=recorded["asr_status"]
                offline_status=other["status"]
                need(gem_status in ("machine_transcript_consistent",
                                    "transcript_mismatch",
                                    "pending_independent_asr"),
                     "Unexpected retrospective Gemini QA category")
                priority=(
                    "P1_CONFLICT_OR_SPEECH_MISMATCH"
                    if gem_status=="transcript_mismatch" or
                       offline_status=="speech_review_required"
                    else "P2_MISSING_GEMINI_TRANSCRIPT"
                    if gem_status=="pending_independent_asr"
                    else "P3_MACHINE_CONSISTENT_HUMAN_UNREVIEWED")
                rows.append({
                    "part":part["part_id"],
                    "slide":slide["slide"],
                    "source_page":slide.get("source_page"),
                    "wav":name,
                    "priority":priority,
                    "spoken_text_expected":element["spoken_text"],
                    "gemini_screen_status":gem_status,
                    "gemini_machine_transcript":recorded.get("transcript") or "",
                    "gemini_word_error_rate":recorded.get("word_error_rate"),
                    "gemini_review_flags":"; ".join(recorded.get("review_flags") or []),
                    "offline_screen_status":offline_status,
                    "offline_machine_transcript":other.get("transcript") or "",
                    "offline_word_error_rate":(
                        other.get("metrics") or {}).get("wer"),
                    "original_wav_sha256":bound[name][1],
                    "reference_text_sha256":source_text_hash,
                    "human_listened":"NO",
                    "exact_words_verified":"NO",
                    "mathematics_pronunciation_verified":"NO",
                    "source_figure_semantics_verified":"NO",
                    "lecturer_approved":"NO",
                    "reviewer_comment":"",
                })
    need(len(rows)==len(names),"Not all recorded narrated elements were reviewed")
    rows.sort(key=lambda row:(row["priority"],int(row["slide"]),row["wav"]))
    # All sources and cross-receipt SHA checks complete BEFORE output creation.
    dest.mkdir()
    audio=dest/"audio"
    audio.mkdir()
    for name, original, digest in state["bindings"]:
        copied=audio/name
        with original.open("rb") as inp,copied.open("xb") as out:
            shutil.copyfileobj(inp,out)
        need(file_sha(copied)==digest,f"Copied speech WAV {name} corrupted")
    titles=[("Review priority", "priority"),("Clip", "wav"),
            ("Slide", "slide"),("Reference narration", "spoken_text_expected"),
            ("Earlier Gemini transcript", "gemini_machine_transcript"),
            ("Earlier offline transcript", "offline_machine_transcript"),
            ("Machine flags", "gemini_review_flags")]
    parts=[
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<title>Thomas calculus source-bound narration: listening review</title>",
        "<style>body{font:16px system-ui,sans-serif;max-width:1050px;margin:28px auto;"
        "padding:0 18px;line-height:1.5;color:#182235}article{padding:18px 0;"
        "border-top:1px solid #bec7d4}h1,h2{margin-bottom:.4em}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;"
        "padding:10px}audio{width:100%}.p1{border-left:5px solid #bb3c3c;"
        "padding-left:14px}.p2{border-left:5px solid #b38c40;padding-left:14px}"
        ".p3{padding-left:14px}small{color:#516070}</style></head><body>",
        "<h1>Thomas 8.4: preserved narration review</h1>",
        "<p><strong>REVIEW ONLY — no human, academic or publication approval.</strong>"
        " Every clip is the exact original WAV bound to the lecture's source,"
        " narration text and synthesis receipt. Machine transcripts are fallible;"
        " their agreement is NOT listening certification.</p>",
        "<p>Start with six P1 discrepancies, then 29 P2 missing Gemini transcripts,"
        " and finally 13 P3 machine-consistent clips. ALL 48 require human listening."
        " Mark decisions in the provided CSV; no browser selection grants approval.</p>"
    ]
    for row in rows:
        style="p1" if row["priority"].startswith("P1") else (
            "p2" if row["priority"].startswith("P2") else "p3")
        parts.append(
            f"<article class='{style}'><h2>{html.escape(row['wav'])}"
            f" — slide {row['slide']}</h2><p><strong>"
            f"{html.escape(row['priority'])}</strong></p>"
            f"<audio controls preload='none' src='audio/{html.escape(row['wav'])}'></audio>")
        for title,key in titles[3:]:
            if row[key]:
                parts.append(
                    f"<p><small>{html.escape(title)}</small></p>"
                    f"<pre>{html.escape(str(row[key]))}</pre>")
        parts.append(
            f"<p><small>Gemini: {html.escape(row['gemini_screen_status'])}; "
            f"offline: {html.escape(row['offline_screen_status'])}</small></p>"
            "<p><strong>Human verification pending:</strong> spoken words,"
            " mathematical pronunciation and figure semantics.</p></article>")
    parts.append("</body></html>")
    with (dest/"index.html").open("x",encoding="utf-8") as out:
        out.write("\n".join(parts))
    with (dest/"lecturer_listening_worklist.csv").open(
            "x",newline="",encoding="utf-8-sig") as file:
        out=csv.DictWriter(file,fieldnames=list(rows[0]))
        out.writeheader()
        for row in rows:
            out.writerow({k:_csv_guard(v) for k,v in row.items()})
    counts={k:sum(x["priority"].startswith(k) for x in rows)
            for k in ("P1","P2","P3")}
    report={
        "schema_version":1,
        "status":"SOURCE_BOUND_HUMAN_LISTENING_QUEUE_UNAPPROVED",
        "source_sha256":state["source_sha256"],
        "slides_sha256":state["slides_sha256"],
        "authored_plan_sha256":state["plan_sha256"],
        "clip_count":len(rows),
        "prioritized_six_clips":[r["wav"] for r in rows if r["priority"].startswith("P1")],
        "priorities":counts,
        "all_gemini_qa_hashes_match_original_audio_and_script":True,
        "all_offline_qa_hashes_match_original_audio_and_script":True,
        "fresh_asr_or_paid_tts_called":False,
        "human_listening_complete":False,
        "mathematical_quality_approved":False,
        "figure_semantics_approved":False,
        "production_approved":False,
        "student_published":False,
        "reviewed_wav_sha256":[{"wav":r["wav"],"sha256":r["original_wav_sha256"]}
                               for r in rows],
    }
    with (dest/"review_packet_manifest.json").open("x",encoding="utf-8") as file:
        json.dump(report,file,indent=2,ensure_ascii=False)
        file.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ("source","slides","authored","frozen","synthesis-receipt",
                "refined-screen","offline-receipts","destination"):
        parser.add_argument("--"+arg,type=Path,required=True)
    opts=parser.parse_args(argv)
    print(json.dumps(make_review_packet(
        source=opts.source,slides=opts.slides,authored=opts.authored,
        frozen=opts.frozen,synthesis_receipt=opts.synthesis_receipt,
        refined_screen=opts.refined_screen,
        offline_receipts=opts.offline_receipts,
        destination=opts.destination),indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
