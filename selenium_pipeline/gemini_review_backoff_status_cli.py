"""Read-only status of a persisted local Gemini retry checkpoint.

This never submits prompts, creates tasks, resets attempt quotas, modifies
originals or incurs provider charges.
"""
import argparse,json
from pathlib import Path
from .gemini_review_backoff_checkpoint import inspect

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint",required=True,type=Path)
    ap.add_argument("--original-folder",required=True,type=Path)
    args=ap.parse_args(argv)
    print(json.dumps(inspect(checkpoint=args.checkpoint,
                             original_folder=args.original_folder),
                     indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
