"""Bounded, source-image-grounded Gemini Flash figure mapping via API.

The UI-only path can fail despite a submitted prompt. This child process uses
MicroGen's existing Gemini key failover, no browser state, and strict output
validation. No mapping output is published unless *every* crop is mapped.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

LINE = re.compile(
    r'^\s*(?P<crop>[A-Za-z0-9_.-]+\.png)\s*:\s*'
    r'"(?P<label>[^"\r\n]{1,100})"\s*:\s*'
    r'(?P<target>[^\r\n]{1,160}\.png)\s*$',
    re.IGNORECASE,
)


def validate_mapping(text: str, crops: list[Path]) -> list[str]:
    """Require an exact, ordered, filename-safe mapping of all actual crops."""
    if not crops or not text.strip():
        raise ValueError("Empty figure mapping or no source crops")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != len(crops):
        raise ValueError(f"Expected {len(crops)} crop mappings, received {len(lines)} lines")
    validated = []
    for expected, raw in zip(crops, lines):
        match = LINE.fullmatch(raw)
        if match is None:
            raise ValueError(f"Malformed figure mapping for {expected.name}")
        name, label, target = match.group("crop"), match.group("label").strip(), match.group("target").strip()
        if name != expected.name:
            raise ValueError(f"Figure mapping order mismatch: expected {expected.name}, got {name}")
        if label.lower() in {"unknown", "figure", "none", "n/a", "error"}:
            raise ValueError(f"Uninformative figure label for {name}")
        if label.lower().startswith("figure") and not re.search(r"\d", label):
            raise ValueError(f"Unnumbered figure label for {name}")
        if any(token in target for token in ("..", "/", "\\", "<", ">", "|", "?", "*", ":")):
            raise ValueError(f"Unsafe target name for {name}")
        if not target.lower().endswith(".png") or target.startswith("."):
            raise ValueError(f"Non-PNG figure output name for {name}")
        # Gemini may describe mathematical figures using equations.
        # Keep the meaning while publishing a file name that downstream
        # image and LaTeX routines can safely process.
        stem = target[:-4]
        for symbol, word in (("=", " equals "), ("^", " power "), ("+", " plus "),
                             ("(", " "), (")", " ")):
            stem = stem.replace(symbol, word)
        stem = " ".join(stem.split())
        if not stem or len(stem) > 150 or not re.fullmatch(r"[A-Za-z0-9_. -]+", stem):
            raise ValueError(f"Unsupported target filename characters for {name}")
        target = stem + ".png"
        validated.append(f'{name} : "{label}" : {target}')
    return validated


def request_mapping(page: Path, crops: list[Path], model: str) -> str:
    """Call the same failover-managed Gemini client already used by TTS."""
    repo = Path(__file__).resolve().parents[1]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from google.genai import types
    from gemini_keys import call_with_client_failover, create_gemini_client

    manifest = "\n".join(f"{i+1}. {p.name}" for i, p in enumerate(crops))
    prompt = (
        "Study this textbook page and its cropped figure images. The FIRST image is "
        "the full page; the following images are the crops in the order listed.\n"
        f"CROPS:\n{manifest}\n"
        "For EACH crop, identify the actual figure caption number from the page. "
        "Never invent a figure number if there is no readable caption: instead use "
        "the exact label Unlabeled image with a short, distinct descriptive target name. "
        "Return exactly one line per crop and no other text. Use the exact corresponding "
        'crop filename at the start of each line. Format: fig_1.png : "Figure 10.4" : Figure 10.4.png. '
        "For unlabeled crops use fig_1.png : \"Unlabeled image\" : descriptive image.png. "
        "You must not alter, reorder, or omit the crop filenames."
    )
    parts = [types.Part.from_text(text=prompt)]
    for image in [page, *crops]:
        if image.suffix.lower() != ".png" or not image.is_file() or not image.stat().st_size:
            raise ValueError(f"Missing/invalid PNG input: {image}")
        parts.append(types.Part.from_bytes(data=image.read_bytes(), mime_type="image/png"))

    def operation(client):
        return client.models.generate_content(
            model=model,
            contents=parts,
            config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=4096),
        )

    response = call_with_client_failover(
        create_gemini_client, operation,
        label=f"Gemini {model} figure mapping {page.name}", max_retries=1,
    )
    result = (response.text or "").strip()
    if not result:
        raise RuntimeError("Gemini API returned no figure mapping text")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", type=Path, required=True)
    parser.add_argument("--crop", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=os.getenv("MICROGEN_LLM_MODEL", "gemini-3.8-flash"))
    args = parser.parse_args(argv)

    raw = request_mapping(args.page, args.crop, args.model)
    try:
        clean = validate_mapping(raw, args.crop)
    except ValueError:
        diagnostic = args.output.with_name(args.output.stem + ".rejected.txt")
        diagnostic.write_text(raw[:12000], encoding="utf-8")
        raise
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pending = args.output.with_name(args.output.name + ".pending")
    pending.write_text("\n".join(clean) + "\n", encoding="utf-8")
    pending.replace(args.output)
    print(f"[figure-api] VERIFIED {len(clean)} mapped source crop(s) with {args.model}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
