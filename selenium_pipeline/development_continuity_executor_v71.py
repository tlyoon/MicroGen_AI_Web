"""MicroGen_AI_Web v7.1 project-wide *offline* forward-progress executor.

This is a durable, on-demand outer controller over existing source-bound,
read-only verification. It is NOT a self-authoring coding agent, a Gemini Send
dispatcher, a scheduled background service, or a release authorization.

Post-checkpoint handoff is observable via actual worker-start/result receipts.
Every task is explicitly allowlisted; no arbitrary shell, provider request,
paid action, repository mutation or student publication can be dispatched.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid


SCHEMA = 1
SAFE_ACTIONS = frozenset({
    "verify_file_sha256", "pytest_suite", "g2_source_reconciliation",
    "g2_review_preflight", "lecture_completion_readonly",
})
ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,55}$")
MAX_TASKS = 96
MAX_ATTEMPTS = 2
MAX_LOG_BYTES = 16000
RECOVERY_FILE = Path(__file__).with_name(
    "development_continuity_recovery_registry_v71.json")
RECOVERY_ACTIONS = {
    "PENDING_CLAIM_NO_WORKER":
        "REUSE_ORIGINAL_CLAIM_RUN_IDEMPOTENT_OFFLINE_ACTION",
    "ORPHANED_CHILD_RESULT":
        "RECONCILE_ORIGINAL_RESULT_BY_TOKEN_WITHOUT_RELAUNCH",
    "UNKNOWN_STARTED_CHILD":
        "AWAIT_ORIGINAL_RECEIPT_AND_FAN_OUT",
    "BOUNDED_OFFLINE_FAILURE":
        "QUARANTINE_ON_LIMIT_AND_SCAN_INDEPENDENT_WORKSTREAM",
    "AUTHORIZATION_GATE":
        "HOLD_UNAUTHORIZED_TASK_SCAN_INDEPENDENT_WORKSTREAM",
    "CONCURRENT_EXECUTOR_OWNER":
        "REFUSE_DUPLICATE_EXECUTOR_DISPATCH_WAIT_FOR_OS_OWNER",
    "CONCURRENT_DAEMON_OWNER":
        "REFUSE_SECOND_DAEMON_OWNER_PRESERVE_ORIGINAL_PROCESS",
    "IMMUTABLE_GLOBAL_OFFLINE_HANDOFF":
        "SCAN_PINNED_INDEPENDENT_OFFLINE_PLANS_NO_MODEL_OR_RELEASE",
    "CHECKOUT_REVISION_DRIFT":
        "PRESERVE_DIRTY_WORKTREE_STAGE_FRESH_VERIFIED_MAIN_AND_GUARDED_CUTOVER",
    "WINDOWS_SOURCE_PINNED_JSON_UTF8_BOM":
        "PARSE_SINGLE_UTF8_BOM_WITH_UNCHANGED_RAW_SHA_AND_REGISTRY",
}


def require_recovery(signature: str, *, registry: Path | None = None) -> str:
    path = Path(registry or RECOVERY_FILE)
    if (not path.is_file() or path.is_symlink()
        or not 1 <= path.stat().st_size <= 4096):
        raise ValueError("Missing or unsafe v7.1 executor recovery registry")
    stored = json.loads(path.read_text(encoding="utf8"))
    expected = {
        "schema_version": 1,
        "status": "MICROGEN_V71_CONTINUITY_RECOVERY_REGISTRY",
        "enabled": True,
        "paid_model_sends_allowed": False,
        "publication_allowed": False,
        "handlers": RECOVERY_ACTIONS,
    }
    if stored != expected or signature not in RECOVERY_ACTIONS:
        raise ValueError("Unregistered or tampered v7.1 recovery mechanism")
    return RECOVERY_ACTIONS[signature]


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _file(path: Path) -> Path:
    path = Path(path).absolute()
    _require(path.is_file() and not path.is_symlink(), "File is missing or linked")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(_file(path).read_bytes()).hexdigest()


def _read_json(path: Path) -> dict:
    _file(path)
    _require(path.stat().st_size <= 240000, "Unbounded JSON input")
    source_text=path.read_text(encoding="utf-8")
    if source_text.startswith("\ufeff"):
        require_recovery("WINDOWS_SOURCE_PINNED_JSON_UTF8_BOM")
        from .recovery_registry import lookup_mechanism
        if (lookup_mechanism(
            "historical_format_disposition",
            "WINDOWS_SOURCE_PINNED_JSON_UTF8_BOM")
            != "ACCEPT_ONE_BOM_PRESERVE_RAW_PLAN_HASH"):
            raise ValueError("Missing verified raw-SHA UTF-8 BOM source recovery")
        source_text=source_text[1:]  # only one BOM; hash remains on ORIGINAL bytes
    data = json.loads(source_text)
    _require(type(data) is dict, "JSON root must be an object")
    return data


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _require(not path.is_symlink(), "Cannot replace linked checkpoint")
    tmp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    try:
        with tmp.open("x", encoding="utf8") as out:
            json.dump(payload, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


@contextlib.contextmanager
def _exclusive(state_dir: Path):
    state_dir.mkdir(parents=True, exist_ok=True)
    _require(not state_dir.is_symlink(), "Linked executor checkpoint directory")
    path = state_dir / "executor.lock"
    _require(not path.is_symlink(), "Linked executor lock is forbidden")
    path.touch(exist_ok=True)
    try:
        stream=path.open("r+b")
    except PermissionError as exc:
        require_recovery("CONCURRENT_EXECUTOR_OWNER")
        raise RuntimeError("Development executor already running") from exc
    with stream as file:
        # A competing Windows reader may be forbidden to WRITE a locked
        # byte before msvcrt.locking; leave initialized lock bytes intact.
        if file.seek(0,os.SEEK_END)==0:
            file.write(b"1")
            file.flush()
        # Windows msvcrt.locking applies to the CURRENT file offset.
        # Acquire and release the exact same first-byte range.
        file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            require_recovery("CONCURRENT_EXECUTOR_OWNER")
            raise RuntimeError("Development executor already running") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                file.seek(0)
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def _plan(path: Path) -> dict:
    data = _read_json(path)
    _require(set(data) == {"schema_version", "project", "tasks"}
             and data["schema_version"] == 1
             and data["project"] == "MicroGen_AI_Web"
             and type(data["tasks"]) is list
             and 0 < len(data["tasks"]) <= MAX_TASKS,
             "Invalid MicroGen v7.1 task plan")
    known = set()
    for task in data["tasks"]:
        _require(type(task) is dict and
                 set(task) == {"id", "workstream", "action", "params",
                               "depends_on", "max_attempts", "authorized"},
                 "Unexpected task fields")
        name = task["id"]
        _require(type(name) is str and ID_RE.fullmatch(name) is not None
                 and name not in known, "Invalid or duplicate task identity")
        known.add(name)
        _require(type(task["workstream"]) is str
                 and bool(ID_RE.fullmatch(task["workstream"])),
                 "Invalid workstream")
        _require(task["action"] in SAFE_ACTIONS
                 and type(task["params"]) is dict
                 and type(task["depends_on"]) is list
                 and task["authorized"] in (True, False)
                 and type(task["authorized"]) is bool
                 and type(task["max_attempts"]) is int
                 and 1 <= task["max_attempts"] <= MAX_ATTEMPTS,
                 "Unsupported or unauthorized executor task parameters")
        _validate_params(task)
    for task in data["tasks"]:
        _require(set(task["depends_on"]) <= known
                 and task["id"] not in task["depends_on"]
                 and len(task["depends_on"]) == len(set(task["depends_on"])),
                 "Unknown or cyclic self-dependency")
    # Entire DAG must be acyclic, even if unrelated tasks can still proceed.
    graph = {t["id"]: t["depends_on"] for t in data["tasks"]}
    visiting, completed = set(), set()
    def visit(name: str):
        _require(name not in visiting, "Cycle in roadmap")
        if name in completed:
            return
        visiting.add(name)
        for parent in graph[name]:
            visit(parent)
        visiting.remove(name)
        completed.add(name)
    for name in graph:
        visit(name)
    return data


def _validate_params(task: dict) -> None:
    action, params = task["action"], task["params"]
    allowed = {
        "verify_file_sha256": {"path", "sha256"},
        "pytest_suite": {"tests", "timeout_seconds"},
        "g2_source_reconciliation": {"queue_root", "folder"},
        "g2_review_preflight": {"queue_root", "folder", "slide"},
        "lecture_completion_readonly": {"source_pdf"},
    }[action]
    _require(set(params) == allowed, "Unregistered worker input")
    if action == "verify_file_sha256":
        _require(type(params["path"]) is str
                 and type(params["sha256"]) is str
                 and bool(re.fullmatch(r"[a-f0-9]{64}", params["sha256"])),
                 "Invalid SHA source task")
    elif action == "pytest_suite":
        names = params["tests"]
        _require(type(names) is list and 0 < len(names) <= 20
                 and all(type(x) is str
                         and re.fullmatch(r"tests/test_[A-Za-z0-9_]+\.py", x)
                         for x in names)
                 and type(params["timeout_seconds"]) is int
                 and 10 <= params["timeout_seconds"] <= 900,
                 "Only bounded repository test modules are allowed")
    elif action == "g2_review_preflight":
        _require(type(params["folder"]) is str
                 and type(params["queue_root"]) is str
                 and type(params["slide"]) is int
                 and 1 <= params["slide"] <= 200,
                 "Invalid exact G2 source-review preflight parameters")
    else:
        _require(all(type(v) is str for v in params.values()),
                 "Invalid source-bound verifier path")


def _event(state: dict, name: str, *, task: str | None = None,
           detail: dict | None = None) -> None:
    event = {"seq": len(state["events"]) + 1, "event": name,
             "task": task, "detail": detail or {}}
    state["events"].append(event)


def _worker(plan_path: Path, state_dir: Path, task_id: str, token: str,
            repo_root: Path) -> int:
    """A separate real child process. It owns no provider/remote Sends."""
    plan = _plan(plan_path)
    tasks = {t["id"]: t for t in plan["tasks"]}
    _require(task_id in tasks and bool(ID_RE.fullmatch(task_id)), "Unknown worker")
    task = tasks[task_id]
    pinned_executor = os.environ.get("MICROGEN_V71_PINNED_EXECUTOR_SHA256")
    _require(pinned_executor is not None
             and pinned_executor == _sha(Path(__file__)),
             "Worker executor version no longer matches parent admission")
    pinned_plan = os.environ.get("MICROGEN_V71_PINNED_PLAN_SHA256")
    _require(pinned_plan is not None and pinned_plan == _sha(plan_path),
             "Worker plan changed between claim and execution")
    _require(task["authorized"] is True, "Worker may not override authorization")
    action, p = task["action"], task["params"]
    receipt = state_dir / "results" / (token + ".json")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    _require(not receipt.exists() and not receipt.is_symlink(),
             "Worker result already committed")
    outcome = {"status": "failed", "task": task_id, "token": token,
               "action": action, "evidence": {}}
    try:
        if action == "verify_file_sha256":
            actual = _sha(Path(p["path"]))
            _require(actual == p["sha256"], "SHA-256 mismatch")
            outcome["evidence"] = {"sha256": actual}
        elif action == "pytest_suite":
            for file in p["tests"]:
                _file(repo_root / file)
            command = [sys.executable, "-m", "pytest", "-q", *p["tests"]]
            result = subprocess.run(command, cwd=repo_root, capture_output=True,
                                    text=True, errors="replace",
                                    timeout=p["timeout_seconds"])
            outcome["evidence"] = {
                "exit_code": result.returncode,
                "stdout_tail": result.stdout[-MAX_LOG_BYTES:],
                "stderr_tail": result.stderr[-MAX_LOG_BYTES:],
            }
            _require(result.returncode == 0, "Regression suite returned failure")
        elif action == "g2_source_reconciliation":
            from .ai_academic_review_consensus import reconcile_actual_review_queue
            report = reconcile_actual_review_queue(
                queue_root=Path(p["queue_root"]), folder=Path(p["folder"]))
            accepted = report.get("accepted_ai_evidence")
            total = report.get("original_utterances")
            pending = report.get("pending_or_disputed")
            _require(report.get("status") ==
                     "INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE"
                     and type(accepted) is list and type(total) is int
                     and type(pending) is int and total > 0
                     and 0 <= pending <= total
                     and len(accepted) + pending == total
                     and report.get("student_publication_authorized") is False,
                     "Unverified G2 source agreement; no false acceptance")
            outcome["evidence"] = {
                "status": report["status"],
                "accepted": len(accepted),
                "total": total,
                "pending": pending,
                "no_provider_requests": True,
                "scientific_review_complete": pending == 0,
                "student_release": False,
            }
        elif action == "g2_review_preflight":
            from .source_review_eligibility_preflight import (
                inspect_original_review_eligibility)
            report = inspect_original_review_eligibility(
                folder=Path(p["folder"]), queue_root=Path(p["queue_root"]),
                slide=p["slide"])
            _require(report.get("status") ==
                     "SOURCE_BOUND_ACADEMIC_REVIEW_SCOPE_PREFLIGHT_NO_SEND"
                     and report.get("slide") == p["slide"]
                     and report.get("review_model_request_sent") is False
                     and report.get("automatic_retry_authorized") is False
                     and report.get("student_publication_authorized") is False
                     and report.get("independent_source_mathematics_approved") is False,
                     "Source preflight must not claim any review, retry or release")
            planning_result = report.get("planning_result")
            _require(type(planning_result) is str
                     and len(planning_result) <= 120,
                     "Unattributable G2 preflight disposition")
            outcome["evidence"] = {
                "slide":p["slide"], "planning_result":planning_result,
                "fresh_internal_review_ready":report.get(
                    "fresh_claimed_internal_selenium_review_ready") is True,
                "model_requests":0, "scientific_acceptance":False,
                "student_release":False,
            }
        elif action == "lecture_completion_readonly":
            from .cleanup import completed_lecture
            from .runner import valid
            folder = _file(Path(p["source_pdf"])).parent
            _require(completed_lecture(folder / "source.pdf"),
                     "Source-bound lecture completion failed")
            _require(valid("slides", folder), "Source-bound slides invalid")
            outcome["evidence"] = {"lecture_completed": True,
                                   "figure_and_slide_gate": True}
        else:
            raise ValueError("Unsupported worker action")
        outcome["status"] = "passed"
    except Exception as exc:
        outcome["evidence"]["error_class"] = type(exc).__name__
        outcome["evidence"]["error"] = str(exc)[:450]
    _atomic_json(receipt, outcome)
    return 0 if outcome["status"] == "passed" else 1


def _result(path: Path, task: dict, token: str) -> dict | None:
    if not path.is_file():
        return None
    result = _read_json(path)
    _require(result.get("task") == task["id"]
             and result.get("token") == token
             and result.get("action") == task["action"]
             and result.get("status") in {"passed", "failed"},
             "Corrupted or misattributed child result receipt")
    return result


def execute(*, plan_path: Path, state_dir: Path, repo_root: Path,
            max_dispatch: int = MAX_TASKS) -> dict:
    """Dispatch every eligible workstream, including after a local batch closes."""
    plan_path = _file(plan_path)
    repo_root = Path(repo_root).resolve()
    state_dir = Path(state_dir).absolute()
    _require(repo_root.is_dir() and not repo_root.is_symlink(),
             "Unsafe code checkout")
    _require(1 <= max_dispatch <= MAX_TASKS, "Invalid bounded execution limit")
    plan = _plan(plan_path)
    pinned = _sha(plan_path)
    executor_sha = _sha(Path(__file__))
    tasks = {t["id"]: t for t in plan["tasks"]}
    with _exclusive(state_dir):
        store = state_dir / "state.json"
        if store.exists():
            state = _read_json(store)
            _require(state.get("plan_sha256") == pinned
                     and state.get("executor_sha256") == executor_sha
                     and state.get("schema_version") == 1
                     and set(state.get("tasks", {})) == set(tasks)
                     and type(state.get("events")) is list,
                     "Changed roadmap requires explicit new checkpoint")
        else:
            state = {"schema_version": 1, "plan_sha256": pinned,
                     "executor_sha256": executor_sha,
                     "tasks": {n: {"status": "pending", "attempts": 0}
                               for n in tasks}, "events": [],
                     "project_complete": False}
            _event(state, "roadmap_admitted", detail={"tasks": len(tasks)})
            _atomic_json(store, state)

        def save():
            _atomic_json(store, state)

        def finalize(task: dict, report: dict):
            record = state["tasks"][task["id"]]
            good = report["status"] == "passed"
            if not good:
                require_recovery("BOUNDED_OFFLINE_FAILURE")
            record["status"] = "passed" if good else (
                "quarantined" if record["attempts"] >= task["max_attempts"]
                else "pending")
            record["evidence"] = report["evidence"]
            record.pop("active", None)
            _event(state, "task_accepted" if good else
                   ("task_quarantined" if record["status"] == "quarantined"
                    else "bounded_retry_available"), task=task["id"])
            save()

        # Repair interrupted checkpoint BEFORE new dispatch, using exact
        # worker results. No duplicate external request is possible because
        # all supported actions are read-only/bounded offline verifications.
        for task in plan["tasks"]:
            record = state["tasks"][task["id"]]
            if record["status"] not in {"dispatched", "awaiting_receipt"}:
                continue
            active = record["active"]
            token = active["token"]
            proof = _result(state_dir/"results"/(token+".json"),task,token)
            if proof is not None:
                require_recovery("ORPHANED_CHILD_RESULT")
                _event(state, "orphaned_worker_result_reconciled",
                       task=task["id"], detail={"token": token})
                finalize(task,proof)
            elif active.get("worker_pid"):
                require_recovery("UNKNOWN_STARTED_CHILD")
                # A child may still be writing its original receipt.
                # Do not start another; later restarts reconcile same token.
                record["status"] = "awaiting_receipt"
                record["evidence"] = {
                    "reason":"UNKNOWN_CHILD_OUTCOME_WAITING_FOR_ORIGINAL_RECEIPT",
                    "old_token":token}
                _event(state,"uncertain_worker_pending_receipt",task=task["id"])
                save()
            else:
                require_recovery("PENDING_CLAIM_NO_WORKER")
                _event(state,"pending_dispatch_recovered",task=task["id"])
                save()

        dispatched = 0
        while dispatched < max_dispatch:
            eligible = None
            for task in plan["tasks"]:
                record = state["tasks"][task["id"]]
                if record["status"] not in ("pending","dispatched"):
                    continue
                if not task["authorized"]:
                    if record["status"] == "pending":
                        require_recovery("AUTHORIZATION_GATE")
                        record["status"] = "awaiting_authorization"
                        _event(state,"authorization_gate_held",task=task["id"])
                        save()
                    continue
                if all(state["tasks"][dep]["status"] == "passed"
                       for dep in task["depends_on"]):
                    eligible = task
                    break
            if eligible is None:
                break
            task = eligible
            record = state["tasks"][task["id"]]
            if record["status"] == "pending":
                token = uuid.uuid4().hex
                record["attempts"] += 1
                record["active"] = {"token":token, "worker_pid":None}
                record["status"] = "dispatched"
                _event(state,"checkpoint_committed",task=task["id"])
                _event(state,"next_task_dispatched",task=task["id"],
                       detail={"token":token, "action":task["action"]})
                save()
            else:
                token = record["active"]["token"]
            # Only used by dedicated crash-and-restart fault injection tests;
            # no real provider or external operation has begun yet.
            if os.environ.get("MICROGEN_V71_TEST_EXIT_AFTER_CLAIM") == task["id"]:
                os._exit(86)
            command = [sys.executable,"-m",
                       "selenium_pipeline.development_continuity_executor_v71",
                       "_worker",str(plan_path),str(state_dir),
                       task["id"],token,str(repo_root)]
            child_env = os.environ.copy()
            child_env["MICROGEN_V71_PINNED_EXECUTOR_SHA256"] = executor_sha
            child_env["MICROGEN_V71_PINNED_PLAN_SHA256"] = pinned
            proc = subprocess.Popen(command,cwd=repo_root,env=child_env,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            record["active"]["worker_pid"] = proc.pid
            _event(state,"worker_started",task=task["id"],
                   detail={"pid":proc.pid,"token":token})
            save()
            # Crash injection AFTER a real child has been started and its
            # pid persisted. Restart must consume original result, not resend.
            if os.environ.get("MICROGEN_V71_TEST_EXIT_AFTER_CHILD_START") == task["id"]:
                os._exit(87)
            try:
                proc.wait(timeout=920)
            except subprocess.TimeoutExpired:
                require_recovery("UNKNOWN_STARTED_CHILD")
                record["status"] = "awaiting_receipt"
                record["evidence"]={"reason":"WORKER_TIMEOUT_WAITING_FOR_RECEIPT",
                                    "pid":proc.pid,"token":token}
                _event(state,"uncertain_worker_pending_receipt",
                       task=task["id"])
                save()
                dispatched += 1
                continue
            proof = _result(state_dir/"results"/(token+".json"),task,token)
            if proof is None:
                record["status"]="quarantined"
                record["evidence"]={"reason":"WORKER_EXIT_WITHOUT_RESULT",
                                    "pid":proc.pid}
                _event(state,"unknown_worker_result_quarantined",
                       task=task["id"])
                save()
            else:
                finalize(task,proof)
            dispatched += 1
            # Crucially, do not return at the task boundary; rescan globally.
        states = [v["status"] for v in state["tasks"].values()]
        state["project_complete"] = all(x=="passed" for x in states)
        state["status"] = (
            "VERIFIED_TASK_PLAN_COMPLETE" if state["project_complete"]
            else "PAUSED_WITH_PENDING_ELIGIBLE_TASKS"
            if dispatched >= max_dispatch and any(x=="pending" for x in states)
            else "BLOCKED_OR_AWAITING_EVIDENCE"
            if any(x in {"quarantined","awaiting_authorization",
                         "awaiting_receipt"} for x in states)
            else "DEPENDENCY_BLOCKED")
        _event(state,"execution_checkpoint",detail={
            "status":state["status"],"dispatch_count":dispatched,
            "completed":states.count("passed"),
            "remaining":len(states)-states.count("passed")})
        save()
        return state


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="cmd",required=True)
    run=sub.add_parser("run")
    run.add_argument("--plan",required=True,type=Path)
    run.add_argument("--state-dir",required=True,type=Path)
    run.add_argument("--repo-root",type=Path,default=Path.cwd())
    run.add_argument("--max-dispatch",type=int,default=MAX_TASKS)
    child=sub.add_parser("_worker")
    for field in ("plan","state_dir","task_id","token","repo_root"):
        child.add_argument(field)
    args=parser.parse_args(argv)
    if args.cmd == "_worker":
        return _worker(Path(args.plan),Path(args.state_dir),args.task_id,
                       args.token,Path(args.repo_root))
    report=execute(plan_path=args.plan,state_dir=args.state_dir,
                   repo_root=args.repo_root,max_dispatch=args.max_dispatch)
    print(json.dumps({
        "status":report["status"],
        "project_complete":report["project_complete"],
        "tasks":{k:v["status"] for k,v in report["tasks"].items()},
        "dispatched":sum(x["event"]=="worker_started" for x in report["events"]),
        "state":str(args.state_dir/"state.json"),
    },indent=2))
    return 0 if report["project_complete"] else 2


if __name__=="__main__":
    raise SystemExit(main())
