"""Source-pinned G2/G3 zero-Send work discovery for the persistent offline daemon.

Do not modify the SHA-pinned v7.1 executor or historic scientific request
journals. Discover only genuinely unfinished *source-review preflight* slides
from an immutable original G2 queue and a completed original G3 source-only
scope. Submit them as new immutable next_*.json handoffs to the existing
allowlisted offline worker. No scientific acceptance, provider requests,
paid API, original-media writes or publication are possible here.

The original G3 source-only work and source-media technical proof are already
complete in the live campaign. Their outstanding scientific/acoustic/video
requirements are a held evidence gate, NOT a fictional runnable worker.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .development_continuity_executor_v71 import _plan, _sha
from .recovery_registry import lookup_mechanism

CONFIG_NAME = "source_backlog_v1.json"
STATUS = "MICROGEN_G2_G3_SOURCE_ONLY_ELIGIBILITY_V1"
KIND = "g2_g3_source_eligible_dispatch"
SIGNATURE = "G2_G3_READONLY_SUPERVISOR_HAS_NO_NEW_VALID_HANDOFF_PLANS"
MECHANISM = "STAGE_REAL_PENDING_G2_SOURCE_PREFLIGHT_HOLD_G3_INDEPENDENT_QA"
MAX_SLIDES = 8
SOURCE_FILES = ("source.pdf", "slides.pdf", "script.txt")
_G3_SECTIONS = ("Serway_8_2", "Serway_8_3")


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _read(path: Path) -> dict:
    _require(path.is_file() and not path.is_symlink()
             and 0 < path.stat().st_size <= 100_000,
             "Missing, linked or oversized source-only admission evidence")
    value = json.loads(path.read_text(encoding="utf8"))
    _require(type(value) is dict, "Invalid admission evidence JSON")
    return value


def _verified_source_config(handoff_dir: Path) -> dict | None:
    config_file = handoff_dir / CONFIG_NAME
    if not config_file.exists() and not config_file.is_symlink():
        return None
    config = _read(config_file)
    _require(set(config) == {
        "schema_version", "status", "g2_queue", "g2_queue_sha256",
        "g2_source", "g2_inputs_sha256", "g3_progress",
        "g3_progress_sha256", "max_slides", "provider_requests_authorized",
        "student_publication_authorized",
    } and config["schema_version"] == 1
        and config["status"] == STATUS
        and config["provider_requests_authorized"] == 0
        and type(config["provider_requests_authorized"]) is int
        and config["student_publication_authorized"] is False
        and type(config["max_slides"]) is int
        and 1 <= config["max_slides"] <= MAX_SLIDES,
        "Unrecognized or unsafe source-only backlog contract")
    _require(set(config["g2_inputs_sha256"]) == set(SOURCE_FILES),
             "Incomplete original textbook input identity")
    for key in ("g2_queue_sha256", "g3_progress_sha256"):
        _require(type(config[key]) is str and len(config[key]) == 64
                 and all(c in "0123456789abcdef" for c in config[key]),
                 "Unattributable original checkpoint SHA")
    for name in SOURCE_FILES:
        value = config["g2_inputs_sha256"][name]
        _require(type(value) is str and len(value) == 64
                 and all(c in "0123456789abcdef" for c in value),
                 "Unattributable original input SHA")
    for key in ("g2_queue", "g2_source", "g3_progress"):
        _require(type(config[key]) is str and Path(config[key]).is_absolute(),
                 "Source-only contract requires explicit absolute paths")
    return config


def discover(*, handoff_dir: Path, state_dir: Path) -> dict:
    """Create at most one first-time bounded G2 handoff, never resend G2/G3."""
    _require(lookup_mechanism(KIND, SIGNATURE) == MECHANISM,
             "G2/G3 eligible-work discovery not in executable recovery registry")
    handoff_dir = Path(handoff_dir).absolute()
    state_dir = Path(state_dir).absolute()
    _require(handoff_dir.is_dir() and state_dir.is_dir()
             and not handoff_dir.is_symlink() and not state_dir.is_symlink()
             and not handoff_dir.is_relative_to(state_dir)
             and not state_dir.is_relative_to(handoff_dir),
             "Independent bounded work inbox and state required")
    config = _verified_source_config(handoff_dir)
    if config is None:
        return {
            "status": "NO_SOURCE_PINNED_AUTO_DISCOVERY_CONFIG",
            "new_plans": 0, "source_g2_jobs": 0,
            "g3_status": "UNCONFIGURED", "new_browser_sends": 0,
            "new_paid_gemini_API_calls": 0,
            "student_publication_authorized": False,
        }
    source = Path(config["g2_source"]).absolute()
    queue = Path(config["g2_queue"]).absolute()
    progress = Path(config["g3_progress"]).absolute()
    _require(source.is_dir() and queue.is_dir()
             and not source.is_symlink() and not queue.is_symlink()
             and not progress.is_symlink()
             and len({source.resolve(), queue.resolve(),
                      handoff_dir.resolve(), state_dir.resolve()}) == 4
             and not handoff_dir.is_relative_to(source)
             and not handoff_dir.is_relative_to(queue)
             and not state_dir.is_relative_to(source)
             and not state_dir.is_relative_to(queue),
             "Source backlog not isolated from original source or queue")
    _require(_sha(queue / "queue.json") == config["g2_queue_sha256"]
             and _sha(progress) == config["g3_progress_sha256"]
             and all(_sha(source / name) ==
                     config["g2_inputs_sha256"][name] for name in SOURCE_FILES),
             "Original G2 or G3 source/checkpoint changed: no replay")
    original = _read(queue / "queue.json")
    _require(original.get("original_source_folder") == str(source)
             and original.get("student_publication_authorized") is False
             and original.get("provider_requests_performed") == 0
             and type(original.get("slide_jobs")) is list
             and 1 <= len(original["slide_jobs"]) <= 24,
             "Original G2 source queue identity/authorization mismatch")
    jobs = original["slide_jobs"]
    ids = [row.get("slide") for row in jobs]
    _require(all(type(row) is dict
                 and type(row.get("slide")) is int
                 and 1 <= row["slide"] <= 200
                 and type(row.get("utterance_count")) is int
                 and row["utterance_count"] > 0
                 and all(row.get({"source.pdf": "original_source_sha256",
                                     "slides.pdf": "original_slides_sha256",
                                     "script.txt": "original_script_sha256"}[name])
                         == config["g2_inputs_sha256"][name]
                         for name in SOURCE_FILES)
                 for row in jobs)
             and len(set(ids)) == len(ids)
             and sum(row["utterance_count"] for row in jobs)
                == original.get("expected_utterances"),
             "G2 jobs diverged from authoritative original source")
    g3 = _read(progress)
    _require(g3.get("schema_version") == 1
             and g3.get("source_only_completed") is True
             and g3.get("source_scientific_QA_complete") is False
             and g3.get("independent_acoustic_QA_complete") is False
             and g3.get("independent_video_highlight_QA_complete") is False
             and g3.get("new_browser_sends") == 0
             and g3.get("new_paid_gemini_API_calls") == 0
             and g3.get("student_publication_authorized") is False
             and type(g3.get("source_sections")) is dict
             and set(g3["source_sections"]) == set(_G3_SECTIONS)
             and all(g3["source_sections"][s].get("status")
                     == "SOURCE_SCOPE_COMPLETE"
                     and g3["source_sections"][s].get("remaining") == 0
                     for s in _G3_SECTIONS),
             "G3 original source scope not independently complete: hold")
    unfinished = [
        slide for slide in ids
        if not ((queue / f"slide_{slide:03d}_initial_review.json").is_file()
                and (queue / f"slide_{slide:03d}_independent_challenge.json").is_file())
    ]
    # The offline preflight can classify old uncertain request windows, but it
    # is prohibited from retrying them or counting them as accepted.
    selected = unfinished[:config["max_slides"]]
    if not selected:
        return {
            "status": "NO_NEW_SOURCE_ONLY_WORK_AWAITING_INDEPENDENT_QA",
            "new_plans": 0, "source_g2_jobs": 0,
            "g3_status": "G3_ORIGINAL_SOURCE_COMPLETE_SCIENCE_AUDIO_VIDEO_OPEN",
            "new_browser_sends": 0, "new_paid_gemini_API_calls": 0,
            "student_publication_authorized": False,
        }
    planned = {
        "schema_version": 1, "project": "MicroGen_AI_Web",
        "tasks": [{
            "id": f"g2_original_source_preflight_{slide:03d}",
            "workstream": "g2",
            "action": "g2_review_preflight",
            "params": {"queue_root": str(queue), "folder": str(source),
                       "slide": slide},
            "depends_on": [], "max_attempts": 1, "authorized": True,
        } for slide in selected],
    }
    # The installed, hash-pinned executor allowlist independently validates
    # every generated task before anyone is allowed to dispatch it.
    filename = f"next_g2_source_preflight_{config['g2_queue_sha256'][:16]}.json"
    path = handoff_dir / filename
    content = (json.dumps(planned, sort_keys=True, indent=2,
                          ensure_ascii=False) + "\n").encode("utf8")
    created = 0
    _require(not path.is_symlink(), "Untrusted candidate handoff link")
    if path.exists():
        _require(path.is_file() and path.read_bytes() == content,
                 "Original G2 preflight source plan changed after admission")
    else:
        try:
            with path.open("xb") as out:
                out.write(content)
                out.flush()
                os.fsync(out.fileno())
            created = 1
        except FileExistsError:
            _require(path.is_file() and not path.is_symlink()
                     and path.read_bytes() == content,
                     "Concurrent differing source plan claim")
    _plan(path)
    return {
        "status": ("G2_SOURCE_PREFLIGHT_HANDOFF_ADMITTED" if created
                   else "G2_SOURCE_PREFLIGHT_ALREADY_CLAIMED_NO_REPLAY"),
        "new_plans": created,
        "source_g2_jobs": len(selected),
        "source_g2_slides": selected,
        "handoff_plan": str(path),
        "handoff_plan_sha256": hashlib.sha256(content).hexdigest(),
        "g3_status": "G3_ORIGINAL_SOURCE_COMPLETE_SCIENCE_AUDIO_VIDEO_OPEN",
        "new_browser_sends": 0, "new_paid_gemini_API_calls": 0,
        "student_publication_authorized": False,
    }
