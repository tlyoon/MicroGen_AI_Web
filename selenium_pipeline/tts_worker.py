from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .tts import _configure_cloud_adc_from_microvid, _gemini_failover_request


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Isolated Gemini TTS slide worker")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", choices=("gemini", "chirp3"), default="gemini")
    parser.add_argument("--model", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--number", type=int, required=True)
    parser.add_argument("--evidence-output", type=Path,
                        help="Optional sanitized request-id observation sidecar")
    parser.add_argument("--confirm-gemini-api-cost", action="store_true")
    parser.add_argument("--confirm-google-cloud-tts-cost", action="store_true")
    args = parser.parse_args(argv)
    from .tts_billing_guard import require_tts_cost_authorization
    require_tts_cost_authorization(
        args.provider, gemini_approved=args.confirm_gemini_api_cost,
        cloud_approved=args.confirm_google_cloud_tts_cost)

    # Worker output is always meant to be a new temporary WAV. Do not
    # spend credits if a direct invocation targets an existing/symlink file.
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(
            "Refusing to overwrite an existing TTS worker WAV: " + args.output.name)
    if args.evidence_output is not None:
        from .tts_worker_evidence import _assert_safe_paths, write_observation
        _assert_safe_paths(args.output, args.evidence_output)
    text = sys.stdin.read()
    try:
        if args.provider == "gemini":
            payload = _gemini_failover_request(text, args.number, args.model, args.voice)
        else:
            _configure_cloud_adc_from_microvid()
            from google.cloud import texttospeech
            from .tts import _chirp_say
            client = texttospeech.TextToSpeechClient()
            payload = _chirp_say(client, text, args.voice)
        with args.output.open("xb") as out:
            out.write(payload)
    except Exception as exc:
        if args.evidence_output is not None:
            write_observation(args.output, args.evidence_output,
                              outcome="exception", exception=exc)
        raise
    if args.evidence_output is not None:
        write_observation(args.output, args.evidence_output, outcome="success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
