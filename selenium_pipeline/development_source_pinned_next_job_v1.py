"""Stage the next independently specified MicroGen code job without human prompting.

Only immutable, SHA-pinned, pre-authored test specifications in a local
catalog may become a code-generation request. Does not call the model, GitHub
merge or publish. Existing unsafe/uncertain jobs are NEVER replayed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from .development_persistent_selenium_author_v1 import validate_job
from .recovery_registry import lookup_mechanism

KIND="autonomous_independent_test_job_selection"
SIGNATURE="CODE_AUTHOR_RUNNING_WITHOUT_NEW_SOURCE_PINNED_ELIGIBLE_JOB"
MECHANISM="STAGE_APPROVED_TEST_SHA_TO_DISTINCT_GIT_WORKTREE_ONCE"
RENEW_SIGNATURE="SOURCE_PINNED_CATALOG_EXHAUSTED_LOCAL_COPY_WHILE_REVIEWED_GIT_MAIN_ADVANCES"
RENEW_MECHANISM="ADMIT_CLEAN_MAIN_TRACKED_CATALOG_SPECS_NO_REPLAY"
SCHEMA="MICROGEN_SOURCE_PINNED_NEXT_JOB_CATALOG_V1"
CATALOG_SHA256="cbec12b6286e0d9225cb8b7ca8933f6c71dd31b21810e4f074f569ac6ca46a7c"
SHA64=re.compile(r"^[a-f0-9]{64}$")
ID=re.compile(r"^[a-z][a-z0-9_]{6,50}$")
MAX_SPECS=20


def need(value,reason):
    if not value:
        raise ValueError(reason)


def sha(path):
    need(path.is_file() and not path.is_symlink(),"Missing or redirected original test")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cmd(args,timeout=60):
    out=subprocess.run(args,text=True,capture_output=True,timeout=timeout)
    need(out.returncode==0,
         "Local Git or GitHub main identity unavailable: "+out.stderr[-180:])
    return out.stdout.strip()


def _catalog(path, *, reviewed_main=False):
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_size<=40000,
         "Missing or oversized approved independent-test catalog")
    if not reviewed_main:
        need(sha(path)==CATALOG_SHA256,
             "Approved next-task catalog SHA differs from reviewed Git source")
    value=json.loads(path.read_text(encoding="utf8"))
    need(type(value) is dict and set(value)=={
        "schema_version","status","jobs","paid_api_authorized",
        "student_publication_authorized"}
         and value["schema_version"]==1 and value["status"]==SCHEMA
         and value["paid_api_authorized"] is False
         and value["student_publication_authorized"] is False
         and type(value["jobs"]) is list
         and 1<=len(value["jobs"])<=MAX_SPECS,
         "Independent code task catalog not safely admitted")
    keys=set()
    for row in value["jobs"]:
        need(type(row) is dict and set(row)=={
            "job_id","spec_path","spec_sha256","test","target",
            "instruction","selenium_mode"}
             and type(row["job_id"]) is str and ID.fullmatch(row["job_id"])
             and row["job_id"] not in keys
             and type(row["spec_path"]) is str
             and re.fullmatch(r"specs/[a-z0-9_]+\.py",row["spec_path"])
             and type(row["spec_sha256"]) is str
             and SHA64.fullmatch(row["spec_sha256"])
             and type(row["test"]) is str
             and re.fullmatch(r"tests/test_[a-z0-9_]+\.py",row["test"])
             and type(row["target"]) is str
             and re.fullmatch(r"selenium_pipeline/[a-z0-9_]+\.py",
                              row["target"])
             and type(row["instruction"]) is str
             and 60<=len(row["instruction"])<=3500
             and row["selenium_mode"] in ("hydrogen","neon"),
             "Invalid original next-code task contract")
        keys.add(row["job_id"])
    return value


def select(*,catalog_path:Path,backlog_root:Path,repo_root:Path,
           git=cmd):
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "New source-pinned job selection repair missing from registry")
    catalog_path=Path(catalog_path).absolute()
    backlog_root=Path(backlog_root).absolute()
    repo_root=Path(repo_root).absolute()
    need(backlog_root.is_dir() and not backlog_root.is_symlink()
         and repo_root.is_dir() and not repo_root.is_symlink()
         and (backlog_root/"inbox").is_dir()
         and (backlog_root/"state").is_dir()
         and not (backlog_root/"inbox").is_symlink()
         and not repo_root.is_relative_to(backlog_root)
         and not backlog_root.is_relative_to(repo_root),
         "Source/main and original code-job inbox not isolated")
    current=git(["git","-C",str(repo_root),"rev-parse","HEAD"])
    remote=git(["gh","api","repos/tlyoon/MicroGen_AI_Web/commits/main",
                "--jq",".sha"])
    need(re.fullmatch(r"[a-f0-9]{40}",current) and remote==current
         and git(["git","-C",str(repo_root),"status","--porcelain"])=="",
         "Only clean exact-current protected GitHub main can stage new code")
    # Prefer the code-reviewed catalog in the exact clean GitHub main tree.
    # This allows new independent test jobs to become eligible after CI and
    # guarded deployment without editing an unreviewed mutable local catalog.
    # Keep the legacy hardcoded-SHA catalog for older isolated installations.
    main_catalog=repo_root/"development_specs"/"approved_source_jobs_v1.json"
    reviewed_main=main_catalog.exists() or main_catalog.is_symlink()
    if reviewed_main:
        need(lookup_mechanism(KIND,RENEW_SIGNATURE)==RENEW_MECHANISM,
             "Verified-main source-catalog renewal absent from registry")
        need(main_catalog.is_file() and not main_catalog.is_symlink()
             and not main_catalog.parent.is_symlink()
             and git(["git","-C",str(repo_root),"ls-files",
                      "--error-unmatch","--",
                      "development_specs/approved_source_jobs_v1.json"])
                 =="development_specs/approved_source_jobs_v1.json",
             "Reviewed main catalog was not committed to verified main")
        catalog_path=main_catalog
    catalog=_catalog(catalog_path,reviewed_main=reviewed_main)
    for row in catalog["jobs"]:
        ident=row["job_id"]
        manifest=backlog_root/"inbox"/(ident+".json")
        need(not manifest.is_symlink(),"Original code job manifest redirected")
        if manifest.exists():
            # Never modify or recycle an existing original job identity.
            need(manifest.is_file(),"Original job path not a regular file")
            continue
        spec=(catalog_path.parent/row["spec_path"]).absolute()
        need(spec.is_relative_to(catalog_path.parent)
             and not spec.parent.is_symlink(),
             "Approved independent test escaped original catalog")
        need(spec.is_file() and not spec.is_symlink()
             and sha(spec)==row["spec_sha256"]
             and spec.stat().st_size<12000,
             "Original independent test specimen changed")
        if reviewed_main:
            relative_spec=spec.relative_to(repo_root).as_posix()
            need(git(["git","-C",str(repo_root),"ls-files",
                      "--error-unmatch","--",relative_spec])
                 ==relative_spec,
                 "Uncommitted original independent test cannot be staged")
        # Preserve exact first approved main source under one new branch.
        worktrees=backlog_root.parent/"MICROGEN_AUTONOMOUS_CODE_WORKTREES_V1"
        need(worktrees.is_dir() and not worktrees.is_symlink()
             and not worktrees.is_relative_to(backlog_root)
             and not backlog_root.is_relative_to(worktrees),
             "Independent source-authoring worktree parent not present")
        repo=worktrees/("job_"+ident)
        need(not repo.exists() and not repo.is_symlink(),
             "Another process may already own this code-generation branch")
        branch="feature/approved_"+ident
        # The catalog is owner-authored; commit the independent test BEFORE
        # any model request. If preparation fails, do not mutate the job inbox.
        git(["git","-C",str(repo_root),"worktree","add","-b",branch,
             str(repo),"HEAD"],timeout=90)
        path=repo/row["test"]
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            need(not path.parent.is_symlink(),
                 "Original independent test destination redirected")
            with path.open("xb") as stream:
                stream.write(spec.read_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            need(sha(path)==row["spec_sha256"],
                 "Independent test copy lost identity")
            git(["git","-C",str(repo),"add","--",row["test"]])
            git(["git","-C",str(repo),"commit","-m",
                 "Pin independent source-test "+ident])
            base=git(["git","-C",str(repo),"rev-parse","HEAD"])
            job={
                "schema_version":1,"project":"MicroGen_AI_Web",
                "job_id":ident,"authorized":True,
                "repo":str(repo),"base_sha":base,"branch":branch,
                "target":row["target"],"target_original_sha256":None,
                "test":row["test"],"test_sha256":row["spec_sha256"],
                "context_path":row["test"],
                "context_sha256":row["spec_sha256"],
                "instruction":row["instruction"],
                "selenium_mode":row["selenium_mode"],
                "max_wait_seconds":150,
                "browser_model_claims":1,
                "paid_api":False,"student_publication":False,
            }
            payload=(json.dumps(job,sort_keys=True,indent=2)+"\n").encode("utf8")
            # Source-pinned job identity is claimed ONCE atomically.
            with manifest.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            validate_job(root=backlog_root,file=manifest)
        except Exception:
            # Never delete a partially written worktree or untrusted claim
            # whose side-effect may have occurred. Surface to recovery.
            raise
        return {"status":"NEW_ELIGIBLE_CODING_JOB_STAGED",
                "job":ident,"source_commit":base,
                "manifest_sha256":sha(manifest),
                "test_sha256":row["spec_sha256"],
                "model_sends":0,"paid_api_requests":0,
                "student_publication_authorized":False}
    # When the pre-reviewed finite catalog is exhausted, construct new
    # independent technical tests from verified unresolved G2/G3 milestones.
    # The compiler itself is reviewed on protected GitHub main and requires
    # a live source checkpoint; it never generates scientific acceptance.
    from .development_g2g3_requirement_task_factory_v1 import derive
    return derive(backlog_root=backlog_root,repo_root=repo_root,git=git)
