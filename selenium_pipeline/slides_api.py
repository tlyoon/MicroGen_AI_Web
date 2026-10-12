"""Gemini Flash API transport for source-grounded Beamer slide generation.

This transport returns raw LaTeX; acceptance is decided by the *same* vendored
sanitizer, Beamer stack sanity compiler and final artifact checks as Selenium.
It deliberately does not publish slides.tex or slides.pdf itself.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path


def request_slides(source: Path, prompt: Path, dimension_json: Path,
                   instruction: str, *, model: str = "gemini-3.8-flash") -> str:
    from google.genai import types
    from gemini_keys import create_gemini_client, call_with_client_failover

    for file in (source, prompt, dimension_json):
        if not file.is_file() or file.is_symlink() or file.stat().st_size == 0:
            raise ValueError(f"Slides API source input missing, empty or unsafe: {file}")
    if not source.read_bytes().startswith(b"%PDF"):
        raise ValueError("Slides API source must be a real PDF")
    if model != "gemini-3.8-flash":
        raise ValueError(f"Refusing slides API model other than vetted Flash: {model}")
    prompt_text = prompt.read_text(encoding="utf-8-sig")
    dimensions = dimension_json.read_text(encoding="utf-8-sig")
    if not prompt_text.strip() or not dimensions.strip():
        raise ValueError("Empty slide-generation instruction or image-dimension metadata")

    payload = [
        types.Part.from_text(text=instruction),
        types.Part.from_text(text=(
            f"Exact contents of {prompt.name}:\n\n{prompt_text}\n\n"
            f"Exact contents of {dimension_json.name}:\n\n{dimensions}\n\n"
            "The attached original source PDF is the sole academic reference. "
            "The metadata names are local image assets; do not invent filenames."
        )),
        types.Part.from_bytes(data=source.read_bytes(), mime_type="application/pdf"),
    ]

    def operation(client):
        return client.models.generate_content(
            model=model, contents=payload,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=int(os.environ.get("MICROGEN_SLIDES_API_MAX_TOKENS", "32768")),
            ),
        )
    reply = call_with_client_failover(
        create_gemini_client, operation, label=f"MicroGen slides PDF {source.name}",
        max_retries=1,
    )
    candidates = getattr(reply, "candidates", None) or []
    reason = str(getattr(candidates[0], "finish_reason", "")).upper() if candidates else ""
    if not reason.endswith("STOP"):
        raise RuntimeError(f"Gemini slides API did not finish normally: {reason or 'no candidate'}")
    content = (getattr(reply, "text", None) or "").strip()
    if not content:
        raise RuntimeError("Gemini slides API returned no visible LaTeX source")
    return content


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--prompt", type=Path, required=True)
    ap.add_argument("--dimensions", type=Path, required=True)
    ap.add_argument("--instruction-file", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--model", default=os.getenv("MICROGEN_LLM_MODEL", "gemini-3.8-flash"))
    args = ap.parse_args(argv)

    if not args.instruction_file.is_file():
        raise ValueError("Missing slide transport instruction file")
    raw = request_slides(
        args.source, args.prompt, args.dimensions,
        args.instruction_file.read_text(encoding="utf-8-sig"), model=args.model,
    )
    # Raw response is an input to the shared Beamer acceptance gate, NOT an
    # approved slides.tex. Leave the latter untouched on API errors.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pending = args.output.with_name(args.output.name + ".pending")
    try:
        pending.write_text(raw + "\n", encoding="utf-8")
        pending.replace(args.output)
    finally:
        pending.unlink(missing_ok=True)
    print("[slides-api] raw source-grounded response captured; awaiting Beamer validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
