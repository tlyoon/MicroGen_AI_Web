from __future__ import annotations
import argparse
import json
from pathlib import Path
from .tts_voice_consistency import _inspect_direct

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--request", type=Path, required=True)
    a = p.parse_args(argv)
    req = json.loads(a.request.read_text(encoding="utf-8"))
    result = _inspect_direct(
        Path(req["candidate"]),
        [Path(x) for x in req["references"]],
        str(req["model"]),
    )
    out = Path(req["output"])
    tmp = out.with_suffix(".json.partial")
    tmp.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
