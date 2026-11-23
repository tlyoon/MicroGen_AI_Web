"""One-shot source-free Neon/High health gate for G3 distinct science QA.

This is a NEW, model-owned synthetic diagnostic. It is not an original
textbook mapping Send, and never uploads any source PDF. A failed or
possibly delivered Send permanently consumes its source/day claim.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

from .g3_source_rejected_offline_repair_v1 import _sha, _canon, need
from .academic_provider_requalification import _REGISTERED
from .three_pc_worker import LocalInstanceLock
from .recovery_registry import lookup_mechanism

ROOT="g3_semantic_source_free_neon_health_v1"
KIND="g3_semantic_neon_health"
SIGNATURE="G3_DISTINCT_SOURCE_SCIENCE_NEEDS_FRESH_VERIFIED_BROWSER"
MECHANISM="ONE_SOURCE_FREE_NEON_HIGH_CLAIM_AND_IMMUTABLE_OWNED_RESULT"
_OK="G3_SOURCE_FREE_NEON_HIGH_HEALTH_VERIFIED"
_BAD="G3_SOURCE_FREE_HEALTH_UNVERIFIED_NO_REPLAY"
_HEX=re.compile(r"[0-9a-f]{64}\Z")


def _expected(source_sha:str,day:str)->tuple[str,str]:
    nonce=hashlib.sha256(
        f"G3-source-free-Neon-High-semantic-v1|{source_sha}|{day}".encode()
    ).hexdigest()[:22]
    return (
        "A synthetic source-free Gemini Neon/High browser-health test. "
        "No textbook, student data or PDF is attached. "
        'Return exactly a single JSON object with no markdown: '
        '{"g3_source_health":"ready","nonce":"'+nonce+'"}',
        nonce)


def _valid(raw:str,nonce:str)->bool:
    if type(raw) is not str or len(raw)>300:
        return False
    def no_duplicate(pairs):
        a={}
        for k,v in pairs:
            if k in a:
                raise ValueError("duplicate synthetic health field")
            a[k]=v
        return a
    try:
        return json.loads(raw,object_pairs_hook=no_duplicate)=={
            "g3_source_health":"ready","nonce":nonce}
    except (ValueError,TypeError):
        return False


def _paths(root:Path,source_sha:str,day:str)->tuple[Path,Path]:
    root=Path(root).absolute()
    need(root.is_dir() and not root.is_symlink()
         and _HEX.fullmatch(source_sha) is not None
         and re.fullmatch(r"20[0-9]{6}",day) is not None,
         "Bounded original G3 source/health journal required")
    folder=root/ROOT/source_sha/day
    need(not folder.is_symlink(),"Linked source-free G3 health claim")
    return folder/"claim.json",folder/"result.json"


def verify(*,root:Path,source_sha:str,day:str,after_unix:float=0)->dict:
    claim_path,result_path=_paths(root,source_sha,day)
    claim=json.loads(claim_path.read_text("utf8")) if claim_path.is_file() else None
    need(type(claim) is dict and not claim_path.is_symlink(),
         "No original source-free Neon/High health claim")
    prompt,nonce=_expected(source_sha,day)
    need(claim.get("schema_version")==1
         and claim.get("source_sha256")==source_sha
         and claim.get("utc_day")==day
         and claim.get("model_family")=="neon"
         and claim.get("thinking_level")=="high"
         and claim.get("no_original_PDF_attached") is True
         and claim.get("one_possible_browser_send") is True
         and claim.get("prompt_sha256")==
             hashlib.sha256(prompt.encode()).hexdigest(),
         "Original synthetic model claim altered")
    if not result_path.exists():
        return {
            "status":"G3_SOURCE_FREE_HEALTH_CLAIMED_NO_REPLAY",
            "new_provider_requests":0,
            "source_pdf_uploaded":False,
            "student_publication_authorized":False,
        }
    need(result_path.is_file() and not result_path.is_symlink()
         and result_path.stat().st_size<8000,
         "Invalid source-free health result")
    receipt=json.loads(result_path.read_text("utf8"))
    need(receipt.get("claim_sha256")==_sha(claim_path)
         and receipt.get("source_sha256")==source_sha
         and receipt.get("model_family")=="neon"
         and receipt.get("thinking_level")=="high"
         and receipt.get("utc_day")==day
         and receipt.get("no_original_PDF_attached") is True
         and receipt.get("student_publication_authorized") is False
         and type(receipt.get("observed_unix")) in (int,float)
         and receipt["observed_unix"]>=claim["claimed_unix"],
         "Foreign or edited health receipt")
    if receipt.get("status")==_OK:
        need(receipt.get("exact_owned_model_text")==
                 '{"g3_source_health":"ready","nonce":"'+nonce+'"}'
             and receipt.get("verified_model_family")=="neon"
             and receipt.get("verified_thinking_level")=="high"
             and receipt.get("gemini_new_user_turn_verified") is True
             and receipt.get("gemini_send_registration_status") in _REGISTERED,
             "Wrong model or unowned synthetic health reply")
    else:
        need(receipt.get("status")==_BAD
             and receipt.get("exact_owned_model_text") is None
             and receipt.get("gemini_new_user_turn_verified") is False,
             "Unverified provider reply cannot certify G3 science")
    valid=(receipt["status"]==_OK
           and receipt["observed_unix"]>after_unix
           and 0<=time.time()-receipt["observed_unix"]<=21600)
    return {**receipt,
            "fresh_neon_high_source_free_health":valid,
            "new_provider_requests":0}


def probe_once(*,root:Path,source_sha:str,now:float|None=None,
               browser_request=None)->dict:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "G3 exact model health mechanism not registered")
    instant=time.time() if now is None else float(now)
    day=datetime.fromtimestamp(instant,timezone.utc).strftime("%Y%m%d")
    root=Path(root).absolute()
    lockdir=root/".g3_source_neon_health_locks"
    need(not lockdir.is_symlink(),"Source-free model owner lock redirected")
    lockdir.mkdir(exist_ok=True)
    with LocalInstanceLock("g3_neon_health_"+source_sha[:20],lockdir):
        claim_path,result_path=_paths(root,source_sha,day)
        if claim_path.exists() or claim_path.is_symlink():
            return verify(root=root,source_sha=source_sha,day=day)
        claim_path.parent.mkdir(parents=True,exist_ok=True)
        prompt,nonce=_expected(source_sha,day)
        claim={
            "schema_version":1,"source_sha256":source_sha,
            "utc_day":day,"model_family":"neon","thinking_level":"high",
            "claimed_unix":instant,
            "prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),
            "no_original_PDF_attached":True,
            "one_possible_browser_send":True,
            "student_publication_authorized":False,
        }
        with claim_path.open("x",encoding="utf8") as out:
            out.write(_canon(claim).decode())
            out.flush();os.fsync(out.fileno())
        raw=None
        try:
            if browser_request is None:
                from .academic_queue_fresh_send_health import _full_family_scope
                from .series_gemini import _browser_request
                with _full_family_scope("pro"):
                    os.environ["MICROGEN_GEMINI_THINKING_LEVEL"]="high"
                    observation=_browser_request(
                        prompt,[],port=9222,wait_cap_s=90,min_chars=20,
                        expected_runtime_family="neon",
                        expected_thinking_level="high",
                        accept_fn=lambda s:_valid(s,nonce))
            else:
                observation=browser_request(prompt,[])
            from .series_gemini import OwnedGeminiResponse
            need(isinstance(observation,OwnedGeminiResponse)
                 and observation.gemini_new_user_turn_verified is True
                 and observation.gemini_send_registration_status in _REGISTERED
                 and observation.gemini_verified_model_family=="neon"
                 and observation.gemini_verified_thinking_level=="high"
                 and _valid(str(observation),nonce),
                 "No attributable exact-family source-free browser result")
            raw=str(observation)
            registration=observation.gemini_send_registration_status
        except Exception:
            registration=None
        result={
            "schema_version":1,"source_sha256":source_sha,
            "utc_day":day,"claim_sha256":_sha(claim_path),
            "model_family":"neon","thinking_level":"high",
            "observed_unix":time.time() if now is None else instant,
            "status":_OK if raw is not None else _BAD,
            "exact_owned_model_text":raw,
            "verified_model_family":"neon" if raw is not None else None,
            "verified_thinking_level":"high" if raw is not None else None,
            "gemini_new_user_turn_verified":raw is not None,
            "gemini_send_registration_status":registration,
            "no_original_PDF_attached":True,
            "student_publication_authorized":False,
            "new_paid_gemini_API_calls":0,
            "new_provider_requests":1,
        }
        with result_path.open("x",encoding="utf8") as out:
            out.write(_canon(result).decode())
            out.flush();os.fsync(out.fileno())
        verified=verify(root=root,source_sha=source_sha,day=day)
        # The newly executed diagnostic DID consume one possible browser
        # Send. A repeat call reuses its immutable receipt and returns zero.
        return {**verified,"new_provider_requests":1,
                "new_paid_gemini_API_calls":0}


def latest(*,root:Path,source_sha:str,after_unix:float)->dict|None:
    base=Path(root).absolute()/ROOT/source_sha
    if not base.exists():
        return None
    need(base.is_dir() and not base.is_symlink(),
         "Untrusted historical G3 source-free claims")
    days=sorted(base.iterdir(),reverse=True)
    need(len(days)<=100,"Unbounded G3 health claim inventory")
    for folder in days:
        need(folder.is_dir() and not folder.is_symlink()
             and re.fullmatch(r"20[0-9]{6}",folder.name) is not None,
             "Invalid source-free health day")
        record=verify(root=root,source_sha=source_sha,
                      day=folder.name,after_unix=after_unix)
        if record.get("fresh_neon_high_source_free_health") is True:
            return record
    return None
