"""Offline geometry extraction, static PDF cleaning, WAV timing and highlight previews.

All outputs go to explicit new paths; no generation job is launched.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pdf_element_geometry import (
    ElementGeometryError, extract_element_geometry, strip_instrumentation_links,
)
from .speech_segment_timing import build_segment_timeline
from .highlight_frames import render_highlight_frames


def _load(path: Path):
    if not path.is_file() or path.stat().st_size > 10_000_000:
        raise ValueError("Missing or oversized JSON input")
    def pairs(items):
        found={}
        for k,v in items:
            if k in found:
                raise ValueError(f"Duplicate JSON key: {k}")
            found[k]=v
        return found
    return json.loads(path.read_text(encoding="utf-8-sig"),object_pairs_hook=pairs)


def _new_json(path: Path, data: dict | list) -> None:
    if not path.parent.is_dir():
        raise ValueError("Output directory does not exist")
    with path.open("x",encoding="utf-8") as file:
        json.dump(data,file,ensure_ascii=False,indent=2)
        file.write("\n")


def main(argv=None):
    p=argparse.ArgumentParser(description="Offline PDF geometry and segment-level highlighting")
    p.add_argument("action",choices=("extract","clean","timeline","preview"))
    p.add_argument("--pdf",type=Path,help="Instrumented Beamer PDF or cleaned PDF")
    p.add_argument("--storyboard",type=Path)
    p.add_argument("--geometry",type=Path)
    p.add_argument("--manifest",type=Path,help="Ordered speech chunk WAV manifest")
    p.add_argument("--audio-root",type=Path)
    p.add_argument("--combined-wav",type=Path)
    p.add_argument("--timeline",type=Path)
    p.add_argument("--receipt",type=Path)
    p.add_argument("--output",type=Path,help="New geometry, clean PDF or output directory")
    a=p.parse_args(argv)
    try:
        if not a.output or not a.pdf and a.action in ("extract","clean","preview"):
            raise ValueError("Required --output and, for PDF actions, --pdf")
        if a.action=="extract":
            if not a.storyboard:
                raise ValueError("Required --storyboard")
            data=extract_element_geometry(a.pdf,_load(a.storyboard))
            _new_json(a.output,data)
            print("Verified rendered element geometry (source fidelity unreviewed).")
        elif a.action=="clean":
            if not a.geometry:
                raise ValueError("Required --geometry")
            data=strip_instrumentation_links(a.pdf,a.output,_load(a.geometry))
            print(json.dumps(data))
        elif a.action=="timeline":
            if not all((a.storyboard,a.geometry,a.manifest,a.audio_root,a.combined_wav,a.receipt)):
                raise ValueError("Required --storyboard, --geometry, --manifest, --audio-root, --combined-wav, --receipt")
            if any(path.exists() for path in (a.output,a.receipt,a.combined_wav)):
                raise ValueError("Refusing to overwrite any existing output")
            data,receipt=build_segment_timeline(
                _load(a.storyboard),_load(a.geometry),_load(a.manifest),
                audio_root=a.audio_root,output_wav=a.combined_wav,
            )
            _new_json(a.output,data)
            _new_json(a.receipt,receipt)
            print("WAV-chunk timing derived (spoken content and word timing unverified).")
        else:
            if not all((a.storyboard,a.geometry,a.timeline)):
                raise ValueError("Required --storyboard, --geometry, --timeline")
            result=render_highlight_frames(
                a.pdf,_load(a.storyboard),_load(a.geometry),_load(a.timeline),
                output_dir=a.output,
            )
            print(f"Rendered {len(result)} semantic highlight preview frames.")
        return 0
    except (ValueError,OSError,KeyError) as exc:
        p.exit(2,f"Geometry/timing blocked: {exc}\n")


if __name__=="__main__":
    raise SystemExit(main())
