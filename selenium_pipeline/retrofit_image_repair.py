"""Audit and rebuild previously published lecture packages after source-verified image fixes.

Image selection/cropping is an LLM/visual-review decision: never invent a mapping.
This command rebuilds verified image/LaTeX patches using unchanged approved narration,
WAVs and QA reports, and publishes only after complete media verification.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from .figure_audit import audit_one, enforce_graphics
from .figure_legibility import audit_wide_figure_legibility
from .slide_narration_sync import record_structural_alignment, verify
from .video_ffmpeg import assemble, ffmpeg_executable, validate_video
from .cleanup import completed_lecture

FRAME = re.compile(r"\\begin\s*\{frame\}.*?\\end\s*\{frame\}", re.S)
FIGURE_MENTION = re.compile(r"\b(?:Figure|Fig\.)\s*(\d+\.\d+[a-z]?)\b", re.I)
PATCH_SUFFIXES = {".tex", ".png", ".jpg", ".jpeg", ".pdf", ".eps"}
FINAL = ("slides.tex", "slides.pdf", "script.txt", "slides.mp4")
MAX_PART_AUDIO_SECONDS = 585  # reserve margin for encoded AAC/video rounding

def digest(file: Path) -> str:
    h = hashlib.sha256()
    with file.open("rb") as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()

def dump(file: Path, record: dict) -> None:
    temporary = file.with_name(file.name + ".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    temporary.replace(file)

def audit(folder: Path) -> dict:
    """Source/image inventory. Potential omission is a REVIEW, never an auto-pass."""
    import fitz
    folder = Path(folder)
    source, tex, pdf = (folder / n for n in ("source.pdf", "slides.tex", "slides.pdf"))
    report = audit_one(folder)
    content = tex.read_text(encoding="utf-8")
    references = report["graphics"]
    with fitz.open(source) as doc:
        source_figures = sorted({m.group(1) for p in doc
                                 for m in FIGURE_MENTION.finditer(p.get_text())})
    with fitz.open(pdf) as doc:
        slide_pages = len(doc)
        rendered_pages = [i + 1 for i, p in enumerate(doc) if p.get_images(full=True)]
    assets = sorted(p.name for p in folder.iterdir()
                    if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
                    and "fig" in p.name.lower())
    listed = {entry.get("filename", "").casefold() for entry in references}
    unused = [p for p in assets if p.casefold() not in listed]
    errors = [entry for entry in references if entry.get("status") != "present"]
    flags = []
    if errors:
        flags.append("missing_or_unsafe_latex_graphics")
    if source_figures and not references:
        flags.append("source_figures_but_no_slide_graphics_review_required")
    # Unused originals can be intentionally retained when cropped panels are used;
    # make this informational rather than automatically claiming a defect.
    notices = (["unused_figure_assets_check_relevance"] if unused else [])
    if references and not rendered_pages:
        flags.append("latex_graphics_absent_from_rendered_pdf")
    return {"subtopic": folder.name, "source_sha256": digest(source),
            "source_figure_mentions": source_figures, "figure_assets": assets,
            "unused_figure_assets": unused, "latex_graphics": references,
            "slides": slide_pages, "rendered_image_pages": rendered_pages,
            "review_flags": flags, "informational_notices": notices,
            "result": "REVIEW_REQUIRED" if flags else "CANDIDATE_FOR_VISUAL_ACCEPTANCE"}

def chapter_audit(root: Path) -> list[dict]:
    root = Path(root)
    chapter = root.name
    if not chapter.isdecimal():
        raise ValueError("Chapter directory must be named with an integer")
    rx = re.compile(rf"^{re.escape(chapter)}\.(\d+)$")
    children = [(int(m.group(1)), child) for child in root.iterdir() if child.is_dir()
                if (m := rx.fullmatch(child.name))]
    return [audit(folder) for _, folder in sorted(children)]

def patch_files(patch: Path) -> list[Path]:
    if not patch.is_dir():
        raise NotADirectoryError(patch)
    contents = list(patch.iterdir())
    if not contents or not (patch / "slides.tex").is_file():
        raise ValueError("Patch must include vetted slides.tex")
    evidence_files = {"source_figure_chain_v1.json",
                      "source_split_figure_chain_v1.json",
                      "figure_repair_provenance.json"}
    for file in contents:
        if (file.is_symlink() or not file.is_file()
                or (file.suffix.lower() not in PATCH_SUFFIXES
                    and file.name not in evidence_files)
                or file.name.lower() in {"source.pdf", "slides.pdf", "script.txt"}):
            raise ValueError("Unsafe or unauthorized patch content: " + file.name)
    return contents

def balanced_groups(durations: list[float],
                    limit: float = MAX_PART_AUDIO_SECONDS) -> list[tuple[int, int]]:
    """Minimize part count, then duration imbalance. Inclusive 1-based slide ranges."""
    if not durations or any(x <= 0 or x >= limit for x in durations):
        raise ValueError("Unpartitionable narration durations")
    n = len(durations)
    total = sum(durations)
    prefix = [0.0]
    for value in durations:
        prefix.append(prefix[-1] + value)
    count = [n + 1] * (n + 1)
    count[n] = 0
    for i in range(n - 1, -1, -1):
        count[i] = min([1 + count[j] for j in range(i + 1, n + 1)
                        if prefix[j] - prefix[i] <= limit] or [n + 1])
    if count[0] > n:
        raise ValueError("No valid part decomposition")
    ideal = total / count[0]
    score = [float("inf")] * (n + 1)
    nxt = [-1] * (n + 1)
    score[n] = 0
    for i in range(n - 1, -1, -1):
        for j in range(i + 1, n + 1):
            duration = prefix[j] - prefix[i]
            if duration > limit:
                break
            if count[i] != count[j] + 1:
                continue
            quality = (duration - ideal) ** 2 + score[j]
            if quality < score[i]:
                score[i], nxt[i] = quality, j
    result = []
    i = 0
    while i < n:
        j = nxt[i]
        if j <= i:
            raise RuntimeError("Invalid split reconstruction")
        result.append((i + 1, j))
        i = j
    return result

def _media_seconds(folder: Path) -> list[float]:
    wavs = sorted((p for p in folder.glob("slide*.wav")
                   if re.fullmatch(r"slide[1-9]\d*\.wav", p.name, re.I)),
                  key=lambda x: int(x.stem[5:]))
    if [p.name for p in wavs] != [f"slide{i}.wav" for i in range(1, len(wavs) + 1)]:
        raise ValueError("Non-contiguous slide WAVs")
    result = []
    for file in wavs:
        with wave.open(str(file), "rb") as stream:
            result.append(stream.getnframes() / stream.getframerate())
    return result

def _source_snapshot(folder: Path) -> dict:
    names = ["source.pdf", "slides.tex", "slides.pdf", "script.txt", "slides.mp4",
             ".microgen_completion.json"]
    names.extend(sorted(p.name for p in folder.glob("slide*.wav")))
    names.extend(sorted(p.name for p in folder.glob("slides_part*.mp4")))
    names.extend(["slides_parts_manifest.json", "slide_narration_sync.json",
                  "tts_fidelity_report.json", "script_risk_report.json"])
    names.extend(sorted(p.name for p in folder.iterdir()
                        if p.is_file() and p.suffix.lower() in
                        {".png", ".jpg", ".jpeg", ".eps"}))
    names.extend(["figures_manifest.json", "source_figure_chain_v1.json",
                  "source_split_figure_chain_v1.json",
                  "figure_repair_provenance.json"])
    return {name: digest(folder / name) if (folder / name).is_file() else None
            for name in sorted(set(names))}

def _validate_unchanged_tts(original: Path, stage: Path, slides: int) -> None:
    if digest(stage / "script.txt") != digest(original / "script.txt"):
        raise ValueError("Narration changed; rerun script/TTS/acoustic stages before video")
    for p in stage.glob("slide*.wav"):
        if digest(p) != digest(original / p.name):
            raise ValueError("Changed WAV requires acoustic reacceptance: " + p.name)
    fidelity = json.loads((stage / "tts_fidelity_report.json").read_text(encoding="utf-8"))
    summary = fidelity.get("summary", {})
    threshold = float(fidelity.get("threshold_percent", 99.0))
    if (summary.get("slides") != slides or summary.get("passed") != slides
            or summary.get("blocking_failures") != 0 or summary.get("review", 0) != 0
            or float(summary.get("minimum_fidelity_percent", -1)) < threshold):
        raise ValueError("Prior TTS acceptance not valid for this slide sequence")
    risk = json.loads((stage / "script_risk_report.json").read_text(encoding="utf-8"))
    if risk.get("summary", {}).get("blocking") != 0:
        raise ValueError("Narration has blocking QA results")

def _render_single_page(doc, number: int, destination: Path) -> None:
    import fitz
    one = fitz.open()
    one.insert_pdf(doc, from_page=number - 1, to_page=number - 1)
    one.save(destination)
    one.close()

def _probe_duration(file: Path) -> float:
    ffmpeg = ffmpeg_executable()
    proc = subprocess.run([str(ffmpeg), "-hide_banner", "-i", str(file)],
                          capture_output=True, text=True, timeout=60, errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", proc.stderr + proc.stdout)
    if not m:
        raise ValueError("Video duration unknown: " + str(file))
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

def _combine_parts(folder: Path, files: list[Path]) -> Path:
    names = folder / "retrofit_concat.txt"
    names.write_text("".join("file '" + f.as_posix().replace("'", "'\\''") + "'\n"
                             for f in files), encoding="utf-8")
    output = folder / "slides.mp4"
    subprocess.run([str(ffmpeg_executable()), "-hide_banner", "-nostdin", "-loglevel",
                    "error", "-y", "-f", "concat", "-safe", "0", "-i", str(names),
                    "-c", "copy", "-movflags", "+faststart", str(output)],
                   check=True, timeout=360)
    validate_video(str(ffmpeg_executable()), output, sum(_probe_duration(p) for p in files) * 0.95)
    return output

def _compare_frame(video: Path, seconds: float, pdf, slide: int, scratch: Path) -> float:
    """Independent decoded-video vs corrected-PDF check, for static slide videos."""
    import fitz
    import numpy as np
    from PIL import Image
    output = scratch / "retrofit_frame.png"
    subprocess.run([str(ffmpeg_executable()), "-hide_banner", "-nostdin",
                    "-loglevel", "error", "-y", "-ss", f"{seconds:.3f}",
                    "-i", str(video), "-frames:v", "1", str(output)],
                   check=True, timeout=90)
    frame = Image.open(output).convert("RGB")
    page = pdf[slide - 1]
    scale = min(1280 / page.rect.width, 720 / page.rect.height)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    expected = Image.new("RGB", (1280, 720), (0, 0, 0))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    expected.paste(im, ((1280 - im.width) // 2, (720 - im.height) // 2))
    if frame.size != expected.size:
        raise ValueError("Unexpected MP4 resolution")
    return float(np.abs(np.asarray(frame, dtype=np.int16)
                        - np.asarray(expected, dtype=np.int16)).mean())


def bootstrap_legacy_source_figures(work: Path) -> dict:
    """Source-only v2 upgrade inside an *isolated* retrofit workspace.

    Old accepted lectures predate the SHA-bound source-caption ledger. Restore
    it deterministically from immutable source.pdf; require every captioned
    source figure's exact filename in active, unguarded LaTeX. Missing figures
    must fail before expensive PDF or media generation. This code must never
    be invoked against a published folder by the retrofitter.
    """
    from .source_caption_figure_chain_v1 import (
        has_real_pdf_header, printed_source_captions,
        recover_printed_source_figures, verify_latex_figure_chain)
    work=Path(work)
    source=work/"source.pdf"
    if not has_real_pdf_header(source):
        return {"status":"LEGACY_NONPDF_SOURCE_FIXTURE"}
    if not printed_source_captions(source):
        return {"status":"NO_PRINTED_SOURCE_FIGURES"}
    # A source-verified crop ledger prepared by a figure-aware reviewer may
    # outperform heuristic automatic crop recovery on complex side captions.
    # Trust it ONLY after rebuilding each source crop and checking hashes,
    # original caption identities and every optional split-panel ledger.
    if (work/"source_figure_chain_v1.json").exists():
        from .source_caption_figure_chain_v1 import verify_figure_crops
        from .source_split_figure_chain_v1 import (
            prepare_split_figure_chain, verify_split_figure_chain)
        verified_crop = verify_figure_crops(work)
        if ((work/"figure_repair_provenance.json").exists()
                and not (work/"source_split_figure_chain_v1.json").exists()):
            # Historical source-exact split panels may lack a ledger; create
            # one only after verifying every source pixel and panel witness.
            prepare_split_figure_chain(work)
        if (work/"source_split_figure_chain_v1.json").exists():
            verify_split_figure_chain(work)
        verified=verify_latex_figure_chain(work)
        return {"status":"LEGACY_SOURCE_FIGURE_BOOTSTRAP_VERIFIED",
                "recovery_status":verified_crop["status"],
                "preverified_source_ledger_reused":True,
                "figure_count":verified["figures_verified"],
                "source_sha256":verified["source_sha256"]}
    recovered=recover_printed_source_figures(work)
    try:
        verified=verify_latex_figure_chain(work)
    except ValueError as exc:
        if ("LaTeX omitted source figures" not in str(exc)
                or not (work/"figure_repair_provenance.json").is_file()):
            raise
        from .source_split_figure_chain_v1 import prepare_split_figure_chain
        prepare_split_figure_chain(work)
        verified=verify_latex_figure_chain(work)
    return {"status":"LEGACY_SOURCE_FIGURE_BOOTSTRAP_VERIFIED",
            "recovery_status":recovered.get("status"),
            "figure_count":verified["figures_verified"],
            "source_sha256":verified["source_sha256"]}



def _completed_legacy_split_lecture(source_pdf: Path) -> bool:
    """Admit historical fully hash-verified multipart lectures for isolated retrofit.

    Legacy lectures may have completion receipts and split videos but no
    archival slides.mp4; the modern cleanup.completed_lecture gate rejects
    those even when their receipts accurately cover all active split videos.
    This is a strict input admission only; corrected staging must still pass
    ALL current source-crop, LaTeX, raster, audio, sync and video checks.
    """
    try:
        folder = Path(source_pdf).parent
        receipt_file = folder / ".microgen_completion.json"
        manifest_file = folder / "slides_parts_manifest.json"
        if not receipt_file.is_file() or not manifest_file.is_file():
            return False
        receipt = json.loads(receipt_file.read_text(encoding="utf8"))
        parts = json.loads(manifest_file.read_text(encoding="utf8"))
        if receipt.get("source_sha256") != digest(source_pdf):
            return False
        hashes = receipt.get("final_sha256")
        if not isinstance(hashes, dict):
            return False
        basics = {"slides.tex", "slides.pdf", "script.txt"}
        for name in basics:
            file = folder / name
            if name not in hashes or not file.is_file() or file.is_symlink() or digest(file) != hashes[name]:
                return False
        records = parts.get("parts")
        if not isinstance(records, list) or not records or len(records)>30:
            return False
        names = [r.get("name",r.get("file")) for r in records if isinstance(r,dict)]
        if len(names)!=len(records) or len(names)!=len(set(names)):
            return False
        if any(not re.fullmatch(r"slides_part\d{2}\.mp4",str(n)) for n in names):
            return False
        actual = {p.name for p in folder.glob("slides_part*.mp4") if p.is_file()}
        if set(names)!=actual:
            return False
        if set(hashes)!=(basics|set(names)):
            return False
        for name, rec in zip(names, records):
            file = folder/name
            if (not file.is_file() or file.is_symlink() or file.stat().st_size<100
                    or digest(file)!=hashes[name] or
                    rec.get("sha256")!=hashes[name]):
                return False
            seconds = _probe_duration(file)
            declared = float(rec["duration_seconds"])
            if not (0<seconds<600 and abs(seconds-declared)<=2.0):
                return False
        if parts.get("image_repair_pdf_sha256") is not None and (
              parts["image_repair_pdf_sha256"]!=hashes["slides.pdf"]):
            return False
        from .slide_narration_sync import verify as verify_sync
        sync = folder/"slide_narration_sync.json"
        if not sync.is_file() or (
              receipt.get("structural_sync_sha256")!=digest(sync)):
            return False
        # The historical PDF-reader revision may produce different
        # page_text_sha256 values for identical, hash-matched PDF bytes.
        # Do NOT accept unverified narration/audio: require all stored
        # original binary hashes, exact WAV hashes and blocks to match.
        sync_data=json.loads(sync.read_text(encoding="utf8"))
        from .slide_narration_sync import script_blocks
        blocks=script_blocks((folder/"script.txt").read_text(encoding="utf8"))
        if (sync_data.get("pdf_sha256")!=hashes["slides.pdf"] or
            sync_data.get("script_sha256")!=hashes["script.txt"] or
            sync_data.get("pages")!=len(blocks) or
            sync_data.get("narration_sha256")!=[
                hashlib.sha256(body.encode()).hexdigest() for body in blocks]):
            return False
        original_wavs=sync_data.get("wav")
        if not isinstance(original_wavs,list) or len(original_wavs)!=len(blocks):
            return False
        for pos,stored in enumerate(original_wavs,1):
            audio_file=folder/f"slide{pos}.wav"
            if (stored.get("file")!=audio_file.name or
                stored.get("sha256")!=digest(audio_file)):
                return False
        # This admits the old package for isolated staging ONLY; the
        # rebuilt slide package must regenerate and verify a new sync.
            import fitz
        with fitz.open(folder/"slides.pdf") as deck:
            slide_count=len(deck)
        wavs = sorted((p for p in folder.glob("slide*.wav")
                      if re.fullmatch(r"slide[1-9]\d*\.wav",p.name)),
                      key=lambda p:int(p.stem[5:]))
        if len(wavs)!=slide_count or [p.name for p in wavs]!=[
                f"slide{i}.wav" for i in range(1,slide_count+1)]:
            return False
        for wav in wavs:
            with wave.open(str(wav),"rb") as track:
                if track.getnframes()<=0 or track.getframerate()<=0:
                    return False
        fidelity=json.loads((folder/"tts_fidelity_report.json").read_text("utf8"))
        summary=fidelity.get("summary",{})
        threshold=float(fidelity.get("threshold_percent",99.0))
        if (summary.get("slides")!=slide_count or
                summary.get("passed")!=slide_count or
                summary.get("blocking_failures")!=0 or summary.get("review",0)!=0 or
                float(summary.get("minimum_fidelity_percent",-1))<threshold):
            return False
        risk=json.loads((folder/"script_risk_report.json").read_text("utf8"))
        if risk.get("summary",{}).get("blocking")!=0:
            return False
        return True
    except (OSError,ValueError,TypeError,KeyError,AttributeError,
            json.JSONDecodeError,RuntimeError,IndexError):
        return False


def stage_rebuild(original: Path, patch: Path, work: Path) -> dict:
    """Rebuild a repaired legacy deck without touching the published folder."""
    import fitz
    original, patch, work = Path(original).resolve(), Path(patch).resolve(), Path(work).resolve()
    edits = patch_files(patch)
    if original == work or original in work.parents or work == patch or work in patch.parents:
        raise ValueError("Work directory must be an independent local staging area")
    if work.exists() and any(work.iterdir()):
        raise FileExistsError("Work directory is not empty: " + str(work))
    work.mkdir(parents=True, exist_ok=True)
    if not (completed_lecture(original / "source.pdf")
            or _completed_legacy_split_lecture(original / "source.pdf")):
        raise ValueError("Original package lacks valid completion proof; use full recovery pipeline")
    before = _source_snapshot(original)
    for p in original.iterdir():
        if not p.is_file() or p.is_symlink():
            continue
        if (p.name in {"source.pdf", "slides.tex", "slides.pdf", "script.txt",
                       "tts_fidelity_report.json", "script_risk_report.json",
                       "figure_repair_provenance.json"}
                or p.suffix.lower() in {".png", ".jpg", ".jpeg", ".eps", ".sty", ".cls"}
                or re.fullmatch(r"slide[1-9]\d*\.wav", p.name, re.I)):
            shutil.copy2(p, work / p.name)
    for p in edits:
        shutil.copy2(p, work / p.name)
    if digest(work / "source.pdf") != before["source.pdf"]:
        raise RuntimeError("Immutable source PDF changed while staging")
    if digest(work / "slides.tex") == before["slides.tex"] and all(
            (original / p.name).exists() and digest(original / p.name) == digest(p)
            for p in edits):
        raise ValueError("No image or slide changes to rebuild")
    # Use only original-source pixels; never transfer legacy unverified
    # figure manifests as a substitute for v2 source-derived evidence.
    source_chain = bootstrap_legacy_source_figures(work)
    for attempt in (1, 2):
        proc = subprocess.run(["pdflatex", "-halt-on-error", "-interaction=nonstopmode",
                               "slides.tex"], cwd=work, capture_output=True, text=True,
                              errors="replace", timeout=240)
        (work / f"retrofit_pdflatex_{attempt}.log").write_text(
            proc.stdout + proc.stderr, encoding="utf-8")
        if proc.returncode:
            raise RuntimeError(f"LaTeX compilation {attempt} failed: "
                               + (proc.stdout + proc.stderr)[-1800:])
    from .source_caption_figure_chain_v1 import (
        has_real_pdf_header, verify_rendered_pdf_source_figures)
    if has_real_pdf_header(work/"source.pdf"):
        # A LaTeX reference does not establish a visible compiled PDF image.
        verify_rendered_pdf_source_figures(work)
    manifest = enforce_graphics(work, repair=True)
    if audit_wide_figure_legibility((work / "slides.tex").read_text("utf-8"), work):
        raise ValueError("Source-grounded figures do not pass readability gate")
    with fitz.open(work / "slides.pdf") as pdf:
        slides = len(pdf)
    old_wavs = _media_seconds(work)
    if slides != len(old_wavs):
        raise ValueError("Slide count changed; re-run script/TTS synchronization stages")
    _validate_unchanged_tts(original, work, slides)
    sync = record_structural_alignment(work)
    if sync != verify(work):
        raise RuntimeError("Regenerated sync receipt failed verification")
    groups = balanced_groups(old_wavs)
    part_records = []
    sampled = []
    with fitz.open(work / "slides.pdf") as pdf:
        for part_no, (start, end) in enumerate(groups, 1):
            subdir = work / f".retrofit_part_{part_no:02}"
            subdir.mkdir()
            for out_num, slide_num in enumerate(range(start, end + 1), 1):
                _render_single_page(pdf, slide_num, subdir / f"slide{out_num}.pdf")
                shutil.copy2(work / f"slide{slide_num}.wav",
                             subdir / f"slide{out_num}.wav")
            part_src = assemble(subdir, output="slides.mp4")
            dest = work / f"slides_part{part_no:02}.mp4"
            shutil.copy2(part_src, dest)
            duration = _probe_duration(dest)
            if not (0 < duration < 600):
                raise ValueError(f"MP4 part too long: {dest}: {duration}")
            validate_video(str(ffmpeg_executable()), dest, sum(old_wavs[start - 1:end]))
            for slide_num in range(start, end + 1):
                if slide_num in {1, slides} or pdf[slide_num - 1].get_images(full=True):
                    offset = sum(old_wavs[start - 1:slide_num - 1])
                    offset += old_wavs[slide_num - 1] / 2
                    error = _compare_frame(dest, offset, pdf, slide_num, work)
                    sampled.append({"slide": slide_num, "decoded_frame_mae": round(error, 3)})
                    if error >= 25:
                        raise RuntimeError("Video frame does not match repaired slide: "
                                           + str(slide_num))
            part_records.append({"file": dest.name, "sha256": digest(dest),
                                 "duration_seconds": round(duration, 3),
                                 "slides": [start, end]})
    full = _combine_parts(work, [work / item["file"] for item in part_records])
    parts = {"subtopic": original.name, "verified_full_sha256": digest(full),
             "source_slides_pdf_sha256": digest(work / "slides.pdf"),
             "full_duration_seconds": round(_probe_duration(full), 3),
             "full_slides_mp4_status": "archival_if_over_600s",
             "split_method": "per_slide_boundary_with_separate_encoder_outputs",
             "active_deliverables": [x["file"] for x in part_records],
             "parts": part_records}
    dump(work / "slides_parts_manifest.json", parts)
    previous = json.loads((original / ".microgen_completion.json").read_text("utf-8"))
    previous.update({"source_sha256": before["source.pdf"],
                     "final_sha256": {n: digest(work / n) for n in FINAL},
                     "structural_sync_sha256": digest(work / "slide_narration_sync.json"),
                     "retrofit": {"date": datetime.now(timezone.utc).isoformat(),
                                  "source": str(original), "parts": len(part_records)}})
    dump(work / ".microgen_completion.json", previous)
    if not completed_lecture(work / "source.pdf"):
        raise RuntimeError("Staged completion verification rejected rebuilt package")
    patched_names = [p.name for p in edits if p.name != "slides.tex"]
    source_chain_names = []
    if source_chain.get("status") == "LEGACY_SOURCE_FIGURE_BOOTSTRAP_VERIFIED":
        from .source_caption_figure_chain_v1 import verify_figure_crops
        source_chain_names = ["source_figure_chain_v1.json",
                              *verify_figure_crops(work)["figures"]]
        if (work/"source_split_figure_chain_v1.json").is_file():
            from .source_split_figure_chain_v1 import verify_split_figure_chain
            verify_split_figure_chain(work)
            source_chain_names.append("source_split_figure_chain_v1.json")
    deliverables = ["slides.tex", "slides.pdf", "figures_manifest.json",
                    "slide_narration_sync.json", "slides.mp4", "slides_parts_manifest.json",
                    *[p["file"] for p in part_records],
                    *patched_names, *source_chain_names]
    deliverables = sorted(set(deliverables))
    state = {"subtopic": original.name, "source_folder": str(original),
             "original_checksums": before, "files": deliverables,
             "stage_checksums": {n: digest(work / n) for n in deliverables},
             "source_sha256": before["source.pdf"],
             "image_references": len(manifest["figures"]),
             "video_frame_samples": sampled, "video_parts": part_records,
             "tts_reused_after_qa": True, "status": "STAGED_ACCEPTED"}
    dump(work / "retrofit_state.json", state)
    return state

def publish(original: Path, work: Path) -> dict:
    """Rollback-safe application of a fully verified, separately staged repair."""
    original, work = Path(original).resolve(), Path(work).resolve()
    state = json.loads((work / "retrofit_state.json").read_text(encoding="utf-8"))
    if state.get("source_folder") != str(original) or state.get("status") != "STAGED_ACCEPTED":
        raise ValueError("Staged package is not approved for this original")
    for name, sha in state["original_checksums"].items():
        actual = digest(original / name) if (original / name).is_file() else None
        if sha != actual:
            raise RuntimeError("Concurrent modification before publication: " + name)
    if not completed_lecture(work / "source.pdf") or verify(work)["pages"] <= 0:
        raise RuntimeError("Staging acceptance lost")
    for name, sha in state["stage_checksums"].items():
        if digest(work / name) != sha:
            raise RuntimeError("Staged asset changed: " + name)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup = original / ".history" / ("retrofit_image_" + stamp)
    backup.mkdir(parents=True, exist_ok=False)
    changed = state["files"]
    original_files = {n: (original / n).is_file() for n in changed}
    for n in [*changed, ".microgen_completion.json"]:
        src = original / n
        if src.is_file():
            shutil.copy2(src, backup / n)
            if digest(src) != digest(backup / n):
                raise RuntimeError("Backup not verified: " + n)
    dump(backup / "source_snapshot.json", state["original_checksums"])
    copied = []
    try:
        for name in changed:
            pending = original / ("." + name + ".retrofit_pending")
            try:
                shutil.copy2(work / name, pending)
                if digest(pending) != state["stage_checksums"][name]:
                    raise RuntimeError("Drive copy hash mismatch: " + name)
                pending.replace(original / name)
                copied.append(name)
            finally:
                pending.unlink(missing_ok=True)
        receipt = original / ".microgen_completion.json"
        pending = original / ".microgen_completion.retrofit_pending"
        try:
            shutil.copy2(work / ".microgen_completion.json", pending)
            pending.replace(receipt)
        finally:
            pending.unlink(missing_ok=True)
        if not completed_lecture(original / "source.pdf"):
            raise RuntimeError("Published package rejected by completion gate")
        verify(original)
        for name, sha in state["stage_checksums"].items():
            if digest(original / name) != sha:
                raise RuntimeError("Published readback mismatch: " + name)
    except BaseException:
        for name in reversed(copied):
            if original_files[name]:
                shutil.copy2(backup / name, original / name)
            else:
                (original / name).unlink(missing_ok=True)
        if (backup / ".microgen_completion.json").exists():
            shutil.copy2(backup / ".microgen_completion.json",
                         original / ".microgen_completion.json")
        raise
    state.update({"status": "PUBLICATION_VERIFIED", "backup": str(backup),
                  "published_at_utc": datetime.now(timezone.utc).isoformat()})
    dump(work / "retrofit_state.json", state)
    dump(original / "retrofit_image_repair_receipt.json", state)
    return state

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--audit-chapter", type=Path)
    action.add_argument("--stage", type=Path, metavar="SUBTOPIC_FOLDER")
    action.add_argument("--publish", type=Path, metavar="SUBTOPIC_FOLDER")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--patch-dir", type=Path)
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args(argv)
    if args.audit_chapter:
        result = {"chapter": args.audit_chapter.name,
                  "packages": chapter_audit(args.audit_chapter)}
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            dump(args.report, result)
    elif args.stage:
        if not args.patch_dir or not args.work_dir:
            parser.error("--stage requires --patch-dir and --work-dir")
        result = stage_rebuild(args.stage, args.patch_dir, args.work_dir)
    else:
        if not args.work_dir:
            parser.error("--publish requires --work-dir")
        result = publish(args.publish, args.work_dir)
    print(json.dumps(result, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
