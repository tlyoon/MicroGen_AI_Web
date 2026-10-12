"""Produce an untrusted draft Beamer document through Gemini Flash API.

The existing vendor Beamer sanity, pdflatex and citation/figure gates remain the
ONLY way a generated draft may become published slides.tex/slides.pdf.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path


def image_inputs(folder: Path, *, limit: int = 80) -> list[Path]:
    figures = sorted(
        (p for p in folder.glob("*.png") if p.is_file() and p.stat().st_size),
        key=lambda p: p.name.lower(),
    )
    if len(figures) > limit:
        raise ValueError(f"Too many input figures ({len(figures)} > {limit}); refuse silent truncation")
    for fig in figures:
        if fig.stat().st_size > 15_000_000:
            raise ValueError(f"Figure exceeds 15 MB API input limit: {fig.name}")
    return figures


def make_request(pdf: Path, prompt: Path, metadata: Path, folder: Path,
                 model: str, feedback: str = "") -> str:
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf" or not pdf.stat().st_size:
        raise FileNotFoundError(f"Missing source PDF: {pdf}")
    if pdf.stat().st_size > 20_000_000:
        raise ValueError("Source PDF exceeds single-request 20 MB limit")
    if not prompt.is_file() or not metadata.is_file():
        raise FileNotFoundError("Missing slide-generation prompt or PNG metadata")

    repo = Path(__file__).resolve().parents[1]
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from google.genai import types
    from gemini_keys import create_gemini_client, call_with_client_failover

    figures = image_inputs(folder)
    extra = (
        "Produce ONE complete LaTeX Beamer document from \\documentclass through "
        "\\end{document} for the attached source PDF. Follow ALL of the supplied "
        "lecture instructions. Do not include student-visible citations, file "
        "provenance or explanatory text outside the LaTeX source. Use only actual "
        "source content and the attached named figures. Keep figures legible and "
        "preserve their aspect ratios. You may use exactly one fenced LaTeX code "
        "block around the complete source.\n"
    )
    if feedback:
        extra += (
            "THE PREVIOUS CANDIDATE FAILED THESE DETERMINISTIC CHECKS; CORRECT "
            "THEM WITHOUT OMITTING SOURCE MATERIAL:\n" + feedback[:2600] + "\n"
        )
    parts = [
        types.Part.from_text(text=extra + "\n" + prompt.read_text(encoding="utf-8")),
        types.Part.from_bytes(data=pdf.read_bytes(), mime_type="application/pdf"),
        types.Part.from_text(text="Actual figure metadata:\n" +
                             metadata.read_text(encoding="utf-8")),
    ]
    for figure in figures:
        parts.append(types.Part.from_text(text=f"Available source figure file: {figure.name}"))
        parts.append(types.Part.from_bytes(data=figure.read_bytes(), mime_type="image/png"))

    def generate(client):
        return client.models.generate_content(
            model=model,
            contents=parts,
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=24000),
        )

    response = call_with_client_failover(
        create_gemini_client, generate,
        label=f"Gemini {model} slide Beamer draft", max_retries=1,
    )
    text = (response.text or "").strip()
    if len(text) < 400 or "\\documentclass" not in text or "\\end{document}" not in text:
        raise RuntimeError("Gemini API produced no complete Beamer document")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=os.getenv("MICROGEN_LLM_MODEL", "gemini-3.8-flash"))
    parser.add_argument("--feedback", default="")
    args = parser.parse_args(argv)
    raw = make_request(args.pdf, args.prompt, args.metadata, args.folder,
                       args.model, args.feedback)
    # This is an unverified draft; the caller's pdflatex/Beamer sanity gate
    # must run before publishing anything as slides.tex.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pending = args.output.with_name(args.output.name + ".pending")
    pending.write_text(raw + "\n", encoding="utf-8")
    pending.replace(args.output)
    print(f"[slide-api] Received unverified Gemini Flash Beamer draft: {len(raw)} chars", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
