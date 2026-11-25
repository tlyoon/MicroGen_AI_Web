"""Conservatively install and verify GitHub server-side CI protection for main.

This complements the audited client-side exact-head merge guard: without
branch protection, another GitHub client could merge around that guard.
Only applies protection when the branch is currently unprotected. Never
overwrites an existing rule, relaxes review requirements or bypasses admin.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from selenium_pipeline.development_ci_gated_merge_v1 import (
    REPO, BRANCH, REQUIRED_WINDOWS_JOBS, need,
)

ENDPOINT=f"repos/{REPO}/branches/{BRANCH}/protection"
KIND="MICROGEN_WINDOWS_ONLY_STRICT_BRANCH_PROTECTION"


def policy()->dict:
    return {
        "required_status_checks":{
            "strict":True,"contexts":sorted(REQUIRED_WINDOWS_JOBS)},
        "enforce_admins":True,
        "required_pull_request_reviews":None,
        "restrictions":None,
        "required_linear_history":True,
        "allow_force_pushes":False,
        "allow_deletions":False,
    }


def verify(actual:dict)->dict:
    need(type(actual) is dict,"Missing GitHub branch protection receipt")
    required=actual.get("required_status_checks") or {}
    enforced=actual.get("enforce_admins") or {}
    linear=actual.get("required_linear_history") or {}
    force=actual.get("allow_force_pushes") or {}
    delete=actual.get("allow_deletions") or {}
    # Do not equate an empty/unknown protection record with success.
    contexts=required.get("contexts")
    need(required.get("strict") is True
         and type(contexts) is list
         and REQUIRED_WINDOWS_JOBS <= set(contexts)
         and enforced.get("enabled") is True
         and linear.get("enabled") is True
         and force.get("enabled") is False
         and delete.get("enabled") is False,
         "GitHub main branch protection does not enforce mandatory Windows CI")
    return {"schema_version":1,
            "status":"GITHUB_MAIN_SERVER_SIDE_WINDOWS_CI_ENFORCED",
            "repo":REPO,"branch":BRANCH,
            "strict_up_to_date_required":True,
            "enforce_administrators":True,
            "squash_compatible_linear_history":True,
            "required_jobs":sorted(REQUIRED_WINDOWS_JOBS),
            "force_pushes_authorized":False,
            "branch_deletions_authorized":False,
            "student_publication_authorized":False,
            "paid_api_calls":0}


def _gh(args:list[str],data:bytes|None=None)->tuple[int,str,str]:
    need(args[:2]==["gh","api"],"Not a trusted GitHub API invocation")
    proc=subprocess.run(args,input=data,capture_output=True,text=True,
                        timeout=50,check=False)
    return proc.returncode,proc.stdout,proc.stderr


def enforce(*,apply:bool=False,request=_gh)->dict:
    get_args=["gh","api",ENDPOINT]
    code,out,err=request(get_args)
    if code==0:
        result=verify(json.loads(out))
        result["operation"]="ALREADY_PROTECTED_NO_MUTATION"
        return result
    need(("404" in err or '"status":404' in out or
          '"status": 404' in out) and "Not Found" in (err+out) or
         code!=0 and "Branch not protected" in (err+out),
         "Unexpected GitHub API failure; do not alter repo protection")
    if not apply:
        return {"schema_version":1,
                "status":"MAIN_NOT_YET_PROTECTED_EXPLICIT_APPLY_REQUIRED",
                "repo":REPO,"branch":BRANCH,
                "merge_policy_implemented":True,
                "server_side_gate_installed":False}
    body=(json.dumps(policy(),sort_keys=True,separators=(",",":"))+"\n").encode()
    with tempfile.TemporaryDirectory(prefix="microgen_branch_protection_") as td:
        file=Path(td)/"protection.json"
        file.write_bytes(body)
        command=["gh","api","--method","PUT",ENDPOINT,
                 "--input",str(file)]
        # No bearer token or privileged settings persisted in repo.
        code,response,error=request(command)
        need(code==0,"GitHub refused server-side branch protection")
        verify(json.loads(response))
    code,response,error=request(get_args)
    need(code==0,"Cannot independently verify branch protection after PUT")
    result=verify(json.loads(response))
    result["operation"]="INSTALLED_AND_READ_BACK"
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args(argv)
    try:
        value=enforce(apply=args.apply)
    except (ValueError,TypeError,KeyError,subprocess.TimeoutExpired) as error:
        value={"status":"GITHUB_BRANCH_PROTECTION_HELD",
               "reason_class":type(error).__name__,
               "reason":str(error)[:180]}
        print(json.dumps(value,indent=2))
        return 2
    print(json.dumps(value,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

