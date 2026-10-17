# Provider-log and billing reconciliation for TTS retries

**17 October 2026. Draft PR #123, stacked after draft #122. Non-billable, read-only, no publication.**

## Two kinds of external evidence — do not confuse them

1. **Provider request logs:** Google AI Studio provides configurable Gemini API logging for eligible paid-tier projects. Logging of GenerateContent requests may be off by default and earlier failed requests might be absent. Some SDK exceptions expose a provider-issued request ID and some do not. Only a provider-generated ID captured in BOTH the local journal and an independently exported provider log, with matching model, status and UTC time, supports exact ID-level correspondence. The normalized export schema in this document is a **MicroGen adapter format, not a native Google API payload**. Never fabricate missing request IDs.
2. **Cloud Billing exports:** BigQuery billing exports contain service, SKU, project, invoice, usage-window, cost and currency data. They generally **do not identify a unique TTS API request**. Time-window overlap may show charges in a surrounding period but cannot prove that a particular MicroGen request incurred them. A project may contain unrelated jobs. Ignore taxes, refunds and adjustments when building the nonnegative regular-charge rows required by this verifier; a negative adjustment should be reconciled separately rather than coerced to a positive charge.

Official documentation:
- https://ai.google.dev/gemini-api/docs/logs-datasets
- https://ai.google.dev/api/generate-content
- https://docs.cloud.google.com/billing/docs/how-to/export-data-bigquery
- https://docs.cloud.google.com/billing/docs/how-to/export-data-bigquery-tables/standard-usage

## Local changes

`tts_attempt_evidence` now records a UTC **completion** timestamp and optional `provider_request_id` on each observed event. It reads older draft journal events without timestamps as legacy entries; such events remain locally hash-verified but **cannot** be exact-matched externally. The request ID is taken only from a safe identifier field or recognized response-header name on an exception; text, raw headers, API keys and transcripts are never included. Some successful API responses currently do not expose request IDs through the existing WAV-only worker boundary. These remain intentionally uncorroborated. The standing Lite→Flash→conditional Chirp fallback authorization and minimum three-attempt rule are unchanged.

## Offline usage

Run in a checked-out development environment with original source folder and externally exported normalized JSON:

```powershell
python -m selenium_pipeline.tts_provider_reconciliation --folder 'X:\Lecture\8.4' --provider-export 'C:\Audits\gemini-requests-normalized.json' --billing-export 'C:\Audits\gcp-billing-normalized.json'
```

Omit an unavailable export rather than creating fictional placeholder records. The command only reads; it prints JSON containing source/journal hashes, exact ID-level matches, unmatched local records, unmatched external records and aggregate billing-window overlap. `real_provider_receipt_proven` remains **false** because importing a self-labeled JSON file does not cryptographically authenticate its origin. A claim of actual independent provider confirmation needs a separately authenticated, original provider export and appropriate identity review.

### Provider request export — MicroGen-normalized schema

```json
{
  "schema_version": 1,
  "kind": "provider_request_export",
  "source_system": "google_ai_studio_logs",
  "exported_at_utc": "2026-10-17T12:00:00Z",
  "rows": [
    {
      "provider": "gemini",
      "model": "gemini-3.8-flash-lite-tts",
      "provider_request_id": "REPLACE_WITH_REAL_PROVIDER_ID",
      "event_time_utc": "2026-10-17T11:58:00Z",
      "http_status": 503
    }
  ]
}
```

Use `google_cloud_logging` for a normalized Cloud Logging request export. The ID must be a real provider-generated identifier; examples are nonfunctional placeholders. API error types are reconciled by HTTP status (408/429/500/502/503/504 are treated as transient). If your original logs do not expose per-request HTTP status, identifier or model, leave the request unsupported rather than inventing it. Matching uses one-to-one IDs, model, provider, outcome and timestamp completion proximity (default five minutes). This is **not proof of account ownership** or cryptographic log authenticity.

### Aggregate billing export — MicroGen-normalized schema

```json
{
  "schema_version": 1,
  "kind": "billing_aggregate_export",
  "source_system": "google_cloud_billing_bigquery",
  "exported_at_utc": "2026-10-18T12:00:00Z",
  "rows": [
    {
      "project_id": "YOUR_PROJECT_ID",
      "service": "SERVICE_DESCRIPTION",
      "sku": "SKU_DESCRIPTION",
      "usage_start_utc": "2026-10-17T11:00:00Z",
      "usage_end_utc": "2026-10-17T12:00:00Z",
      "cost": "0.0200",
      "currency": "USD"
    }
  ]
}
```

Billing windows are compared against locally observed completion times. The report never derives API call counts, unit prices, request models or the price of a specific WAV from aggregated charges. Amounts are accumulated **only within the same currency**, and carry an explicit `not_per_request` label. You must verify the actual project and SKU in the source export; this module cannot independently prove ownership from JSON labels.

## Operational safety and release boundaries

- No API calls, no Cloud Billing/BigQuery queries, no changes to original audio, no auto-generated attestation, no provider credentials accessed, and no draft merges.
- No editing or disclosure of local secrets, response headers, full transcripts, source PDFs or learner information in any export.
- The separate Cloud authorization gate continues to use the local actual-outcome journal, not optional external billing availability. Missing provider logs **do not** revoke the owner's previously agreed conditional fallback permission.
- Authentic narrator listening, mathematical and complete multipanel-figure integrity, each MP4 **strictly under 600 seconds**, synchronized pixel-highlight QA and explicit Moodle publication approval are still required.
- Tests run only in clean isolated temporary checkouts on HP, Dell-115 and Yoga 6. Preserve all dirty production Drive repositories and originals; Zenbook excluded.

**Security limitation:** A hash-chain and JSON export can be rewritten by a sufficiently privileged actor. Independent provenance requires authentic provider-side records obtained and preserved through a trusted export process; this tool offers a transparent comparison report, not a certificate of remote execution or payment.