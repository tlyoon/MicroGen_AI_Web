"""Persistent bounded Selenium code authoring, NEVER the release/academic daemon.

Reads immutable, source-SHA-pinned development jobs from an independent inbox.
Each job can make at most one Gemini Selenium browser Send. Returns and saves
untrusted text, statically checks a pure-Python module, applies it to an
isolated Git branch, and runs a pre-existing, source-pinned pytest contract.
No old provider Send retry, paid API, publication, PR merge, or sandbox bypass.

A separate certified GitHub gate may later merge a verified candidate.
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
import time

from .development_continuity_executor_v71 import _atomic_json, _exclusive

STATUS = "MICROGEN_PERSISTENT_SELENIUM_CODE_AUTHOR_V1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[a-z][a-z0-9_-]{4,55}\Z")
PATH = re.compile(r"(?:selenium_pipeline|tests)/[a-z0-9_./-]{5,120}\.py\Z")
TERMINAL = frozenset({
    "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION",
    "UNSAFE_MODEL_REPLY_QUARANTINED",
    "SOURCE_TEST_FAILED_QUARANTINED",
    "PROVIDER_SEND_UNCERTAIN_NO_REPLAY",
    "SOURCE_INPUT_CHANGED_NO_SEND",
})
MAX_REPLY = 80_000
MAX_CONTEXT = 18_000
MAX_JOBS = 16
MAX_SLEEP = 300
_BLOCKED = frozenset({
    "eval", "exec", "compile", "__import__", "open", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "breakpoint", "memoryview",
})
_ALLOWED_IMPORTS = frozenset({"re", "json", "math", "statistics"})
_ALLOWED_BUILTINS = frozenset({
    "str", "int", "float", "bool", "len", "range", "enumerate", "zip",
    "sorted", "reversed", "all", "any", "min", "max", "sum",
    "isinstance", "dict", "list", "tuple", "set", "abs", "round",
})


def require(value: bool, reason: str):
    if not value:
        raise ValueError(reason)


def sha(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(),
            "Missing or symlinked immutable file")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def read(path: Path, maximum: int = 120_000) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 2 <= path.stat().st_size <= maximum,
            "Missing, linked or oversized job evidence")
    value = json.loads(path.read_text(encoding="utf8"))
    require(type(value) is dict, "Job evidence must be JSON object")
    return value


def git(repo: Path, *args: str) -> str:
    outcome = subprocess.run(["git", "-C", str(repo), *args],
                             capture_output=True, text=True, timeout=35)
    require(outcome.returncode == 0,
            "Git source verification failed: " + outcome.stderr[-180:])
    return outcome.stdout.strip()


def validate_source(source: str):
    """Bounded static sanity policy, NOT a substitute for a sandbox.

    Only narrow pure Python, imports of preapproved non-IO libraries,
    function declarations and constants. No dynamic imports, filesystem,
    networking, subprocesses, dunder access, or call expressions at module
    scope. More powerful source changes must use separately authorized jobs.
    """
    require(type(source) is str
            and 40 <= len(source.encode("utf8")) <= MAX_REPLY
            and "\0" not in source, "Unbounded code model output")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError("Generated source invalid Python") from exc
    require(1 <= len(tree.body) <= 28,
            "Unbounded or blank source module")
    for top in tree.body:
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
            require(isinstance(top, ast.FunctionDef)
                    and not top.decorator_list
                    and not top.name.startswith("_")
                    and 1 <= len(top.body) <= 85,
                    "Untrusted top-level function or decorator")
        elif isinstance(top, ast.Import):
            require(all(x.asname is None
                        and x.name in _ALLOWED_IMPORTS
                        for x in top.names), "Import outside pure-library allowlist")
        elif isinstance(top, ast.ImportFrom):
            require(top.level == 0 and top.module in _ALLOWED_IMPORTS
                    and all(x.asname is None
                            and not x.name.startswith("_")
                            for x in top.names),
                    "Import-from outside pure-library allowlist")
        elif isinstance(top, ast.Assign):
            require(len(top.targets) == 1
                    and isinstance(top.targets[0], ast.Name)
                    and top.targets[0].id.isupper()
                    and isinstance(top.value, ast.Constant),
                    "Only literal uppercase module constants allowed")
        elif isinstance(top, ast.Expr):
            require(isinstance(top.value, ast.Constant)
                    and type(top.value.value) is str,
                    "Only module docstrings allowed")
        else:
            raise ValueError("Unsafe Python top-level statement")
    for node in ast.walk(tree):
        require(not isinstance(node, (
            ast.Lambda, ast.ClassDef, ast.AsyncFunctionDef,
            ast.Await, ast.Yield, ast.YieldFrom, ast.Global,
            ast.Nonlocal, ast.With, ast.AsyncWith, ast.Try,
            ast.Raise, ast.Delete, ast.NamedExpr, ast.Continue,
        )), "Unsafe dynamic Python construct")
        if isinstance(node, ast.Name):
            require(not node.id.startswith("__")
                    and node.id not in _BLOCKED,
                    "Restricted dynamic Python name")
        if isinstance(node, ast.Attribute):
            require(not node.attr.startswith("_"),
                    "Private or magic attribute forbidden")
        if isinstance(node, ast.Call):
            require(isinstance(node.func, (ast.Name, ast.Attribute))
                    and (not isinstance(node.func, ast.Name)
                         or node.func.id not in _BLOCKED),
                    "Untrusted dynamic call target")
    return source.rstrip() + "\n"


def parse_reply(raw: str) -> str:
    require(type(raw) is str and 40 <= len(raw.encode("utf8")) <= MAX_REPLY,
            "Missing or oversized original model reply")
    raw = raw.replace("\r\n", "\n").strip()
    fence = chr(96) * 3
    if raw.startswith(fence + "python"):
        raw = raw[len(fence + "python"):].strip()
        require(raw.endswith(fence), "Unclosed generated code fence")
        raw = raw[:-3].strip()
    elif raw.startswith(fence):
        raw = raw[3:].strip()
        require(raw.endswith(fence), "Unclosed source fence")
        raw = raw[:-3].strip()
    return validate_source(raw)


def validate_job(*, root: Path, file: Path) -> dict:
    root = Path(root).absolute()
    file = Path(file).absolute()
    require(root.is_dir() and not root.is_symlink()
            and not file.is_symlink() and file.parent == root / "inbox",
            "Only independent original inbox files admitted")
    job = read(file)
    require(set(job) == {
        "schema_version", "project", "job_id", "authorized",
        "repo", "base_sha", "branch", "target", "target_original_sha256",
        "test", "test_sha256", "context_path", "context_sha256",
        "instruction", "selenium_mode", "max_wait_seconds",
        "browser_model_claims", "paid_api", "student_publication",
    } and job["schema_version"] == 1
        and job["project"] == "MicroGen_AI_Web"
        and job["authorized"] is True
        and job["browser_model_claims"] == 1
        and type(job["browser_model_claims"]) is int
        and job["paid_api"] is False
        and job["student_publication"] is False
        and type(job["job_id"]) is str and ID.fullmatch(job["job_id"])
        and file.name == job["job_id"] + ".json"
        and type(job["base_sha"]) is str and SHA40.fullmatch(job["base_sha"])
        and type(job["target"]) is str and PATH.fullmatch(job["target"])
        and type(job["test"]) is str
        and job["test"].startswith("tests/test_")
        and PATH.fullmatch(job["test"])
        and type(job["context_path"]) is str
        and PATH.fullmatch(job["context_path"])
        and type(job["instruction"]) is str
        and 60 <= len(job["instruction"]) <= 3500
        and job["selenium_mode"] in ("hydrogen", "neon")
        and type(job["max_wait_seconds"]) is int
        and 60 <= job["max_wait_seconds"] <= 160,
        "Unapproved or unbounded original code-authoring request")
    require(all(type(job[k]) is str and SHA64.fullmatch(job[k])
                for k in ("test_sha256", "context_sha256")),
            "Immutable independent test/context hashes required")
    require(job["target_original_sha256"] is None or (
        type(job["target_original_sha256"]) is str
        and SHA64.fullmatch(job["target_original_sha256"])),
        "Original target identity missing")
    repo = Path(job["repo"]).absolute()
    require(repo.is_dir() and not repo.is_symlink()
            and not repo.is_relative_to(root)
            and not root.is_relative_to(repo)
            and (repo / ".git").exists()
            and job["branch"].startswith("feature/")
            and len(job["branch"]) <= 90
            and all(x not in job["branch"] for x in ("..", " ", "\\")),
            "Code-generation branch must be isolated from worker inbox")
    require(git(repo, "rev-parse", "HEAD") == job["base_sha"]
            and git(repo, "branch", "--show-current") == job["branch"],
            "Original Git branch changed after admission")
    require(sha(repo / job["test"]) == job["test_sha256"]
            and sha(repo / job["context_path"]) == job["context_sha256"],
            "Original independent test or context changed")
    owner = root / "state" / job["job_id"] / "coding_state.json"
    if owner.exists() or owner.is_symlink():
        prior = read(owner)
        require(prior.get("job_sha256") == sha(file),
                "Original coding job changed after model claim")
    target = repo / job["target"]
    require(not target.is_symlink(),
            "Redirected source target forbidden")
    old = job["target_original_sha256"]
    if target.is_file() and (old is None or sha(target) != old):
        state_dir = root / "state" / job["job_id"]
        checkpoint = read(state_dir / "coding_state.json")
        reply_file = state_dir / "original_model_reply.txt"
        require(reply_file.is_file() and not reply_file.is_symlink()
                and checkpoint.get("job_sha256") == sha(file)
                and checkpoint.get("status") in (
                    "MODEL_REPLY_SAVED", "SOURCE_APPLIED_CANDIDATE",
                    "SOURCE_CANDIDATE_TESTED_NO_PUBLICATION",
                    "SOURCE_TEST_FAILED_QUARANTINED")
                and checkpoint.get("model_reply_sha256") == sha(reply_file)
                and sha(target) == hashlib.sha256(
                    parse_reply(reply_file.read_text("utf8")).encode("utf8")
                ).hexdigest(),
                "Existing source target differs from authenticated saved reply")
    else:
        require((old is None and not target.exists())
                or (old is not None and sha(target) == old),
                "Source target changed after original job was authored")
    return job


def prompt_for(job: dict, context: str, independent_test: str) -> str:
    result = (
        "You are an offline Python code author for the MicroGen_AI_Web project.\n"
        "Return ONLY one complete Python module for the exact target path. "
        "No markdown, commentary, commands, file I/O, networking, subprocesses, "
        "dynamic imports, object introspection or model calls. "
        "Use only pure functions and optional imports from re/json/math/statistics. "
        "No class, decorators, or top-level executable statements.\n"
        "The independent tests below are authoritative. Implement the requested "
        "functionality to pass them without editing the tests.\n"
        "Task: " + job["instruction"] + "\n"
        "Target path: " + job["target"] + "\n"
        "<EXISTING_SOURCE_REFERENCE>\n" + context + "\n</EXISTING_SOURCE_REFERENCE>\n"
        "<INDEPENDENT_TESTS>\n" + independent_test + "\n</INDEPENDENT_TESTS>\n"
    )
    require(len(result.encode("utf8")) <= 26_000,
            "Source-pinned code prompt too large")
    return result


def save_once(path: Path, payload: bytes):
    require(not path.is_symlink(), "Symlinked response/receipt rejected")
    if path.exists():
        require(path.is_file() and path.read_bytes() == payload,
                "Prior original response changed")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def step(*, root: Path, job_path: Path, sender=None) -> dict:
    root = Path(root).absolute()
    job_path = Path(job_path).absolute()
    job = validate_job(root=root, file=job_path)
    repo = Path(job["repo"]).absolute()
    state_dir = root / "state" / job["job_id"]
    with _exclusive(state_dir):
        state_file = state_dir / "coding_state.json"
        reply = state_dir / "original_model_reply.txt"
        model_claimed = False
        job_hash = sha(job_path)
        if state_file.exists():
            state = read(state_file)
            require(state.get("job_sha256") == job_hash,
                    "Original coding job changed: no replay")
            if state["status"] in TERMINAL:
                return state
            require(state["status"] in {
                "SEND_CLAIMED_UNCERTAIN", "MODEL_REPLY_SAVED",
                "SOURCE_APPLIED_CANDIDATE"},
                "Unknown saved coding state cannot retry")
        else:
            require(git(repo, "status", "--porcelain") == "",
                    "Source branch not clean before first model claim")
            state = {
                "schema_version": 1, "status": "SEND_CLAIMED_UNCERTAIN",
                "job_sha256": job_hash, "base_sha": job["base_sha"],
                "job_id": job["job_id"], "model_claims": 1,
                "model_sends": 0, "paid_api_requests": 0,
                "student_publication_authorized": False,
                "candidate_merged": False,
            }
            _atomic_json(state_file, state)
            model_claimed = True
        if not reply.exists():
            if not model_claimed:
                state["status"] = "PROVIDER_SEND_UNCERTAIN_NO_REPLAY"
                _atomic_json(state_file, state)
                return state
            try:
                ctx = (repo / job["context_path"]).read_text("utf8")
                tests = (repo / job["test"]).read_text("utf8")
                require(len(ctx.encode("utf8")) <= MAX_CONTEXT
                        and len(tests.encode("utf8")) <= 12_000,
                        "Unbounded source-pinned model context")
                prompt = prompt_for(job, ctx, tests)
                if sender is None:
                    from .development_browser_code_transport_v71 import (
                        selenium_sender)
                    raw = selenium_sender(
                        prompt, repo=repo,
                        max_wait_seconds=job["max_wait_seconds"],
                        ui_mode=job["selenium_mode"],
                    )
                else:
                    raw = sender(prompt)
                require(type(raw) is str
                        and 40 <= len(raw.encode("utf8")) <= MAX_REPLY,
                        "Original model reply absent or oversized")
                save_once(reply, raw.encode("utf8"))
            except BaseException:
                # Never assume failure happened before the Selenium Send.
                state["status"] = "PROVIDER_SEND_UNCERTAIN_NO_REPLAY"
                _atomic_json(state_file, state)
                raise
        raw = reply.read_bytes()
        require(40 <= len(raw) <= MAX_REPLY, "Saved model reply unsafe")
        state["model_reply_sha256"] = sha(reply)
        state["status"] = "MODEL_REPLY_SAVED"
        _atomic_json(state_file, state)
        try:
            source = parse_reply(raw.decode("utf8")).encode("utf8")
        except (ValueError, UnicodeError):
            state["status"] = "UNSAFE_MODEL_REPLY_QUARANTINED"
            _atomic_json(state_file, state)
            return state
        target = repo / job["target"]
        require(not target.is_symlink(), "Unsafe target path")
        before = job["target_original_sha256"]
        current = sha(target) if target.is_file() else None
        new_digest = hashlib.sha256(source).hexdigest()
        require(current in (before, new_digest),
                "Candidate path changed outside original job")
        if current != new_digest:
            save_once(state_dir / "candidate_source.blob", source)
            temp = target.with_name(target.name + ".candidate_new")
            require(not temp.exists(), "Unreconciled prior temp source")
            with temp.open("xb") as stream:
                stream.write(source)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, target)
        state["status"] = "SOURCE_APPLIED_CANDIDATE"
        state["candidate_sha256"] = new_digest
        _atomic_json(state_file, state)
        require(sha(target) == new_digest,
                "Generated source differs from saved model reply")
        changed = git(repo, "status", "--porcelain")
        require(all(row[3:] == job["target"] for row in changed.splitlines()),
                "Unexpected generated changes outside the authorized source")
        require(subprocess.run(
            ["git", "-C", str(repo), "diff", "--check"],
            capture_output=True, timeout=30).returncode == 0,
            "Generated source has an invalid Git diff")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", job["test"]],
                cwd=repo, capture_output=True, text=True, timeout=420,
            )
            state["pytest_exit_code"] = result.returncode
            state["pytest_output_tail"] = (result.stdout or "")[-1300:]
            state["pytest_stderr_tail"] = (result.stderr or "")[-400:]
            state["status"] = ("SOURCE_CANDIDATE_TESTED_NO_PUBLICATION"
                               if result.returncode == 0
                               else "SOURCE_TEST_FAILED_QUARANTINED")
        except subprocess.TimeoutExpired:
            state["status"] = "SOURCE_TEST_FAILED_QUARANTINED"
            state["failure_class"] = "PytestTimeout"
        _atomic_json(state_file, state)
        return state


def scan(*, root: Path, sender=None) -> dict:
    root = Path(root).absolute()
    require(root.is_dir() and not root.is_symlink()
            and (root / "inbox").is_dir()
            and not (root / "inbox").is_symlink()
            and (root / "state").is_dir(),
            "Persistent worker not initialized safely")
    candidates = sorted((root / "inbox").glob("*.json"))
    require(len(candidates) <= MAX_JOBS, "Too many unapproved coding jobs")
    outcomes = []
    for job_path in candidates:
        try:
            info = step(root=root, job_path=job_path, sender=sender)
            outcomes.append({
                "job": job_path.name, "status": info["status"],
                "model_claims": info.get("model_claims", 0),
                "paid_api_requests": 0,
            })
        except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            outcomes.append({
                "job": job_path.name, "status": "ELIGIBILITY_OR_SEND_HELD",
                "error_class": type(exc).__name__, "paid_api_requests": 0,
            })
            continue
    return {
        "schema_version": 1, "status": STATUS,
        "jobs": outcomes, "new_paid_api_requests": 0,
        "student_publication_authorized": False,
    }


def serve(*, root: Path, poll_seconds: int = 30,
          max_cycles: int = 0, sender=None) -> dict:
    require(type(poll_seconds) is int and 1 <= poll_seconds <= MAX_SLEEP
            and type(max_cycles) is int and 0 <= max_cycles <= 10000,
            "Unbounded polling settings")
    root = Path(root).absolute()
    cycles = 0
    while True:
        outcome = scan(root=root, sender=sender)
        cycles += 1
        _atomic_json(root / "worker_heartbeat.json", {
            **outcome, "cycles": cycles,
            "worker_pid": os.getpid(),
            "heartbeat_epoch": time.time(),
        })
        if max_cycles and cycles >= max_cycles:
            return outcome
        time.sleep(poll_seconds)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--poll-seconds", type=int, default=30)
    p.add_argument("--max-cycles", type=int, default=0)
    args = p.parse_args(argv)
    report = serve(root=args.root, poll_seconds=args.poll_seconds,
                   max_cycles=args.max_cycles)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
