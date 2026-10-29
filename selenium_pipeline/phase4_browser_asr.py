"""Explicit opt-in browser-only Gemini ASR using the existing owned Selenium tab.

Does NOT use google.genai, fallback to API, Whisper, or the expected narration
text. The UI response must be complete JSON and remains review-only.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from .series_gemini import _browser_request, decode_storyboard_response

MODEL_ID="gemini-flash-web-ui"


class AudioUnsupportedError(RuntimeError):
    """Gemini Flash web UI explicitly could not process attached WAV."""


class AmbiguousBrowserResponseError(RuntimeError):
    """Browser may have submitted the job but a verified reply is absent."""
PROMPT=(
    "Listen to the attached WAV recording, without any reference script. "
    "Transcribe only words truly audible in the recording, including spoken "
    "mathematical signs, variables, operators, and numerical values. "
    "Do not guess missing phrases or reformulate the audio. "
    "If you cannot listen to this WAV, explicitly return status unsupported. "
    "Return exactly one JSON object with two keys: "
    '{"status":"complete","transcript":"verbatim spoken words"} '
    "for an intelligible recording, or "
    '{"status":"unsupported","transcript":""} '
    "if file attachment/audio understanding is unavailable. "
    "Do not include the source script, explanations, or Markdown."
)

def _is_complete_json_reply(raw: str)->bool:
    try:
        data=decode_storyboard_response(raw)
        return (set(data)=={"status","transcript"} and
                data["status"] in ("complete","unsupported") and
                isinstance(data["transcript"],str))
    except Exception:
        return False

def parse_response(raw: str) -> str:
    try:
        data=decode_storyboard_response(raw)
    except Exception as exc:
        raise ValueError("Untrusted or incomplete Gemini web audio answer") from exc
    if set(data)!={"status","transcript"}:
        raise ValueError("Gemini web reply does not match ASR evidence schema")
    if data["status"]!="complete":
        raise AudioUnsupportedError(
            "Gemini web UI explicitly reported audio attachment unsupported")
    value=data["transcript"]
    if not isinstance(value,str) or len(value)>15000 or len(value.split())<2:
        raise ValueError("Empty, incomplete or oversized browser ASR transcript")
    if re.search(r"(sorry|cannot (access|listen|transcribe)|unable to (open|process)).{0,60}(file|wav|audio)",value,re.I):
        raise ValueError("Gemini responded with audio-unsupported apology")
    return value.strip()

def transcribe(path:Path,*,port:int=9222,wait_cap_s:int=180,
               transport=None)->str:
    path=Path(path).resolve()
    if (not path.is_file() or path.suffix.lower()!=".wav"
            or path.is_symlink() or path.stat().st_size>8_000_000):
        raise ValueError("Browser ASR requires one local WAV of at most 8 MB")
    if not 30<=wait_cap_s<=420 or not 1<=port<=65535:
        raise ValueError("Browser ASR port or wait bound invalid")
    if transport is None:
        from .series_bridge import SeriesBridgeError
        try:
            response=_browser_request(PROMPT,[path],port=port,
                                      wait_cap_s=wait_cap_s,
                                      min_chars=20,
                                      accept_fn=_is_complete_json_reply)
        except SeriesBridgeError as exc:
            # A submitted prompt may have an answer in the quarantine; do
            # not resubmit automatically or count a screenshot as a transcript.
            raise AmbiguousBrowserResponseError(
                "Browser reply was not verified; inspect quarantine before retry") from exc
    else:
        response=transport(PROMPT,[path])
    return parse_response(response)

if __name__=="__main__":
    arg=argparse.ArgumentParser()
    arg.add_argument("--wav",required=True,type=Path)
    arg.add_argument("--port",type=int,default=9222)
    arg.add_argument("--wait-cap",type=int,default=180)
    arg.add_argument("--confirm-live",action="store_true")
    a=arg.parse_args()
    if not a.confirm_live:raise SystemExit("Browser transcription requires --confirm-live")
    print(json.dumps({"status":"REVIEW_ONLY_NO_ACADEMIC_APPROVAL",
                      "transcript":transcribe(a.wav,port=a.port,
                                              wait_cap_s=a.wait_cap)},ensure_ascii=False))
