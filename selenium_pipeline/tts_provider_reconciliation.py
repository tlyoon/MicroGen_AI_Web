"""Offline reconciliation of local TTS attempt journal with EXTERNALLY exported records.

Only an actual provider request ID shared between local journal and an external
request log can establish an ID-level association. Cloud Billing SKU/window
costs are aggregates, NEVER proof that a particular API call was billed.

All external JSON is untrusted input, even if it declares a Google issuer.
No network, credentials, Google SDK, TTS synthesis, or source-file mutation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from .runner import blocks
from .tts_attempt_evidence import AttemptEvidence, TTSAttemptEvidenceError


class TTSExternalEvidenceError(ValueError):
    pass


def _bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise TTSExternalEvidenceError(f"Missing or symlinked evidence file: {path.name}")
    return path.read_bytes()


def _data(path: Path, kind: str) -> tuple[dict, str]:
    raw = _bytes(path)
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise TTSExternalEvidenceError(f"Invalid {kind} JSON") from exc
    if not isinstance(obj, dict) or obj.get("schema_version") != 1:
        raise TTSExternalEvidenceError(f"Invalid {kind} schema version")
    return obj, hashlib.sha256(raw).hexdigest()


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise TTSExternalEvidenceError("Evidence timestamps must be ISO UTC ending Z")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TTSExternalEvidenceError("Malformed external UTC timestamp") from exc
    if dt.utcoffset().total_seconds() != 0:
        raise TTSExternalEvidenceError("External timestamps must be UTC")
    return dt


def _outcome_for_http(status: int) -> str:
    if type(status) is not int or not (100 <= status <= 599):
        raise TTSExternalEvidenceError("Invalid provider HTTP status")
    if 200 <= status < 300:
        return "success"
    if status in (408, 429, 500, 502, 503, 504):
        return "transient_failure"
    return "permanent_failure"


def _load_requests(path: Path) -> tuple[list[dict], str]:
    doc, digest = _data(path, "provider-request")
    if (doc.get("kind") != "provider_request_export"
            or doc.get("source_system") not in (
                "google_ai_studio_logs", "google_cloud_logging")
            or not isinstance(doc.get("rows"), list)):
        raise TTSExternalEvidenceError("Unrecognized request-log export format")
    _utc(doc.get("exported_at_utc"))
    seen = set()
    rows = []
    for row in doc["rows"]:
        if (not isinstance(row, dict)
                or row.get("provider") not in ("gemini", "chirp3")
                or row.get("model") not in (
                    "gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts", "chirp3-hd")
                or (row["provider"] == "gemini") !=
                   (row["model"] != "chirp3-hd")
                or not isinstance(row.get("provider_request_id"), str)
                or not 8 <= len(row["provider_request_id"]) <= 128
                or not all(c.isalnum() or c in "_:-." for c in
                           row["provider_request_id"])):
            raise TTSExternalEvidenceError("Unsafe or incomplete external request record")
        key = row["provider_request_id"]
        if key in seen:
            raise TTSExternalEvidenceError("Duplicate external provider request ID")
        seen.add(key)
        dt = _utc(row.get("event_time_utc"))
        status = _outcome_for_http(row.get("http_status"))
        rows.append({**row, "_utc": dt, "_outcome": status})
    return rows, digest


def _load_billing(path: Path) -> tuple[list[dict], str]:
    doc, digest = _data(path, "billing")
    if (doc.get("kind") != "billing_aggregate_export"
            or doc.get("source_system") != "google_cloud_billing_bigquery"
            or not isinstance(doc.get("rows"), list)):
        raise TTSExternalEvidenceError("Unknown billing-aggregate export format")
    _utc(doc.get("exported_at_utc"))
    rows = []
    for row in doc["rows"]:
        if (not isinstance(row, dict) or not isinstance(row.get("project_id"), str)
                or not isinstance(row.get("service"), str)
                or not isinstance(row.get("sku"), str)
                or not isinstance(row.get("currency"), str)
                or len(row["currency"]) != 3):
            raise TTSExternalEvidenceError("Incomplete billing usage row")
        start, end = _utc(row.get("usage_start_utc")), _utc(row.get("usage_end_utc"))
        try:
            cost = Decimal(str(row["cost"]))
        except (KeyError, InvalidOperation, TypeError) as exc:
            raise TTSExternalEvidenceError("Invalid billing amount") from exc
        if not cost.is_finite() or cost < 0 or start >= end:
            raise TTSExternalEvidenceError("Invalid billing usage window or cost")
        rows.append({**row, "_start": start, "_end": end, "_cost": cost})
    return rows, digest


def audit(folder: Path, *, provider_export: Path | None = None,
          billing_export: Path | None = None, tolerance_seconds: int = 300) -> dict:
    """Read-only, no-Google-call audit; unknown IDs cannot be exact-matched."""
    if type(tolerance_seconds) is not int or not 0 <= tolerance_seconds <= 3600:
        raise TTSExternalEvidenceError("Time tolerance must be 0–3600 seconds")
    if folder.is_symlink() or not folder.is_dir():
        raise TTSExternalEvidenceError("Source folder missing or unsafe")
    folder = folder.resolve(strict=True)
    raw = _bytes(folder / "script.txt")
    narration = blocks(raw.decode("utf-8"))
    if not narration:
        raise TTSExternalEvidenceError("No original slide narration")
    if not (folder / ".tts_attempt_evidence" / "identity.json").is_file():
        raise TTSExternalEvidenceError("No recorded local TTS attempt evidence")
    try:
        local = AttemptEvidence(folder, narration)
        events = local.read()
    except (TTSAttemptEvidenceError, UnicodeDecodeError) as exc:
        raise TTSExternalEvidenceError(f"Invalid local TTS journal: {exc}") from exc
    if not events:
        raise TTSExternalEvidenceError("Attempt journal is empty")
    external = []
    provider_digest = None
    if provider_export is not None:
        external, provider_digest = _load_requests(provider_export)
    by_id = {row["provider_request_id"]: row for row in external}
    matches = []
    gaps = []
    claimed_ids = set()
    for event in events:
        local_id = event.get("provider_request_id")
        if not local_id:
            gaps.append({"sequence": event["sequence"],
                         "reason": "no_provider_request_id_in_local_event"})
            continue
        if local_id in claimed_ids:
            raise TTSExternalEvidenceError("Local provider request ID was reused")
        claimed_ids.add(local_id)
        row = by_id.get(local_id)
        if row is None:
            gaps.append({"sequence": event["sequence"],
                         "reason": "no_matching_provider_log_record"})
            continue
        if "observed_at_utc" not in event:
            gaps.append({"sequence": event["sequence"],
                         "reason": "legacy_event_has_no_utc_timestamp"})
            continue
        delta = abs((_utc(event["observed_at_utc"]) - row["_utc"]).total_seconds())
        if (row["provider"] != event["provider"]
                or row["model"] != event["model"]
                or row["_outcome"] != event["outcome"]
                or delta > tolerance_seconds):
            gaps.append({"sequence": event["sequence"],
                         "reason": "provider_log_disagrees_on_model_status_or_time"})
            continue
        matches.append({"sequence": event["sequence"],
                        "provider_request_id": local_id,
                        "provider": event["provider"], "model": event["model"],
                        "http_status": row["http_status"],
                        "time_difference_seconds": round(delta, 3)})
    orphaned = len(set(by_id) - {row["provider_request_id"] for row in matches})
    request_status = (
        "NO_PROVIDER_EXPORT" if provider_export is None else
        "ALL_EVENTS_ID_MATCHED" if len(matches) == len(events) and not orphaned else
        "PARTIAL_ID_MATCH" if matches else "NO_VERIFIABLE_ID_MATCH")
    billing_info = {
        "status": "NO_BILLING_EXPORT",
        "attribution": "not_available",
        "matched_usage_windows": 0,
        "cost_by_currency": {},
        "export_sha256": None,
    }
    if billing_export is not None:
        bill, billing_digest = _load_billing(billing_export)
        times = [_utc(event["observed_at_utc"])
                 for event in events if event.get("observed_at_utc")]
        overlapping = [row for row in bill if any(
            row["_start"] <= time < row["_end"] for time in times)]
        totals = defaultdict(Decimal)
        for row in overlapping:
            totals[row["currency"]] += row["_cost"]
        billing_info = {
            "status": ("USAGE_WINDOW_OVERLAP_ONLY" if overlapping else
                       "NO_WINDOW_OVERLAP"),
            "attribution": "aggregated_service_sku_project_time_only_not_per_request",
            "matched_usage_windows": len(overlapping),
            "cost_by_currency": {k: str(v) for k,v in sorted(totals.items())},
            "export_sha256": billing_digest,
        }
    return {
        "status": "OFFLINE_RECONCILIATION_ONLY_NO_PROVIDER_AUTHENTICATION",
        "source_script_sha256": hashlib.sha256(raw).hexdigest(),
        "local_attempt_journal_tip_sha256": local.tip(),
        "local_attempt_count": len(events),
        "local_failure_counts": dict(sorted(Counter(
            event["model"] for event in events
            if event["outcome"] == "transient_failure").items())),
        "provider_export_sha256": provider_digest,
        "provider_request_correlation": {
            "status": request_status,
            "matched_requests": matches,
            "unmatched_local_events": gaps,
            "unmatched_external_record_count": orphaned,
            "source_authentication": "external_json_not_cryptographically_authenticated",
        },
        "billing": billing_info,
        "automatic_cloud_authorization_changed": False,
        "real_provider_receipt_proven": False,
        "billable_api_calls_performed": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline, read-only TTS provider/billing export reconciliation")
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--provider-export", type=Path)
    parser.add_argument("--billing-export", type=Path)
    parser.add_argument("--tolerance-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    print(json.dumps(audit(args.folder, provider_export=args.provider_export,
                           billing_export=args.billing_export,
                           tolerance_seconds=args.tolerance_seconds),
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
