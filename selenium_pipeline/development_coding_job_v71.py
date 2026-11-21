"""On-demand, single-send, isolated MicroGen v7.1 code-repair candidate.

NOT part of the always-on OFFLINE Windows daemon. A verified candidate is
NOT automatically pushed, merged, published, or approved for G2/G3/release.
Only the exact source-bound job may be given a workspace-write Codex session.
Uncertain Codex outcomes are quarantined rather than blindly retried.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .development_continuity_executor_v71 import (
    _atomic_json, _exclusive, _read_json, _sha,
)

ALLOWED_ROOTS = ("selenium_pipeline/", "tests/", "docs/")
HEX40 = re.compile(r"[0-9a-f]{40}")
JOB_ID = re.compile(r"[a-z][a-z0-9_-]{2,55}")
BRANCH = re.compile(r"feature/pr[0-9]+-[a-z0-9-]{8,90}")
SAFE_FILE = re.compile(r"[a-zA-Z0-9_.\-/]{5,170}")
STATUS = ("EXTERNAL_MODEL_RESULT_UNCERTAIN",
          "MODEL_RESPONDED_UNVERIFIED", "LOCAL_CODING_CANDIDATE_VERIFIED",
          "MODEL_NO_SOURCE_DIFF_QUARANTINED",
          "MODEL_SOURCE_CHANGE_QUARANTINED")
REGISTRY = Path(__file__).with_name(
    "development_coding_recovery_registry_v71.json")
RECOVERY_HANDLERS = {
    "MODEL_RESPONDED_NO_SOURCE_DIFF":
        "QUARANTINE_NOOP_PRESERVE_RESPONSE_AND_ADVANCE_OFFLINE_BACKLOG",
    "MODEL_MODIFIED_UNAPPROVED_FILES":
        "QUARANTINE_UNTRUSTED_DIFF_NEVER_PUSH_OR_PUBLISH",
    "MODEL_RESPONDED_TEST_FAILED":
        "RETEST_EXISTING_RESPONSE_WITH_ZERO_MODEL_REPLAY",
    "OLDER_MAIN_MODEL_RESPONSE_RECONCILIATION":
        "ATTEST_ORIGINAL_REPLIED_JOB_WITH_ZERO_NEW_MODEL_SENDS",
    "CODEX_HOST_EFFECTIVE_READONLY":
        "PERSIST_HOST_POLICY_CAPABILITY_BLOCK_NO_ADDITIONAL_MODEL_SENDS",
}


def require_recovery(signature:str, *,registry:Path|None=None)->str:
    file=Path(registry or REGISTRY)
    require(file.is_file() and not file.is_symlink()
            and 1 <= file.stat().st_size <= 4096,
            "Missing executable source-bound coding recovery registry")
    config=json.loads(file.read_text(encoding="utf8"))
    expected={
        "schema_version":1,
        "status":"MICROGEN_V71_SOURCE_BOUND_CODING_RECOVERY_V1",
        "enabled":True,
        "max_additional_model_calls":0,
        "may_create_or_merge_pr":False,
        "may_release_students":False,
        "handlers":RECOVERY_HANDLERS,
    }
    require(config==expected and signature in RECOVERY_HANDLERS,
            "Unregistered or modified source-bound coding recovery")
    return RECOVERY_HANDLERS[signature]


def require(value: bool, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                       text=True, timeout=35)
    require(p.returncode == 0, "Git source admission failed: " + p.stderr[-300:])
    return p.stdout.strip()


def admit_job(*, job_path: Path, repo: Path, state_dir: Path,
              checkpoint_root: Path, verify_remote: bool = True,
              allow_existing_candidate: bool = False) -> dict:
    """All paths and requests are immutable before any external model call."""
    job_path, repo, state_dir, checkpoint_root = (
        Path(p).resolve() for p in (job_path, repo, state_dir, checkpoint_root))
    require(checkpoint_root.is_dir() and repo.is_dir()
            and repo != checkpoint_root and repo.is_relative_to(checkpoint_root)
            and state_dir.is_relative_to(checkpoint_root)
            and not state_dir.is_relative_to(repo)
            and job_path.is_file() and not job_path.is_symlink()
            and job_path.is_relative_to(checkpoint_root)
            and (repo / ".git").exists() and not (repo / ".git").is_symlink(),
            "Code authoring requires an isolated checkpoint worktree")
    job = _read_json(job_path)
    require(set(job) == {"schema_version","project","job_id","main_sha",
                         "branch","instruction","allowed_files",
                         "required_tests","max_seconds","authorized",
                         "codex_sha256"},
            "Unexpected coding job fields")
    require(job["schema_version"] == 1 and job["project"]=="MicroGen_AI_Web"
            and job["authorized"] is True
            and isinstance(job["job_id"], str)
            and bool(JOB_ID.fullmatch(job["job_id"]))
            and isinstance(job["main_sha"], str)
            and bool(HEX40.fullmatch(job["main_sha"]))
            and type(job["codex_sha256"]) is str
            and bool(re.fullmatch(r"[a-f0-9]{64}",job["codex_sha256"]))
            and isinstance(job["branch"], str)
            and bool(BRANCH.fullmatch(job["branch"]))
            and isinstance(job["instruction"], str)
            and 40 <= len(job["instruction"]) <= 8000
            and isinstance(job["max_seconds"], int)
            and 30 <= job["max_seconds"] <= 1200,
            "Missing explicit bounded coding authorization")
    files = job["allowed_files"]
    tests = job["required_tests"]
    require(type(files) is list and 1 <= len(files) <= 12
            and len(set(files)) == len(files)
            and type(tests) is list and 1 <= len(tests) <= 12
            and len(set(tests)) == len(tests),
            "Code change or regression allowlist is invalid")
    for name in files:
        require(type(name) is str and SAFE_FILE.fullmatch(name)
                and not name.startswith(("/",".","\\"))
                and ".." not in Path(name).parts
                and "\\" not in name
                and any(name.startswith(p) for p in ALLOWED_ROOTS)
                and Path(name).suffix in (".py",".json",".md"),
                "Code files may only be approved relative sources")
    for test in tests:
        require(type(test) is str and SAFE_FILE.fullmatch(test)
                and test.startswith("tests/") and test.endswith(".py")
                and ".." not in Path(test).parts
                and "\\" not in test
                and ((repo / test).is_file() or test in files),
                "Cannot inject arbitrary test or shell command")
    require((allow_existing_candidate or _git(repo,"status","--porcelain")=="")
            and _git(repo,"rev-parse","HEAD")==job["main_sha"]
            and _git(repo,"branch","--show-current")==job["branch"],
            "Code authoring may begin only on a source-pinned feature branch")
    if verify_remote:
        result = subprocess.run(
            ["git","-C",str(repo),"ls-remote","origin","refs/heads/main"],
            capture_output=True,text=True,timeout=30)
        require(result.returncode==0
                and result.stdout.split()
                and result.stdout.split()[0]==job["main_sha"],
                "Code branch is not based on current GitHub main")
    return {"job":job,"job_sha256":_sha(job_path),"repo":repo,
            "state_dir":state_dir,"job_path":job_path}


def _codex_command(codex: Path, repo: Path) -> list[str]:
    require(codex.is_file() and not codex.is_symlink()
            and codex.name.casefold() in ("codex.cmd","codex.exe","codex"),
            "Untrusted external coding program")
    return [str(codex),"exec","--ephemeral","--ignore-user-config",
            "--sandbox","workspace-write",
            "-c","sandbox_workspace_write.network_access=false",
            "-C",str(repo),"-"]


def changed_files(repo: Path) -> list[str]:
    """Reject renames and untracked unknown files; no hidden tree modification."""
    status = _git(repo,"status","--porcelain")
    names = []
    for line in status.splitlines():
        require(len(line)>=4 and line[2]==" " and " -> " not in line,
                "Renamed or malformed source change is not allowed")
        names.append(line[3:].strip().strip('"'))
    return names


def _verify_changes(repo: Path, job: dict) -> dict:
    altered = changed_files(repo)
    allowed = set(job["allowed_files"])
    require(bool(altered) and len(set(altered))==len(altered)
            and set(altered).issubset(allowed),
            "Coding worker changed outside its source allowlist")
    for name in altered:
        path = repo/name
        require(path.is_file() and not path.is_symlink()
                and path.resolve().is_relative_to(repo),
                "Only regular, allowed source files may be modified")
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf8"),filename=str(path))
    check=subprocess.run(["git","-C",str(repo),"diff","--check"],
                         capture_output=True,text=True,timeout=30)
    require(check.returncode==0,"Modified source diff contains whitespace errors")
    return {"changed_files":altered,
            "file_sha256":{name:_sha(repo/name) for name in altered}}


def _run_model(command: list[str], prompt: str, *, cwd: Path,
               timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(command,input=prompt,text=True,cwd=cwd,
                          capture_output=True,timeout=timeout)


def _verify_tests(*,repo:Path,job:dict,runner=None)->dict:
    command=[sys.executable,"-m","pytest","-q",*job["required_tests"]]
    run=runner or subprocess.run
    r=run(command,cwd=repo,capture_output=True,text=True,timeout=600)
    require(r.returncode==0,"Coding candidate failed mandatory regressions")
    return {"status":"LOCAL_TESTS_PASSED",
            "test_modules":job["required_tests"],
            "test_output_excerpt":(r.stdout or "")[-2400:]}


def run_once(*,job_path:Path,repo:Path,state_dir:Path,checkpoint_root:Path,
             codex_path:Path, model_runner=None,test_runner=None,
             verify_remote:bool=True)->dict:
    """One model invocation max per immutable job; restart never repeats it."""
    previous=Path(state_dir).resolve()/"coding_job_state.json"
    admission=admit_job(job_path=job_path,repo=repo,state_dir=state_dir,
                        checkpoint_root=checkpoint_root,
                        verify_remote=verify_remote,
                        allow_existing_candidate=previous.is_file()
                        and not previous.is_symlink())
    job,repo,state_dir=admission["job"],admission["repo"],admission["state_dir"]
    codex_path=Path(codex_path).resolve()
    require(codex_path.is_file() and not codex_path.is_symlink()
            and _sha(codex_path)==job["codex_sha256"],
            "Authorized Codex CLI wrapper SHA changed; do not make model call")
    state_dir.mkdir(parents=True,exist_ok=True)
    with _exclusive(state_dir):
        state_file=state_dir/"coding_job_state.json"
        if state_file.exists():
            state=_read_json(state_file)
            require(state.get("job_sha256")==admission["job_sha256"],
                    "Original coding job changed after model claim")
            if state["status"]=="EXTERNAL_MODEL_RESULT_UNCERTAIN":
                raise RuntimeError(
                    "Model submission may have been consumed; reconcile, never resend")
            require(state["status"] in STATUS,"Unknown coding checkpoint")
            if state["status"] in (
                "MODEL_NO_SOURCE_DIFF_QUARANTINED",
                "MODEL_SOURCE_CHANGE_QUARANTINED"):
                require(state.get("recovery_action") in RECOVERY_HANDLERS.values(),
                        "Unknown quarantined coding job")
                return state
            if state["status"]=="LOCAL_CODING_CANDIDATE_VERIFIED":
                prior=state.get("evidence")
                require(type(prior) is dict
                        and type(prior.get("file_sha256")) is dict,
                        "No preserved code acceptance")
                verified=_verify_changes(repo,job)
                require(verified["file_sha256"]==prior["file_sha256"]
                        and verified["changed_files"]==prior["changed_files"],
                        "Accepted source changed after checkpoint admission")
                return state
        else:
            from .development_coding_provider_health_v71 import (
                require_workspace_write_capability)
            require_workspace_write_capability(
                checkpoint_root=Path(checkpoint_root),
                cli_sha256=job["codex_sha256"])
            cmd=_codex_command(Path(codex_path).resolve(),repo)
            state={"schema_version":1,"status":"EXTERNAL_MODEL_RESULT_UNCERTAIN",
                   "job_sha256":admission["job_sha256"],
                   "main_sha":job["main_sha"],
                   "repo":str(repo),
                   "model_invocations_claimed":1,
                   "candidate_pr_pushed":False,"student_release":False}
            _atomic_json(state_file,state)
            runner=model_runner or _run_model
            try:
                guard=(
                    "This is a bounded source-only coding task. Never use "
                    "network/remote services, credentials, browser automation, "
                    "Task Scheduler, provider Sends, publication or Git pushes. "
                    "Edit ONLY these explicitly allowed files: "
                    + ", ".join(job["allowed_files"])
                    + ". End with a concise change summary.\n\n")
                result=runner(cmd,guard+job["instruction"],cwd=repo,
                              timeout=job["max_seconds"])
            except (OSError,subprocess.TimeoutExpired) as exc:
                raise RuntimeError(
                    "Coding model outcome uncertain, no replay permitted") from exc
            require(result.returncode==0,
                    "Coding model outcome uncertain, no replay permitted")
            state["status"]="MODEL_RESPONDED_UNVERIFIED"
            # Never persist untrusted model text or possible credentials in
            # the restart checkpoint. Evidence is hashed and output bounded.
            response=str(result.stdout or "")
            state["model_output_sha256"]=hashlib.sha256(
                response.encode("utf8")).hexdigest()
            state["model_output_chars"]=len(response)
            _atomic_json(state_file,state)
            # Host policy can silently downgrade a requested workspace-write
            # session to read-only. A successful text response is not proof
            # that any coding capability existed. Persist a shared blocker
            # before considering another model job.
            from .development_coding_provider_health_v71 import (
                is_host_readonly, persist_host_denial)
            if is_host_readonly(str(result.stderr or "")):
                remedy=require_recovery("CODEX_HOST_EFFECTIVE_READONLY")
                health=persist_host_denial(
                    checkpoint_root=Path(checkpoint_root),
                    job_sha256=admission["job_sha256"],
                    cli_sha256=job["codex_sha256"],
                    stderr=str(result.stderr))
                state["status"]="MODEL_NO_SOURCE_DIFF_QUARANTINED"
                state["failure_class"]="CODEX_HOST_EFFECTIVE_READONLY"
                state["recovery_action"]=remedy
                state["provider_capability_status"]=health["status"]
                state["next_independent_workstream_eligible"]=True
                state["candidate_pr_pushed"]=False
                state["student_release"]=False
                _atomic_json(state_file,state)
                return state
        # A response with no source change is a *real* model no-op, not a
        # successful code repair. Never re-Send the original model request.
        # Persist a registered source-bound quarantine and let the parent
        # roadmap advance independent workstreams.
        try:
            evidence=_verify_changes(repo,job)
        except (ValueError,SyntaxError) as exc:
            try:
                altered=changed_files(repo)
            except ValueError:
                altered=["UNTRUSTED_RENAME_OR_GIT_STATUS"]
            signature=("MODEL_RESPONDED_NO_SOURCE_DIFF" if not altered
                       else "MODEL_MODIFIED_UNAPPROVED_FILES")
            remedy=require_recovery(signature)
            state["status"]=(
                "MODEL_NO_SOURCE_DIFF_QUARANTINED" if not altered
                else "MODEL_SOURCE_CHANGE_QUARANTINED")
            state["recovery_action"]=remedy
            state["failure_class"]=signature
            state["changed_files_observed"]=altered[:12]
            state["model_invocations_claimed"]=1
            state["candidate_pr_pushed"]=False
            state["next_independent_workstream_eligible"]=True
            state["student_release"]=False
            _atomic_json(state_file,state)
            return state
        try:
            tests=_verify_tests(repo=repo,job=job,runner=test_runner)
        except ValueError:
            state["recovery_action"]=require_recovery(
                "MODEL_RESPONDED_TEST_FAILED")
            state["status"]="MODEL_RESPONDED_UNVERIFIED"
            state["next_model_send_authorized"]=False
            _atomic_json(state_file,state)
            raise
        state["status"]="LOCAL_CODING_CANDIDATE_VERIFIED"
        state["evidence"]={**evidence,**tests,"main_sha":job["main_sha"]}
        _atomic_json(state_file,state)
        return state


def reconcile_existing_response(*,job_path:Path,repo:Path,state_dir:Path,
                               checkpoint_root:Path,codex_path:Path,
                               test_runner=None)->dict:
    """Reconcile already returned model output from an older admitted main.

    The saved historical job remains source- and branch-locked; remote main
    advancement cannot force a duplicate model Send. Never accepts an
    unfinished or possibly consumed request as eligible for regeneration.
    """
    state_file=Path(state_dir).resolve()/"coding_job_state.json"
    require(state_file.is_file() and not state_file.is_symlink(),
            "No original model response claim for safe reconciliation")
    prior=_read_json(state_file)
    require(prior.get("status") in (
                "MODEL_RESPONDED_UNVERIFIED",
                "MODEL_NO_SOURCE_DIFF_QUARANTINED",
                "MODEL_SOURCE_CHANGE_QUARANTINED",
                "LOCAL_CODING_CANDIDATE_VERIFIED"),
            "Only a known completed model response may be reconciled")
    remedy=require_recovery("OLDER_MAIN_MODEL_RESPONSE_RECONCILIATION")
    def forbidden_model_invocation(*args,**kwargs):
        raise RuntimeError("No provider Send is allowed during historical reconciliation")
    result=run_once(
        job_path=job_path,repo=repo,state_dir=state_dir,
        checkpoint_root=checkpoint_root,codex_path=codex_path,
        model_runner=forbidden_model_invocation,
        test_runner=test_runner,verify_remote=False)
    require(result.get("model_invocations_claimed")==1,
            "Unattributable old coding-model invocation")
    return result


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--job",type=Path,required=True)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--state-dir",type=Path,required=True)
    p.add_argument("--checkpoint-root",type=Path,required=True)
    p.add_argument("--codex",type=Path,required=True)
    actions=p.add_mutually_exclusive_group(required=True)
    actions.add_argument("--run",action="store_true")
    actions.add_argument("--reconcile-only",action="store_true")
    actions.add_argument("--attest-provider-denial",action="store_true")
    p.add_argument("--stderr-evidence",type=Path)
    a=p.parse_args(argv)
    try:
        if os.name=="nt":
            require(os.environ.get("COMPUTERNAME","").casefold()=="dell-115",
                    "Code-authoring boundary restricted to Dell-115")
            allowed_cli=(Path(os.environ["APPDATA"])/"npm"/"codex.cmd").resolve()
            require(Path(a.codex).resolve()==allowed_cli,
                    "Only the actual current-user Codex CLI is authorized")
        if a.attest_provider_denial:
            require(a.stderr_evidence is not None,
                    "Historical host denial needs original untrusted stderr")
            from .development_coding_provider_health_v71 import (
                reconcile_saved_denial)
            result=reconcile_saved_denial(
                checkpoint_root=a.checkpoint_root,
                job_path=a.job,state_dir=a.state_dir,
                cli_path=a.codex,stderr_path=a.stderr_evidence)
            print(json.dumps(result,indent=2))
            return 0  # Provider capability denied, not coding accepted.
        if a.reconcile_only:
            result=reconcile_existing_response(
                job_path=a.job,repo=a.repo,state_dir=a.state_dir,
                checkpoint_root=a.checkpoint_root,codex_path=a.codex)
        else:
            result=run_once(job_path=a.job,repo=a.repo,state_dir=a.state_dir,
                            checkpoint_root=a.checkpoint_root,codex_path=a.codex)
        print(json.dumps(result,indent=2))
        return (0 if result["status"]=="LOCAL_CODING_CANDIDATE_VERIFIED" else 2)
    except (RuntimeError,ValueError,OSError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status":"CODE_CANDIDATE_BLOCKED_NOT_RELEASED",
                          "error_type":type(exc).__name__,
                          "next_provider_sends_authorized":False,
                          "student_release":False}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
