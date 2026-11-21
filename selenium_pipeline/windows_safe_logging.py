"""Provider-safe console output on Windows CP1252; never crash after Send."""
from __future__ import annotations

import sys
import time


def safe_log(message: str, level: str = "INFO", *, stream=None) -> None:
    """Escape only non-encodable output characters without mutating evidence."""
    output = stream if stream is not None else sys.stdout
    when = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{when}] [{level}] {message}"
    encoding = getattr(output, "encoding", None) or "utf-8"
    try:
        line.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        line = line.encode("ascii", errors="backslashreplace").decode("ascii")
    print(line, file=output, flush=True)
