"""Fail-closed slide/narration synchronization gate.

A structural receipt binds exact PDF pages to numbered script blocks and WAVs.
An image-only PDF change invalidates that receipt even if page count is unchanged.\nThis is NOT a semantic or audio-transcription quality assessment.
"""
from __future__ import annotations
import hashlib
import json
import re
import wave
from pathlib import Path
import pymupdf

RECEIPT = "slide_narration_sync.json"
def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def script_blocks(script: str) -> list[str]:
    from .runner import blocks
    return [body for _, body in blocks(script)]

def inspect(folder: Path) -> dict:
    folder=Path(folder)
    pdf=folder/"slides.pdf"
    script=folder/"script.txt"
    blocks=script_blocks(script.read_text(encoding="utf-8"))
    with pymupdf.open(pdf) as doc:
        pages=len(doc)
        page_text=[hashlib.sha256(p.get_text().encode("utf-8")).hexdigest() for p in doc]
    if pages!=len(blocks):
        raise ValueError(f"Slides/narration count mismatch: {pages} pages vs {len(blocks)} blocks")
    wavs=sorted(folder.glob("slide*.wav"))
    expected={f"slide{i}.wav" for i in range(1,pages+1)}
    if {p.name for p in wavs}!=expected:
        raise ValueError("Missing, extra or incorrectly numbered WAV files")
    audio=[]
    for wav in sorted(wavs,key=lambda p:int(p.stem[5:])):
        with wave.open(str(wav),"rb") as stream:
            duration=stream.getnframes()/stream.getframerate()
        if duration<=0.05:
            raise ValueError(f"Empty WAV: {wav.name}")
        audio.append({"file":wav.name,"sha256":sha(wav),"duration_s":round(duration,3)})
    return {"version":1,"pdf_sha256":sha(pdf),"script_sha256":sha(script),
            "pages":pages,"page_text_sha256":page_text,
            "narration_sha256":[hashlib.sha256(b.encode()).hexdigest() for b in blocks],
            "wav":audio}

def verify(folder: Path) -> dict:
    folder=Path(folder)
    receipt=folder/RECEIPT
    if not receipt.is_file():
        raise ValueError("No verified slide/narration synchronization receipt; manual review or narration regeneration required")
    saved=json.loads(receipt.read_text(encoding="utf-8"))
    actual=inspect(folder)
    if saved!=actual:
        raise ValueError("Slide, narration or audio changed since synchronization approval")
    return actual

def record_structural_alignment(folder: Path) -> dict:
    """Record structurally matching assets after narration/TTS QA; not semantic approval."""
    folder=Path(folder)
    report=inspect(folder)
    (folder/RECEIPT).write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report


