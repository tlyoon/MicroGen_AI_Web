"""Explicit operator commands for Phase 4 isolated Gemini/TTS series adapters.

No command modifies source.pdf or legacy runner outputs. Live model calls
must be separately selected by action and --confirm-live.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .series_bridge import (
    SeriesBridgeError,read_json,prepare_authoring_bundle,stage_tts_job,
    accept_legacy_tts_batch,invoke_existing_tts,write_json_new,
)
from .series_gemini import request_storyboard_candidate


def main(argv=None):
    p=argparse.ArgumentParser(description="Isolated physics/math multipart Gemini+TTS integration")
    p.add_argument("action",choices=("prepare","candidate","stage-tts","run-tts","accept-wavs"))
    p.add_argument("--source-root",type=Path)
    p.add_argument("--source-pdf",type=Path)
    p.add_argument("--outline",type=Path)
    p.add_argument("--plan",type=Path)
    p.add_argument("--domain")
    p.add_argument("--profile-file",type=Path)
    p.add_argument("--part",help="Approved video part, e.g. part_01")
    p.add_argument("--authoring-folder",type=Path)
    p.add_argument("--storyboard",type=Path)
    p.add_argument("--review-receipt",type=Path)
    p.add_argument("--tts-folder",type=Path)
    p.add_argument("--output",type=Path,help="New folder or JSON file")
    p.add_argument("--provider",choices=("gemini","chirp3"),default="gemini")
    p.add_argument("--model",default="gemini-3.8-flash-lite-tts")
    p.add_argument("--voice",default="Kore")
    p.add_argument("--chrome-port",type=int,default=9222)
    p.add_argument("--confirm-live",action="store_true",
                   help="Explicitly authorize spending time/credits on a live Gemini/TTS call")
    args=p.parse_args(argv)

    try:
        live=args.action in ("candidate","run-tts")
        if live and not args.confirm_live:
            raise SeriesBridgeError("Live transport requires explicit --confirm-live")
        if args.action in ("run-tts","accept-wavs") and args.output and args.output.exists():
            raise SeriesBridgeError("Refusing to overwrite existing WAV manifest")
        if args.action in ("prepare","candidate","stage-tts"):
            essential=(args.source_root,args.source_pdf,args.outline,
                       args.plan,args.domain,args.part)
            if any(x is None for x in essential):
                raise SeriesBridgeError(
                    "Need source-root, source-pdf, reviewed outline, plan, domain and part"
                )
            kw=dict(
                source_root=args.source_root,source_pdf=args.source_pdf,
                outline=read_json(args.outline),plan=read_json(args.plan),
                domain=args.domain,part_id=args.part,profile_file=args.profile_file,
            )
        if args.action=="prepare":
            if not args.output:
                raise SeriesBridgeError("Prepare requires --output NEW folder")
            result=prepare_authoring_bundle(**kw,output_dir=args.output)
        elif args.action=="candidate":
            if not args.authoring_folder or not args.output:
                raise SeriesBridgeError("Candidate requires authoring-folder and output JSON")
            result=request_storyboard_candidate(
                **kw,authoring_folder=args.authoring_folder,
                candidate_path=args.output,chrome_port=args.chrome_port,
            )
        elif args.action=="stage-tts":
            if not all((args.storyboard,args.review_receipt,args.output)):
                raise SeriesBridgeError("Stage TTS requires storyboard, review-receipt and output folder")
            result=stage_tts_job(
                **kw,storyboard=read_json(args.storyboard),
                review_receipt=read_json(args.review_receipt),
                destination=args.output,
            )
        elif args.action in ("run-tts","accept-wavs"):
            if not args.tts_folder:
                raise SeriesBridgeError("Need --tts-folder from a reviewed staged TTS job")
            board=read_json(args.tts_folder/"storyboard.json")
            if args.action=="run-tts":
                result={
                    "status":"real_tts_completed_fidelity_QA_pending",
                    "wav_segment_manifest":invoke_existing_tts(
                        tts_dir=args.tts_folder,storyboard=board,
                        provider=args.provider,model=args.model,voice=args.voice,
                    ),
                }
            else:
                result={
                    "status":"tts_wav_structure_verified_spoken_audio_unreviewed",
                    "wav_segment_manifest":accept_legacy_tts_batch(args.tts_folder,board),
                }
            if args.output:
                write_json_new(args.output,result["wav_segment_manifest"])
        else:
            raise SeriesBridgeError("Unsupported action")
        print(json.dumps(result,indent=2))
        return 0
    except (SeriesBridgeError,ValueError,OSError,KeyError) as exc:
        p.exit(2,f"Series integration blocked: {exc}\n")


if __name__=="__main__":
    raise SystemExit(main())
