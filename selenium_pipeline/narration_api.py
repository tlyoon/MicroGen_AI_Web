"""Gemini Flash API transport for source-grounded slide-by-slide narration.

The output is a raw candidate only. The existing narration postprocessor,
exact-title/page checks, script risk lint, TTS QA and video certification still
run without being bypassed.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def request_narration(slides: Path, source: Path, rendered_prompt: Path,
                      instructions: Path, model: str) -> str:
    for item in (slides, source, rendered_prompt, instructions):
        if not item.is_file() or item.is_symlink() or item.stat().st_size == 0:
            raise ValueError(f"Missing/invalid narration input: {item}")
    if not slides.name.lower().endswith(".pdf") or source.name.lower() != "source.pdf":
        raise ValueError("Narration requires slides.pdf and original source.pdf")
    if not model.endswith("-flash") or "pro" in model.lower():
        raise ValueError("Narration API accepts Gemini Flash only, never Pro")
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from google.genai import types
    from gemini_keys import call_with_client_failover, create_gemini_client

    details = rendered_prompt.read_text(encoding="utf-8")
    instruction = instructions.read_text(encoding="utf-8")
    if len(details.strip()) < 150 or len(instruction.strip()) < 100:
        raise ValueError("Incomplete source-grounded narration prompt")
    parts = [
        types.Part.from_text(text=(
            "Generate the complete numbered narration script for the ACTUAL "
            "slides.pdf attached as the first PDF. Use original source.pdf "
            "attached as second PDF only for scientific context. "
            "The visible slide order and exact titles in slides.pdf control. "
            "Never invent slides or omit blocks. Math must be spoken plain "
            "English, not Latex or symbols. Return ONLY the complete script, "
            "no code fences and no commentary. Follow ALL rendered prompts "
            "and validation feedback below.\n\n"
            "SOURCE AND FORMAT INSTRUCTIONS:\n"+details+
            "\n\nCURRENT REPAIR INSTRUCTIONS:\n"+instruction
        )),
        types.Part.from_bytes(data=slides.read_bytes(), mime_type="application/pdf"),
        types.Part.from_bytes(data=source.read_bytes(), mime_type="application/pdf"),
    ]
    def operation(client):
        return client.models.generate_content(
            model=model, contents=parts,
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=32768),
        )
    response = call_with_client_failover(
        create_gemini_client, operation,
        label=f"Gemini Flash narrated lecture {slides.name}", max_retries=1,
    )
    answer = (response.text or "").strip()
    if len(answer) < 120 or "Slide 1" not in answer:
        raise RuntimeError("Gemini Flash narration API returned no usable slide script")
    return answer


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--slides", required=True, type=Path)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--rendered-prompt", required=True, type=Path)
    p.add_argument("--instructions", required=True, type=Path)
    p.add_argument("--raw-output", required=True, type=Path)
    p.add_argument("--model", default=os.getenv("MICROGEN_LLM_MODEL", "gemini-3.8-flash"))
    a = p.parse_args(argv)
    answer = request_narration(a.slides, a.source, a.rendered_prompt, a.instructions, a.model)
    a.raw_output.parent.mkdir(parents=True, exist_ok=True)
    pending = a.raw_output.with_name(a.raw_output.name + ".pending")
    try:
        pending.write_text(answer + "\n", encoding="utf-8")
        pending.replace(a.raw_output)
    finally:
        pending.unlink(missing_ok=True)
    print(f"[narration-api] Received {len(answer)} raw characters from {a.model}; "
          "exact slide blocks and speech safety remain under local QA", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
