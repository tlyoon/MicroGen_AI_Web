"""Run a source-bound offline multipart highlight REVIEW preview.

No production certificate, no Gemini, no TTS request, no student publication.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .series_review_preview import PreviewSeriesError, render_review_series

def main(argv=None):
    ap=argparse.ArgumentParser(description="Render review-only highlighted lesson parts")
    ap.add_argument("--source-pdf",required=True,type=Path)
    ap.add_argument("--prepared-parts",required=True,type=Path)
    ap.add_argument("--output-root",required=True,type=Path)
    args=ap.parse_args(argv)
    try:
        result=render_review_series(source_pdf=args.source_pdf,
               inputs_root=args.prepared_parts,output_root=args.output_root)
    except (PreviewSeriesError,ValueError,OSError,RuntimeError) as exc:
        print("REVIEW_PREVIEW_FAILED:",str(exc))
        return 2
    print(json.dumps({"status":result["status"],
                      "part_durations_s":[p["encoded_mp4_seconds"] for p in result["parts"]],
                      "production_approved":False,"student_published":False},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
