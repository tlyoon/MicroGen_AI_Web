"""Isolated worker for one Gemini TTS-fidelity audio inspection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .tts_fidelity import _inspect_audio_direct


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args(argv)

    request = json.loads(args.request.read_text(encoding="utf-8"))
    wav_path = Path(request["wav_path"])
    script = str(request["script"])
    model = str(request["model"])
    output_path = Path(request["output_path"])

    payload = _inspect_audio_direct(wav_path, script, model=model)
    temporary = output_path.with_suffix(".json.partial")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
