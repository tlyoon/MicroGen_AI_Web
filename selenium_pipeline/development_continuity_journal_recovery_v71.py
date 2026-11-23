"""Crash-safe v7.1 recovery of unbounded *duplicate* idle polling events.

The historical full JSON is immutable, SHA-addressed and retained. Only
adjacent identical execution_checkpoint entries are consolidated; all
admission, claim, dispatch, result and release events remain. No provider
request, task replay or student publication is available in this module.

Do not edit development_continuity_executor_v71.py: its original SHA is
embedded in actual persisted source-plan checkpoints and worker receipts.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from .development_continuity_executor_v71 import (
    _atomic_json, _exclusive, _plan, _read_json, _sha, _require,
)
from .recovery_registry import lookup_mechanism

KIND="v71_polling_journal_recovery"
SIGNATURE="V71_REPEATED_IDLE_CHECKPOINT_EVENTS_EXCEED_JSON_READ_BOUND"
REMEDY="ARCHIVE_SHA_PINNED_FULL_JOURNAL_DEDUP_IDENTICAL_IDLE_EVENTS"
INPUT_LIMIT_BYTES=240000
COMPACT_TRIGGER_BYTES=180000
MAX_LEGACY_STATE_BYTES=4_000_000
MAX_LEGACY_EVENTS=16_000


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_original(path: Path) -> tuple[bytes,dict]:
    _require(path.is_file() and not path.is_symlink(),
             "Original state journal is not an ordinary file")
    size=path.stat().st_size
    _require(0<size<=MAX_LEGACY_STATE_BYTES,
             "Oversized source journal exceeds bounded repair capacity")
    original=path.read_bytes()
    _require(len(original)==size,"Source journal changed while reading")
    value=json.loads(original.decode("utf8"))
    _require(type(value) is dict,"Source journal must remain a JSON object")
    return original,value


def _verify_state(state:dict, *, plan_path:Path)->None:
    from . import development_continuity_executor_v71 as original
    plan=_plan(plan_path)
    _require(state.get("schema_version")==1
             and state.get("plan_sha256")==_sha(plan_path)
             and state.get("executor_sha256")==_sha(Path(original.__file__))
             and type(state.get("tasks")) is dict
             and set(state["tasks"])=={t["id"] for t in plan["tasks"]}
             and type(state.get("events")) is list
             and 1<=len(state["events"])<=MAX_LEGACY_EVENTS
             and type(state.get("project_complete")) is bool,
             "Original journal plan/executor/worker status identity changed")
    for index,event in enumerate(state["events"],1):
        _require(type(event) is dict
                 and set(event)=={"seq","event","task","detail"}
                 and type(event["seq"]) is int and event["seq"]==index
                 and type(event["event"]) is str
                 and (event["task"] is None or
                      event["task"] in state["tasks"])
                 and type(event["detail"]) is dict,
                 "Source journal event sequence or original proof is invalid")
    for task in plan["tasks"]:
        row=state["tasks"][task["id"]]
        _require(type(row) is dict
                 and row.get("status") in {
                   "pending","dispatched","awaiting_receipt",
                   "passed","quarantined","awaiting_authorization"}
                 and type(row.get("attempts")) is int
                 and 0<=row["attempts"]<=task["max_attempts"],
                 "Unsafe source task record during journal archive")


def _attest_existing_archive(state_dir:Path,state:dict)->None:
    info=state.get("idle_journal_archive")
    if info is None:
        return
    _require(type(info) is dict and set(info)=={
        "original_state_sha256","original_event_count",
        "removed_identical_idle_poll_events","preserved_full_history",
        "current_event_seq_epoch",
    } and info.get("preserved_full_history") is True
       and type(info.get("original_event_count")) is int
       and type(info.get("removed_identical_idle_poll_events")) is int
       and type(info.get("current_event_seq_epoch")) is int
       and info["original_event_count"]>info["removed_identical_idle_poll_events"]>0
       and info["current_event_seq_epoch"]>0
       and type(info.get("original_state_sha256")) is str
       and re.fullmatch(r"[0-9a-f]{64}",info["original_state_sha256"]),
       "Malformed prior immutable polling-journal archive witness")
    file=state_dir/"journal_archive"/(
        "state_"+info["original_state_sha256"]+".json")
    raw,historical=_read_original(file)
    _require(_sha_bytes(raw)==info["original_state_sha256"]
             and type(historical.get("events")) is list
             and len(historical["events"])==info["original_event_count"],
             "Source journal's prior immutable archive is missing or changed")


def recover_journal(*,state_dir:Path,plan_path:Path,
                    trigger_bytes:int=COMPACT_TRIGGER_BYTES)->dict:
    """Return a verified no-send compaction receipt, or a no-op.

    Runs before execute() and holds the SAME exclusive executor ownership
    byte lock. A crash after archiving but before atomic state replacement
    leaves the original state intact; restarting reuses the exact SHA archive.
    """
    _require(type(trigger_bytes) is int
             and 1<=trigger_bytes<=COMPACT_TRIGGER_BYTES,
             "Invalid bounded journal trigger")
    _require(lookup_mechanism(KIND,SIGNATURE)==REMEDY,
             "v7.1 polling journal repair not registered")
    state_dir=Path(state_dir).absolute()
    plan_path=Path(plan_path).absolute()
    with _exclusive(state_dir):
        state_file=state_dir/"state.json"
        if not state_file.exists():
            return {"status":"NO_PRIOR_JOURNAL","provider_sends":0}
        _require(not state_file.is_symlink(),"Linked source journal")
        if state_file.stat().st_size<trigger_bytes:
            # Recheck historical byte-preserving archive even if the ENTIRE
            # archive folder was deleted after a successful compaction.
            _,current=_read_original(state_file)
            _attest_existing_archive(state_dir,current)
            return {"status":"JOURNAL_UNDER_THRESHOLD","provider_sends":0}
        original_bytes,data=_read_original(state_file)
        _verify_state(data,plan_path=plan_path)
        _attest_existing_archive(state_dir,data)
        original_events=data["events"]
        retained=[]
        removed=0
        for event in original_events:
            if (event["event"]=="execution_checkpoint"
                and event["task"] is None
                and retained
                and retained[-1]["event"]=="execution_checkpoint"
                and retained[-1]["task"] is None
                and retained[-1]["detail"]==event["detail"]):
                removed+=1
                continue
            retained.append(dict(event))
        _require(removed>0,
                 "No redundant idle polling event exists to compact safely")
        for index,event in enumerate(retained,1):
            event["seq"]=index  # local sequence; full original sequence archived
        compact=dict(data)
        compact["events"]=retained
        witness=_sha_bytes(original_bytes)
        compact["idle_journal_archive"]={
            "original_state_sha256":witness,
            "original_event_count":len(original_events),
            "removed_identical_idle_poll_events":removed,
            "preserved_full_history":True,
            "current_event_seq_epoch":1+
                int((data.get("idle_journal_archive") or {}).get(
                    "current_event_seq_epoch",0)),
        }
        output=(json.dumps(compact,sort_keys=True,indent=2)+"\n").encode("utf8")
        _require(len(output)<COMPACT_TRIGGER_BYTES,
                 "Compacted journal remains too large; preserve source")
        # SHA-addressed, write-once historical archive; never overwrite bytes
        # and never prune any admitted task, original receipt or raw evidence.
        archive_dir=state_dir/"journal_archive"
        if not archive_dir.exists():
            archive_dir.mkdir()
        _require(archive_dir.is_dir() and not archive_dir.is_symlink(),
                 "Unsafe archive directory")
        archive=archive_dir/("state_"+witness+".json")
        if archive.exists() or archive.is_symlink():
            _require(archive.is_file() and not archive.is_symlink()
                     and archive.read_bytes()==original_bytes,
                     "Pre-existing journal archive conflicts with original")
        else:
            # Crash during archive WRITE must never strand a partially
            # populated final SHA-addressed file. Link completed temp bytes
            # atomically with create-if-absent semantics (Windows NTFS works).
            temporary=archive.with_name(
                archive.name+".tmp."+uuid.uuid4().hex)
            try:
                with temporary.open("xb") as stream:
                    stream.write(original_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    os.link(temporary,archive)
                except FileExistsError:
                    _require(archive.is_file() and not archive.is_symlink()
                             and archive.read_bytes()==original_bytes,
                             "Concurrent or conflicting original archive")
            finally:
                if temporary.exists():
                    temporary.unlink()
        _require(_sha_bytes(archive.read_bytes())==witness,
                 "Archived original journal SHA mismatch")
        _atomic_json(state_file,compact)
        verified=_read_json(state_file)
        _require(verified==compact,
                 "Atomic journal compaction did not preserve current state")
        return {
            "status":"ORIGINAL_POLLING_JOURNAL_SHA_ARCHIVED_AND_COMPACTED",
            "original_state_sha256":witness,
            "archive_path":str(archive),
            "original_events":len(original_events),
            "retained_events":len(retained),
            "removed_duplicate_idle_events":removed,
            "input_bytes":len(original_bytes),
            "compacted_bytes":state_file.stat().st_size,
            "plan_sha256":compact["plan_sha256"],
            "executor_sha256":compact["executor_sha256"],
            "paid_model_sends":0,
            "student_publication_authorized":False,
        }
