"""Add safe bounds to Beamer figure placement before candidate compilation."""
from __future__ import annotations

import re

FRAMES = re.compile(r"\\begin\s*\{frame\}[\s\S]*?\\end\s*\{frame\}")
GRAPHICS = re.compile(r"\\includegraphics(?P<opts>\s*\[[^\]]*\])?\s*\{(?P<name>[^{}]+)\}")

def bound_beamer_graphics(source: str) -> tuple[str, int]:
    """Return (TeX, changed_graphic_count), preserving other source text."""
    count = 0
    def rewrite_frame(frame: re.Match) -> str:
        nonlocal count
        body = frame.group(0)

        def rewrite_graphic(match: re.Match) -> str:
            nonlocal count
            prefix = body[:match.start()]
            if "%" in prefix.rsplit("\n", 1)[-1]:
                return match.group(0)
            options_raw = match.group("opts")
            options = [p.strip() for p in (options_raw[1:-1] if options_raw else "").split(",") if p.strip()]
            column_tokens = list(re.finditer(r"\\(?:begin|end)\s*\{column\}", prefix))
            in_column = bool(column_tokens and "begin" in column_tokens[-1].group(0))
            def has_option(name: str) -> bool:
                return any(re.match(r"(?i)^" + name + r"(?:\s*=|$)", part) for part in options)

            if in_column:
                options = [
                    r"width=\linewidth" if re.match(r"(?i)^width\s*=", p)
                    and (r"\textwidth" in p or r"\paperwidth" in p) else p
                    for p in options
                ]
            if not has_option("width"):
                options.append(r"width=\linewidth")
            if not has_option("height"):
                options.append(r"height=0.52\textheight" if in_column else r"height=0.65\textheight")
            if not has_option("keepaspectratio"):
                options.append("keepaspectratio")
            output = r"\includegraphics[" + ",".join(options) + "]{" + match.group("name") + "}"
            if output != match.group(0):
                count += 1
            return output

        return GRAPHICS.sub(rewrite_graphic, body)

    result = FRAMES.sub(rewrite_frame, source)
    return result, count
