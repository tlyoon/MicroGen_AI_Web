"""Authorize one post-repair retry ONLY for SHA-bound verified pre-Send failures.

Historical unknown Gemini requests must not be retransmitted. An old job is
eligible only after a different, independently verified repository revision,
the exact same source PDF digest, and a recorded model-menu failure before Send.
The next failed attempt on that revision cannot run again without another fix.
"""
from __future__ import annotations
from pathlib import Path
import re

PRE_SEND_SIGNATURES=(
    "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND",
    "PRE_SEND_MODEL_FALLBACK_NOT_AUTHORIZED_WITHOUT_EXACT_MENU_EVIDENCE",
)
UNCERTAIN_MARKERS=(
    "UNCERTAIN_SEND", "Gemini wait:", "PROVIDER_SEND_ACCEPTED",
    "Gemini submission registered", "response_captured",
    "IndeterminateSend", "UNKNOWN_PROVIDER_OUTCOME",
    "REQUEST_OUTCOME_UNCERTAIN", "TIMEOUT_OUTCOME_UNCERTAIN",
)

def verified_new_code_presend_retry(entry:dict, new_sha:str, log_dir:Path)->bool:
    """No state mutation, provider request or inferred historical outcome."""
    if (not isinstance(entry,dict) or entry.get("status")!="BLOCKED_PRE_SEND"
        or not isinstance(new_sha,str) or
        not re.fullmatch(r"[a-f0-9]{40}",new_sha)):
        return False
    tries=entry.get("attempts")
    if not isinstance(tries,list) or not tries:
        return False
    source=entry.get("source_sha256")
    if not isinstance(source,str) or not re.fullmatch(r"[a-f0-9]{64}",source):
        return False
    if any(not isinstance(x,dict) or x.get("source_sha256")!=source
           for x in tries):
        return False
    last=tries[-1]
    if (last.get("code_sha")==new_sha or
        not re.fullmatch(r"[a-f0-9]{40}",str(last.get("code_sha","")))
        or not isinstance(last.get("returncode"),int)
        or isinstance(last.get("returncode"),bool)
        or last["returncode"]==0):
        return False
    try:
        log=Path(last["log"])
        if (log.parent.resolve()!=Path(log_dir).resolve() or
            log.suffix!=".log" or not log.is_file()
            or log.stat().st_size>2_000_000):
            return False
        raw=log.read_text("utf8",errors="replace")
    except (OSError,TypeError,ValueError,KeyError):
        return False
    if (not all(marker in raw for marker in PRE_SEND_SIGNATURES)
        or any(marker in raw for marker in UNCERTAIN_MARKERS)):
        return False
    if not any(("GeminiModelError: "+marker) in raw
               for marker in PRE_SEND_SIGNATURES):
        return False
    return True
