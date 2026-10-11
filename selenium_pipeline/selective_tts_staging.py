"""Prepare isolated selective narration TTS without changing published audio."""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
from .runner import blocks

def prepare(folder: Path, affected: list[int], replacements: dict[int, str],
            destination: Path) -> dict:
    folder, destination = Path(folder), Path(destination)
    source = (folder / "script.txt").read_text(encoding="utf-8")
    original = dict(blocks(source))
    numbers = sorted(original)
    selected = sorted(set(affected))
    if not selected or any(n not in original for n in selected):
        raise ValueError("Affected slide numbers must be valid and nonempty")
    if set(replacements) != set(selected):
        raise ValueError("Explicit reviewed narration required for every affected slide")
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("Refusing to overwrite a populated staging directory")
    destination.mkdir(parents=True, exist_ok=True)
    candidate = destination / ".tts_candidate"
    candidate.mkdir(exist_ok=True)
    for n in numbers:
        wav = folder / f"slide{n}.wav"
        if not wav.is_file():
            raise FileNotFoundError(wav)
        if n not in selected:
            shutil.copy2(wav, candidate / wav.name)
    # The maintained TTS engine parses template_v2 slide headers and can
    # preserve preseeded candidates, but never assumes existing WAVs are valid.
    revised = []
    for n in numbers:
        body = replacements[n] if n in replacements else original[n]
        if not body.strip():
            raise ValueError(f"Empty narration for slide {n}")
        revised.append(f"**Slide {n} [45 sec]:\n{body.strip()}**")
    (destination / "script.txt").write_text("\n\n".join(revised)+"\n",encoding="utf-8")
    report={"affected":selected,"total_slides":len(numbers),
            "source_script_sha256":hashlib.sha256(source.encode()).hexdigest(),
            "status":"staged_requires_tts_and_qa",
            "published_audio_unchanged":True}
    (destination / "selective_repair_manifest.json").write_text(
        json.dumps(report,indent=2),encoding="utf-8")
    return report

