"""Fail-closed versioned recovery intelligence for the normal MicroGen pipeline.

This registry selects *only existing code-reviewed mechanisms*. It never
executes arbitrary registry code, resets retries, resubmits ambiguous Gemini
requests, overrides QA or authorizes paid operations. The stage's own claim,
source, authorization, and scientific acceptance checks remain authoritative.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

REGISTRY_PATH = Path(__file__).resolve().parent / "recovery_registry_v1.json"
_STATUS = "MICROGEN_EXECUTABLE_RECOVERY_REGISTRY_V1"
_HANDLERS = {
    "selection_action": "NORMAL_SOURCE_BOUND_G2_SUPERVISOR_AND_QUEUE",
    "source_review_claim": "NORMAL_ORIGINAL_G2_HISTORICAL_CLAIM_PREVENT_NEW_SEND",
    "supervisor_status": "NORMAL_SOURCE_BOUND_G2_SUPERVISOR_AND_QUEUE",
    "owned_transport_diagnostic": "OWNED_GEMINI_SELENIUM_RESPONSE_QUARANTINE",
    "offline_dependency": "NORMAL_G2_INDEPENDENT_SOURCE_READINESS",
    "source_mapping_repair": "NORMAL_VERIFIED_ELEMENT_RANKER",
    "slide_layout_repair": "NORMAL_BEAMER_HEADLINE_GEOMETRY_RECOVERY",
    "source_highlight_abi": "NORMAL_HISTORICAL_SOURCE_PIXEL_COMPOSITOR",
    "presend_capability_repair": "NORMAL_EXISTING_OWNED_GEMINI_ACCOUNT_CAPABILITY_PREFLIGHT",
    "transport_selection": "NORMAL_ACADEMIC_OWNED_ROUTE_AND_VERIFIED_MODEL_THINKING_PREFLIGHT",
    "tts_runtime_repair": "NORMAL_ISOLATED_TTS_WORKER_SDK_PREFLIGHT",
    "pr_stack_audit": "NORMAL_GITHUB_OPEN_PR_STACK_HEAD_CHAIN_AUDIT",
    "history_batch_inventory": "NORMAL_WINDOWS_HISTORICAL_STACK_BATCH_PLANNER",
    "history_test_root_inventory": "NORMAL_WINDOWS_HISTORICAL_STACK_BATCH_PLANNER",
    "historical_pdf_parser_abi": "NORMAL_ORIGINAL_SOURCE_E2E_READONLY_ABI_REVIEW",
    "historical_batch_execution": "NORMAL_WINDOWS_HISTORICAL_BATCH_EXECUTOR",
    "historical_format_disposition": "NORMAL_WINDOWS_SOURCE_BOUND_HISTORY_FORMAT_DISPOSITION",
    "test_helper_imports": "NORMAL_TEST_PACKAGE_SIBLING_IMPORT_RECOVERY",
    "offline_dev_autoforward": "NORMAL_WINDOWS_OFFLINE_CODE_DEVELOPMENT_CONTROLLER",
    "global_checkpoint_handoff": "NORMAL_V71_PROJECT_WIDE_OBSERVABLE_SUPERVISOR",
    "daemon_owner_attestation": "NORMAL_V71_PROJECT_WIDE_OBSERVABLE_SUPERVISOR",
    "paid_api_scope": "NORMAL_SELENIUM_ONLY_GEMINI_EGRESS_GUARD",
    "request_cost_accounting": "NORMAL_DURABLE_GEMINI_REQUEST_COST_LEDGER",
    "code_authoring_handoff": "NORMAL_AUTHORIZED_SOURCE_PATCH_HANDOFF",
    "browser_coding_transport": "NORMAL_ONE_CLAIM_SELENIUM_CODE_REVIEW",
    "browser_stdout_encoding": "NORMAL_WINDOWS_BROWSER_NONASCII_LOGGER_RECOVERY",
    "browser_coding_response_shape": "NORMAL_GEMINI_SOURCE_ONLY_CODE_CAPTURE_RECOVERY",
    "bounded_coding_dispatch": "NORMAL_SINGLE_OWNER_BROWSER_CODE_DISPATCH",
    "historical_quarantine_integrity": "NORMAL_IMMUTABLE_PROVIDER_CAPTURE_EVIDENCE_AUDIT",
    "g2_distinct_focused_source_review": "NORMAL_SOURCE_GROUNDED_DISTINCT_REVIEW_ADMISSION",
    "autonomous_recovery_continuation": "NORMAL_BOUNDED_SOURCE_VERIFIED_RECOVERY_FORWARD_CONTROLLER",
    "gemini_failure_controller": "NORMAL_SOURCE_BOUND_SELENIUM_FAILURE_CONTINUATION",
    "g3_legacy_visual_recovery": "NORMAL_G3_SOURCE_PINNED_ISOLATED_HIGHLIGHT_REBUILD",
    "g3_semantic_mapping_continuation": "NORMAL_SOURCE_PINNED_G3_BROWSER_REVIEW_AUTOCONTINUATION",
    "g3_multisection_autoforward": "NORMAL_SOURCE_PINNED_MULTISECTION_BROWSER_RECOVERY_CAMPAIGN",
    "g3_rejected_source_quote_offline_repair": "NORMAL_G3_REJECTED_PUBLISHER_QUOTE_OFFLINE_WORKLIST",
    "g3_semantic_source_repair": "NORMAL_G3_DISTINCT_UTTERANCE_SOURCE_SEMANTIC_QA_ADMISSION",
    "g3_semantic_neon_health": "NORMAL_G3_SOURCE_FREE_OWNED_NEON_HIGH_HEALTH",
    "g3_distinct_semantic_science": "NORMAL_G3_TWO_PASS_SOURCE_GROUNDED_SEMANTIC_REVIEW",
    "g3_semantic_context_recovery": "NORMAL_G3_SCIENTIFIC_REVIEW_CONTEXT_RETRIEVAL",
    "g3_source_context_autoforward": "NORMAL_G3_IMMUTABLE_CONTEXT_SCIENCE_AUTO_FORWARD",
    "g3_owned_browser_wall_recovery": "NORMAL_G3_FINITE_SOURCE_BROWSER_RESPONSE_WINDOW",
    "g3_cross_campaign_held_send": "NORMAL_G3_SCOPE_PERSISTENT_UNCERTAIN_SEND_EXCLUSION",
    "g3_prepass_source_gap_repair": "NORMAL_G3_ORIGINAL_SOURCE_TRANSITION_VS_SCIENCE_REPAIR",
    "g3_post_send_health_invalidation": "NORMAL_G3_REQUIRE_POST_INCIDENT_SOURCE_HEALTH",
    "g3_original_visual_question_audit": "NORMAL_ORIGINAL_RENDERED_REVIEW_QUESTION_SOURCE_EVIDENCE",
    "g3_unreviewed_source_preflight": "NORMAL_G3_PIN_UNTOUCHED_SOURCE_SLIDES_WITHOUT_SEND",
    "g3_finite_campaign_cap_reentry": "NORMAL_G3_REUSE_ORIGINAL_FINITE_CAMPAIGN_WITH_TIGHTER_EFFECTIVE_CAP",
    "g3_untouched_source_witness": "NORMAL_G3_STAGE_ORIGINAL_PUBLISHER_SOURCE_WITNESS_NO_SEND",
    "g3_rejected_content_continuation": "NORMAL_SOURCE_REJECTION_WITHOUT_PROVIDER_UNCERTAINTY",
    "v71_polling_journal_recovery": "NORMAL_IMMUTABLE_IDLE_JOURNAL_COMPACTION",
    "caption_identity_parity": "NORMAL_REAL_SOURCE_FIGURE_CAPTION_CROSS_PARSER_CHECK",
    "head_patch_format": "NORMAL_WINDOWS_CUMULATIVE_PATCH_FORMAT_PREFLIGHT",
    "narrated_mp4_stage_only": "NORMAL_EXPLICIT_NARRATED_MP4_SCOPE",
    "ch11_stage_only_pdf_text_parity": "NORMAL_STRICT_UNRELEASED_VIDEO_PREVIEW_TEXT_ABI_RECOVERY",
    "youtube_multipart_publication": "NORMAL_SOURCE_PINNED_ONE_TO_N_YOUTUBE_DOCX_RECONCILIATION",
}
_REQUIRED = {
    "id", "match_type", "signature", "mechanism", "classification",
    "handler", "preconditions", "verification_test", "last_verified_date",
    "environment", "retry_policy", "enabled",
}
_KINDS = frozenset(_HANDLERS)


def load_registry(path: Path | None = None) -> dict:
    target = Path(path or REGISTRY_PATH)
    if not target.is_file() or target.is_symlink():
        raise ValueError("Recovery registry absent or linked: stop before stage execution")
    # Versioned registry has grown with executable, verified repairs. Retain
    # finite 128-KiB byte cap PLUS the original strict 200-entry/schema gates;
    # the legacy 64-KiB cap would otherwise strand all verified recoveries.
    if not 0 < target.stat().st_size <= 131072:
        raise ValueError("Invalid size of persistent recovery registry")
    obj = json.loads(target.read_text(encoding="utf8"))
    if (type(obj) is not dict or obj.get("schema_version") != 1
            or obj.get("status") != _STATUS or type(obj.get("entries")) is not list
            or not 1 <= len(obj["entries"]) <= 200):
        raise ValueError("Invalid persistent recovery registry structure")
    ids, names = set(), set()
    for e in obj["entries"]:
        if (type(e) is not dict or set(e) != _REQUIRED
                or type(e["enabled"]) is not bool
                or e["match_type"] not in _KINDS
                or e["handler"] != _HANDLERS.get(e["match_type"])
                or not all(type(e[field]) is str and 1 <= len(e[field]) <= 255
                           for field in _REQUIRED - {"enabled"})
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{5,99}", e["id"])
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{5,129}", e["signature"])
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{5,129}", e["mechanism"])
                or e["last_verified_date"] > "2099-12-31"):
            raise ValueError("Unverified or unsafe recovery registry entry")
        k = (e["match_type"], e["signature"])
        if e["id"] in ids or k in names:
            raise ValueError("Duplicate or ambiguous recovery registry signature")
        ids.add(e["id"])
        names.add(k)
    return obj


def lookup_mechanism(match_type: str, signature: str,
                     *, path: Path | None = None) -> str | None:
    """Return one code-reviewed recovery label, never arbitrary executable."""
    if match_type not in _KINDS or type(signature) is not str:
        raise ValueError("Unrecognized recovery match type or signature")
    registry = load_registry(path)
    for entry in registry["entries"]:
        if entry["match_type"] == match_type and entry["signature"] == signature:
            # Disabled/retired remedies fail closed; never silently fall back
            # to a supposedly equivalent new provider retry.
            if not entry["enabled"]:
                raise ValueError("Recovery mechanism explicitly retired or disabled")
            return entry["mechanism"]
    return None
