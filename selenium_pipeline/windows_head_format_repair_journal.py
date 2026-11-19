"""Crash-safe, SHA-bound write-ahead journal for opt-in cosmetic source repair.

Used solely by windows_head_whitespace_recovery in a clean isolated Windows
developer worktree. No publisher content, provider requests, Git rewrite,
automatic commit or release. A crash between file replacements is recoverable.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

from .original_multisource_recovery_campaign import CampaignRecoveryBlocked, require

SCHEMA = 1
MAX_JOURNAL_BYTES = 4_000_000
MAX_FILES = 50


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _encode(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n").encode("utf-8")


def _integrity(body: dict) -> str:
    return _hash(json.dumps(
        {k: v for k, v in body.items() if k != "integrity_sha256"},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8"))


def journal_paths(repo: Path, head: str) -> tuple[Path, Path]:
    require(re.fullmatch(r"[0-9a-f]{40}", head) is not None,
            "Source repair journal has an invalid source HEAD")
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    repo = Path(repo).absolute()
    require(os.name == "nt" and local.is_dir()
            and repo.is_relative_to(local) and repo.is_dir()
            and not repo.is_symlink(),
            "Source repair journal is only valid in isolated native Windows checkout")
    root = local / "MicroGen_AI_Web_Checkpoints" / "head_format_repair_journal_v1"
    require(not root.is_symlink() and not root.parent.is_symlink(),
            "Linked source repair journal root")
    root.mkdir(parents=True, exist_ok=True)
    prefix = _hash(str(repo).lower().encode("utf-8"))[:18] + "_" + head[:18]
    return root / (prefix + ".intent.json"), root / (prefix + ".result.json")


def _source_path(repo: Path, rel: str) -> Path:
    pure = PurePosixPath(rel)
    require(type(rel) is str and rel.startswith(("docs/", "tests/", "selenium_pipeline/"))
            and len(rel) <= 255
            and not pure.is_absolute() and not any(p in (".", "..", "")
                                                 for p in pure.parts)
            and "\\" not in rel and ":" not in rel,
            "Repair intent references unsafe source path")
    target = repo / Path(*pure.parts)
    require(target.is_file() and not target.is_symlink()
            and target.resolve().is_relative_to(repo.resolve()),
            "Repair journal target is absent or linked")
    return target


def _decode_file(entry: dict, repo: Path) -> tuple[Path, bytes, bytes]:
    require(type(entry) is dict
            and set(entry) == {"path", "before_b64", "after_b64",
                               "before_sha256", "after_sha256"},
            "Unexpected repair journal entry fields")
    path = _source_path(repo, entry["path"])
    try:
        before = base64.b64decode(entry["before_b64"], validate=True)
        after = base64.b64decode(entry["after_b64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise CampaignRecoveryBlocked("Invalid source recovery journal encoding") from exc
    require(0 < len(before) <= 2_000_000 and 0 < len(after) <= 2_000_000
            and _hash(before) == entry["before_sha256"]
            and _hash(after) == entry["after_sha256"]
            and before != after,
            "Source journal original/replacement bytes were altered")
    # Decode+recheck original format operation, never trust stored bytes alone.
    from .windows_head_whitespace_recovery import _normalize, inspect_head_patch
    if entry["path"].endswith(".py"):
        try:
            require(
                ast.dump(ast.parse(before.decode("utf-8-sig")),
                         include_attributes=True) ==
                ast.dump(ast.parse(after.decode("utf-8-sig")),
                         include_attributes=True),
                "Recovered Python AST would not be invariant")
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise CampaignRecoveryBlocked(
                "Recovered Python source is not syntactically valid") from exc
    elif entry["path"].endswith(".md"):
        require(before != after, "Recovered Markdown source unchanged")
    else:
        require(False, "Unrecognized source journal format")
    # Recompute the precisely allowed source change from recorded original
    # diagnostic, with current file path already reverified.
    # The later callers verify exact branch, patch, and file state.
    return path, before, after


def _read_intent(repo: Path, head: str, path: Path) -> tuple[dict, list]:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= MAX_JOURNAL_BYTES,
            "Missing, linked or oversized source repair intent")
    obj = json.loads(path.read_text(encoding="utf-8"))
    require(type(obj) is dict
            and set(obj) == {"schema_version", "status", "source_head_sha",
                             "repository", "source_checker_sha256", "entries",
                             "original_warnings", "integrity_sha256"}
            and obj["schema_version"] == SCHEMA
            and obj["status"] == "PENDING_EXACT_HEAD_COSMETIC_SOURCE_REPAIR"
            and obj["source_head_sha"] == head
            and obj["repository"] == str(repo)
            and obj["source_checker_sha256"] ==
                _hash((Path(__file__).parent /
                       "windows_head_whitespace_recovery.py").read_bytes())
            and obj["integrity_sha256"] == _integrity(obj)
            and type(obj["entries"]) is list
            and 1 <= len(obj["entries"]) <= MAX_FILES
            and type(obj["original_warnings"]) is list
            and len(obj["original_warnings"]) <= MAX_FILES,
            "Source repair journal does not match installed source code and HEAD")
    decoded = [_decode_file(e, repo) for e in obj["entries"]]
    require(len({p for p, _, _ in decoded}) == len(decoded),
            "Duplicate source target in recovery journal")
    # Recompute every operation from exact Git diagnostics and original bytes.
    from .windows_head_whitespace_recovery import _normalize, inspect_head_patch
    static = inspect_head_patch(repo=repo)
    require(static["exact_head_sha"] == head
            and static["findings"] == obj["original_warnings"],
            "Changed exact-head Git format diagnostics during source recovery")
    prepared = {}
    for finding in obj["original_warnings"]:
        target = _source_path(repo, finding["path"])
        previous = prepared[target][1] if target in prepared else next(
            (before for p, before, _ in decoded if p == target), None)
        require(previous is not None,
                "Unexplained source file in persisted cosmetic repair")
        updated = _normalize(repo, finding, previous)
        prepared[target] = (previous, updated)
    require({p: a for p, _, a in decoded}
            == {p: a for p, (_, a) in prepared.items()},
            "Source journal contains an unrecognized file change")
    return obj, decoded


def _new_receipt(path: Path, value: dict) -> None:
    require(not path.exists() and not path.is_symlink(),
            "Would overwrite an existing immutable source journal receipt")
    raw = _encode(value)
    require(0 < len(raw) <= MAX_JOURNAL_BYTES,
            "Source journal size exceeds explicit bound")
    # A crash during intent/result fsync must not leave a torn *authoritative*
    # receipt. Only a staging file outside source may remain, and the
    # per-repository OS lock ensures the next attempt can safely discard it.
    stage = path.with_name(path.name + ".staging")
    require(not stage.is_symlink() and not stage.is_dir(),
            "Unsafe source journal staged receipt")
    if stage.exists():
        require(stage.is_file()
                and stage.stat().st_size <= MAX_JOURNAL_BYTES,
                "Unrecognized staged source journal evidence")
        stage.unlink()
    with stage.open("xb") as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())
    require(stage.read_bytes() == raw
            and not path.exists() and not path.is_symlink(),
            "Staged source journal receipt conflicts with final destination")
    os.replace(stage, path)


def _atomic_install(target: Path, content: bytes, intent: Path,
                    index: int) -> None:
    """Stage on same local Windows volume, then replace one whole source file."""
    tmp = intent.parent / (intent.stem + f".f{index:03d}.stage")
    require(not tmp.is_symlink() and not tmp.is_dir(),
            "Unsafe staged source repair path")
    if tmp.exists():
        # A prior process may have terminated during stage write. Staging
        # lies outside repo, and the locked exact journal owns this name.
        tmp.unlink()
    with tmp.open("xb") as out:
        out.write(content)
        out.flush()
        os.fsync(out.fileno())
    require(tmp.read_bytes() == content,
            "Staged atomic replacement was not byte-exact")
    os.replace(tmp, target)


def _require_only_journal_dirty_paths(repo: Path, files: list) -> None:
    """A crash journal must not authorize unrelated dirty worktree changes."""
    p = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain",
         "--untracked-files=all"],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=35, check=False,
    )
    require(p.returncode == 0 and not p.stderr.strip(),
            "Cannot verify isolated worktree against recovery journal")
    allowed = {path.relative_to(repo).as_posix() for path, _, _ in files}
    for line in p.stdout.splitlines():
        require(line.startswith(" M ")
                and line[3:].replace("\\", "/") in allowed,
                "Unexplained dirty or staged source change during recovery")


def _apply(repo: Path, intent: Path, result: Path, obj: dict,
           files: list, checker) -> dict:
    _require_only_journal_dirty_paths(repo, files)
    if result.exists():
        require(result.is_file() and not result.is_symlink()
                and all(path.read_bytes() == after
                        for path, _, after in files),
                "Completed source repair changed after its verified result")
    # The exact source file may be in either known before/after state after
    # process death, but NEVER silently overwrite an unexplained third state.
    for index, (path, before, after) in enumerate(files, start=1):
        actual = path.read_bytes()
        require(actual in (before, after),
                "Source changed outside crash-recovery journal; stop")
        if actual == before:
            _atomic_install(path, after, intent, index)
    require(not checker(repo, include_worktree=True),
            "Repaired cumulative source patch still has Git warnings")
    record = {
        "schema_version": SCHEMA,
        "status": "SOURCE_FORMAT_REPAIR_PERSISTENTLY_APPLIED",
        "source_head_sha": obj["source_head_sha"],
        "intent_sha256": _hash(intent.read_bytes()),
        "file_count": len(files),
        "automatic_merge_authorized": False,
        "student_publication_authorized": False,
    }
    if result.exists():
        require(result.is_file() and not result.is_symlink()
                and result.read_bytes() == _encode(record),
                "Completed source repair receipt altered or conflicts")
        already = True
    else:
        _new_receipt(result, record)
        already = False
    return {
        "status": "CURRENT_ISOLATED_SOURCE_SAFE_WHITESPACE_NORMALIZED",
        "source_head_sha_before_repair": obj["source_head_sha"],
        "normalized_file_count": len(files),
        "repaired_historical_patch_warning_count": len(obj["original_warnings"]),
        "original_patch_warnings_retained_as_evidence": obj["original_warnings"],
        "python_ast_unchanged": True,
        "historical_commits_rewritten": False,
        "git_commit_created": False,
        "new_model_or_tts_calls": False,
        "automatic_merge_authorized": False,
        "student_publication_authorized": False,
        "new_worktree_dirty_for_review_and_commit": bool(files),
        "journal_recovered_or_reused_after_restart": already,
        "journal_path": str(intent),
    }


def resume_pending(*, repo: Path, head: str, checker) -> dict | None:
    intent, result = journal_paths(repo, head)
    if not intent.exists():
        require(not result.exists(), "Orphan completed source repair receipt")
        return None
    obj, files = _read_intent(repo, head, intent)
    # Existing done receipts are validated by _apply, and files by hashes.
    was_done = result.exists()
    report = _apply(repo, intent, result, obj, files, checker)
    report["journal_recovered_or_reused_after_restart"] = True
    report["previous_run_completed"] = was_done
    return report


def apply_prepared(*, repo: Path, head: str, prepared: dict,
                   original_warnings: list[dict], checker) -> dict:
    intent, result = journal_paths(repo, head)
    require(not intent.exists() and not result.exists(),
            "Existing source repair journal must be resumed, not overwritten")
    require(1 <= len(prepared) <= MAX_FILES
            and 1 <= len(original_warnings) <= MAX_FILES,
            "Unbounded or empty source repair plan")
    entries = []
    for path, (before, after) in prepared.items():
        rel = path.relative_to(repo).as_posix()
        _source_path(repo, rel)
        require(path.read_bytes() == before and after != before,
                "Original isolated file changed during source repair planning")
        entries.append({
            "path": rel, "before_b64": base64.b64encode(before).decode("ascii"),
            "after_b64": base64.b64encode(after).decode("ascii"),
            "before_sha256": _hash(before),
            "after_sha256": _hash(after),
        })
    body = {
        "schema_version": SCHEMA,
        "status": "PENDING_EXACT_HEAD_COSMETIC_SOURCE_REPAIR",
        "source_head_sha": head,
        "repository": str(repo),
        "source_checker_sha256": _hash((Path(__file__).parent /
                                      "windows_head_whitespace_recovery.py").read_bytes()),
        "entries": entries,
        "original_warnings": original_warnings,
    }
    body["integrity_sha256"] = _integrity(body)
    _new_receipt(intent, body)
    obj, files = _read_intent(repo, head, intent)
    return _apply(repo, intent, result, obj, files, checker)
