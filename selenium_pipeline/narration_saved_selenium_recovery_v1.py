"""Recover a prior Selenium narration capture without another model Send.

Use only the same source and compiled slides, exact PDF slide count and
first title, a complete script and current strict ambiguity lint. Never
reuse an uncertain model request or invent missing narration.
"""
from __future__ import annotations
import json
import hashlib
import re
from pathlib import Path

def _sha(p: Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def recover_saved_selenium_candidate(folder:Path,source:Path)->dict|None:
    folder=Path(folder);source=Path(source)
    transcript=folder/"script.txt"
    if transcript.exists():return None
    src=folder/"source.pdf";slidepdf=folder/"slides.pdf"
    stamp=folder/".selenium_pipeline_state.json"
    titles=folder/"slide_titles_exact.json"
    if not all(p.is_file() and not p.is_symlink() for p in (src,slidepdf,stamp,titles,source)):
        return None
    state=json.loads(stamp.read_text(encoding="utf8"))
    if state.get("source_sha256")!=_sha(source) or _sha(src)!=_sha(source):
        return None
    if not isinstance(state.get("completed",{}).get("slides"),dict):
        return None
    title_data=json.loads(titles.read_text(encoding="utf8"))
    expected=title_data.get("titles",[])
    count=title_data.get("slide_count")
    if count!=len(expected) or not count or count>200:return None
    files=sorted(folder.glob("script.rejected_selenium_attempt_*.txt"),
        key=lambda p:p.stat().st_mtime_ns,reverse=True)
    for candidate in files:
        if not candidate.is_file() or candidate.is_symlink():
            continue
        if candidate.stat().st_mtime_ns < max(src.stat().st_mtime_ns,slidepdf.stat().st_mtime_ns):
            continue
        try:
            content=candidate.read_text(encoding="utf8")
            from .vendor_template_v2.script_tts_risk import analyze_script_text,parse_blocks
            blocks=parse_blocks(content)
            risk=analyze_script_text(content)
        except (ValueError,UnicodeError,ImportError):
            continue
        if (risk["summary"]["blocking"] or len(blocks)!=count
            or [b[0] for b in blocks]!=list(range(1,count+1))):
            continue
        first=blocks[0][1].strip()
        if first!=str(expected[0].get("title","")).strip():
            continue
        import pymupdf
        with pymupdf.open(slidepdf) as pdf:
            if len(pdf)!=count:continue
        # Nothing from the original accepted text is changed. The write is atomic.
        tmp=folder/"script.txt.saved_candidate_recovery"
        if tmp.exists():return None
        tmp.write_bytes(candidate.read_bytes())
        try:
            if analyze_script_text(tmp.read_text(encoding="utf8"))["summary"]["blocking"]:
                return None
            tmp.replace(transcript)
        finally:
            tmp.unlink(missing_ok=True)
        receipt={"status":"accepted_saved_selenium_candidate",
            "source_sha256":_sha(source),"slides_sha256":_sha(slidepdf),
            "candidate":candidate.name,"script_sha256":_sha(transcript),
            "exact_slide_count":count,"original_candidate_preserved":True,
            "zero_new_model_sends":True}
        (folder/".microgen_saved_selenium_narration_recovery.json").write_text(
            json.dumps(receipt,indent=2),encoding="utf8")
        return receipt
    return None
