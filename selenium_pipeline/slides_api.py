"""Bounded Gemini Flash API transport for source-grounded Beamer slide drafts.

Returns only raw model output. The existing vendor slide pipeline must sanitize,
check page-figure/Beamer structure, compile, and reject citation artifacts before
a draft can be published. The API cannot certify educational content by itself.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

def request_slides(source: Path, prompt: Path, dimensions: Path,
                   instructions: Path, model: str) -> str:
    sources = (
        (source, "application/pdf"),
        (prompt, "text/plain"),
        (dimensions, "application/json"),
        (instructions, "text/plain"),
    )
    for file, mime in sources:
        if not file.is_file() or file.is_symlink() or file.stat().st_size == 0:
            raise ValueError(f"Missing/invalid {mime} input: {file}")
    if source.suffix.lower() != ".pdf":
        raise ValueError("Source must be the actual source.pdf textbook file")
    if not model.endswith("-flash") or "pro" in model.lower():
        raise ValueError("Slide API accepts only Gemini Flash, never Pro")
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from google.genai import types
    from gemini_keys import call_with_client_failover, create_gemini_client

    rendered = prompt.read_text(encoding="utf-8")
    instruction = instructions.read_text(encoding="utf-8")
    dims = dimensions.read_text(encoding="utf-8")
    if len(rendered.strip()) < 200 or len(instruction.strip()) < 100:
        raise ValueError("The current source-specific slide prompt is incomplete")
    parts = [
        types.Part.from_text(text=(
            "Prepare source-grounded LaTeX Beamer teaching slides. The attached "
            "application/pdf is the sole academic source. Use the complete, "
            "current rendered prompt and PNG dimension metadata below. "
            "Return the exact full raw LaTeX document in one fenced latex block, "
            "from documentclass to end document. Do not invent missing figures, "
            "sources, or reference numbers. Never use a Pro model.\n\n"
            "SOURCE-SPECIFIC INSTRUCTIONS:\n" + rendered +
            "\n\nFINAL TRANSPORT REQUIREMENTS:\n" + instruction +
            "\n\nPNG DIMENSIONS:\n" + dims
        )),
        types.Part.from_bytes(data=source.read_bytes(), mime_type="application/pdf"),
    ]
    def operation(client):
        return client.models.generate_content(
            model=model,
            contents=parts,
            config=types.GenerateContentConfig(
                temperature=0.25,
                max_output_tokens=32768,
            ),
        )
    response = call_with_client_failover(
        create_gemini_client, operation,
        label=f"Gemini Flash slides {source.name}", max_retries=1,
    )
    answer = (response.text or "").strip()
    if not answer or len(answer) < 100:
        raise RuntimeError("Gemini Flash API returned no usable slide draft")
    if "\\documentclass" not in answer or "\\end{document}" not in answer:
        raise ValueError("Gemini Flash API returned an incomplete LaTeX document")
    return answer


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--rendered-prompt", required=True, type=Path)
    p.add_argument("--dimensions", required=True, type=Path)
    p.add_argument("--instructions", required=True, type=Path)
    p.add_argument("--raw-output", required=True, type=Path)
    p.add_argument("--model", default=os.getenv("MICROGEN_LLM_MODEL", "gemini-3.8-flash"))
    a = p.parse_args(argv)
    result = request_slides(a.source, a.rendered_prompt, a.dimensions, a.instructions, a.model)
    a.raw_output.parent.mkdir(parents=True, exist_ok=True)
    pending = a.raw_output.with_name(a.raw_output.name + ".pending")
    try:
        pending.write_text(result + "\n", encoding="utf-8")
        pending.replace(a.raw_output)
    finally:
        pending.unlink(missing_ok=True)
    print(f"[slides-api] Received {len(result)} raw characters from {a.model}; "
          f"Beamer sanity/compile and source figures still require validation", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
