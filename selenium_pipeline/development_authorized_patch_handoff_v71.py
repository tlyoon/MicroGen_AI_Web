"""Authorized, restart-safe external code-patch handoff, independent of Codex.

This sidecar consumes only a locally authorized, source-SHA-pinned manifest and
whole-file blobs supplied by a trusted connected code-writing session. It does
not summon or impersonate a coding model, relax a host sandbox, clear a Codex
capability denial, send Gemini requests, merge PRs, or release lecture content.

The normal always-on v7.1 continuity daemon remains intentionally read-only.
A distinct invocation explicitly admits one candidate in an isolated Git worktree.
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
import uuid

from .development_continuity_executor_v71 import (
    _atomic_json, _exclusive, _read_json, _sha,
)
from .recovery_registry import lookup_mechanism

HEX = re.compile(r"^[a-f0-9]{64}$")
SHA40 = re.compile(r"^[a-f0-9]{40}$")
JOB = re.compile(r"^[a-z][a-z0-9_-]{3,60}$")
SOURCE = re.compile(r"^[A-Za-z0-9_./-]{5,160}$")
BRANCH = re.compile(r"^feature/[a-z0-9][a-z0-9-]{5,100}$")
ALLOWED = ("selenium_pipeline/", "tests/", "docs/")
PROTECTED = frozenset({
    "selenium_pipeline/development_coding_provider_health_v71.py",
    "selenium_pipeline/development_coding_recovery_registry_v71.json",
    "selenium_pipeline/paid_api_policy.py",
    "selenium_pipeline/recovery_registry.py",
    "selenium_pipeline/recovery_registry_v1.json",
    "selenium_pipeline/development_authorized_patch_handoff_v71.py",
})
RECOVERY_SIGNATURE = "HOST_READONLY_USE_AUTHORIZED_ATOMIC_CODE_HANDOFF"
RECOVERY_MECHANISM = "ADMIT_PINNED_EXTERNAL_CODE_BLOBS_TEST_IN_ISOLATED_WORKTREE"
MAX_SOURCE_BYTES = 350_000


def ensure(condition: bool, reason: str):
    if not condition:
        raise ValueError(reason)


def sha_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _git(repo: Path, *argv: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *argv], capture_output=True,
        text=True, timeout=25,
    )
    ensure(proc.returncode == 0, "Git admission failed: " + proc.stderr[-180:])
    return proc.stdout.strip()


def _changed_paths(repo: Path) -> set[str]:
    """Expand Git's condensed '?? tests/' status to actual untracked files."""
    summary = _git(repo, "status", "--porcelain")
    for item in summary.splitlines():
        ensure(len(item) >= 4 and " -> " not in item
               and item[:2] not in {"R ", " R", "C ", " C"},
               "Source rename/copy forbidden")
    changed = set()
    for arguments in (
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        changed.update(_git(repo, *arguments).splitlines())
    return changed


def _path(repo: Path, name: str) -> Path:
    ensure(isinstance(name, str) and SOURCE.fullmatch(name)
           and not name.startswith((".", "/"))
           and not any(segment in (".", "..") for segment in name.split("/"))
           and "\\" not in name
           and name.startswith(ALLOWED)
           and name not in PROTECTED
           and Path(name).suffix in (".py", ".md", ".json"),
           "Unapproved candidate source path")
    file = repo / name
    ensure(file.resolve().is_relative_to(repo.resolve()),
           "Candidate escapes isolated source worktree")
    parent = file.parent
    while parent != repo:
        ensure(not parent.is_symlink(), "Linked source parent forbidden")
        parent = parent.parent
    ensure(not file.is_symlink(), "Linked source forbidden")
    return file


def _validate_manifest(raw: dict) -> dict:
    ensure(type(raw) is dict and set(raw) in ({
        "schema_version", "project", "job_id", "base_sha",
        "branch", "authorized", "source", "files", "tests",
    }, {
        "schema_version", "project", "job_id", "base_sha",
        "branch", "authorized", "source", "files", "tests",
        "model_provenance",
    }), "Unexpected code handoff schema")
    is_model = raw.get("source") == "source_pinned_selenium_model_reply"
    ensure(("model_provenance" in raw) == is_model
           and raw.get("source") in {
               "trusted_connected_coding_session",
               "source_pinned_selenium_model_reply",
           }, "Untrusted code source identity or authorization")
    ensure(raw["schema_version"] == 1
           and raw["project"] == "MicroGen_AI_Web"
           and raw["authorized"] is True
           and isinstance(raw["job_id"], str)
           and JOB.fullmatch(raw["job_id"])
           and isinstance(raw["base_sha"], str)
           and SHA40.fullmatch(raw["base_sha"])
           and isinstance(raw["branch"], str)
           and BRANCH.fullmatch(raw["branch"]),
           "Explicit source-bound code authorization missing")
    entries = raw["files"]
    tests = raw["tests"]
    ensure(type(entries) is list and 1 <= len(entries) <= 12
           and type(tests) is list and 1 <= len(tests) <= 12
           and len(tests) == len(set(tests)), "Unbounded candidate/test scope")
    seen = set()
    for item in entries:
        ensure(type(item) is dict
               and set(item) == {"path", "old_sha256", "new_sha256"},
               "Unexpected candidate file schema")
        name = item["path"]
        ensure(isinstance(name, str) and SOURCE.fullmatch(name)
               and name not in seen
               and isinstance(item["new_sha256"], str)
               and HEX.fullmatch(item["new_sha256"])
               and (item["old_sha256"] is None or
                    isinstance(item["old_sha256"], str)
                    and HEX.fullmatch(item["old_sha256"])),
               "Invalid or repeated candidate file identity")
        seen.add(name)
    for test in tests:
        ensure(isinstance(test, str) and test.startswith("tests/")
               and test.endswith(".py") and SOURCE.fullmatch(test)
               and ".." not in test, "Unapproved regression test")
    return raw


def _load_candidate(job_path: Path, payload_dir: Path, repo: Path) -> tuple[dict, list]:
    ensure(job_path.is_file() and not job_path.is_symlink()
           and 10 < job_path.stat().st_size <= 40000
           and payload_dir.is_dir() and not payload_dir.is_symlink(),
           "Candidate manifest/payload not admitted")
    job = _validate_manifest(_read_json(job_path))
    entries = []
    paths = set()
    for item in job["files"]:
        dest = _path(repo, item["path"])
        paths.add(item["path"])
        content = payload_dir / (item["new_sha256"] + ".blob")
        ensure(content.is_file() and not content.is_symlink()
               and 1 <= content.stat().st_size <= MAX_SOURCE_BYTES,
               "Candidate payload absent or unsafe")
        raw = content.read_bytes()
        ensure(sha_bytes(raw) == item["new_sha256"],
               "Candidate source payload changed after preparation")
        try:
            data = raw.decode("utf-8")
        except UnicodeError as exc:
            raise ValueError("Candidate source is not UTF-8") from exc
        ensure("\0" not in data, "Binary candidate source forbidden")
        if dest.suffix == ".py":
            ast.parse(data, filename=item["path"])
        entries.append((item, dest, raw))
    for name in job["tests"]:
        _path(repo, name)
        ensure(name in paths or (repo / name).is_file(),
               "Mandatory regression test missing")
    if job["source"] == "source_pinned_selenium_model_reply":
        provenance = job["model_provenance"]
        ensure(type(provenance) is dict
               and set(provenance) == {"receipt_path", "receipt_sha256"}
               and isinstance(provenance["receipt_sha256"], str)
               and HEX.fullmatch(provenance["receipt_sha256"]),
               "Invalid browser model receipt identity")
        receipt_path = Path(provenance["receipt_path"]).absolute()
        ensure(receipt_path.is_file() and not receipt_path.is_symlink()
               and not receipt_path.is_relative_to(repo)
               and receipt_path.stat().st_size <= 20000
               and _sha(receipt_path) == provenance["receipt_sha256"],
               "Missing or changed authenticated browser model receipt")
        receipt = _read_json(receipt_path)
        ensure(type(receipt) is dict
               and receipt.get("status") == "MODEL_REPLY_CAPTURED_UNTRUSTED"
               and receipt.get("transport") == "gemini_selenium"
               and receipt.get("model_requests_claimed") == 1
               and receipt.get("authorized") is True
               and type(receipt.get("response_sha256")) is str
               and HEX.fullmatch(receipt["response_sha256"])
               and type(receipt.get("job_sha256")) is str
               and HEX.fullmatch(receipt["job_sha256"])
               and len(entries) == 1
               and len(job["tests"]) == 1
               and entries[0][0]["path"] == job["tests"][0]
               and receipt.get("target_path") == entries[0][0]["path"]
               and receipt.get("source_sha256") == entries[0][0]["new_sha256"],
               "Model response provenance does not identify authorized candidate")
        reply_path = receipt_path.parent / "model_response_untrusted.txt"
        ensure(reply_path.is_file() and not reply_path.is_symlink()
               and reply_path.stat().st_size <= 50000
               and _sha(reply_path) == receipt["response_sha256"],
               "Original model response missing or altered; NO WRITE")
        # Untrusted source must be statically safe before any pytest execution.
        from .development_browser_code_transport_v71 import safe_test_source
        ensure(entries[0][0]["path"].startswith("tests/test_")
               and entries[0][0]["path"].endswith(".py"),
               "Untrusted browser model may write only a verified test module")
        safe_test_source(entries[0][2].decode("utf8"))
    return job, entries


def run(*, job_path: Path, payload_dir: Path, repo: Path,
        state_dir: Path, timeout_seconds: int = 450,
        fault_after_write: bool = False) -> dict:
    """Admit one explicit candidate; no provider calls and no Git publication."""
    ensure(30 <= timeout_seconds <= 900, "Unbounded test duration")
    original = (Path(job_path).absolute(), Path(payload_dir).absolute(),
                Path(repo).absolute(), Path(state_dir).absolute())
    job_path, payload_dir, repo, state_dir = original
    ensure(repo.is_dir() and not repo.is_symlink()
           and (repo / ".git").exists()
           and not repo.is_relative_to(state_dir)
           and not state_dir.is_relative_to(repo)
           and not job_path.is_relative_to(repo)
           and not payload_dir.is_relative_to(repo)
           and not state_dir.is_symlink(),
           "Code worker must use separate isolated paths")
    ensure(lookup_mechanism("code_authoring_handoff", RECOVERY_SIGNATURE)
           == RECOVERY_MECHANISM,
           "Missing registered authorized patch worker; NO WRITE")
    job, entries = _load_candidate(job_path, payload_dir, repo)
    ensure(_git(repo, "rev-parse", "HEAD") == job["base_sha"]
           and _git(repo, "branch", "--show-current") == job["branch"],
           "Candidate not at immutable authorized branch and main SHA")
    raw_job_hash = _sha(job_path)
    with _exclusive(state_dir):
        record_path = state_dir / "code_handoff_state.json"
        if record_path.exists():
            state = _read_json(record_path)
            ensure(state.get("job_sha256") == raw_job_hash
                   and state.get("base_sha") == job["base_sha"]
                   and state.get("status") in {
                       "CLAIMED", "APPLYING", "TEST_FAILED_QUARANTINED",
                       "VERIFIED_CANDIDATE_NO_PUBLICATION",
                   }, "Changed or foreign coding claim; NO REPLAY")
            ensure(state["status"] != "TEST_FAILED_QUARANTINED",
                   "Prior failed candidate quarantined; make a new job")
        else:
            ensure(_git(repo, "status", "--porcelain") == "",
                   "Initial code workspace must be clean")
            state = {
                "schema_version": 1, "job_sha256": raw_job_hash,
                "job_id": job["job_id"], "base_sha": job["base_sha"],
                "status": "CLAIMED", "applied_paths": [],
                "model_requests": 0, "codex_host_denial_cleared": False,
                "candidate_pr_pushed": False, "student_release": False,
            }
            _atomic_json(record_path, state)
        expected_names = {e[0]["path"] for e in entries}
        altered = _changed_paths(repo)
        ensure(altered.issubset(expected_names),
               "Foreign source modifications found; NO WRITE")
        for item, dest, raw in entries:
            before = item["old_sha256"]
            current = sha_bytes(dest.read_bytes()) if dest.is_file() else None
            if current == item["new_sha256"]:
                continue  # completed write before a process crash
            ensure(current == before and (before is not None) == dest.is_file(),
                   "Candidate source differs from original and new digest")
            ensure(not dest.exists() or dest.is_file(),
                   "Untrusted source file type")
            state["status"] = "APPLYING"
            _atomic_json(record_path, state)
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".candidate." + uuid.uuid4().hex)
            try:
                with tmp.open("xb") as writer:
                    writer.write(raw)
                    writer.flush()
                    os.fsync(writer.fileno())
                os.replace(tmp, dest)
            finally:
                if tmp.exists():
                    tmp.unlink()
            state["applied_paths"] = sorted(set(state["applied_paths"])
                                            | {item["path"]})
            _atomic_json(record_path, state)
            if fault_after_write:
                raise RuntimeError("INJECTED_POST_WRITE_CRASH_RESTART_RECOVERABLE")
        changed = _changed_paths(repo)
        ensure(changed, "Verified code candidate must modify actual files")
        ensure(changed == expected_names, "Candidate changed unexpected files")
        for item, dest, raw in entries:
            ensure(dest.is_file() and not dest.is_symlink()
                   and sha_bytes(dest.read_bytes()) == item["new_sha256"],
                   "Modified source digest not matched")
        ensure(subprocess.run(
            ["git", "-C", str(repo), "diff", "--check"],
            capture_output=True, timeout=35,
        ).returncode == 0, "Candidate diff whitespace invalid")
        if state["status"] == "VERIFIED_CANDIDATE_NO_PUBLICATION":
            return state
        try:
            test_result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", *job["tests"]],
                cwd=repo, capture_output=True, text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            state["status"] = "TEST_FAILED_QUARANTINED"
            state["test_failure_class"] = "TimeoutExpired"
            _atomic_json(record_path, state)
            raise ValueError("Candidate regression timed out and quarantined")
        if test_result.returncode != 0:
            state["status"] = "TEST_FAILED_QUARANTINED"
            state["test_failure_class"] = "PytestFailure"
            state["test_output_tail"] = (test_result.stdout or "")[-600:]
            _atomic_json(record_path, state)
            raise ValueError("Candidate regression failed and quarantined")
        state["status"] = "VERIFIED_CANDIDATE_NO_PUBLICATION"
        state["applied_paths"] = sorted(expected_names)
        state["new_file_sha256"] = {
            item["path"]: item["new_sha256"] for item, _, _ in entries
        }
        state["tests_passed"] = job["tests"]
        state["test_output_tail"] = (test_result.stdout or "")[-500:]
        _atomic_json(record_path, state)
        return state


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--job", type=Path, required=True)
    p.add_argument("--payload-dir", type=Path, required=True)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--run", action="store_true", required=True)
    args = p.parse_args(argv)
    result = run(job_path=args.job, payload_dir=args.payload_dir,
                 repo=args.repo, state_dir=args.state_dir)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
