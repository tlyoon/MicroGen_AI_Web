"""Read-only full original MicroGen lecture acceptance audit."""
import argparse,json
from pathlib import Path
from .unified_original_lecture_acceptance import inspect_original_multimedia_acceptance
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--original-folder",required=True,type=Path)
 p.add_argument("--queue-root",required=True,type=Path)
 p.add_argument("--candidate",type=Path)
 args=p.parse_args(argv)
 print(json.dumps(inspect_original_multimedia_acceptance(
     original_folder=args.original_folder,queue_root=args.queue_root,
     candidate=args.candidate),indent=2,sort_keys=True))
 return 0
if __name__=="__main__":raise SystemExit(main())
