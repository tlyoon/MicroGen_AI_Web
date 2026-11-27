"""Bounded source-verified code candidate -> protected GitHub PR -> CI -> merge.

A durable transaction journal precedes every remote GitHub side effect.
An uncertain push, create-PR or merge is ONLY reconciled from remote state:
never repeat an uncertain mutation. This module never submits a model request,
calls a paid API, authorizes science acceptance or publishes to students.

Production guarded cutover is delegated to the existing, separately certified
guarded revision executor; a merged source alone is NOT a deployment.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .development_persistent_selenium_author_v1 import (
    validate_job, sha, read, git, validate_source, parse_reply)
from .development_ci_gated_merge_v1 import (
    inspect as exact_ci_inspect,
    gate as exact_ci_gate,
    MERGED, PASS)
from .recovery_registry import lookup_mechanism

KIND="autonomous_verified_candidate_promotion"
SIGNATURE="SOURCE_TESTED_CODE_JOB_STOPS_BEFORE_GITHUB_PR_WINDOWS_CI"
MECHANISM="JOURNAL_CAS_BRANCH_PR_EXACT_CI_MERGE_AND_DEPLOY_GATE"
REPO="tlyoon/MicroGen_AI_Web"
SHA40=re.compile(r"^[a-f0-9]{40}$")
ID=re.compile(r"^[a-z][a-z0-9_]{6,50}$")
DONE=frozenset({"ALREADY_ON_VERIFIED_MAIN","MERGED_AWAITING_GUARDED_CUTOVER",
                "GUARDED_DEPLOYED","GITHUB_WINDOWS_CI_FAILED_HELD"})
REMOTE_HOLD="REMOTE_MUTATION_UNCERTAIN_NO_RETRY"


def need(ok,reason):
    if not ok:
        raise ValueError(reason)


def run(cmd,timeout=90):
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    need(p.returncode==0,
         "Trusted Git/GitHub operation held: "+p.stderr[-200:])
    return p.stdout.strip()


def api(path):
    need(path.startswith("repos/"+REPO+"/")
         and not any(x in path for x in (" ","\n","\r",";","|")),
         "Untrusted remote GitHub API path")
    return json.loads(run(["gh","api",path],timeout=40))


def save(path:Path,value:dict):
    path=Path(path)
    need(path.parent.is_dir() and not path.parent.is_symlink()
         and not path.is_symlink(),"Unsafe original promotion checkpoint")
    body=(json.dumps(value,sort_keys=True,indent=2)+"\n").encode("utf8")
    temp=path.with_suffix(".pending")
    need(not temp.exists() and not temp.is_symlink(),
         "Interrupted promotion state write needs reconciliation")
    with temp.open("xb") as stream:
        stream.write(body);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)


def _original(job_path,root):
    root=Path(root).absolute()
    job_path=Path(job_path).absolute()
    need(job_path.is_file() and not job_path.is_symlink()
         and job_path.parent==root/"inbox","Untrusted source code job")
    job=read(job_path)
    need(type(job.get("job_id")) is str and
         ID.fullmatch(job["job_id"]),
         "Untrusted original candidate ID")
    evidence=root/"state"/job["job_id"]
    receipt=read(evidence/"coding_state.json")
    need(receipt.get("job_sha256")==sha(job_path)
         and receipt.get("status")=="SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
         and receipt.get("pytest_exit_code")==0
         and receipt.get("model_claims")==1
         and receipt.get("model_sends")==1
         and receipt.get("paid_api_requests")==0
         and receipt.get("student_publication_authorized") is False
         and receipt.get("candidate_merged") is False,
         "Only independently tested original one-claim source may be promoted")
    # The original model output is pinned even when its separate original
    # worktree was committed after tests and validate_job no longer applies.
    reply=evidence/"original_model_reply.txt"
    need(sha(reply)==receipt.get("model_reply_sha256"),
         "Original owned browser response was modified")
    # An untrusted local source file cannot be substituted for the original
    # model response merely by forging a candidate checkpoint filename.
    original_source=parse_reply(reply.read_text(encoding="utf8"))
    need(hashlib.sha256(original_source.encode("utf8")).hexdigest()==
         receipt.get("candidate_sha256"),
         "Candidate not reproducible from original immutable model reply")
    target=Path(job["repo"])/job["target"]
    test=Path(job["repo"])/job["test"]
    context=Path(job["repo"])/job["context_path"]
    need(sha(target)==receipt.get("candidate_sha256")
         and sha(test)==job["test_sha256"]
         and sha(context)==job["context_sha256"]
         and job["paid_api"] is False
         and job["student_publication"] is False
         and Path(job["repo"]).is_dir()
         and not Path(job["repo"]).is_symlink(),
         "Untrusted code candidate/test/source association")
    # Always re-run the restricted AST verifier on the actual candidate.
    validate_source(target.read_text(encoding="utf8"))
    return job,receipt


def _pr_lookup(branch,head_sha):
    need(re.fullmatch(r"auto/promote_[a-z0-9_]+_[a-f0-9]{8}",branch)
         and SHA40.fullmatch(head_sha),
         "Unpinned PR discovery contract")
    result=run(["gh","pr","list","--repo",REPO,
                "--head",branch,"--state","all","--limit","100",
                "--json","number,state,headRefOid,baseRefName"])
    values=json.loads(result)
    need(type(values) is list and len(values)<=1,
         "Ambiguous multiple GitHub pull requests for original branch")
    if not values:return None
    pr=values[0]
    need(pr.get("headRefOid")==head_sha
         and pr.get("baseRefName")=="main"
         and type(pr.get("number")) is int,
         "Existing PR source head changed after original claimed request")
    return pr


def _failed_exact_head_ci(head_sha,fetch):
    """Never conflate a completed failed Windows run with a pending run."""
    try:
        value=fetch(f"repos/{REPO}/actions/runs?head_sha={head_sha}&event=pull_request&per_page=100")
    except (ValueError,OSError,KeyError,TypeError):
        return False
    runs=value.get("workflow_runs")
    if type(runs) is not list:return False
    return any(r.get("head_sha")==head_sha
               and r.get("status")=="completed"
               and r.get("conclusion") not in (None,"success")
               for r in runs)


def promote(*,job_path:Path,root:Path,main_repo:Path,
            promotions:Path,merge_ci:bool=True,run_cmd=run,
            fetch=api,lookup=_pr_lookup) -> dict:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "Verified code promotion absent from executable repair registry")
    root=Path(root).absolute()
    main_repo=Path(main_repo).absolute()
    promotions=Path(promotions).absolute()
    need(main_repo.is_dir() and not main_repo.is_symlink()
         and promotions.is_dir() and not promotions.is_symlink()
         and not promotions.is_relative_to(main_repo)
         and root.is_dir() and not root.is_symlink(),
         "Independent code staging/checkpoint directories required")
    job,source=_original(job_path,root)
    ident=job["job_id"]
    saved=promotions/(ident+".json")
    source_hash=source["candidate_sha256"]
    state=read(saved) if saved.exists() else None
    if state:
        need(state.get("job_sha256")==sha(job_path)
             and state.get("source_sha256")==source_hash
             and state.get("original_reply_sha256")==source["model_reply_sha256"],
             "Promotion checkpoint belongs to a changed source/model request")
        if state["status"] in DONE:return state
    else:
        state={"schema_version":1,"status":"SOURCE_VERIFIED",
               "job_id":ident,"job_sha256":sha(job_path),
               "source_sha256":source_hash,
               "original_reply_sha256":source["model_reply_sha256"],
               "model_sends":0,"paid_api_requests":0,
               "student_publication_authorized":False}
        save(saved,state)

    # Always check GitHub's actual current main before ANY new PR branch.
    main=fetch("repos/"+REPO+"/commits/main")
    main_sha=main.get("sha")
    need(type(main_sha) is str and SHA40.fullmatch(main_sha)
         and git(main_repo,"rev-parse","HEAD")==main_sha
         and git(main_repo,"status","--porcelain")=="",
         "Original promotion base must be current clean protected main")
    current_target=main_repo/job["target"]
    current_test=main_repo/job["test"]
    if (current_target.is_file() and current_test.is_file()
            and sha(current_target)==source_hash
            and sha(current_test)==job["test_sha256"]):
        state["status"]="ALREADY_ON_VERIFIED_MAIN"
        state["verified_main_sha"]=main_sha
        save(saved,state);return state

    worktrees=promotions/"worktrees"
    need(worktrees.is_dir() and not worktrees.is_symlink(),
         "Trusted isolated Git worktrees parent missing")
    branch="auto/promote_"+ident+"_"+source_hash[:8]
    target=worktrees/("promote_"+ident)
    if "promotion_base_sha" not in state:
        need(not target.exists(),"Original candidate worktree was not claimed")
        state.update(status="WORKTREE_CLAIMED",
                     promotion_base_sha=main_sha,branch=branch)
        save(saved,state)
    else:
        need(state["promotion_base_sha"]==main_sha,
             "Protected main changed during PR preparation: source-rebase gate")
    if not target.exists():
        run_cmd(["git","-C",str(main_repo),"worktree","add","-b",
                 branch,str(target),main_sha],timeout=90)
    need(target.is_dir() and not target.is_symlink()
         and git(target,"branch","--show-current")==branch,
         "Original promotion branch not anchored to Git worktree")

    for name,origin in ((job["target"],Path(job["repo"])/job["target"]),
                        (job["test"],Path(job["repo"])/job["test"])):
        dest=target/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        need(not dest.is_symlink(),"Promotion target path redirected")
        if dest.is_file():
            need(sha(dest)==sha(origin),
                 "Previously staged candidate differs from original model")
        else:
            with dest.open("xb") as f:
                f.write(origin.read_bytes());f.flush();os.fsync(f.fileno())
    need(sha(target/job["target"])==source_hash
         and sha(target/job["test"])==job["test_sha256"],
         "Copied promoted candidate did not preserve source/test SHA")

    if "promotion_commit_sha" not in state:
        result=subprocess.run(
            [sys.executable,"-m","pytest","-q",job["test"]],
            cwd=target,capture_output=True,text=True,timeout=420)
        need(result.returncode==0,
             "Original independent tests fail in clean promotion checkout: "+
             result.stdout[-250:])
        run_cmd(["git","-C",str(target),"add","--",
                 job["target"],job["test"]])
        run_cmd(["git","-C",str(target),"diff","--cached","--check"])
        run_cmd(["git","-C",str(target),"commit","-m",
                 "Autopromote source-tested "+ident])
        state["promotion_commit_sha"]=git(target,"rev-parse","HEAD")
        need(SHA40.fullmatch(state["promotion_commit_sha"]),
             "New candidate commit lacks immutable source identity")
        state["status"]="CANDIDATE_COMMITTED"
        save(saved,state)
    commit=state["promotion_commit_sha"]
    need(git(target,"rev-parse","HEAD")==commit
         and git(target,"status","--porcelain")=="",
         "Committed candidate changed after independent validation")

    # PUSH: one irreversible original claim, then remote-readback on restart.
    remote=run_cmd(["git","-C",str(target),"ls-remote","origin",
                    "refs/heads/"+branch])
    remote_sha=remote.split()[0] if remote else None
    if remote_sha is None and state.get("push_claimed"):
        state["status"]=REMOTE_HOLD
        state["reason"]="PUSH_RESULT_UNCERTAIN_NO_RESUBMISSION"
        save(saved,state);return state
    if remote_sha is None:
        state["push_claimed"]=True
        state["status"]="GITHUB_PUSH_CLAIMED"
        save(saved,state)
        try:
            run_cmd(["git","-C",str(target),"push","origin",
                     commit+":refs/heads/"+branch],timeout=120)
        except (ValueError,OSError,subprocess.TimeoutExpired):
            # Must reread remote; NEVER repeat unknown original push.
            remote=run_cmd(["git","-C",str(target),"ls-remote","origin",
                            "refs/heads/"+branch])
            if not remote or remote.split()[0]!=commit:
                state["status"]=REMOTE_HOLD
                state["reason"]="PUSH_RESULT_UNCERTAIN_NO_RESUBMISSION"
                save(saved,state);return state
        remote_sha=commit
    need(remote_sha==commit,"GitHub candidate branch identity diverged")
    state["status"]="GITHUB_BRANCH_VERIFIED"
    save(saved,state)

    pr=lookup(branch,commit)
    if pr is None and state.get("pr_claimed"):
        state["status"]=REMOTE_HOLD
        state["reason"]="CREATE_PR_RESULT_UNCERTAIN_NO_RESUBMISSION"
        save(saved,state);return state
    if pr is None:
        state["pr_claimed"]=True
        state["status"]="CREATE_GITHUB_PR_CLAIMED"
        save(saved,state)
        try:
            run_cmd(["gh","pr","create","--repo",REPO,"--base","main",
                     "--head",branch,
                     "--title","[AutoCode] Verified "+ident,
                     "--body",
                     "Original Selenium one-Send source SHA "+source_hash+
                     ". Independent test SHA "+job["test_sha256"]+
                     ". Zero paid Gemini API calls. No scientific or student "
                     "publication acceptance. Exact-head Windows CI required."],
                    timeout=90)
        except (ValueError,OSError,subprocess.TimeoutExpired):
            pass
        pr=lookup(branch,commit)
        if pr is None:
            state["status"]=REMOTE_HOLD
            state["reason"]="CREATE_PR_RESULT_UNCERTAIN_NO_RESUBMISSION"
            save(saved,state);return state
    number=pr["number"]
    state["pr_number"]=number
    state["status"]="GITHUB_PR_VERIFIED"
    save(saved,state)
    if pr["state"]=="MERGED":
        # Exact head check from GitHub, not an untrusted local label.
        final=fetch(f"repos/{REPO}/pulls/{number}")
        need(final.get("head",{}).get("sha")==commit
             and final.get("merged_at"),"Merged PR provenance missing")
        state["status"]="MERGED_AWAITING_GUARDED_CUTOVER"
        state["merge_commit_sha"]=final["merge_commit_sha"]
        save(saved,state);return state
    need(pr["state"]=="OPEN",
         "Original PR closed without merge; no further mutation")
    if not merge_ci:
        return state
    # CI can take minutes. Do not rerun a model or GitHub mutation while
    # waiting. Only the existing exact-head gate is authorized to merge.
    try:
        proof=exact_ci_inspect(pr_number=number)
    except (ValueError,KeyError,TypeError,OSError,subprocess.TimeoutExpired):
        state["status"]=("GITHUB_WINDOWS_CI_FAILED_HELD"
                         if _failed_exact_head_ci(commit,fetch)
                         else "GITHUB_WINDOWS_CI_AWAITING_EVIDENCE")
        save(saved,state);return state
    need(proof["status"]==PASS and proof["head_sha"]==commit,
         "Original protected GitHub CI result mismatched source")
    if not state.get("merge_claimed"):
        state["merge_claimed"]=True
        state["status"]="EXACT_HEAD_GITHUB_MERGE_CLAIMED"
        save(saved,state)
        try:
            outcome=exact_ci_gate(pr_number=number,perform_merge=True)
            if outcome.get("status")==MERGED:
                state["merge_commit_sha"]=outcome["merge_commit_sha"]
        except (ValueError,KeyError,TypeError,OSError,subprocess.TimeoutExpired):
            pass
    # A remote merge outcome, even after error, is resolved by fresh GitHub
    # REST evidence, never by issuing another merge request.
    final=fetch(f"repos/{REPO}/pulls/{number}")
    if (final.get("head",{}).get("sha")==commit
            and final.get("merged_at")
            and final.get("state")=="closed"):
        state["status"]="MERGED_AWAITING_GUARDED_CUTOVER"
        state["merge_commit_sha"]=final["merge_commit_sha"]
        save(saved,state);return state
    state["status"]=REMOTE_HOLD
    state["reason"]="MERGE_OUTCOME_UNCERTAIN_NO_RESUBMISSION"
    save(saved,state)
    return state
