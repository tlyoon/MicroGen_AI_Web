"""Read-only revision reconciliation for MicroGen Dell production checkouts.

Never resets, pulls, stashes, edits the active worktree, or touches a
running daemon. A clean *new* staging clone is allowed only on request.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ORIGIN = "https://github.com/tlyoon/MicroGen_AI_Web.git"


def _git(*args: str, cwd: Path | None = None) -> str:
    p = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        timeout=45, check=False,
    )
    if p.returncode:
        raise RuntimeError("git " + " ".join(args[:2]) + " failed: " + p.stderr[:400])
    return p.stdout.strip()


def audit(repo: Path, *, expected_origin: str = DEFAULT_ORIGIN) -> dict:
    """Compare a checkout to the live upstream; dirty files are never altered."""
    from .development_continuity_executor_v71 import require_recovery
    require_recovery("CHECKOUT_REVISION_DRIFT")
    repo = Path(repo).resolve()
    result = {"schema_version": 1, "repository": str(repo),
              "status": "UNVERIFIED", "safe_to_cutover": False,
              "recommended_action": "STOP_AND_INSPECT"}
    try:
        inside = _git("rev-parse", "--show-toplevel", cwd=repo)
        if Path(inside).resolve() != repo:
            raise ValueError("not the root of the requested checkout")
        origin = _git("remote", "get-url", "origin", cwd=repo)
        if origin != expected_origin:
            raise ValueError("unexpected origin URL")
        head = _git("rev-parse", "HEAD", cwd=repo)
        if not re.fullmatch("[0-9a-f]{40}", head):
            raise ValueError("invalid local commit")
        dirty = _git("status", "--porcelain", "--untracked-files=normal", cwd=repo)
        result.update(local_sha=head, dirty=bool(dirty),
                      modified_lines=len(dirty.splitlines()))
        remote = _git("ls-remote", "origin", "refs/heads/main", cwd=repo)
        match = re.fullmatch(r"([0-9a-f]{40})\s+refs/heads/main", remote)
        if not match:
            raise ValueError("cannot verify exact upstream main SHA")
        result["remote_sha"] = match.group(1)
        if dirty:
            result.update(status="DIRTY_PRESERVE", recommended_action=
                          "BACKUP_DIFF_AND_STAGE_SEPARATE_CLEAN_CHECKOUT")
        elif head != match.group(1):
            result.update(status="STALE_CLEAN", recommended_action=
                          "STAGE_SEPARATE_CLEAN_CHECKOUT")
        else:
            result.update(status="SYNCED_CLEAN", safe_to_cutover=True,
                          recommended_action="RUN_TESTS_AND_GUARDED_CUTOVER")
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        result["error"] = str(error)[:400]
    return result


def stage(repo: Path, destination: Path, *, expected_origin: str = DEFAULT_ORIGIN) -> dict:
    """Clone only into a fresh path; never reconfigure any existing checkout."""
    report = audit(repo, expected_origin=expected_origin)
    destination = Path(destination).resolve()
    if report["status"] == "UNVERIFIED":
        return report
    if destination.exists():
        return {**report, "stage_status": "REFUSED_EXISTING_DESTINATION"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        _git("clone", "--filter=blob:none", "--branch", "main",
             expected_origin, str(destination))
        staged = audit(destination, expected_origin=expected_origin)
        if staged["status"] != "SYNCED_CLEAN":
            return {**report, "stage_status": "STAGED_NOT_VERIFIED",
                    "staged_audit": staged}
        return {**report, "stage_status": "STAGED_CLEAN",
                "staged_sha": staged["local_sha"],
                "staged_path": str(destination)}
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        return {**report, "stage_status": "STAGE_FAILED", "error": str(error)[:400]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = (stage(args.repo, args.stage) if args.stage else audit(args.repo))
    result["checked_at_utc"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temp = args.report.with_name(args.report.name + ".tmp")
        temp.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf8")
        temp.replace(args.report)
    return 0 if (result.get("stage_status") == "STAGED_CLEAN"
                 or result["status"] == "SYNCED_CLEAN") else 2


if __name__ == "__main__":
    raise SystemExit(main())

