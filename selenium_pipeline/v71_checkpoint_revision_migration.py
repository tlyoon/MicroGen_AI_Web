"""Audited migration of pinned v7.1 offline-executor checkpoints.

Only this exact recovery-registry-only source delta is permitted. All task,
provider-claim, handoff, plan and journal bytes remain unchanged. Never modifies
an existing source state, git checkout or scheduled task.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

from .development_continuity_executor_v71 import require_recovery

_ALLOWED_DELTA = (
    '    "CHECKOUT_REVISION_DRIFT":\n'
    '        "PRESERVE_DIRTY_WORKTREE_STAGE_FRESH_VERIFIED_MAIN_AND_GUARDED_CUTOVER",\n'
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_delta(old: Path, new: Path) -> tuple[str, str]:
    old_raw = old.read_bytes()
    new_raw = new.read_bytes()
    old_norm = old_raw.replace(b"\r\n", b"\n")
    new_norm = new_raw.replace(b"\r\n", b"\n")
    delta = _ALLOWED_DELTA.encode("utf8")
    if new_norm.count(delta) != 1 or new_norm.replace(delta, b"", 1) != old_norm:
        raise ValueError("Executor changed beyond the exact approved registry handler delta")
    return hashlib.sha256(old_raw).hexdigest(), hashlib.sha256(new_raw).hexdigest()


def migrate(*, source: Path, destination: Path, old_executor: Path,
            new_executor: Path, primary_plan: Path) -> dict:
    """Make a NEW checkpoint from a source snapshot; fail closed on any drift."""
    require_recovery("CHECKOUT_REVISION_DRIFT")
    raw_source = Path(source).absolute()
    if raw_source.is_symlink():
        raise ValueError("Unsafe linked checkpoint source")
    source = raw_source.resolve()
    destination = Path(destination).absolute()
    old_executor = Path(old_executor)
    new_executor = Path(new_executor)
    primary_plan = Path(primary_plan)
    if destination == source or source in destination.parents:
        raise ValueError("Destination cannot be nested inside source")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Existing destination cannot be overwritten")
    if not source.is_dir() or source.is_symlink():
        raise ValueError("Unsafe source checkpoint directory")
    if not all(p.is_file() and not p.is_symlink()
               for p in (old_executor, new_executor, primary_plan)):
        raise ValueError("Missing or linked pinned source/plan")
    for candidate in source.rglob("*"):
        if candidate.is_symlink():
            raise ValueError("Linked checkpoint content forbidden")
    old_sha, new_sha = _verify_delta(old_executor, new_executor)
    head = source / "state.json"
    if not head.is_file():
        raise ValueError("Primary executor checkpoint absent")
    primary = json.loads(head.read_text(encoding="utf8"))
    plan_sha = _sha(primary_plan)
    if primary.get("plan_sha256") != plan_sha:
        raise ValueError("Primary roadmap SHA differs from source")
    hb_file = source / "daemon_heartbeat.json"
    if not hb_file.is_file():
        raise ValueError("Original daemon heartbeat is missing")
    beat = json.loads(hb_file.read_text(encoding="utf8"))
    if (beat.get("plan_sha256") != plan_sha
            or beat.get("provider_sends") != 0
            or beat.get("student_publication_authorized") is not False):
        raise ValueError("Original offline authorization boundary cannot be proved")
    paths = sorted(source.rglob("state.json"))
    if not paths or not all(json.loads(p.read_text(encoding="utf8")).get("executor_sha256")==old_sha
                            for p in paths):
        raise ValueError("Mixed or unexpected executor checkpoint pins")
    snapshots = {str(p.relative_to(source)): _sha(p) for p in paths}
    # No mutable active checkpoint is altered. Stage and publish a separate tree.
    staged = destination.with_name(destination.name + ".stage")
    if staged.exists() or staged.is_symlink():
        raise ValueError("Existing staging path cannot be overwritten")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns(
            "daemon.lock", "executor.lock", "daemon_heartbeat.json"))
        originals = {}
        updated = {}
        for p in paths:
            rel = p.relative_to(source)
            # Detect source mutations during snapshot copying (the caller should
            # normally stop the old process first).
            if _sha(p) != snapshots[str(rel)]:
                raise ValueError("Source checkpoint changed during migration")
            dest_file = staged / rel
            raw = dest_file.read_bytes()
            regex = (rb'("executor_sha256"\s*:\s*")'
                     + old_sha.encode() + rb'(")')
            altered, count = re.subn(regex, lambda m: m.group(1)
                                    + new_sha.encode() + m.group(2), raw)
            if count != 1:
                raise ValueError("Missing or ambiguous exact executor pin")
            dest_file.write_bytes(altered)
            originals[str(rel)] = snapshots[str(rel)]
            updated[str(rel)] = _sha(dest_file)
            parsed = json.loads(dest_file.read_text(encoding="utf8"))
            if parsed.get("executor_sha256") != new_sha:
                raise ValueError("Checkpoint pin migration did not verify")
        receipt = {
            "schema_version": 1,
            "status": "V71_EXACT_REGISTRY_ONLY_EXECUTOR_PIN_MIGRATED",
            "old_executor_sha256": old_sha,
            "new_executor_sha256": new_sha,
            "primary_plan_sha256": plan_sha,
            "source_checkpoint": str(source),
            "destination_checkpoint": str(destination),
            "original_state_hashes": originals,
            "migrated_state_hashes": updated,
            "checkpoint_count": len(paths),
            "provider_sends": 0,
            "student_publication_authorized": False,
            "source_was_not_modified": True,
        }
        (staged / "checkpoint_revision_migration_receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True), encoding="utf8")
        staged.rename(destination)
        return receipt
    except Exception:
        if staged.exists():
            shutil.rmtree(staged)
        raise


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--old-executor", type=Path, required=True)
    parser.add_argument("--new-executor", type=Path, required=True)
    parser.add_argument("--primary-plan", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = migrate(source=args.source, destination=args.destination,
                      old_executor=args.old_executor, new_executor=args.new_executor,
                      primary_plan=args.primary_plan)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
