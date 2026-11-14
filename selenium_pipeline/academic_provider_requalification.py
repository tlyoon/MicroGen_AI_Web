"""One source-free Gemini browser response probe before resuming G2 claims.

Normal G2 academic-review dispatch uses this only AFTER two distinct
source-owned requests failed to produce attributable complete replies and
their finite cooldown expired. Requalification never uploads a textbook,
touches a source claim or issues a second uncertain browser Send.

Every UTC calendar day/source/model has at most ONE new nonce-specific
provider diagnostic. A repeated invocation revalidates the first immutable
result or reports its unresolved claim without resubmitting. A good reply
alone does NOT certify any academic utterance, source geometry, audio or G2.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import time
from datetime import datetime,timezone


class AcademicProbeError(ValueError):
    pass


ROOT=".microgen_academic_response_requalification"
_REGISTERED=frozenset((
    "NEW_USER_TURN_AND_COMPOSER_CLEARED",
    "NEW_MODEL_RESPONSE_AND_COMPOSER_CLEARED",
    "NEW_CONVERSATION_ROUTE_AND_COMPOSER_CLEARED",
))


def _must(ok,message):
    if not ok:
        raise AcademicProbeError(message)


def _read(path:Path)->dict:
    _must(path.is_file() and not path.is_symlink()
          and 0<path.stat().st_size<=4096,"Unsafe academic health receipt")
    value=json.loads(path.read_text(encoding="utf8"))
    _must(type(value) is dict,"Invalid academic health receipt")
    return value


def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base(checkpoint_parent:Path,source_sha:str,family:str)->Path:
    parent=Path(checkpoint_parent).absolute()
    _must(parent.is_dir() and not parent.is_symlink()
          and re.fullmatch(r"[0-9a-f]{64}",str(source_sha)) is not None
          and family in ("flash","pro"),
          "Invalid academic response health scope")
    base=parent/ROOT
    _must(not base.is_symlink(),"Unsafe health root")
    scoped=base/source_sha/family
    _must(not scoped.is_symlink() and not scoped.parent.is_symlink(),
          "Unsafe model health folder")
    return scoped


def _day(now:float)->str:
    _must(type(now) in (int,float) and 0<=now<=4102444800,
          "Invalid bounded academic health time")
    return datetime.fromtimestamp(now,timezone.utc).strftime("%Y%m%d")


def _expected(*,source_sha:str,family:str,day:str)->tuple[str,str]:
    # Unique stable synthetic prompt per day/source/model. Never include
    # original figure, equation, narration or any user document.
    nonce=hashlib.sha256(
        ("microgen-academic-probe-v1:"+source_sha+":"+family+":"+day)
        .encode("ascii")).hexdigest()[:20]
    prompt=(
        "MicroGen source-free Gemini browser response-health diagnostic. "
        "No documents or original source are attached. "
        "Return only the exact JSON object below, no explanation or fences: "
        +json.dumps({"microgen_health":"ok","nonce":nonce},
                    separators=(",",":"),sort_keys=True)
    )
    return prompt,nonce


def _paths(*,checkpoint_parent:Path,source_sha:str,family:str,
           day:str)->tuple[Path,Path]:
    home=_base(checkpoint_parent,source_sha,family)/day
    _must(re.fullmatch(r"20[0-9]{6}",day) is not None,
          "Invalid UTC academic health slot")
    _must(not home.is_symlink(),"Unsafe academic health slot")
    return home/"claim.json",home/"result.json"


def verify_result(*,result_path:Path,checkpoint_parent:Path,
                  source_sha:str,family:str)->dict:
    """Recheck physical original no-Send claim and independently typed reply."""
    result_path=Path(result_path).absolute()
    base=_base(checkpoint_parent,source_sha,family)
    _must(result_path.parent.parent==base and result_path.name=="result.json",
          "Health result belongs to unrelated scope")
    claim_path=result_path.parent/"claim.json"
    claim=_read(claim_path)
    receipt=_read(result_path)
    prompt,nonce=_expected(source_sha=source_sha,family=family,
                           day=result_path.parent.name)
    _must(claim.get("schema_version")==1
          and claim.get("source_sha256")==source_sha
          and claim.get("model_family")==family
          and claim.get("thinking_level")=="medium"
          and claim.get("utc_day")==result_path.parent.name
          and claim.get("synthetic_prompt_sha256")==
              hashlib.sha256(prompt.encode("utf8")).hexdigest()
          and claim.get("no_original_source_attached") is True
          and claim.get("at_most_one_possible_model_send") is True
          and claim.get("G2_approved") is False,
          "Health claim drift or invalid model/thinking contract")
    _must(receipt.get("schema_version")==1
          and receipt.get("source_sha256")==source_sha
          and receipt.get("model_family")==family
          and receipt.get("thinking_level")=="medium"
          and receipt.get("utc_day")==result_path.parent.name
          and receipt.get("claim_sha256")==_sha(claim_path)
          and receipt.get("model_sends_possible") in (0,1)
          and receipt.get("no_original_source_uploaded") is True
          and receipt.get("G2_approved") is False
          and receipt.get("student_publication_authorized") is False
          and type(receipt.get("observed_unix")) in (int,float)
          and 0<=receipt["observed_unix"]<=4102444800,
          "Invalid one-shot academic health receipt")
    if receipt.get("status")=="SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED":
        response=receipt.get("response_text")
        _must(isinstance(response,str) and len(response)<=180
              and _is_exact(response,nonce)
              and receipt.get("gemini_new_user_turn_verified") is True
              and receipt.get("gemini_send_registration_status") in _REGISTERED
              and receipt.get("model_sends_possible")==1,
              "Health proof has no complete owned response and registered Send")
    else:
        _must(receipt.get("status")=="NO_VERIFIED_SOURCE_FREE_RESPONSE"
              and receipt.get("response_text") is None
              and receipt.get("gemini_new_user_turn_verified") is not True,
              "Unrecognized academic health attempt state")
    return receipt


def latest_success(*,checkpoint_parent:Path,source_sha:str,
                   family:str,after_unix:float,now:float)->dict|None:
    """Find existing independently verified health after the last failure."""
    scoped=_base(checkpoint_parent,source_sha,family)
    if not scoped.exists():
        return None
    _must(scoped.is_dir() and not scoped.is_symlink(),
          "Invalid academic health history directory")
    days=list(scoped.iterdir())
    _must(len(days)<=400,"Provider health history requires audit")
    winners=[]
    for folder in days:
        _must(folder.is_dir() and not folder.is_symlink()
              and re.fullmatch(r"20[0-9]{6}",folder.name) is not None,
              "Unsafe academic health entry")
        result=folder/"result.json"
        if not result.exists():
            continue
        receipt=verify_result(result_path=result,
             checkpoint_parent=checkpoint_parent,source_sha=source_sha,
             family=family)
        if (receipt["status"]=="SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"
                and after_unix<receipt["observed_unix"]<=now):
            winners.append(receipt)
    return max(winners,key=lambda x:x["observed_unix"]) if winners else None


def probe_once(*,checkpoint_parent:Path,source_sha:str,family:str,
               chrome_port:int=9222,now:float|None=None,
               browser_request=None)->dict:
    """At most one unique source-free Send in this UTC day, model and source.

    Run ONLY after a verified owned Pro/Medium or Flash/Medium preflight.
    Underlying _browser_request repeats only known-unsent pre-Send setup;
    any possibly accepted Send remains ONE and cannot be replayed here.
    """
    instant=float(time.time() if now is None else now)
    _must(type(chrome_port) is int and 1<=chrome_port<=65535,
          "Invalid authorized Gemini debug port")
    _must(os.getenv("MICROGEN_GEMINI_UI_MODE","flash").strip().lower()==family
          and os.getenv("MICROGEN_GEMINI_THINKING_LEVEL","medium").strip().lower()
              =="medium",
          "Health model/thinking differs from original G2 route")
    day=_day(instant)
    prompt,nonce=_expected(source_sha=source_sha,family=family,day=day)
    claim_path,result_path=_paths(checkpoint_parent=checkpoint_parent,
        source_sha=source_sha,family=family,day=day)
    _must(not claim_path.parent.is_symlink(),"Unsafe health claim folder")
    claim_path.parent.mkdir(parents=True,exist_ok=True)
    if result_path.exists():
        existing=verify_result(result_path=result_path,
            checkpoint_parent=checkpoint_parent,source_sha=source_sha,
            family=family)
        return {**existing,"reused_immutable_probe":True,
                "new_provider_requests":0}
    if claim_path.exists() or claim_path.is_symlink():
        return {"status":"PRIOR_SOURCE_FREE_PROBE_UNCERTAIN_NO_RESEND",
                "new_provider_requests":0,
                "source_sha256":source_sha,"model_family":family,
                "G2_approved":False,"student_publication_authorized":False}
    claim={
        "schema_version":1,"source_sha256":source_sha,
        "model_family":family,"thinking_level":"medium",
        "utc_day":day,
        "synthetic_prompt_sha256":hashlib.sha256(
            prompt.encode("utf8")).hexdigest(),
        "no_original_source_attached":True,
        "at_most_one_possible_model_send":True,
        "G2_approved":False,
    }
    with claim_path.open("x",encoding="utf8") as out:
        json.dump(claim,out,sort_keys=True,indent=2)
        out.write("\n");out.flush();os.fsync(out.fileno())
    response=None
    safe_error_class=None
    try:
        if browser_request is None:
            from .series_gemini import _browser_request
            received=_browser_request(prompt,[],port=chrome_port,
                       wait_cap_s=90,min_chars=16,
                       accept_fn=lambda s:_is_exact(s,nonce))
        else:
            received=browser_request(prompt,chrome_port)
        from .series_gemini import OwnedGeminiResponse
        _must(isinstance(received,OwnedGeminiResponse)
              and getattr(received,"gemini_new_user_turn_verified",None)
                  is True
              and getattr(received,"gemini_send_registration_status",None)
                  in _REGISTERED
              and _is_exact(str(received),nonce),
              "Untrusted browser health result; no requalification")
        response=str(received)
        registration=received.gemini_send_registration_status
    except Exception as exc:
        safe_error_class=type(exc).__name__
        registration=None
    outcome={
        "schema_version":1,"source_sha256":source_sha,
        "model_family":family,"thinking_level":"medium",
        "utc_day":day,"claim_sha256":_sha(claim_path),
        "observed_unix":instant,
        "status":("SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED"
                  if response is not None else
                  "NO_VERIFIED_SOURCE_FREE_RESPONSE"),
        "response_text":response,
        "gemini_new_user_turn_verified":True if response is not None else False,
        "gemini_send_registration_status":registration,
        "model_sends_possible":1,
        "new_provider_requests":1,
        "no_original_source_uploaded":True,
        "safe_error_class":safe_error_class,
        "G2_approved":False,"student_publication_authorized":False,
    }
    with result_path.open("x",encoding="utf8") as out:
        json.dump(outcome,out,sort_keys=True,indent=2)
        out.write("\n");out.flush();os.fsync(out.fileno())
    return verify_result(result_path=result_path,
        checkpoint_parent=checkpoint_parent,source_sha=source_sha,
        family=family)


def _is_exact(raw:str,nonce:str)->bool:
    if not isinstance(raw,str) or len(raw)>180:
        return False
    def no_duplicate_keys(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ValueError("Duplicate synthetic health response key")
            result[key]=value
        return result
    try:
        return json.loads(raw,object_pairs_hook=no_duplicate_keys)=={
            "microgen_health":"ok","nonce":nonce}
    except (ValueError,TypeError):
        return False
