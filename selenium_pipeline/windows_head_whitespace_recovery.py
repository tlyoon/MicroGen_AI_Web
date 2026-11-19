"""Safe current-head cosmetic whitespace recovery on an isolated Windows checkout.

This never rewrites past Git commits, source PDFs or scientific receipts.
The ONLY automatic edits allowed are extra empty lines at end of Python files
(with identical Python AST) and a single Markdown trailing space (not a
Markdown hard-break pair). Unexpected Git diagnostic types fail closed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

from .original_multisource_recovery_campaign import CampaignRecoveryBlocked, require

SIGNATURE = "CUMULATIVE_HEAD_PATCH_HAS_SAFE_COSMETIC_WHITESPACE"
MECHANISM = "NORMALIZE_AST_INVARIANT_PYTHON_EOF_AND_SINGLE_MARKDOWN_SPACE"
_WARNING = re.compile(
    r"^(?P<path>[^:\n]+):(?P<line>[1-9]\d*): "
    r"(?P<kind>new blank line at EOF|trailing whitespace)\.$"
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf8",
        errors="replace", timeout=45, check=False,
    )


def _require_repo(repo: Path) -> Path:
    require(os.name == "nt", "Native Dell-115 Windows-only source repair")
    repo = Path(repo).absolute()
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(local.is_dir() and repo.is_dir()
            and not repo.is_symlink() and repo.is_relative_to(local)
            and (repo / ".git").exists() and not (repo / ".git").is_symlink(),
            "Only isolated user-local Git worktree may be audited or repaired")
    return repo


def _get_patch_warnings(repo: Path, *, include_worktree: bool) -> list[dict]:
    args = (("diff", "--no-ext-diff", "--check", "origin/main")
            if include_worktree else
            ("diff", "--no-ext-diff", "--check", "origin/main..HEAD"))
    p = _git(repo, *args)
    # Windows Git autocrlf may emit an ordinary conversion notice even when
    # --check succeeds. A tightly matched warning is not a patch violation.
    notices = [x for x in p.stderr.splitlines() if x.strip()]
    benign_eol_notice = re.compile(
        r"^warning: in the working copy of '[^']+', "
        r"LF will be replaced by CRLF the next time Git touches it$")
    require(p.returncode in (0, 2)
            and all(benign_eol_notice.fullmatch(x) is not None
                    for x in notices),
            "Git diff check unavailable or unexpected stderr: "
            + str(p.returncode) + " " + p.stderr[:200])
    lines = [x for x in p.stdout.splitlines() if x]
    items = []
    for line in lines:
        if line.startswith("+"):
            # Git prints the offending addition after a whitespace diagnostic.
            require(items and items[-1]["kind"] == "trailing whitespace"
                    and "addition" not in items[-1],
                    "Detached Git diff trailing whitespace sample")
            items[-1]["addition"] = line
            continue
        m = _WARNING.fullmatch(line)
        require(m is not None,
                "Unsafe or unrecognized cumulative Git whitespace finding")
        rel = m.group("path")
        pure = PurePosixPath(rel)
        require(not pure.is_absolute() and ".." not in pure.parts
                and not rel.startswith(("/", "\\"))
                and len(rel) <= 256,
                "Unsafe Git whitespace path")
        items.append({"path": rel, "line": int(m.group("line")),
                      "kind": m.group("kind")})
    require((p.returncode == 0) == (not items),
            "Inconsistent Git diff check outcome")
    return items


def inspect_head_patch(*, repo: Path) -> dict:
    repo = _require_repo(repo)
    head = _git(repo, "rev-parse", "HEAD")
    base = _git(repo, "rev-parse", "origin/main")
    require(head.returncode == base.returncode == 0
            and re.fullmatch(r"[0-9a-f]{40}", head.stdout.strip())
            and re.fullmatch(r"[0-9a-f]{40}", base.stdout.strip()),
            "Exact Git head or tracked main unavailable")
    findings = _get_patch_warnings(repo, include_worktree=False)
    return {
        "status": ("CUMULATIVE_HEAD_PATCH_FORMAT_CLEAN" if not findings else
                   "CUMULATIVE_HEAD_PATCH_FORMAT_REQUIRES_REVIEW"),
        "exact_head_sha": head.stdout.strip(),
        "tracked_main_sha": base.stdout.strip(),
        "patch_warning_count": len(findings),
        "findings": findings,
        "clean": not findings,
        "automatic_merge_authorized": False,
        "student_publication_authorized": False,
    }


def _normalize(repo: Path, item: dict, before: bytes) -> bytes:
    rel = item["path"]
    target = repo / Path(*PurePosixPath(rel).parts)
    require(target.is_file() and not target.is_symlink()
            and target.resolve().is_relative_to(repo.resolve())
            and len(before) <= 12_000_000,
            "Unsafe or oversized source path for cosmetic repair")
    if item["kind"] == "new blank line at EOF":
        require(rel.endswith(".py") and rel.startswith(
            ("selenium_pipeline/", "tests/")),
            "Only Python source/test EOF cosmetic repair permitted")
        # Keep every byte of content and original newline convention
        # except one or more extra blank lines at end of the module.
        newline = b"\r\n" if b"\r\n" in before else b"\n"
        require(before.endswith(newline + newline),
                "Expected redundant Python EOF blank line is absent")
        after = before.rstrip(b"\r\n") + newline
        require(ast.dump(ast.parse(before.decode("utf-8-sig")),
                         include_attributes=True) ==
                ast.dump(ast.parse(after.decode("utf-8-sig")),
                         include_attributes=True),
                "Python syntax tree changed during format-only recovery")
        return after
    require(item["kind"] == "trailing whitespace"
            and rel.endswith(".md") and rel.startswith("docs/"),
            "Only Markdown single-space repair permitted")
    parts = before.splitlines(keepends=True)
    index = item["line"] - 1
    require(0 <= index < len(parts),
            "Wrong Markdown source line from Git diff diagnostic")
    line = parts[index]
    ending = b"\r\n" if line.endswith(b"\r\n") else (
        b"\n" if line.endswith(b"\n") else b"")
    body = line[:-len(ending)] if ending else line
    # Two spaces are intentional Markdown hard line breaks: NEVER change.
    require(body.endswith(b" ") and not body.endswith(b"  "),
            "Markdown hard-break or unknown whitespace cannot be auto-repaired")
    parts[index] = body[:-1] + ending
    return b"".join(parts)


def repair_safe_current_source(*, repo: Path) -> dict:
    """Opt-in development recovery, never called from read-only release audit."""
    repo = _require_repo(repo)
    from .recovery_registry import lookup_mechanism
    require(lookup_mechanism("head_patch_format", SIGNATURE) == MECHANISM,
            "Executable safe formatting remedy missing or retired")
    from .three_pc_worker import LocalInstanceLock
    from .windows_head_format_repair_journal import (
        resume_pending, apply_prepared,
    )
    local = Path(os.environ["LOCALAPPDATA"]).absolute()
    lock_key = hashlib.sha256(str(repo).lower().encode("utf-8")).hexdigest()[:20]
    with LocalInstanceLock(
        "format_repair_" + lock_key,
        local / "MicroGen_AI_Web_Checkpoints" / "head_format_repair_locks",
    ):
        initial = inspect_head_patch(repo=repo)
        # Resume a prior crash BEFORE the normal clean-worktree preflight.
        # Dirty source is permitted only when byte-for-byte accounted for in
        # an immutable exact-HEAD write-ahead intent.
        resumed = resume_pending(
            repo=repo, head=initial["exact_head_sha"],
            checker=_get_patch_warnings,
        )
        if resumed is not None:
            return resumed
        state = _git(repo, "status", "--porcelain")
        require(state.returncode == 0 and not state.stdout.strip(),
                "Do not rewrite a dirty or concurrently changing source checkout")
        findings = initial["findings"]
        require(len(findings) <= 50,
                "Too many cumulative formatting findings for bounded safe repair")
        prepared: dict[Path, tuple[bytes, bytes]] = {}
        for finding in findings:
            path = repo / Path(*PurePosixPath(finding["path"]).parts)
            before = prepared[path][0] if path in prepared else path.read_bytes()
            current = prepared[path][1] if path in prepared else before
            after = _normalize(repo, finding, current)
            prepared[path] = (before, after)
        if prepared:
            return apply_prepared(
                repo=repo, head=initial["exact_head_sha"],
                prepared=prepared, original_warnings=findings,
                checker=_get_patch_warnings,
            )
        return {
            "status": "CURRENT_CUMULATIVE_PATCH_ALREADY_CLEAN",
            "source_head_sha_before_repair": initial["exact_head_sha"],
            "normalized_file_count": 0,
            "repaired_historical_patch_warning_count": 0,
            "original_patch_warnings_retained_as_evidence": [],
            "python_ast_unchanged": True,
            "historical_commits_rewritten": False,
            "git_commit_created": False,
            "new_model_or_tts_calls": False,
            "automatic_merge_authorized": False,
            "student_publication_authorized": False,
            "new_worktree_dirty_for_review_and_commit": False,
        }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path,
                   default=Path(__file__).resolve().parent.parent)
    p.add_argument("--repair-current-isolated-source", action="store_true")
    a = p.parse_args(argv)
    try:
        report = (repair_safe_current_source(repo=a.repo)
                  if a.repair_current_isolated_source else
                  inspect_head_patch(repo=a.repo))
    except (OSError, CampaignRecoveryBlocked, ValueError,
            subprocess.TimeoutExpired) as exc:
        print(json.dumps({
            "status": "HEAD_PATCH_SAFE_RECOVERY_BLOCKED",
            "reason": str(exc),
            "automatic_merge_authorized": False,
            "student_publication_authorized": False}, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report.get("clean", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
