"""TTS-friendly scientific speech normalization.

Adapted from tlyoon/microcredential-video-generator. This is deliberately
conservative: it normalizes common notation for speech without rewriting the
scientific content.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

_DEFAULT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("±", " plus or minus "),
    ("×", " times "),
    ("÷", " divided by "),
    ("π", " pi "),
    ("Δ", " delta "),
    ("σ", " sigma "),
    ("Ω", " ohms "),
    ("°C", " degrees Celsius "),
    ("%", " percent "),
)


def normalize_scientific_speech(
    text: str,
    extra_replacements: Mapping[str, str] | None = None,
) -> str:
    if not text:
        return ""

    out = str(text)
    replacements = list(_DEFAULT_REPLACEMENTS)
    if extra_replacements:
        replacements.extend((str(k), str(v)) for k, v in extra_replacements.items())
    for source, target in replacements:
        out = out.replace(source, target)

    unit_patterns = (
        (r"\bkg\s*/\s*m(?:\^?3|³)\b", " kilograms per cubic metre "),
        (r"\bkg\s+m(?:\^\s*-?3|⁻³)\b", " kilograms per cubic metre "),
        (r"\bg\s*/\s*cm(?:\^?3|³)\b", " grams per cubic centimetre "),
        (r"\bg\s+cm(?:\^\s*-?3|⁻³)\b", " grams per cubic centimetre "),
        (r"\bm\s*/\s*s(?:\^?2|²)\b", " metres per second squared "),
        (r"\bm\s+s(?:\^\s*-?2|⁻²)\b", " metres per second squared "),
        (r"\bm\s*/\s*s\b", " metres per second "),
        (r"\bm\s+s(?:\^\s*-?1|⁻¹)\b", " metres per second "),
        (r"\bcm\s*/\s*s\b", " centimetres per second "),
        (r"\bmm\b", " millimetres "),
        (r"\bcm\b", " centimetres "),
    )
    for pattern, replacement in unit_patterns:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)

    out = re.sub(r"\\mathrm\{([^{}]+)\}", r"\1", out)
    out = re.sub(r"\\text\{([^{}]+)\}", r"\1", out)
    out = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1 divided by \2", out)
    out = re.sub(r"([A-Za-z0-9)]+)\s*\^\s*2\b", r"\1 squared", out)
    out = re.sub(r"([A-Za-z0-9)]+)\s*\^\s*3\b", r"\1 cubed", out)
    out = out.replace("²", " squared ").replace("³", " cubed ")

    out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out
