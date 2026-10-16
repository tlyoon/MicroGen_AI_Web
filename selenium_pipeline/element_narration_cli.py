"""Stage explicit element-level real WAVs for isolated review rendering."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .element_narration_stage import prepare

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--source-pdf",required=True,type=Path)
    p.add_argument("--slides-pdf",required=True,type=Path)
    p.add_argument("--authored-json",required=True,type=Path)
    p.add_argument("--recorded-audio",required=True,type=Path)
    p.add_argument("--destination",required=True,type=Path)
    a=p.parse_args(argv)
    result=prepare(source_pdf=a.source_pdf,slides_pdf=a.slides_pdf,
         authored_json=a.authored_json,recorded_audio=a.recorded_audio,
         destination=a.destination)
    print(json.dumps(result,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
