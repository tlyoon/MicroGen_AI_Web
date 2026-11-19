"""Source-grounded classification of quarantined historical Git format diagnostics.

This is a read-only companion to the registered historical batch executor.
It does not forgive source defects by Git exit code alone, alter past SHAs,
make code/academic approval claims, or publish student content.
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

from .original_multisource_recovery_campaign import CampaignRecoveryBlocked, require
from .windows_historical_stack_batch_executor import execute_batches
from .windows_head_whitespace_recovery import inspect_head_patch

SIGNATURE = "HISTORICAL_GIT_FORMAT_FINDINGS_NEED_SOURCE_DISPOSITION"
MECHANISM = "VERIFY_HISTORICAL_DIAGNOSTICS_AGAINST_EXACT_GIT_BLOBS"
SCHEMA = 1
MAX_WARNINGS = 100
MAX_BYTES = 8_000_000
_WARNING = re.compile(
    r"^(?P<path>[^:\r\n]{1,255}):(?P<line>[1-9]\d*): "
    r"(?P<kind>new blank line at EOF|trailing whitespace)\.$"
)


def _git_bytes(repo: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        p = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CampaignRecoveryBlocked(
            "Exact historical source Git operation unavailable") from exc
    require(type(p.returncode) is int
            and len(p.stdout) <= MAX_BYTES and len(p.stderr) <= MAX_BYTES,
            "Unbounded or malformed historical Git source")
    return p


def _historical_blob(repo: Path, sha: str, path: str) -> bytes:
    require(re.fullmatch(r"[a-f0-9]{40}", sha) is not None,
            "Invalid historical SHA")
    # Git can interpret a path containing colon as a revision expression;
    # explicitly forbid colon, traversal and option-like path beginnings.
    pure = Path(path.replace("/", os.sep))
    require(path.startswith(("selenium_pipeline/", "tests/", "docs/"))
            and not path.startswith("-")
            and "\\" not in path and ":" not in path
            and not any(s in ("..", ".", "") for s in path.split("/"))
            and not pure.is_absolute(),
            "Historical warning is outside approved source paths")
    p = _git_bytes(repo, "show", f"{sha}:{path}")
    require(p.returncode == 0 and not p.stderr,
            "Historical Git blob missing or invalid")
    return p.stdout


def _source_disposition(*, path: str, line: int, kind: str,
                        source: bytes, addition: str | None) -> str:
    require(len(source) <= MAX_BYTES and not b"\x00" in source,
            "Binary or oversized source cannot be classified as cosmetic")
    if kind == "new blank line at EOF":
        require(addition is None
                and path.endswith(".py")
                and path.startswith(("tests/", "selenium_pipeline/")),
                "Only Python EOF diagnostics can be AST-verified")
        newline = b"\r\n" if b"\r\n" in source else b"\n"
        require(source.endswith(newline + newline),
                "Reported historical Python EOF blank line was not verified")
        clean = source.rstrip(b"\r\n") + newline
        try:
            lhs = ast.dump(ast.parse(source.decode("utf-8-sig")),
                           include_attributes=True)
            rhs = ast.dump(ast.parse(clean.decode("utf-8-sig")),
                           include_attributes=True)
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            raise CampaignRecoveryBlocked(
                "Historical Python EOF source cannot be verified") from exc
        require(lhs == rhs, "Historical Python AST changes on newline removal")
        return "HISTORICAL_PYTHON_EOF_AST_INVARIANT"

    require(kind == "trailing whitespace" and path.startswith("docs/")
            and path.endswith(".md") and addition is not None,
            "Unrecognized historical trailing-whitespace diagnosis")
    lines = source.splitlines()
    require(1 <= line <= len(lines),
            "Historical Git diagnostic source line is missing")
    raw = lines[line - 1]
    require(raw.decode("utf-8") == addition[1:]
            and addition.startswith("+"),
            "Historical Git added-line sample differs from committed source")
    spaces = len(raw) - len(raw.rstrip(b" "))
    require(spaces >= 1,
            "Git warning source line does not contain trailing ASCII space")
    if spaces >= 2:
        return "HISTORICAL_INTENTIONAL_MARKDOWN_HARDBREAK"
    return "HISTORICAL_SINGLE_MARKDOWN_TRAILING_SPACE"


def _inspect_sha(repo: Path, sha: str) -> list[dict]:
    require(re.fullmatch(r"[a-f0-9]{40}", sha) is not None,
            "Invalid historical warning commit")
    p = _git_bytes(repo, "show", "--no-ext-diff", "--no-renames",
                   "--format=", "--check", sha)
    require(p.returncode != 0 and not p.stderr,
            "Previously quarantined Git format finding is no longer present")
    try:
        output = p.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CampaignRecoveryBlocked(
            "Historical Git warnings cannot be decoded safely") from exc
    result: list[dict] = []
    for s in output.splitlines():
        if s.startswith("+"):
            require(result and result[-1]["kind"] == "trailing whitespace"
                    and result[-1].get("addition") is None,
                    "Unanchored historical added line")
            result[-1]["addition"] = s
            continue
        m = _WARNING.fullmatch(s)
        require(m is not None, "Unknown historical Git failure type")
        result.append({
            "sha": sha, "path": m["path"], "line": int(m["line"]),
            "kind": m["kind"], "addition": None,
        })
        require(len(result) <= MAX_WARNINGS,
                "Too many warnings in one historical commit")
    require(result, "Historical Git failure had no parsed diagnostic")
    checked = []
    for item in result:
        source = _historical_blob(repo, sha, item["path"])
        category = _source_disposition(
            path=item["path"], line=item["line"], kind=item["kind"],
            source=source, addition=item["addition"])
        checked.append({
            "historical_commit_sha": sha,
            "path": item["path"], "source_line": item["line"],
            "git_diagnostic": item["kind"],
            "source_blob_sha256": hashlib.sha256(source).hexdigest(),
            "disposition": category,
            "original_git_check_failure_preserved": True,
            "semantic_code_review_approved": False,
        })
    return checked


def _record_bytes(record: dict) -> bytes:
    return (json.dumps(record, sort_keys=True, indent=2,
                       ensure_ascii=False) + "\n").encode("utf8")


def classify_history(*, repo: Path, first_batch: int = 1,
                     last_batch: int | None = None,
                     max_commits: int = 2500) -> dict:
    """Read receipts, inspect each failing commit's immutable source blob.

    Existing read-only batch executor can resume all its saved passes; this
    review deliberately rechecks the small set of historical warnings.
    """
    from .recovery_registry import lookup_mechanism
    require(lookup_mechanism("historical_format_disposition", SIGNATURE)
            == MECHANISM, "Historical format disposition mechanism retired")
    preflight = inspect_head_patch(repo=repo)
    require(preflight["clean"] is True,
            "Current cumulative source patch must be clean before disposition")
    audit = execute_batches(repo=repo, first_batch=first_batch,
                            last_batch=last_batch, max_commits=max_commits)
    records = audit["batch_receipts"]
    warning_pairs = [
        (b["batch_number"], sha)
        for b in records for sha in b["failure_commit_shas"]
    ]
    require(len(warning_pairs) <= MAX_WARNINGS
            and len(set(sha for _, sha in warning_pairs))
            == len(warning_pairs),
            "Unbounded or duplicate historical warning commits")
    findings = []
    for batch_no, sha in warning_pairs:
        for item in _inspect_sha(Path(repo), sha):
            findings.append({"batch_number": batch_no, **item})
            require(len(findings) <= MAX_WARNINGS,
                    "Unbounded historical diagnostic count")
    classes = {
        k: sum(x["disposition"] == k for x in findings)
        for k in (
            "HISTORICAL_PYTHON_EOF_AST_INVARIANT",
            "HISTORICAL_SINGLE_MARKDOWN_TRAILING_SPACE",
            "HISTORICAL_INTENTIONAL_MARKDOWN_HARDBREAK",
        )
    }
    require(sum(classes.values()) == len(findings),
            "Historical warning classification is incomplete")
    result = {
        "schema_version": SCHEMA,
        "status": "HISTORICAL_GIT_FORMAT_DIAGNOSTICS_CLASSIFIED_REVIEW_PENDING",
        "exact_head_sha": audit["exact_head_sha"],
        "current_cumulative_git_patch_clean": True,
        "reviewed_batch_count": audit["batch_count_completed"],
        "historical_failing_commit_count": len(warning_pairs),
        "historical_diagnostic_count": len(findings),
        "historical_quarantined_batches_retained":
            audit["quarantined_batch_numbers"],
        "class_counts": classes,
        "source_verified_diagnostics": findings,
        "historical_git_commit_changes_rewritten": False,
        "semantic_code_review_completed": False,
        "independent_academic_qa_accepted": False,
        "automatic_merge_authorized": False,
        "student_publication_authorized": False,
        "model_or_tts_calls": 0,
    }
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(os.name == "nt" and local.is_dir()
            and Path(repo).absolute().is_relative_to(local),
            "Historical disposition only allowed on local Windows worktree")
    own = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    home = local / "MicroGen_AI_Web_Checkpoints" / "historical_format_disposition_v1"
    require(not home.is_symlink() and not home.parent.is_symlink(),
            "Linked historical format receipt directory")
    home.mkdir(parents=True, exist_ok=True)
    path = home / (audit["exact_head_sha"][:20] + "_" + own[:12] + "_b"
                   + f"{first_batch:03d}-"
                   + f"{(last_batch or audit['last_batch']):03d}.json")
    raw = _record_bytes(result)
    require(len(raw) <= MAX_BYTES and not path.is_symlink(),
            "Unsafe historical format evidence receipt")
    if path.exists():
        require(path.is_file() and path.read_bytes() == raw,
                "Historical format result differs from saved source receipt")
        reused = True
    else:
        try:
            with path.open("xb") as out:
                out.write(raw)
                out.flush()
                os.fsync(out.fileno())
        except FileExistsError:
            require(not path.is_symlink() and path.read_bytes() == raw,
                    "Concurrent historical format evidence conflict")
        reused = False
    return {**result, "receipt_reused_after_restart": reused,
            "receipt_path": str(path)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path,
                   default=Path(__file__).resolve().parent.parent)
    p.add_argument("--first-batch", type=int, default=1)
    p.add_argument("--last-batch", type=int)
    a = p.parse_args(argv)
    try:
        result = classify_history(
            repo=a.repo, first_batch=a.first_batch, last_batch=a.last_batch)
    except (CampaignRecoveryBlocked, OSError, ValueError,
            subprocess.TimeoutExpired, KeyError) as exc:
        print(json.dumps({
            "status": "HISTORICAL_FORMAT_DISPOSITION_BLOCKED",
            "reason": str(exc), "semantic_code_review_completed": False,
            "automatic_merge_authorized": False,
            "student_publication_authorized": False}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
