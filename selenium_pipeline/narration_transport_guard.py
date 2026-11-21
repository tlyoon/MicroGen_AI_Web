"""Source-and-slide-bound Gemini narration API request claims.

Reuse the previously verified single-request claim mechanics, but isolate
narration from slide-generation receipts. The instruction fingerprint binds
both textbook source PDF SHA and the compiled slides PDF SHA. Unknown API
outcomes must not be automatically resent with identical credentials.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from .slide_transport_guard import SlideAttemptClaim, IndeterminateSend


def narration_api_claim(
    source_pdf: Path, slides_pdf: Path, prompt: Path, instruction: str,
    *, ordinal: int = 1, root: Path | None = None,
) -> SlideAttemptClaim:
    source = Path(source_pdf)
    if not source.is_file() or not source.read_bytes().startswith(b"%PDF"):
        raise ValueError("Missing authentic narration textbook source PDF")
    if not Path(slides_pdf).is_file() or not Path(slides_pdf).read_bytes().startswith(b"%PDF"):
        raise ValueError("Missing authentic compiled slide PDF")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    private_root = root or (
        Path(os.getenv("LOCALAPPDATA") or Path.home() / ".cache")
        / "Microvid" / "narration_send_claims"
    )
    return SlideAttemptClaim(
        Path(slides_pdf), Path(prompt),
        "narration-api-v1\ntextbook-source-sha256=" + source_sha + "\n" + instruction,
        backend="api", ordinal=ordinal, root=private_root,
    )
