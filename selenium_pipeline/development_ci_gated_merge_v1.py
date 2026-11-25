"""Fail-closed, exact-commit Windows CI-gated MicroGen PR merge.

The CI pass must be the latest workflow run for the unchanged PR head,
and both required Windows jobs must have completed successfully in the SAME
workflow attempt. No --auto, --admin, provider requests, student release or
replay of historical scientific sends is permitted.

This executable client-side gate complements, not replaces, server-enforced
main branch protection; it cannot block another actor from using the GitHub UI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .recovery_registry import lookup_mechanism

REPO="tlyoon/MicroGen_AI_Web"
BRANCH="main"
WORKFLOW_NAME="MicroGen reliability regressions"
WORKFLOW_PATH=".github/workflows/microgen-reliability-tests.yml"
REQUIRED_WINDOWS_JOBS=frozenset({
    "offline-regressions",
    "Full offline suite (Windows, Python 3.12)",
})
KIND="development_pr_ci_gated_merge"
SIGNATURE="GITHUB_UNPROTECTED_MAIN_ALLOWED_PR_MERGE_BEFORE_WINDOWS_CI_COMPLETE"
MECHANISM="VERIFY_LATEST_EXACT_PR_HEAD_ALL_REQUIRED_WINDOWS_CI_BEFORE_MATCH_HEAD_MERGE"
PASS="EXACT_HEAD_WINDOWS_CI_GATES_PASSED_NO_MERGE"
MERGED="EXACT_HEAD_WINDOWS_CI_GATES_PASSED_AND_PR_MERGED"
SHA=re.compile(r"^[a-f0-9]{40}$")
MAX_RUNS=100


def need(ok,why):
    if not ok:
        raise ValueError(why)


def canonical(payload:dict)->bytes:
    return (json.dumps(payload,ensure_ascii=False,sort_keys=True,
                       separators=(",",":"),allow_nan=False)+"\n").encode("utf8")


def api(path:str)->dict:
    # gh reads its existing authenticated Windows account, not new tokens.
    need(bool(path) and path.startswith("repos/"+REPO+"/")
         and not any(x in path for x in ("\r","\n"," ",";","|")),
         "Refuse arbitrary GitHub API command")
    proc=subprocess.run(["gh","api",path],capture_output=True,
                        text=True,timeout=45,check=False)
    need(proc.returncode==0 and len(proc.stdout)<4_000_000,
         "GitHub source API unavailable; CI gate HOLDS")
    value=json.loads(proc.stdout)
    need(type(value) is dict,"Unexpected GitHub API response")
    return value


def issue_merge(pr:int,head_sha:str)->None:
    need(type(pr) is int and 1<=pr<=1_000_000
         and type(head_sha) is str and SHA.fullmatch(head_sha),
         "Unsafe PR/head for guarded merge")
    # REST API supports SHA-based compare-and-swap without the GitHub CLI's
    # GraphQL mutation path. The live historical failure was a CLI nonzero
    # response after GitHub actually created a squash commit.
    request={"sha":head_sha,"merge_method":"squash"}
    with tempfile.TemporaryDirectory(prefix="microgen_exact_head_merge_") as temp:
        request_file=Path(temp)/"request.json"
        request_file.write_bytes(canonical(request))
        args=["gh","api","--method","PUT",
              f"repos/{REPO}/pulls/{pr}/merge",
              "--input",str(request_file)]
        proc=subprocess.run(args,capture_output=True,text=True,timeout=100,
                            check=False)
    if proc.returncode!=0:
        # Nonzero is not evidence that a remote side effect did not occur.
        message=(proc.stderr or proc.stdout or "").strip().replace("\r"," ").replace("\n"," ")
        message=re.sub(r"(?:gh[opusr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,})",
                       "[REDACTED_TOKEN]",message,flags=re.I)
        raise ValueError("GitHub exact-head REST merge outcome uncertain, exit="
                         +str(proc.returncode)+": "+message[:210])
    reply=json.loads(proc.stdout)
    need(type(reply) is dict and reply.get("merged") is True
         and _sha(reply.get("sha")),
         "REST response not a verified merge, reconcile original PR before retry")


def _sha(value)->bool:
    return type(value) is str and SHA.fullmatch(value) is not None


def _stamp(value):
    need(type(value) is str and value.endswith("Z"),
         "Missing UTC GitHub run timestamp")
    return datetime.fromisoformat(value.replace("Z","+00:00"))


def inspect(*,pr_number:int,fetch=api)->dict:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "CI merge policy absent from executable recovery registry")
    need(type(pr_number) is int and 1<=pr_number<=1_000_000,
         "Invalid pull request number")
    pr=fetch(f"repos/{REPO}/pulls/{pr_number}")
    head=pr.get("head") or {}
    base=pr.get("base") or {}
    head_sha=head.get("sha")
    branch=head.get("ref")
    need(pr.get("number")==pr_number and pr.get("state")=="open"
         and pr.get("merged_at") is None
         and pr.get("draft") is False and pr.get("mergeable") is True
         and _sha(head_sha) and type(branch) is str and len(branch)>3
         and base.get("ref")==BRANCH
         and head.get("repo",{}).get("full_name")==REPO
         and base.get("repo",{}).get("full_name")==REPO,
         "Only open, mergeable, non-draft PRs from authorized repo to main")
    original_base_sha=base.get("sha")
    need(_sha(original_base_sha),"Unpinned PR base commit")
    current_main=fetch(f"repos/{REPO}/branches/{BRANCH}")
    need(current_main.get("name")==BRANCH
         and current_main.get("commit",{}).get("sha")==original_base_sha,
         "PR base changed; update and requalify Windows CI before merge")
    workflow=fetch(f"repos/{REPO}/actions/workflows/{WORKFLOW_PATH.split('/')[-1]}")
    workflow_id=workflow.get("id")
    need(type(workflow_id) is int and workflow_id>0
         and workflow.get("path")==WORKFLOW_PATH
         and workflow.get("name")==WORKFLOW_NAME
         and workflow.get("state")=="active",
         "Expected active Windows CI workflow identity missing")
    listing=fetch(f"repos/{REPO}/actions/runs?head_sha={head_sha}&event=pull_request&per_page={MAX_RUNS}")
    runs=listing.get("workflow_runs")
    total=listing.get("total_count")
    need(type(runs) is list and type(total) is int
         and 0<=total<=MAX_RUNS and len(runs)==total,
         "Ambiguous or paginated exact-head workflow history")
    applicable=[r for r in runs if (
        r.get("head_sha")==head_sha
        and r.get("head_branch")==branch
        and r.get("event")=="pull_request"
        and r.get("repository",{}).get("full_name") in (None,REPO)
        and r.get("head_repository",{}).get("full_name") in (None,REPO))]
    # A second applicable workflow can fail even when the main regression
    # suite passes. Validate the latest attempt of EVERY source-head workflow.
    by_workflow={}
    for r in applicable:
        ident=r.get("workflow_id")
        need(type(ident) is int and ident>0 and
             type(r.get("id")) is int and type(r.get("run_attempt")) is int,
             "Unknown PR workflow run provenance")
        newest=by_workflow.get(ident)
        key=lambda v:(_stamp(v.get("created_at")),
                      v["id"],v["run_attempt"])
        if newest is None or key(r)>key(newest):
            by_workflow[ident]=r
    need(bool(by_workflow),"No matching PR-head workflow history")
    need(all(r.get("status")=="completed"
             and r.get("conclusion")=="success"
             and _stamp(r["created_at"])>=_stamp(pr["created_at"])
             for r in by_workflow.values()),
         "Another applicable PR-head workflow is pending or failed")
    matching=[r for r in applicable if (
        r.get("workflow_id")==workflow_id
        and r.get("path")==WORKFLOW_PATH
        and r.get("name")==WORKFLOW_NAME)]
    need(bool(matching),"No exact PR-head Windows CI workflow run found")
    # Do not select an older successful run if a newer attempt is pending.
    matching.sort(key=lambda r:(_stamp(r.get("created_at")),
                                r.get("id",0),r.get("run_attempt",0)),
                  reverse=True)
    run=matching[0]
    need(by_workflow[workflow_id]==run,
         "Latest active Windows workflow identity disagrees with run path")
    run_id=run.get("id")
    attempt=run.get("run_attempt")
    need(type(run_id) is int and run_id>0
         and type(attempt) is int and attempt>=1
         and _stamp(run["created_at"])>=_stamp(pr["created_at"])
         and run.get("status")=="completed"
         and run.get("conclusion")=="success",
         "Current exact-head Windows CI run not successfully complete")
    jobs=fetch(f"repos/{REPO}/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
    values=jobs.get("jobs")
    count=jobs.get("total_count")
    need(type(values) is list and type(count) is int
         and 2<=count<=100 and len(values)==count,
         "Incomplete CI job inventory, no merge")
    by_name={}
    for item in values:
        name=item.get("name")
        need(type(name) is str and name not in by_name
             and item.get("status")=="completed"
             and item.get("conclusion")=="success"
             and item.get("head_sha")==head_sha
             and item.get("run_id")==run_id
             and item.get("workflow_name")==WORKFLOW_NAME,
             "Missing, duplicated, pending, failed, or mismatched CI job")
        by_name[name]=item
    need(REQUIRED_WINDOWS_JOBS <= set(by_name),
         "Both mandatory Windows CI jobs must succeed on exact PR head")
    evidence=[{"job":name,"id":by_name[name]["id"],
               "conclusion":"success"}
              for name in sorted(by_name)]
    proof={"schema_version":1,"status":PASS,
           "repo":REPO,"pr_number":pr_number,"base_branch":BRANCH,
           "base_sha":original_base_sha,
           "head_sha":head_sha,"head_branch":branch,
           "workflow_id":workflow_id,"workflow_run_id":run_id,
           "workflow_run_attempt":attempt,
           "required_windows_jobs":sorted(REQUIRED_WINDOWS_JOBS),
           "verified_jobs":evidence,
           "new_provider_requests":0,
           "new_paid_gemini_api_calls":0,
           "student_publication_authorized":False}
    proof["evidence_fingerprint"]=hashlib.sha256(canonical(proof)).hexdigest()
    return proof


def gate(*,pr_number:int,perform_merge:bool=False,fetch=api,
         merge_fn=issue_merge)->dict:
    first=inspect(pr_number=pr_number,fetch=fetch)
    if not perform_merge:
        return first
    # Re-query the PR, main and every CI receipt immediately before merge.
    second=inspect(pr_number=pr_number,fetch=fetch)
    need(first==second,"CI evidence or PR head changed before merge; HOLD")
    try:
        merge_fn(pr_number,first["head_sha"])
    except (ValueError,OSError,subprocess.TimeoutExpired) as error:
        # The historical PR #654 failure returned GraphQL errors AFTER a
        # GitHub-authored squash commit with exactly the approved source
        # tree had already appeared on main, while the PR stayed OPEN.
        # Never assume a nonzero remote command means no side effect.
        saved=fetch(f"repos/{REPO}/pulls/{pr_number}")
        need(saved.get("head",{}).get("sha")==first["head_sha"],
             "Merge response uncertain and PR head changed: HOLD")
        if saved.get("merged_at") is not None and saved.get("state")=="closed":
            return {**first,"status":MERGED,
                    "merged_at":saved["merged_at"],
                    "merge_commit_sha":saved.get("merge_commit_sha"),
                    "recovered_after_failed_client_response":True,
                    "automatic_merge_used":False}
        current=fetch(f"repos/{REPO}/branches/{BRANCH}")
        current_sha=current.get("commit",{}).get("sha")
        if _sha(current_sha) and current_sha!=first["base_sha"]:
            main_commit=fetch(f"repos/{REPO}/git/commits/{current_sha}")
            requested_head=fetch(f"repos/{REPO}/git/commits/{first['head_sha']}")
            parent_sha=[v.get("sha") for v in main_commit.get("parents",[])]
            same_tree=(main_commit.get("tree",{}).get("sha")==
                       requested_head.get("tree",{}).get("sha"))
            if same_tree and parent_sha==[first["base_sha"]]:
                return {**first,
                        "status":"REMOTE_SQUASH_TREE_IDENTICAL_BUT_PR_STILL_OPEN_HOLD",
                        "main_commit_sha":current_sha,
                        "same_file_tree_verified":True,
                        "merge_completed":False,
                        "previous_client_error_class":type(error).__name__,
                        "original_request_retried":False,
                        "student_publication_authorized":False}
        raise ValueError(
            "Client merge outcome uncertain; independently inspected PR/main; "
            "no retry authorized. "+str(error)[:150]) from error
    # A timed-out merge command is uncertain; callers must inspect remote
    # PR state, not retry the same operation blindly.
    saved=fetch(f"repos/{REPO}/pulls/{pr_number}")
    need(saved.get("merged_at") is not None
         and saved.get("state")=="closed"
         and saved.get("head",{}).get("sha")==first["head_sha"],
         "Merge completion has no matching remote GitHub receipt")
    return {**first,"status":MERGED,
            "merged_at":saved["merged_at"],
            "merge_commit_sha":saved.get("merge_commit_sha"),
            "automatic_merge_used":False}


def persist(path:Path,payload:dict)->None:
    path=Path(path).absolute()
    need(not path.is_symlink() and not path.parent.is_symlink()
         and path.suffix==".json",
         "Refuse redirected merge audit receipt")
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".pending")
    need(not temp.is_symlink(),"Refuse redirected pending merge receipt")
    with temp.open("wb") as output:
        output.write(canonical(payload))
        output.flush()
        os.fsync(output.fileno())
    os.replace(temp,path)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr",type=int,required=True)
    parser.add_argument("--merge",action="store_true",
                        help="Explicitly perform audited squash merge after two exact CI checks")
    parser.add_argument("--receipt",type=Path)
    args=parser.parse_args(argv)
    try:
        result=gate(pr_number=args.pr,perform_merge=args.merge)
    except (ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as error:
        result={"schema_version":1,"status":"CI_MERGE_GATE_HELD",
                "pr_number":args.pr,"reason_class":type(error).__name__,
                "reason":str(error)[:180],
                "new_provider_requests":0,
                "student_publication_authorized":False,
                "merge_completed":False}
        if args.receipt:
            persist(args.receipt,result)
        print(json.dumps(result,indent=2))
        return 2
    if args.receipt:
        persist(args.receipt,result)
    print(json.dumps(result,indent=2))
    return 0 if result["status"] in {PASS,MERGED} else 2


if __name__=="__main__":
    raise SystemExit(main())

