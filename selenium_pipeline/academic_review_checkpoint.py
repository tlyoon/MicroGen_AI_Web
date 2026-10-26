"""Crash-safe, local-only Gemini academic-review submission checkpoints.

Never resend an ambiguous request. The claim is written to disk BEFORE the
browser submit callback, so a process crash, timeout, re-login or new session
cannot repeat an unknown already-sent request. Recovery only consumes saved
model-response evidence. No text or academic approval is manufactured.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

STATE_NAME="request_state.json"
CLAIM_NAME="dispatch_attempted.claim"
VALID_STATES={"PREPARED_NOT_SENT","SUBMITTED_OR_UNCERTAIN",
              "NO_RESPONSE_UNRESOLVED","MODEL_REPLY_OBSERVED_UNVALIDATED",
              "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED","REJECTED_RESPONSE_UNTRUSTED",
              "LEGACY_SENT_NO_RESPONSE"}
MAX_RAW=1_800_000

class ReviewCheckpointError(ValueError):
    pass

def _require(ok:bool,detail:str):
    if not ok: raise ReviewCheckpointError(detail)

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _canon(value)->bytes:
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf8")

def _write_new(path:Path,value:dict):
    with path.open("x",encoding="utf8") as f:
        json.dump(value,f,indent=2,ensure_ascii=False,sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())

def _update(path:Path,value:dict):
    # This is not a submission lock: CLAIM_NAME is the durable write-once lock.
    tmp=path.with_name(path.name+".new")
    with tmp.open("x",encoding="utf8") as f:
        json.dump(value,f,indent=2,ensure_ascii=False,sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp,path)

def fingerprint(*,request_text:str,source_hashes:dict,review_mode:str,
                revised_text_hashes:list[str]|None=None)->str:
    _require(type(request_text) is str and bool(request_text.strip()),
             "Exact bounded Gemini prompt required")
    _require(type(source_hashes) is dict and set(source_hashes)=={
        "source.pdf","slides.pdf","script.txt"}, "Three original hashes required")
    _require(all(type(v) is str and len(v)==64 and
                 all(c in "0123456789abcdef" for c in v)
                 for v in source_hashes.values()),
             "Exact source SHA256 required")
    _require(review_mode in {"INITIAL_REVIEW","INDEPENDENT_CHALLENGE"},
             "Unknown independent review mode")
    extra=revised_text_hashes or []
    _require(type(extra) is list and all(type(x) is str and len(x)==64 for x in extra),
             "Bounded revised utterance hashes required")
    return _sha(_canon({"prompt_sha256":_sha(request_text.encode("utf8")),
                        "originals":source_hashes,"review_mode":review_mode,
                        "revised_text_sha256":extra}))

def _source_proof(folder:Path,expected:dict)->dict:
    folder=Path(folder).absolute()
    _require(folder.is_dir() and not folder.is_symlink(),
             "Actual source folder required")
    actual={}
    for name in ("source.pdf","slides.pdf","script.txt"):
        path=folder/name
        _require(path.is_file() and not path.is_symlink(),
                 "Missing or linked original "+name)
        actual[name]=_sha(path.read_bytes())
    _require(actual==expected,"Protected source changed from checkpoint")
    return actual

def _load(checkpoint:Path)->dict:
    path=Path(checkpoint)/STATE_NAME
    _require(path.is_file() and not path.is_symlink(),
             "Missing request checkpoint; refuse resend")
    state=json.loads(path.read_text(encoding="utf8"))
    _require(type(state) is dict and state.get("schema_version")==1
             and state.get("status") in VALID_STATES
             and type(state.get("request_fingerprint")) is str,
             "Invalid or untrusted request checkpoint")
    return state

def prepare(*,checkpoint:Path,original_folder:Path,request_text:str,
            source_hashes:dict,review_mode:str,
            revised_text_hashes:list[str]|None=None)->dict:
    root=Path(checkpoint).absolute()
    original=Path(original_folder).absolute()
    _require(root!=original and not root.is_relative_to(original)
             and root.parent.is_dir() and not root.parent.is_symlink(),
             "Use an independent existing AppData parent, not original folder")
    actual=_source_proof(original,source_hashes)
    digest=fingerprint(request_text=request_text,source_hashes=actual,
                       review_mode=review_mode,revised_text_hashes=revised_text_hashes)
    if root.exists():
        found=_load(root)
        _require(found["request_fingerprint"]==digest,
                 "Existing window uses different request; no silent override")
        return found
    root.mkdir(mode=0o700)
    state={"schema_version":1,"request_fingerprint":digest,
           "prompt_sha256":_sha(request_text.encode("utf8")),
           "source_sha256":actual["source.pdf"],
           "slides_sha256":actual["slides.pdf"],
           "script_sha256":actual["script.txt"],
           "revised_text_sha256":revised_text_hashes or [],
           "review_mode":review_mode,
           "status":"PREPARED_NOT_SENT",
           "submission_may_have_occurred":False,
           "can_auto_retry":False,
           "academic_approval":False,"tts_authorized":False,
           "student_publication_authorized":False}
    _write_new(root/STATE_NAME,state)
    return state

def mark_submission_maybe(checkpoint:Path,*,expected_fingerprint:str)->dict:
    root=Path(checkpoint).absolute()
    state=_load(root)
    _require(state["request_fingerprint"]==expected_fingerprint,
             "Different corrected text / source / review mode")
    _require(state["status"]=="PREPARED_NOT_SENT",
             "Request already attempted, failed, or imported; never auto-resubmit")
    # Reserve across ALL request windows under the same AppData parent, not
    # merely the same child directory. A new chat/checkpoint directory with
    # identical prompt and source must not bypass the one-submit contract.
    # If a crash occurs between either durable exclusive claim, conservatively
    # treat the request as possibly submitted. A different review mode or a
    # specifically changed authorization-bound prompt yields a new identity.
    index=root.parent/".microgen_academic_review_once"
    index.mkdir(exist_ok=True)
    with (index/(expected_fingerprint+".claim")).open("x",encoding="utf8") as f:
        f.write("ONCE-ONLY academic Gemini send claim\n")
        f.flush()
        os.fsync(f.fileno())
    with (root/CLAIM_NAME).open("x",encoding="utf8") as f:
        f.write(expected_fingerprint+"\n")
        f.flush()
        os.fsync(f.fileno())
    state.update(status="SUBMITTED_OR_UNCERTAIN",
                 submission_may_have_occurred=True)
    _update(root/STATE_NAME,state)
    return state

def record_observation(checkpoint:Path,*,raw:str,
                       expected_fingerprint:str)->dict:
    root=Path(checkpoint).absolute()
    state=_load(root)
    _require(state["request_fingerprint"]==expected_fingerprint
             and (root/CLAIM_NAME).is_file()
             and state["status"] in {"SUBMITTED_OR_UNCERTAIN",
                                    "NO_RESPONSE_UNRESOLVED"},
             "No previously-claimed matching browser request")
    _require(type(raw) is str and len(raw)<=MAX_RAW,
             "Oversized or missing owned response")
    data=raw.encode("utf8")
    with (root/"model_response_untrusted.txt").open("xb") as f:
        f.write(data);f.flush();os.fsync(f.fileno())
    state.update(status=("MODEL_REPLY_OBSERVED_UNVALIDATED" if raw.strip()
                         else "NO_RESPONSE_UNRESOLVED"),
                 response_sha256=_sha(data),
                 response_length_chars=len(raw),
                 can_auto_retry=False)
    _update(root/STATE_NAME,state)
    return state

def validate_saved(*,checkpoint:Path,expected_fingerprint:str,validator)->dict:
    root=Path(checkpoint).absolute()
    state=_load(root)
    _require(state["request_fingerprint"]==expected_fingerprint
             and state["status"] in {"MODEL_REPLY_OBSERVED_UNVALIDATED",
                                     "REJECTED_RESPONSE_UNTRUSTED",
                                     "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"}
             and (root/CLAIM_NAME).is_file(),
             "Cannot accept absent or unsent model text")
    path=root/"model_response_untrusted.txt"
    _require(path.is_file() and not path.is_symlink()
             and path.stat().st_size<=MAX_RAW*4,
             "Original model reply missing or replaced")
    raw=path.read_text(encoding="utf8")
    _require(raw.strip() and _sha(raw.encode("utf8"))==state.get("response_sha256")
             and len(raw)==state.get("response_length_chars"),
             "Reply is empty, truncated or changed")
    _require(callable(validator),"Independent source validator required")
    try:
        result=validator(raw)
        _require(type(result) is dict and
                 result.get("student_publication_authorized") is False
                 and result.get("academic_mathematics_independently_verified") is False,
                 "Single pass must not self-approve academic publication")
    except Exception:
        state["status"]="REJECTED_RESPONSE_UNTRUSTED"
        _update(root/STATE_NAME,state)
        raise
    state["status"]="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"
    state["verified_reply_sha256"]=_sha(raw.encode("utf8"))
    # Validation result is returned to caller; one source-cited AI pass is
    # explicitly NOT mathematical consensus or a production permit.
    _update(root/STATE_NAME,state)
    return result

def submit_once(*,checkpoint:Path,original_folder:Path,
                request_text:str,source_hashes:dict,review_mode:str,
                transport,validator,revised_text_hashes:list[str]|None=None)->dict:
    state=prepare(checkpoint=checkpoint,original_folder=original_folder,
                  request_text=request_text,source_hashes=source_hashes,
                  review_mode=review_mode,
                  revised_text_hashes=revised_text_hashes)
    digest=state["request_fingerprint"]
    mark_submission_maybe(checkpoint,expected_fingerprint=digest)
    try:
        raw=transport(request_text,
                      [Path(original_folder)/"source.pdf",
                       Path(original_folder)/"slides.pdf"])
    except Exception:
        # NO resend; callback may have sent prompt before error. Keep
        # SUBMITTED_OR_UNCERTAIN permanently until same-response recovery.
        raise
    record_observation(checkpoint,raw=raw,expected_fingerprint=digest)
    return validate_saved(checkpoint=checkpoint,
                          expected_fingerprint=digest,validator=validator)

def legacy_no_response(*,legacy_window:Path,checkpoint:Path)->dict:
    """Import 2026-10-26 pre-existing no-response request WITHOUT dispatch.

    Imports only request hashes/status; no password, prompt or browser access.
    """
    old=Path(legacy_window).absolute()
    failed=json.loads((old/"failure_no_retry.json").read_text(encoding="utf8"))
    request=json.loads((old/"request_sha256.json").read_text(encoding="utf8"))
    window=json.loads((old/"review_window.json").read_text(encoding="utf8"))
    _require(failed.get("status")=="SINGLE_AUTHORIZED_WINDOW_EXHAUSTED"
             and failed.get("possible_browser_submission") is True
             and failed.get("math_approval") is False
             and request.get("attached_source_sha256")==window.get("original_source_sha256")
             and type(request.get("prompt_sha256")) is str
             and len(request["prompt_sha256"])==64,
             "Legacy no-response evidence not verified")
    root=Path(checkpoint).absolute()
    _require(not root.exists() and root.parent.is_dir()
             and not root.is_relative_to(old),"Fresh isolated import required")
    root.mkdir()
    state={"schema_version":1,"request_fingerprint":request["prompt_sha256"],
           "prompt_sha256":request["prompt_sha256"],
           "source_sha256":window["original_source_sha256"],
           "review_mode":"INITIAL_REVIEW",
           "status":"LEGACY_SENT_NO_RESPONSE",
           "submission_may_have_occurred":True,
           "model_response_chars":0,
           "can_auto_retry":False,
           "academic_approval":False,"tts_authorized":False,
           "student_publication_authorized":False,
           "legacy_import":True}
    _write_new(root/STATE_NAME,state)
    # Even if someone edits the JSON to PREPARED, O_EXCL prevents submission.
    with (root/CLAIM_NAME).open("x",encoding="utf8") as f:
        f.write("LEGACY_NO_RESPONSE_NEVER_AUTO_RESEND\n")
    return state

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--import-legacy",type=Path)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--status",action="store_true")
    a=p.parse_args(argv)
    if a.import_legacy:
        result=legacy_no_response(legacy_window=a.import_legacy,
                                  checkpoint=a.checkpoint)
    elif a.status:result=_load(a.checkpoint)
    else:p.error("Choose --import-legacy or --status; never submits online")
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
