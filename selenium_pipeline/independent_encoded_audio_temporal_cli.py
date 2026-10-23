"""Read-only independent sample-level audit of preserved original WAV in MP4.

No modification of original teaching assets and no mathematical or
spoken-word/audio voice/student publication certification.
"""
import argparse,json
from pathlib import Path
from .independent_encoded_audio_temporal_audit import audit_encoded_original_pcm
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--original-folder",required=True,type=Path)
 p.add_argument("--review-folder",required=True,type=Path)
 a=p.parse_args(argv)
 print(json.dumps(audit_encoded_original_pcm(original_folder=a.original_folder,
                                             review_folder=a.review_folder),
                  sort_keys=True,indent=2))
 return 0
if __name__=="__main__":raise SystemExit(main())
