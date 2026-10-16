"""Prepare Thomas 8.4 real-spoken-WAV, slide-level HIGHLIGHT REVIEW inputs.

This is a deliberately non-production adapter from a separately produced and
verified MicroGen_AI lecture bundle to MicroGen_AI_Web's experimental renderer.
Each existing WAV narrates an ENTIRE slide. One highlighted visual region per
slide DOES NOT constitute element-specific speech alignment or lecture approval.
No TTS, paid calls, edits to textbooks, acceptance receipts, or publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import wave
from pathlib import Path

import pymupdf

PREFIX = "microgen-element:"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as target:
        json.dump(value, target, indent=2, ensure_ascii=False)
        target.write("\n")


def check(ok, message):
    if not ok:
        raise ValueError(message)


def select_visible_region(page):
    """Choose one existing CONTENT region, never a fabricated overlay."""
    full = page.rect
    candidates = []
    for item in page.get_images(full=True):
        for rect in page.get_image_rects(item[0]):
            if (rect.width >= 35 and rect.height >= 25
                    and rect.y0 >= 32 and rect.y1 < full.height - 20
                    and rect.get_area() < full.get_area() * .8):
                candidates.append((100000 + rect.get_area(), rect, "figure"))
    if candidates:
        return max(candidates, key=lambda row: row[0])[1:]
    for block in page.get_text("blocks"):
        if len(block) <= 4 or not isinstance(block[4], str):
            continue
        rect = pymupdf.Rect(block[:4])
        if not block[4].strip() or rect.is_empty:
            continue
        if rect.y0 < 34 or rect.y1 > full.height - 17:
            continue
        if rect.width < 12 or rect.height < 6 or rect.get_area() >= full.get_area() * .8:
            continue
        # Prefer informative content blocks, not titles and footers.
        score = rect.get_area() + min(len(block[4]), 500) * 15
        candidates.append((score, rect, "text"))
    if candidates:
        return max(candidates, key=lambda row: row[0])[1:]
    # Title card: title centered in slide, no conventional body elements.
    candidates = []
    for block in page.get_text("blocks"):
        if len(block) <= 4 or not isinstance(block[4], str):
            continue
        rect = pymupdf.Rect(block[:4])
        if block[4].strip() and 30 <= rect.y0 <= full.height-20 and rect.width >= 20:
            candidates.append((rect.get_area(), rect, "text"))
    check(bool(candidates), "No source-content rectangle found")
    return max(candidates, key=lambda row: row[0])[1:]


def prepare(source_dir, destination):
    folder = Path(source_dir).resolve()
    dest = Path(destination).resolve()
    check(folder.is_dir(), "Verified source folder is missing")
    check(dest != folder and not dest.is_relative_to(folder), "Cannot stage inside textbook folder")
    check(not dest.exists() and dest.parent.is_dir(), "Review input destination must not already exist")
    expected = ["source.pdf", "slides.pdf", "script_tts.json",
                ".microgen_verified_completion.json"]
    check(all((folder / f).is_file() for f in expected), "Incomplete original lecture inputs")
    receipt = json.loads((folder / ".microgen_verified_completion.json").read_text(encoding="utf-8"))
    sidecar = json.loads((folder / "script_tts.json").read_text(encoding="utf-8"))
    check(receipt["slide_count"] == len(sidecar["slides"]) == 17,
          "Expected exact Thomas 8.4 17-slide source")
    for filename, key in (("source.pdf", "source_sha256"),
                          ("slides.pdf", "slides_pdf_sha256"),
                          ("script_tts.json", "sidecar_sha256")):
        check(sha(folder / filename) == receipt[key], "Source checksum changed: " + filename)
    voice_ids = []
    wav_data = []
    first_format = None
    for i in range(1, 18):
        file = folder / f"slide{i}.wav"
        check(file.is_file() and sha(file) == receipt["wav_sha256"][i-1],
              f"Missing or changed verified WAV {i}")
        with wave.open(str(file), "rb") as input_wave:
            fmt = (input_wave.getnchannels(), input_wave.getsampwidth(),
                   input_wave.getframerate(), input_wave.getcomptype())
            sec = input_wave.getnframes() / input_wave.getframerate()
        check(sec > .05, "Empty source spoken WAV")
        check(first_format is None or first_format == fmt, "Inconsistent WAV PCM formats")
        first_format = fmt
        wav_data.append(sec)
    # Slide 8 is a natural boundary after the first reference-triangle example.
    groups = (list(range(1, 9)), list(range(9, 18)))
    check(all(sum(wav_data[i-1] for i in group) < 590 for group in groups),
          "Source narration too long for selected part boundaries")
    plan = {"source_sha256": receipt["source_sha256"],
            "slides_pdf_sha256": receipt["slides_pdf_sha256"],
            "legacy_wav_sha256": receipt["wav_sha256"],
            "boundary_after_slide": 8,
            "status": "review_only_legacy_slide_granular_audio_not_speech_aligned"}
    plan_sha = hashlib.sha256(json.dumps(plan, sort_keys=True,
             separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    with pymupdf.open(folder / "slides.pdf") as pdf:
        check(len(pdf) == 17, "Slide PDF count differs from receipt")
        # All checksum and structural checks have passed; now create NEW staging tree.
        dest.mkdir()
        try:
            write_json(dest / "series_inputs.json", {
                "schema_version": 1, "status": "review_only_source_bound_inputs",
                "source_sha256": receipt["source_sha256"],
                "plan_sha256": plan_sha, "parts": ["part_01", "part_02"]})
            anchors = []
            for n, slides in enumerate(groups, 1):
                part_id = f"part_{n:02d}"
                part_dir = dest / part_id
                part_dir.mkdir()
                (part_dir / "wav").mkdir()
                chosen = pymupdf.open()
                board = {"schema_version": 1, "part_id": part_id,
                         "plan_sha256": plan_sha, "slides": [],
                         "narration_segments": []}
                chunks = []
                for local_index, original_index in enumerate(slides, 1):
                    sid = f"{part_id}.s{local_index:03d}"
                    eid = f"{sid}.target01"
                    segid = f"n{local_index}"
                    original = pdf[original_index - 1]
                    rect, kind = select_visible_region(original)
                    check(rect.get_area() < original.rect.get_area() * .85,
                          "Oversize target rectangle")
                    new_page = chosen.new_page(width=original.rect.width,
                                               height=original.rect.height)
                    new_page.show_pdf_page(new_page.rect, pdf, original_index-1)
                    new_page.insert_link({"kind": pymupdf.LINK_URI,
                                          "from": rect, "uri": PREFIX+eid})
                    narration = sidecar["slides"][original_index-1]
                    check(narration["slide"] == original_index, "Narration slide drift")
                    words = narration.get("tts_text") or narration["narration"]
                    board["slides"].append({"slide_id": sid,
                        "title": narration.get("title", f"Slide {original_index}"),
                        "elements": [{"element_id": eid, "kind": kind,
                                      "source_concept_ids": ["legacy_slide_unit"],
                                      "source_page": 1}]})
                    board["narration_segments"].append({
                        "segment_id": segid, "slide_id": sid,
                        "element_ids": [eid],
                        "spoken_text": words,
                        "estimated_duration_s": round(wav_data[original_index-1], 3)})
                    dest_wav = part_dir / "wav" / f"n{local_index}.wav"
                    shutil.copy2(folder / f"slide{original_index}.wav", dest_wav)
                    check(sha(dest_wav) == receipt["wav_sha256"][original_index-1],
                          "WAV changed during copy")
                    chunks.append({"segment_id": segid,
                        "filename": f"n{local_index}.wav",
                        "speech_sha256": hashlib.sha256(words.encode("utf-8")).hexdigest(),
                        "voice_id": "legacy_unknown_voice_consistency_unverified",
                        "pause_after_ms": 0})
                    anchors.append({"original_slide": original_index,
                        "part_id": part_id, "element_id": eid,
                        "rect_pt": [round(v, 2) for v in rect], "kind": kind,
                        "audio_seconds": round(wav_data[original_index-1], 3),
                        "spoken_words_not_independently_verified": True})
                chosen.save(part_dir / "instrumented.pdf", garbage=4, deflate=True)
                chosen.close()
                write_json(part_dir / "storyboard.json", board)
                write_json(part_dir / "tts_chunks.json", {
                    "schema_version": 1, "part_id": part_id,
                    "segments": chunks})
            write_json(dest / "pilot_provenance.json", {
                "status": "REVIEW_ONLY_NOT_PRODUCTION_COMPLIANT",
                "scope": "real spoken audio + original slides + one highlighted region per slide",
                "source_dir": str(folder),
                "source_sha256": receipt["source_sha256"],
                "slides_pdf_sha256": receipt["slides_pdf_sha256"],
                "source_audio_seconds": round(sum(wav_data),3),
                "part_audio_seconds": [round(sum(wav_data[i-1] for i in g),3)
                                       for g in groups],
                "documented_gaps": [
                    "The old WAV is entire-slide narration, not element-specific TTS.",
                    "Text hashes are from sidecar, not proven word-for-word audio.",
                    "One approximate target per slide cannot establish semantic timing.",
                    "Source page metadata is placeholder 1; not academically reviewed.",
                    "No academic approval, full-video content audit, or publication."
                ], "anchors": anchors})
        except BaseException:
            # Never leave a seemingly valid partial staging bundle.
            shutil.rmtree(dest, ignore_errors=True)
            raise
    print(json.dumps({"stage": str(dest), "part_audio_seconds":
                      [round(sum(wav_data[i-1] for i in g),3) for g in groups],
                      "segments": len(anchors), "status": "review_only"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.source_dir, args.destination)
