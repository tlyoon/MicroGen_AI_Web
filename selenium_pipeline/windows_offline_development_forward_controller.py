"""Persistent source-bound, offline-only code-development forward controller.

Runs a small *curated* sequence of historical regression milestones. Uses
immutable exact-HEAD and code-policy-locked journal receipts to move from a
passing (or quarantined) task to the next independent eligible task without a
new operator invocation. It does not send model messages, trigger TTS or media
publication, certify original science, merge PRs, or schedule itself after exit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, require,
)
from .windows_historical_stack_batch_plan import plan_stack
from .windows_historical_stack_batch_executor import execute_batches

SCHEMA = 1
SIGNATURE = "OFFLINE_HISTORICAL_CODE_REVIEW_NEEDS_RESTARTABLE_AUTOFORWARD"
MECHANISM = "SOURCE_LOCKED_CURATED_OFFLINE_TASK_QUEUE_AND_RESTART"
# These are source-only, no-network regression suites independently exercised
# on the same historical batch windows on 19 November 2026. They are NOT
# academic/media acceptance tests or billable provider integration tests.
TASKS = (
    {
        "id": "historical_source_regressions_batch_1",
        "batch": 1,
        "first_commit_prefix": "d42413c",
        "last_commit_prefix": "98cbbae",
        "modules": (
            "tests.test_asr_layout_carryover",
            "tests.test_asr_scene_visual_gates",
        ),
    },
    {
        "id": "historical_source_regressions_batch_2",
        "batch": 2,
        "first_commit_prefix": "e47c570",
        "last_commit_prefix": "b2be156",
        "modules": (
            "tests.test_browser_tts_preflight",
            "tests.test_element_plan_autodraft",
        ),
    },
    {
        "id": "historical_source_regressions_batch_3",
        "batch": 3,
        "first_commit_prefix": "433bf0f",
        "last_commit_prefix": "fa3bbd7",
        "modules": (
            "tests.test_element_narration_gemini",
            "tests.test_tts_cli_bootstrap",
        ),
    },
    {
        "id": "historical_source_regressions_batch_4",
        "batch": 4,
        "first_commit_prefix": "0627ca4",
        "last_commit_prefix": "cd034fb",
        "modules": (
            "tests.test_tts_candidate_integrity",
            "tests.test_tts_paid_entrypoint_authorization",
        ),
    },
    {
        "id": "historical_source_regressions_batch_5",
        "batch": 5,
        "first_commit_prefix": "d15c82c",
        "last_commit_prefix": "282ce5a",
        "modules": (
            "tests.test_tts_pcm_contract",
            "tests.test_tts_reviewed_element_compat",
        ),
    },
    {
        "id": "historical_source_regressions_batch_6",
        "batch": 6,
        "first_commit_prefix": "32334d1",
        "last_commit_prefix": "b0413a9",
        "modules": (
            "tests.test_tts_fallback_downstream_provenance",
            "tests.test_tts_restored_fallback_policy",
        ),
    },
    {
        "id": "historical_source_regressions_batch_7",
        "batch": 7,
        "first_commit_prefix": "6645679",
        "last_commit_prefix": "cc7fdf5",
        "modules": (
            "tests.test_tts_attempt_evidence",
            "tests.test_tts_qa_promotion",
        ),
    },
    {
        "id": "historical_source_regressions_batch_8",
        "batch": 8,
        "first_commit_prefix": "bb5847f",
        "last_commit_prefix": "ff80a1e",
        "modules": (
            "tests.test_tts_provider_reconciliation",
            "tests.test_tts_worker_request_evidence",
        ),
    },
    {
        "id": "historical_source_regressions_batch_9",
        "batch": 9,
        "first_commit_prefix": "86a468c",
        "last_commit_prefix": "cd7bff8",
        "modules": (
            "tests.test_element_draft_drift_audit",
            "tests.test_read_only_video_review_audit",
        ),
    },
    {
        "id": "historical_source_regressions_batch_10",
        "batch": 10,
        "first_commit_prefix": "8c0aa6d",
        "last_commit_prefix": "af0058d",
        "modules": (
            "tests.test_automatic_multielement_narration",
            "tests.test_automatic_element_audio_stage",
        ),
    },
    {
        "id": "historical_source_regressions_batch_11",
        "batch": 11,
        "first_commit_prefix": "ecd2308",
        "last_commit_prefix": "f1bb4bf",
        "modules": (
            "tests.test_figure_panel_geometry",
            "tests.test_figure_caption_column_audit",
        ),
    },
    {
        "id": "historical_source_regressions_batch_12",
        "batch": 12,
        "first_commit_prefix": "a175cf6",
        "last_commit_prefix": "6ac6e26",
        "modules": (
            "tests.test_figure_declared_panel_reflow",
            "tests.test_figure_layout_recovery_dispatch",
        ),
    },
    {
        "id": "historical_source_regressions_batch_13",
        "batch": 13,
        "first_commit_prefix": "0b671ba",
        "last_commit_prefix": "8c0f3a9",
        "modules": (
            "tests.test_batch_element_sync_acceptance",
            "tests.test_element_tts_safe_handoff",
        ),
    },
    {
        "id": "historical_source_regressions_batch_14",
        "batch": 14,
        "first_commit_prefix": "d500880",
        "last_commit_prefix": "bd5083f",
        "modules": (
            "tests.test_figure83_fraction_spatial_identity",
            "tests.test_figure83_operator_scale_coherence",
        ),
    },
    {
        "id": "historical_source_regressions_batch_15",
        "batch": 15,
        "first_commit_prefix": "fe17b9b",
        "last_commit_prefix": "aa10802",
        "modules": (
            "tests.test_figure83_combined_acceptance",
            "tests.test_figure83_element_audio_integrity",
        ),
    },
    {
        "id": "historical_source_regressions_batch_16",
        "batch": 16,
        "first_commit_prefix": "b699112",
        "last_commit_prefix": "3a6b32f",
        "modules": (
            "tests.test_ai_academic_review_consensus",
            "tests.test_ai_academic_review_queue",
        ),
    },
    {
        "id": "historical_source_regressions_batch_17",
        "batch": 17,
        "first_commit_prefix": "0f4d81e",
        "last_commit_prefix": "a6c38ad",
        "modules": (
            "tests.test_ai_compact_original_challenge",
            "tests.test_gemini_ambiguous_response_resolution",
        ),
    },
    {
        "id": "historical_source_regressions_batch_18",
        "batch": 18,
        "first_commit_prefix": "b57d355",
        "last_commit_prefix": "7ed71b1",
        "modules": (
            "tests.test_encoded_part_audio_fidelity",
            "tests.test_gemini_bridge_failure_triage",
        ),
    },
    {
        "id": "historical_source_regressions_batch_19",
        "batch": 19,
        "first_commit_prefix": "6d1af85",
        "last_commit_prefix": "6cd6266",
        "modules": (
            "tests.test_gemini_placeholder_grace",
            "tests.test_original_review_ambiguous_response_receipts",
            "tests.test_quote_spatial_continuity",
            "tests.test_original_trig_substitution_numeric_preflight",
        ),
    },
    {
        "id": "historical_source_regressions_batch_20",
        "batch": 20,
        "first_commit_prefix": "144f973",
        "last_commit_prefix": "6b45ee3",
        "modules": (
            "tests.test_original_slide4_exact_source_evidence",
            "tests.test_source_locked_academic_review",
            "tests.test_original_principal_root_interval_qa",
        ),
    },
    {
        "id": "historical_source_regressions_batch_21",
        "batch": 21,
        "first_commit_prefix": "48ca661",
        "last_commit_prefix": "549f858",
        "modules": (
            "tests.test_original_slide4_math_correction_pilot",
            "tests.test_original_slide4_pcm_provenance_pilot",
        ),
    },
    {
        "id": "historical_source_regressions_batch_22",
        "batch": 22,
        "first_commit_prefix": "1a400b9",
        "last_commit_prefix": "44aac0d",
        "modules": (
            "tests.test_automatic_math_semantic_qa",
        ),
    },
    {
        "id": "historical_source_regressions_batch_23",
        "batch": 23,
        "first_commit_prefix": "e2e634f",
        "last_commit_prefix": "56b0522",
        "modules": (
            "tests.test_academic_review_checkpoint",
            "tests.test_original_replacement_video_handoff",
        ),
    },
    {
        "id": "historical_source_regressions_batch_24",
        "batch": 24,
        "first_commit_prefix": "c94c6a0",
        "last_commit_prefix": "10ff0b2",
        "modules": (
            "tests.test_original_slide4_corrected_segment_handoff",
            "tests.test_offline_corrected_bundle_verify",
        ),
    },
    {
        "id": "historical_source_regressions_batch_25",
        "batch": 25,
        "first_commit_prefix": "589c7df",
        "last_commit_prefix": "ed54d02",
        "modules": (
            "tests.test_offline_corrected_audio_intake",
            "tests.test_offline_replacement_replanner",
        ),
    },
    {
        "id": "historical_source_regressions_batch_26",
        "batch": 26,
        "first_commit_prefix": "03d0d55",
        "last_commit_prefix": "5260e8f",
        "modules": (
            "tests.test_offline_replacement_replanner",
            "tests.test_real_pcm_chunk_original_slide4_highlight",
            "tests.test_real_source_figure82_and_encoded_slide4_highlight",
        ),
    },
    {
        "id": "historical_source_regressions_batch_27",
        "batch": 27,
        "first_commit_prefix": "a689adb",
        "last_commit_prefix": "ca563ad",
        "modules": (
            "tests.test_gemini38_tts_interactions_sdk",
            "tests.test_offline_vosk_corrected_math_speech_qa",
        ),
    },
    {
        "id": "historical_source_regressions_batch_28",
        "batch": 28,
        "first_commit_prefix": "9d63586",
        "last_commit_prefix": "af05424",
        "modules": (
            "tests.test_tts_flexible_pronunciation_contract",
            "tests.test_tts_soundalike_production_integration",
        ),
    },
    {
        "id": "historical_source_regressions_batch_29",
        "batch": 29,
        "first_commit_prefix": "28e06f4",
        "last_commit_prefix": "0913382",
        "modules": (
            "tests.test_original_thomas84_offline_word_pdf_timing",
            "tests.test_original_thomas84_real_word_timed_pdf_highlight_review",
            "tests.test_original_thomas84_trig_identity_proof",
        ),
    },
    {
        "id": "historical_source_regressions_batch_30",
        "batch": 30,
        "first_commit_prefix": "cf81e49",
        "last_commit_prefix": "f3ade52",
        "modules": (
            "tests.test_original_thomas84_math_domain_crosscheck",
            "tests.test_original_thomas84_trig_identity_proof",
            "tests.test_original_thomas84_worked_examples_math_proof",
        ),
    },
    {
        "id": "historical_source_regressions_batch_31",
        "batch": 31,
        "first_commit_prefix": "9df0d85",
        "last_commit_prefix": "ffb0582",
        "modules": (
            "tests.test_dell_tts_outage_circuit_recovery",
            "tests.test_visual_element_mapping_readiness",
            "tests.test_automatic_math_semantic_qa",
        ),
    },
    {
        "id": "historical_source_regressions_batch_32",
        "batch": 32,
        "first_commit_prefix": "fa3cc7d",
        "last_commit_prefix": "b6416a7",
        "modules": (
            "tests.test_element_plan_autodraft",
        ),
    },
    {
        "id": "historical_source_regressions_batch_33",
        "batch": 33,
        "first_commit_prefix": "5149524",
        "last_commit_prefix": "af33521",
        "modules": (
            "tests.test_tts_attempt_evidence",
            "tests.test_tts_restored_fallback_policy",
        ),
    },
    {
        "id": "historical_source_regressions_batch_34",
        "batch": 34,
        "first_commit_prefix": "48e8a73",
        "last_commit_prefix": "866b1e9",
        "modules": (
            "tests.test_original_thomas84_trig_identity_proof",
            "tests.test_original_thomas84_full_utterance_release_guard",
        ),
    },
    {
        "id": "historical_source_regressions_batch_35",
        "batch": 35,
        "first_commit_prefix": "2f56563",
        "last_commit_prefix": "54c1e00",
        "modules": (
            "tests.test_original_thomas84_66_independent_media_audit",
            "tests.test_original_thomas84_all66_combined_final_release_gate",
            "tests.test_original_thomas84_trig_identity_proof",
        ),
    },
    {
        "id": "historical_source_regressions_batch_36",
        "batch": 36,
        "first_commit_prefix": "e3634bd",
        "last_commit_prefix": "6f70cfa",
        "modules": (
            "tests.test_verified_evidence_reuse_contract",
            "tests.test_cached_tts_no_reauthorization",
        ),
    },
    {
        "id": "historical_source_regressions_batch_37",
        "batch": 37,
        "first_commit_prefix": "59e3c09",
        "last_commit_prefix": "42cce57",
        "modules": (
            "tests.test_rich_element_mapping_checkpoint",
            "tests.test_video_handoff_script_optional",
            "tests.test_versioned_scholarly_accepted_scope_board",
        ),
    },
    {
        "id": "historical_source_regressions_batch_38",
        "batch": 38,
        "first_commit_prefix": "21d1cbe",
        "last_commit_prefix": "8f9c096",
        "modules": (
            "tests.test_sourcebound_completion_guard",
            "tests.test_rich_unresolved_model_queue",
            "tests.test_original_multisource_recovery_campaign",
        ),
    },
    {
        "id": "historical_source_regressions_batch_39",
        "batch": 39,
        "first_commit_prefix": "43424ed",
        "last_commit_prefix": "b7ed966",
        "modules": (
            "tests.test_windows_lecture_progression_coordinator",
            "tests.test_windows_provider_readiness_probe",
            "tests.test_windows_bounded_stage_process",
        ),
    },
    {
        "id": "historical_source_regressions_batch_40",
        "batch": 40,
        "first_commit_prefix": "92f55ce",
        "last_commit_prefix": "a390578",
        "modules": (
            "tests.test_windows_historical_stack_batch_plan",
            "tests.test_windows_github_pr_stack_readonly_audit",
            "tests.test_windows_crop_converter_reuse",
        ),
    },
    {
        "id": "historical_source_regressions_batch_41",
        "batch": 41,
        "first_commit_prefix": "ad461f4",
        "last_commit_prefix": "73d72d7",
        "modules": (
            "tests.test_ai_academic_review_auto_next",
            "tests.test_gemini_postsubmit_no_resend",
            "tests.test_pre_tts_source_math_review_without_wav",
        ),
    },
    {
        "id": "historical_source_regressions_batch_42",
        "batch": 42,
        "first_commit_prefix": "a45c693",
        "last_commit_prefix": "f57e552",
        "modules": (
            "tests.test_gemini_selenium_only_policy",
            "tests.test_gemini_response_recovery",
            "tests.test_durable_tts_observed_failure_resume",
        ),
    },
    {
        "id": "historical_source_regressions_batch_43",
        "batch": 43,
        "first_commit_prefix": "241ccbf",
        "last_commit_prefix": "edcb3a8",
        "modules": (
            "tests.test_gemini_adaptive_ui_thinking",
            "tests.test_gemini_model_atomic_picker",
            "tests.test_original_review_ambiguous_response_receipts",
        ),
    },
    {
        "id": "historical_source_regressions_batch_44",
        "batch": 44,
        "first_commit_prefix": "846ff43",
        "last_commit_prefix": "c2e5656",
        "modules": (
            "tests.test_figure_uncaptioned_source_recovery",
            "tests.test_source_quote_section_scope",
            "tests.test_pcm_signal_integrity",
        ),
    },
    {
        "id": "historical_source_regressions_batch_45",
        "batch": 45,
        "first_commit_prefix": "40ec7b1",
        "last_commit_prefix": "734ec9e",
        "modules": (
            "tests.test_academic_provider_requalification",
            "tests.test_gemini_ui_protocol_v2",
            "tests.test_windows_new_source_browser_admission",
        ),
    },
    {
        "id": "historical_source_regressions_batch_46",
        "batch": 46,
        "first_commit_prefix": "827043e",
        "last_commit_prefix": "6c3299e",
        "modules": (
            "tests.test_g2_forward_recovery_engine",
            "tests.test_academic_dual_pdf_capability",
            "tests.test_windows_forward_source_campaign",
        ),
    },
    {
        "id": "historical_source_regressions_batch_47",
        "batch": 47,
        "first_commit_prefix": "9e57b93",
        "last_commit_prefix": "219a4e5",
        "modules": (
            "tests.test_gemini_dynamic_task_router",
            "tests.test_gemini_owned_picker_js_fallback",
            "tests.test_series_existing_browser_profile_policy",
        ),
    },
    {
        "id": "historical_source_regressions_batch_48",
        "batch": 48,
        "first_commit_prefix": "68fc031",
        "last_commit_prefix": "<HISTORICAL_ANCHOR_MEMBER>",
        "historical_anchor_prefix": "048c0cf",
        "modules": (
            "tests.test_windows_offline_development_forward_controller",
            "tests.test_windows_historical_stack_batch_executor",
            "tests.test_historical_pdf_parser_abi_recovery",
        ),
    },
)
MAX_STEPS = len(TASKS)
MAX_ATTEMPTS = 2
MAX_RECEIPT_BYTES = 256_000
MAX_LOG_BYTES = 500_000


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(obj: dict) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)
            + "\n").encode("utf-8")


def _integrity(obj: dict) -> str:
    return _sha(json.dumps(
        {k: v for k, v in obj.items() if k != "integrity_sha256"},
        sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8"))


def _enveloped(record: dict) -> dict:
    result = dict(record)
    result["integrity_sha256"] = _integrity(result)
    return result


def _check_envelope(path: Path, expected: dict | None = None) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= MAX_RECEIPT_BYTES,
            "Missing, linked, empty or oversized developer checkpoint")
    obj = json.loads(path.read_text(encoding="utf-8"))
    require(type(obj) is dict
            and obj.get("integrity_sha256") == _integrity(obj)
            and obj.get("schema_version") == SCHEMA,
            "Corrupt or forged developer checkpoint")
    if expected is not None:
        require(all(obj.get(k) == v for k, v in expected.items()),
                "Developer checkpoint disagrees with original Git/task identity")
    return obj


def _atomic_create(path: Path, data: dict) -> None:
    """Write-once receipt, atomic even if a process dies during fsync."""
    require(not path.exists() and not path.is_symlink(),
            "Refuse to overwrite developer evidence")
    raw = _json_bytes(_enveloped(data))
    require(len(raw) <= MAX_RECEIPT_BYTES,
            "Developer checkpoint exceeds finite size")
    tmp = path.with_suffix(path.suffix + ".staging")
    require(not tmp.is_symlink() and not tmp.is_dir(),
            "Unsafe developer evidence stage")
    if tmp.exists():
        require(tmp.is_file() and tmp.stat().st_size <= MAX_RECEIPT_BYTES,
                "Unexpected staged developer evidence")
        tmp.unlink()  # stage is outside source, lock guards ownership
    with tmp.open("xb") as fd:
        fd.write(raw)
        fd.flush()
        os.fsync(fd.fileno())
    require(tmp.read_bytes() == raw and not path.exists(),
            "Staged developer checkpoint was altered")
    os.replace(tmp, path)


def _verify_repo(repo: Path) -> None:
    repo = Path(repo).absolute()
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(os.name == "nt" and local.is_dir()
            and repo.is_dir() and not repo.is_symlink()
            and repo.is_relative_to(local)
            and (repo / ".git").exists(),
            "Only a local clean Dell Windows Git worktree is eligible")
    p = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain",
         "--untracked-files=all"],
        capture_output=True, text=True, timeout=30,
        check=False,
    )
    require(p.returncode == 0 and not p.stderr.strip()
            and not p.stdout.strip(),
            "Any unrecognized local/staged source edit blocks autonomous review")


def _source_modules(repo: Path, task: dict) -> list[dict]:
    result = []
    for name in task["modules"]:
        require(re.fullmatch(r"tests\.test_[A-Za-z0-9_]+", name) is not None,
                "Arbitrary dynamic Python module refused")
        path = repo / (name.replace(".", "/") + ".py")
        require(path.is_file() and not path.is_symlink()
                and path.resolve().is_relative_to(repo.resolve())
                and path.stat().st_size <= 3_000_000,
                "Missing, linked or unbounded curated test source")
        result.append({"name": name, "source_sha256": _sha(path.read_bytes())})
    require(1 <= len(result) <= 10,
            "No authorized bounded test modules for development stage")
    return result


def _subprocess_offline_tests(repo: Path, modules: tuple[str, ...]) -> dict:
    """Run source-regression tests with Python socket egress denied.

    Uses the actual local tests package and does NOT patch producer code.
    An explicitly selected offline unit test cannot silently use requests,
    urllib or the usual socket-based Gemini/Cloud transports.
    """
    script = """
import socket
import sys
import unittest

def deny(*args, **kwargs):
    raise RuntimeError("OFFLINE_SOURCE_TEST_NETWORK_DENIED")

socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
"""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MICROGEN_OFFLINE_SOURCE_REGRESSION"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-c", script, *modules],
            cwd=repo, env=env, capture_output=True, text=True,
            errors="replace", timeout=150, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "LOCAL_TEST_OPERATION_BLOCKED",
            "error_type": type(exc).__name__,
            "exit_code": None,
            "reported_test_count": 0,
            "reported_skip_count": 0,
            "captured_output_sha256": None,
            "success": False,
        }
    out = (proc.stdout + "\n" + proc.stderr).encode("utf-8")
    require(len(out) <= MAX_LOG_BYTES, "Offline test output too large")
    run = re.search(r"Ran (\d+) tests? in", proc.stderr)
    skipped = re.search(r"skipped=(\d+)", proc.stderr)
    passed = (proc.returncode == 0 and run is not None
              and int(run.group(1)) > (int(skipped.group(1)) if skipped else 0)
              and re.search(r"^OK\b", proc.stderr, re.M) is not None
              and "FAILED" not in proc.stderr)
    return {
        "status": ("OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING" if passed
                   else "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED"),
        "exit_code": proc.returncode,
        "reported_test_count": int(run.group(1)) if run else 0,
        "reported_skip_count": int(skipped.group(1)) if skipped else 0,
        "captured_output_sha256": _sha(out),
        "success": passed,
    }


def _folder(repo: Path, head: str) -> Path:
    require(re.fullmatch(r"[a-f0-9]{40}", head) is not None,
            "Unsafe development HEAD")
    local = Path(os.environ["LOCALAPPDATA"]).absolute()
    own = _sha(Path(__file__).read_bytes())
    ident = _sha(str(repo).lower().encode("utf-8"))[:16]
    home = (local / "MicroGen_AI_Web_Checkpoints"
            / "offline_development_autoforward_v1")
    require(not home.is_symlink() and not home.parent.is_symlink(),
            "Linked developer task receipt directory")
    home.mkdir(parents=True, exist_ok=True)
    dest = home / (ident + "_" + head[:20] + "_" + own[:12])
    require(not dest.is_symlink(),
            "Unsafe source-bound development task checkpoint")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _ensure_roadmap(repo: Path, head: str, folder: Path) -> Path:
    """Write-once, exact-source executable task roadmap for restart checks."""
    roadmap = folder / "roadmap.json"
    record = {
        "schema_version": SCHEMA,
        "status": "CURATED_OFFLINE_DEVELOPMENT_ROADMAP_ACTIVE",
        "repository_path": str(repo),
        "exact_source_head_sha": head,
        "tasks": [{
            "task_id": task["id"],
            "historical_batch_number": task["batch"],
            "dependencies": [],
            "accepted_result": "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING",
            "provider_or_paid_operations_authorized": False,
            "automatic_merge_authorized": False,
            "student_publication_authorized": False,
        } for task in TASKS],
        "selection": "SOURCE_LOCKED_ORDER_NEXT_UNCOMPLETED_AFTER_VERIFIED_CHECK",
        "roadmap_complete_implies_scientific_acceptance": False,
    }
    if roadmap.exists():
        old = _check_envelope(roadmap, record)
        require(old == _enveloped(record),
                "Persisted roadmap differs from executable source policy")
    else:
        _atomic_create(roadmap, record)
    return roadmap


def _task_identity(repo: Path, head: str, batch: dict,
                   task: dict, tests: list[dict]) -> dict:
    return {
        "schema_version": SCHEMA,
        "source_head_sha": head,
        "repository_path": str(repo),
        "task_id": task["id"],
        "batch_number": task["batch"],
        "first_commit_sha": batch["first_commit_sha"],
        "last_commit_sha": batch["end_inclusive_sha"],
        "batch_changed_paths_sha256": batch["all_touched_paths_sha256"],
        "reviewed_test_sources": tests,
        "network_or_provider_sends_authorized": False,
        "automatic_merge_authorized": False,
        "student_publication_authorized": False,
        "historical_semantic_review_completed": False,
    }


def _require_historical_anchor(repo: Path, batch: dict,
                               anchor_prefix: str) -> None:
    """Prove prior verified historical code remains inside the same SHA window.

    The latest Git HEAD may advance into batch 49 or later; old batch 48
    still belongs to its independently verified original 20 commits.
    Do not require the *current* repo HEAD to equal the historical batch end.
    """
    require(re.fullmatch(r"[0-9a-f]{7}", anchor_prefix) is not None
            and re.fullmatch(r"[a-f0-9]{40}", batch["start_exclusive_sha"])
            and re.fullmatch(r"[a-f0-9]{40}", batch["end_inclusive_sha"])
            and type(batch["commit_count"]) is int
            and 1 <= batch["commit_count"] <= 20,
            "Invalid immutable historical source membership")
    p = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--topo-order", "--reverse",
         batch["start_exclusive_sha"] + ".." + batch["end_inclusive_sha"]],
        capture_output=True, text=True, encoding="utf8",
        errors="replace", timeout=40, check=False,
    )
    members = p.stdout.splitlines()
    require(p.returncode == 0 and not p.stderr.strip()
            and len(members) == batch["commit_count"]
            and all(re.fullmatch(r"[0-9a-f]{40}", sha) is not None
                    for sha in members)
            and sum(sha.startswith(anchor_prefix) for sha in members) == 1,
            "Historical batch 48 lost its original code anchor")


def _execute_task(repo: Path, head: str, batch: dict, task: dict,
                  folder: Path, runner) -> dict:
    require(batch["batch_number"] == task["batch"]
            and batch["first_commit_sha"].startswith(
                task["first_commit_prefix"])
            and (task["last_commit_prefix"] ==
                 "<HISTORICAL_ANCHOR_MEMBER>"
                 or batch["end_inclusive_sha"].startswith(
                     task["last_commit_prefix"])),
            "Developer task does not belong to original SHA-bound history")
    if task["last_commit_prefix"] == "<HISTORICAL_ANCHOR_MEMBER>":
        require(task["batch"] == 48
                and task["historical_anchor_prefix"] == "048c0cf",
                "Unrecognized historical final batch anchor")
        _require_historical_anchor(
            repo, batch, task["historical_anchor_prefix"])
    modules = _source_modules(repo, task)
    identity = _task_identity(repo, head, batch, task, modules)
    intent = folder / (task["id"] + ".intent.json")
    result = folder / (task["id"] + ".result.json")
    if intent.exists():
        _check_envelope(intent, {
            **identity, "status": "PENDING_OFFLINE_SOURCE_CODE_REGRESSION",
        })
        intent_reused = True
    else:
        _atomic_create(intent, {
            **identity, "status": "PENDING_OFFLINE_SOURCE_CODE_REGRESSION",
        })
        intent_reused = False
    if result.exists():
        saved = _check_envelope(result, identity)
        require(saved.get("status") in (
                    "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING",
                    "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED",
                    "OFFLINE_SOURCE_REGRESSION_EXHAUSTED_QUARANTINED")
                and type(saved.get("success")) is bool
                and saved["success"] == (
                    saved["status"] == "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING")
                and type(saved.get("attempt_count")) is int
                and 1 <= saved["attempt_count"] <= MAX_ATTEMPTS
                and type(saved.get("reported_test_count")) is int
                and type(saved.get("reported_skip_count")) is int
                and 0 <= saved["reported_skip_count"] <= saved["reported_test_count"]
                and (not saved["success"] or (
                    saved.get("exit_code") == 0
                    and saved["reported_test_count"] > saved["reported_skip_count"]
                    and re.fullmatch(r"[a-f0-9]{64}", str(
                        saved.get("captured_output_sha256"))) is not None)),
                "Saved task result conflicts with executable acceptance policy")
        return {**saved, "receipt_reused_after_restart": True,
                "result_receipt_path": str(result)}
    # A real process might have died after writing an intent or attempt.
    # Only offline, source-whitelisted tests may be retried after such death.
    attempts = []
    for ix in range(1, MAX_ATTEMPTS + 1):
        path = folder / (task["id"] + f".attempt{ix}.json")
        if path.exists():
            _check_envelope(path, {
                **identity, "status": "OFFLINE_TEST_ATTEMPT_CLAIMED",
                "attempt_number": ix,
            })
            attempts.append(ix)
    remaining = next((n for n in range(1, MAX_ATTEMPTS + 1)
                      if n not in attempts), None)
    if remaining is None:
        test_result = {
            "status": "OFFLINE_SOURCE_REGRESSION_EXHAUSTED_QUARANTINED",
            "success": False, "exit_code": None,
            "reported_test_count": 0, "reported_skip_count": 0,
            "captured_output_sha256": None,
        }
        count = MAX_ATTEMPTS
    else:
        _atomic_create(
            folder / (task["id"] + f".attempt{remaining}.json"),
            {**identity, "status": "OFFLINE_TEST_ATTEMPT_CLAIMED",
             "attempt_number": remaining},
        )
        try:
            test_result = runner(repo, task["modules"])
        except (Exception, KeyboardInterrupt):
            # A dying worker consumes one test-only attempt claim; the next
            # invocation can safely restart remaining offline work.
            raise
        require(type(test_result) is dict
                and type(test_result.get("success")) is bool
                and test_result.get("status") in (
                    "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING",
                    "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED",
                    "LOCAL_TEST_OPERATION_BLOCKED",
                )
                and type(test_result.get("reported_test_count")) is int
                and type(test_result.get("reported_skip_count")) is int
                and 0 <= test_result["reported_skip_count"]
                    <= test_result["reported_test_count"]
                and (not test_result["success"] or (
                    test_result["status"]
                    == "OFFLINE_SOURCE_REGRESSION_PASS_REVIEW_PENDING"
                    and test_result.get("exit_code") == 0
                    and test_result["reported_test_count"] > test_result["reported_skip_count"])),
                "Unrecognized or inconsistent offline test receipt")
        if test_result["status"] == "LOCAL_TEST_OPERATION_BLOCKED":
            test_result = {**test_result,
                           "status": "OFFLINE_SOURCE_REGRESSION_FAILED_QUARANTINED"}
        count = remaining
    _verify_repo(repo)
    # No change to historical source or published lecture files on success.
    complete = {
        **identity, **test_result,
        "attempt_count": count,
        "prior_crash_attempt_resumed": bool(attempts),
        "intent_reused": intent_reused,
        "previous_historical_patch_findings_retained": True,
    }
    _atomic_create(result, complete)
    return {**complete, "receipt_reused_after_restart": False,
            "result_receipt_path": str(result)}


def advance_offline(*, repo: Path, max_steps: int = MAX_STEPS,
                    runner=None) -> dict:
    """Select each eligible historical task and continue in the same process."""
    from .recovery_registry import lookup_mechanism
    from .three_pc_worker import LocalInstanceLock
    require(lookup_mechanism(
        "offline_dev_autoforward", SIGNATURE) == MECHANISM,
        "Continuous offline code-review recovery mechanism disabled")
    require(type(max_steps) is int and 1 <= max_steps <= MAX_STEPS,
            "Bounded development runner requires a finite 1–30 tasks per invocation")
    repo = Path(repo).absolute()
    _verify_repo(repo)
    plan = plan_stack(repo=repo)
    require(plan["status"] == "HISTORICAL_STACK_READ_ONLY_BATCH_PLAN_AVAILABLE"
            and plan["local_worktree_clean"] is True
            and plan["commits_behind_origin_main"] == 0,
            "Historical offline roadmap requires verified exact source stack")
    head = plan["exact_head_sha"]
    require(len(plan["batches"]) >= TASKS[-1]["batch"],
            "Bounded roadmap is missing historical commit membership")
    folder = _folder(repo, head)
    lock = _sha(str(repo).lower().encode("utf-8"))[:20]
    reports = []
    with LocalInstanceLock(
        "autoforward_" + lock, folder.parent / "locks",
    ):
        # Recheck after acquiring exclusive OS lock; multiple invocations
        # cannot reserve competing attempts against the same source task.
        _verify_repo(repo)
        roadmap_path = _ensure_roadmap(repo, head, folder)
        new_tasks_this_process = 0
        for task in TASKS:
            if new_tasks_this_process >= max_steps:
                break
            batch = plan["batches"][task["batch"] - 1]
            patches = execute_batches(
                repo=repo,
                first_batch=task["batch"],
                last_batch=task["batch"],
            )
            require(patches["exact_head_sha"] == head
                    and patches["batch_count_completed"] == 1
                    and patches["student_publication_authorized"] is False,
                    "Historical check not independently verified for task")
            # Formatting findings retain their original quarantine, even if
            # a separate code-test suite succeeds.
            report = _execute_task(
                repo, head, batch, task, folder,
                runner or _subprocess_offline_tests,
            )
            if not report["receipt_reused_after_restart"]:
                new_tasks_this_process += 1
            reports.append({
                **report,
                "historical_patch_quarantine_retained":
                    patches["quarantined_batch_numbers"],
                "next_eligible_task": (
                    TASKS[len(reports)]["id"]
                    if len(reports) < len(TASKS) else None),
            })
            _verify_repo(repo)
    passing = sum(r["success"] for r in reports)
    return {
        "schema_version": SCHEMA,
        "status": ("BOUNDED_OFFLINE_DEVELOPMENT_QUEUE_ADVANCED_REVIEW_PENDING"
                   if passing == len(reports) else
                   "BOUNDED_OFFLINE_DEVELOPMENT_WITH_QUARANTINED_TASKS"),
        "exact_source_head_sha": head,
        "persistent_roadmap_path": str(roadmap_path),
        "tasks_executed_or_reused": len(reports),
        "new_tasks_completed_this_process": new_tasks_this_process,
        "offline_source_regression_pass_count": passing,
        "pending_roadmap_task_count": len(TASKS) - len(reports),
        "tasks": reports,
        "automatic_forward_on_verified_task": True,
        "continuation_across_process_end_requires_authorized_runner": True,
        "automatic_merge_authorized": False,
        "historical_semantic_review_completed": False,
        "independent_academic_qa_accepted": False,
        "new_paid_or_model_requests_made": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo", type=Path,
                     default=Path(__file__).resolve().parent.parent)
    cli.add_argument("--max-steps", type=int, default=MAX_STEPS)
    args = cli.parse_args(argv)
    try:
        result = advance_offline(repo=args.repo, max_steps=args.max_steps)
    except (CampaignRecoveryBlocked, OSError, ValueError, KeyError,
            RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({
            "status": "OFFLINE_CODE_DEVELOPMENT_BLOCKED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "automatic_merge_authorized": False,
            "student_publication_authorized": False,
        }, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["offline_source_regression_pass_count"] == len(
        result["tasks"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
