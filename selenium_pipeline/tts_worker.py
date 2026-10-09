from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .tts import _gemini_failover_request


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Isolated Gemini TTS slide worker")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--number", type=int, required=True)
    args = parser.parse_args(argv)

    text = sys.stdin.read()
    payload = _gemini_failover_request(text, args.number, args.model, args.voice)
    args.output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
