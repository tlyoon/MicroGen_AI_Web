"""Execute one MicroGen stage with shared Gemini lane protection.

Called only by three_pc_worker; the outer worker enforces independent watchdogs.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from gemini_lane import gemini_lane

REMOTE_STAGES = frozenset({"figures", "slides", "narration", "tts", "tts_qa"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--subchapter", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--chrome-port", type=int, default=9222)
    args = parser.parse_args(argv)

    cmd = [
        sys.executable, "-u", "-m", "selenium_pipeline",
        "--source-root", args.source_root,
        "--subchapter", args.subchapter,
        "--from-stage", args.stage,
        "--through-stage", args.stage,
        "--chrome-port", str(args.chrome_port),
    ]
    if args.stage in REMOTE_STAGES:
        # Selenium stages do not use gemini_lane internally. Holding one
        # cooperative ticket around the entire stage avoids simultaneous
        # Gemini calls across the distributed Chrome/API workers.
        with gemini_lane(f"selenium_{args.stage}", model="development-flash"):
            return subprocess.call(cmd)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
