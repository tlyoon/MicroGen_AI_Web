"""Source-grounded Gemini Flash narration via API (no Chrome UI dependency).

Uses the existing API key failover and feeds both exact textbook/PDF inputs
plus the fully rendered narration instruction to Gemini. Only complete,
well-formed numbered raw responses are staged; final acceptance remains
owned by the vendored narration title/speech-safety validation and TTS QA.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re

HEADER = re.compile(r"(?im)^\s*\*{0,2}\s*Slide\s+(\d+)\s*\[[^\]\r\n]+\]\s*:")


def validate_raw_script(text: str, expected_slides: int) -> None:
    if expected_slides < 1:
        raise ValueError("Expected slide count must be positive")
    if not isinstance(text, str) or len(text.strip()) < max(200, expected_slides * 60):
        raise ValueError("Gemini API narration was empty or suspiciously short")
    indices = [int(x) for x in HEADER.findall(text)]
    if indices != list(range(1, expected_slides + 1)):
        raise ValueError(
            f"Gemini API narration blocks invalid: expected 1..{expected_slides}, "
            f"found {indices[:expected_slides+5]}"
        )


def request_narration(
    slides_pdf: Path,
    source_pdf: Path,
    rendered_prompt: Path,
    instruction: str,
    *,
    model: str = "gemini-3.8-flash",
) -> str:
    from google.genai import types
    from gemini_keys import call_with_client_failover, create_gemini_client

    documents = (slides_pdf, source_pdf)
    for path in (*documents, rendered_prompt):
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise ValueError(f"Missing, empty or unsafe narration input: {path}")
    if any(not p.read_bytes().startswith(b"%PDF") for p in documents):
        raise ValueError("Narration documents must be PDFs")
    if model != "gemini-3.8-flash":
        raise ValueError(f"Refusing non-Flash narration model: {model}")
    parts = [
        types.Part.from_text(text=instruction),
        types.Part.from_text(text=(
            "The exact narration instructions from gen_script_prompt_v10_rendered.txt "
            "follow. Obey these instructions and use both attached PDFs."
            "\n\n" + rendered_prompt.read_text(encoding="utf-8-sig")
        )),
        types.Part.from_bytes(data=slides_pdf.read_bytes(), mime_type="application/pdf"),
        types.Part.from_bytes(data=source_pdf.read_bytes(), mime_type="application/pdf"),
    ]

    def operation(client):
        return client.models.generate_content(
            model=model,
            contents=parts,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=int(os.getenv("MICROGEN_NARRATION_API_MAX_TOKENS", "32768")),
            ),
        )

    response = call_with_client_failover(
        create_gemini_client, operation,
        label=f"MicroGen_AI_Web Flash narration {slides_pdf.name}",
        max_retries=1,
    )
    candidates = getattr(response, "candidates", None) or []
    reason = str(getattr(candidates[0], "finish_reason", "")).upper() if candidates else ""
    if not reason.endswith("STOP"):
        raise RuntimeError(f"Gemini narration API did not finish normally: {reason or 'no candidate'}")
    result = (getattr(response, "text", None) or "").strip()
    if not result:
        raise RuntimeError("Gemini narration API completed without any visible script text")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slides", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--instruction-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-slides", type=int, required=True)
    parser.add_argument("--model", default=os.getenv("MICROGEN_LLM_MODEL", "gemini-3.8-flash"))
    args = parser.parse_args(argv)

    instruction = args.instruction_file.read_text(encoding="utf-8-sig")
    text = request_narration(args.slides, args.source, args.prompt, instruction, model=args.model)
    try:
        validate_raw_script(text, args.expected_slides)
    except ValueError:
        diagnostic = args.output.with_suffix(".rejected.txt")
        diagnostic.write_text(text[:200_000], encoding="utf-8")
        raise

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + ".pending")
    try:
        temporary.write_text(text + "\n", encoding="utf-8")
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"[narration-api] VERIFIED {args.expected_slides} numbered raw narration blocks", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
