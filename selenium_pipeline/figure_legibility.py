"""Detect dangerously small wide figures before Beamer slide acceptance.

Layout review is distinct from checking figure presence or completeness.
Image aspect ratio does not prove a composite, so this conservative gate
requests a redesign rather than claiming to count or crop subpanels.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

FRAME = re.compile(r"\\begin\s*\{frame\}[\s\S]*?\\end\s*\{frame\}")
IMAGE = re.compile(r"\\includegraphics(?P<opts>\s*\[[^\]]*\])?\s*\{(?P<name>[^{}]+)\}")
COLUMN = re.compile(
    r"\\begin\s*\{column\}(?:\[[^\]]*\])?\s*\{([^{}]+)\}"
    r"|\\column\s*\{([^{}]+)\}|\\end\s*\{column\}"
)
WIDTH = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*\\(?:textwidth|linewidth)\s*$")
DEFAULT_ASPECT_RATIO = 2.6
DEFAULT_MAX_COLUMN_FRACTION = 0.65


def _commented(source: str, pos: int) -> bool:
    line = source[source.rfind("\n", 0, pos) + 1:pos]
    for hit in re.finditer("%", line):
        n = 0
        j = hit.start() - 1
        while j >= 0 and line[j] == "\\":
            n += 1
            j -= 1
        if n % 2 == 0:
            return True
    return False


def _column_fraction(frame: str, pos: int) -> float | None:
    active = None
    for m in COLUMN.finditer(frame[:pos]):
        if _commented(frame, m.start()):
            continue
        if m.group(0).lstrip().startswith(r"\end"):
            active = None
        else:
            length = (m.group(1) or m.group(2) or "").strip()
            found = WIDTH.fullmatch(length)
            if length in (r"\textwidth", r"\linewidth"):
                active = 1.0
            else:
                active = float(found.group(1)) if found else 0.0
    return active

def _effective_width_fraction(options: str | None, column: float | None) -> float:
    """Estimate final figure width against full-frame text width.

    A return value of zero means an unrecognized graphic width and requires
    conservative review for a wide image.
    """
    text = options or ""
    m = re.search(
        r"(?i)(?:^|,)\s*width\s*=\s*(\d*\.?\d*)\s*\\(linewidth|textwidth)\b", text
    )
    if not m:
        return 0.0
    multiplier = float(m.group(1)) if m.group(1) else 1.0
    if m.group(2).lower() == "linewidth":
        return multiplier * (column if column is not None else 1.0)
    return multiplier



def audit_wide_figure_legibility(
    latex: str,
    image_root: Path,
    *,
    min_aspect_ratio: float = DEFAULT_ASPECT_RATIO,
    max_column_fraction: float = DEFAULT_MAX_COLUMN_FRACTION,
) -> list[dict]:
    """Return reproducible layout issues, never modify a LaTeX file or figure."""
    image_root = Path(image_root)
    issues = []
    for frame_index, frame in enumerate(FRAME.finditer(latex), 1):
        body = frame.group(0)
        for item in IMAGE.finditer(body):
            if _commented(body, item.start()):
                continue
            column_fraction = _column_fraction(body, item.start())
            filename = item.group("name").strip()
            relative = Path(filename)
            if relative.is_absolute() or ".." in relative.parts:
                issues.append({"reason": "unsafe_image_reference",
                               "frame": frame_index, "image": filename})
                continue
            path = image_root / relative
            if not path.is_file():
                # The existing required-graphics gate handles missing figures.
                continue
            try:
                with Image.open(path) as im:
                    w, h = im.size
            except (OSError, ValueError):
                issues.append({"reason": "unreadable_figure",
                               "frame": frame_index, "image": filename})
                continue
            if w <= 0 or h <= 0:
                issues.append({"reason": "unreadable_figure",
                               "frame": frame_index, "image": filename})
                continue
            aspect = w / h
            if aspect >= min_aspect_ratio:
                options = item.group("opts")
                width = _effective_width_fraction(
                    options[1:-1] if options else None, column_fraction
                )
                if width <= max_column_fraction:
                    issues.append({
                        "reason": ("wide_figure_too_small_in_column"
                                   if column_fraction is not None else "wide_figure_too_small"),
                        "frame": frame_index,
                        "image": filename,
                        "aspect_ratio": round(aspect, 3),
                        "column_width_fraction": column_fraction,
                        "effective_width_fraction": round(width, 3),
                        "recommendation": "dedicated_full_width_figure_frame",
                    })
    return issues


def legibility_retry_instruction(issues: list[dict]) -> str:
    """Tell the next bounded Gemini attempt how to repair the layout."""
    names = ", ".join(
        f"frame {x['frame']} image {x['image']!r}" for x in issues[:5]
    )
    return (
        "\nREQUIRED FIGURE LEGIBILITY CORRECTION: The prior candidate failed "
        "the source-image geometric layout gate: " + names + ". "
        "Do not place these wide illustrations in narrow Beamer columns. "
        "Keep their original image file and all scientific statements; "
        "use a dedicated full-width figure-focused frame immediately after "
        "the corresponding explanation frame, with width and height bounds "
        "and keepaspectratio. You may increase the slide count; provide "
        "complete updated Beamer LaTeX. Never crop panels, invent labels or "
        "omit the teaching points. This correction is mandatory."
    )
