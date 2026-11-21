"""Source-bound block for Codex CLI effective sandbox downgraded to read-only.

A request for workspace-write does not prove the host grants it. Observe
actual Codex stderr, persist a no-new-Sends capability gate, and advance
independent offline development. Never weaken host security or auto-retry
the already-consumed coding-model request.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re

from .development_continuity_executor_v71 import _read_json, _sha, _atomic_json

POLICY_NAME="microgen_coding_cli_policy_block_v71.json"
STATUS="CODING_CLI_EFFECTIVE_READONLY_BLOCKED"
RULE="HOST_WORKSPACE_WRITE_DENIED_NO_AUTOMATIC_MODEL_RETRY"
SHA64=re.compile(r"[0-9a-f]{64}")


def _require(x:bool, reason:str)->None:
    if not x:
        raise ValueError(reason)


def blocker_path(checkpoint_root:Path)->Path:
    root=Path(checkpoint_root).resolve()
    _require(root.is_dir() and not root.is_symlink(),
             "Unknown isolated coding checkpoint")
    if os.name=="nt":
        local=Path(os.environ["LOCALAPPDATA"]).resolve()
        _require(root.parent==local/"MicroGen_AI_Web_Checkpoints",
                 "Shared model capability gate must be in approved Dell checkpoint")
    return root.parent/POLICY_NAME


def _validate(payload:dict)->None:
    expected={
        "schema_version","status","reason","source_job_sha256",
        "codex_cli_sha256","observed_stderr_sha256",
        "requested_sandbox","observed_sandbox",
        "block_additional_model_calls","require_policy_requalification",
        "student_release_authorized","may_auto_clear",
    }
    _require(type(payload) is dict and set(payload)==expected
             and payload["schema_version"]==1
             and payload["status"]==STATUS
             and payload["reason"]==RULE
             and all(type(payload[k]) is str and SHA64.fullmatch(payload[k])
                     for k in ("source_job_sha256","codex_cli_sha256",
                               "observed_stderr_sha256"))
             and payload["requested_sandbox"]=="workspace-write"
             and payload["observed_sandbox"]=="read-only"
             and payload["block_additional_model_calls"] is True
             and payload["require_policy_requalification"] is True
             and payload["student_release_authorized"] is False
             and payload["may_auto_clear"] is False,
             "Missing or tampered Codex effective-sandbox policy evidence")


def is_host_readonly(stderr:str)->bool:
    return (isinstance(stderr,str)
            and re.search(r"(?m)^\s*sandbox:\s*read-only\s*$",stderr) is not None
            and "blocked by policy" in stderr.casefold()
            and "codex" in stderr.casefold())


def persist_host_denial(*,checkpoint_root:Path,job_sha256:str,
                        cli_sha256:str,stderr:str)->dict:
    _require(type(stderr) is str and 0<len(stderr)<=100_000
             and is_host_readonly(stderr),
             "Unverified effective read-only policy; no policy mutation")
    _require(all(type(x) is str and SHA64.fullmatch(x)
                 for x in (job_sha256,cli_sha256)),
             "Untrusted source-bound CLI/job identity")
    payload={
        "schema_version":1,
        "status":STATUS,"reason":RULE,
        "source_job_sha256":job_sha256,
        "codex_cli_sha256":cli_sha256,
        "observed_stderr_sha256":hashlib.sha256(stderr.encode("utf8")).hexdigest(),
        "requested_sandbox":"workspace-write",
        "observed_sandbox":"read-only",
        "block_additional_model_calls":True,
        "require_policy_requalification":True,
        "student_release_authorized":False,
        "may_auto_clear":False,
    }
    target=blocker_path(checkpoint_root)
    _require(not target.is_symlink(),"Unsafe provider capability gate")
    if target.exists():
        saved=_read_json(target)
        _validate(saved)
        _require(saved==payload,
                 "Existing capability denial differs; refuse rewrite")
    else:
        _atomic_json(target,payload)
    return payload


def require_workspace_write_capability(*,checkpoint_root:Path,
                                       cli_sha256:str)->None:
    _require(type(cli_sha256) is str and SHA64.fullmatch(cli_sha256),
             "Unknown trusted model CLI binary")
    target=blocker_path(checkpoint_root)
    _require(not target.is_symlink(),"Unsafe code-model policy state")
    if not target.exists():
        return
    saved=_read_json(target)
    _validate(saved)
    # A provider binary update does not by itself prove host policy changed.
    raise ValueError(
        "Codex host enforced read-only sandbox; do not send any new coding "
        "model request until independently authorized policy requalification")


def reconcile_saved_denial(*,checkpoint_root:Path,job_path:Path,
                           state_dir:Path,cli_path:Path,
                           stderr_path:Path)->dict:
    """Read original returned model evidence only, never invoke Codex."""
    root=Path(checkpoint_root).resolve()
    job_path=Path(job_path).resolve()
    state_dir=Path(state_dir).resolve()
    cli_path=Path(cli_path).resolve()
    stderr_path=Path(stderr_path).resolve()
    _require(job_path.is_file() and not job_path.is_symlink()
             and job_path.is_relative_to(root)
             and state_dir.is_relative_to(root)
             and stderr_path.is_file() and not stderr_path.is_symlink()
             and stderr_path.is_relative_to(root)
             and 1<=stderr_path.stat().st_size<=100_000
             and cli_path.is_file() and not cli_path.is_symlink(),
             "Unsafe source-bound historical coding-model evidence")
    record=_read_json(state_dir/"coding_job_state.json")
    job=_read_json(job_path)
    _require(record.get("job_sha256")==_sha(job_path)
             and record.get("model_invocations_claimed")==1
             and record.get("status")=="MODEL_NO_SOURCE_DIFF_QUARANTINED"
             and record.get("candidate_pr_pushed") is False
             and job.get("codex_sha256")==_sha(cli_path)
             and type(record.get("model_output_sha256")) is str,
             "No safe previously returned coding-model response to reconcile")
    return persist_host_denial(
        checkpoint_root=root,job_sha256=_sha(job_path),
        cli_sha256=_sha(cli_path),
        stderr=stderr_path.read_text(encoding="utf8",errors="replace"))
