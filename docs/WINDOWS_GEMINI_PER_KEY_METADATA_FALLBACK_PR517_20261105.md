# PR517 — Verify Gemini API fallback key with non-generating per-key metadata

**Scope:** general MicroGen_AI_Web Windows API key rotation, not the separate
API-based MicroGen_AI project and not another textbook PDF repair.

Prior PR516 demonstrated Gemini API model metadata reachable using **only the
first configured key**. The existing `gemini_keys.call_with_key_failover`
already supports ordered numbered keys and simulates quota/billing, 401/403/
429 and 503/504 fallback for independent normal operations. However, metadata
of key #2 was not independently checked, and neither a successful metadata
GET nor a simulated rotation is evidence of a successful paid generation.

PR517 adds `windows_gemini_api_key_pool_preflight`:
- Native Windows only, `%LOCALAPPDATA%\Microvid\.env` through the standard
  environment loader and deduplicated `get_gemini_api_keys()`.
- Optional `--verify-each-key-model-metadata` checks up to six distinct keys,
  exactly **one** Google `models.get` per key, one SDK attempt, 10s timeout.
- Reports only ordinal, expected model-name match, structured error code
  and safe exception class. Never prints key values or raw SDK error text.
- A failed primary GET cannot conceal a successful second key; the second
  key is independently verified for *new independent work* but remains
  unproven for generate_content quota or service health.
- Existing single-send original source policy **never retries** an
  ambiguous old 503/504 or swaps keys on a possibly submitted job.
- The general provider route preflight optionally accepts the verified
  key-pool evidence through `--verify-all-api-key-metadata`, including
  the case where key #1 metadata fails but key #2 succeeds, and still
  requires separate paid-generation consent.

### Actual Dell-115 evidence on 5 November 2026

Ran the isolated native Windows worker against the configured keys,
with no source PDF, no prompt and **zero** model-generation/TTS calls:

| Key ordinal | Independent model metadata GET |
|---|---|
| 1 | `VETTED_MODEL_METADATA_REACHABLE` |
| 2 | `VETTED_MODEL_METADATA_REACHABLE` |

Result: `KEY_POOL_METADATA_CHECKED_AT_LEAST_ONE_REACHABLE`,
`fallback_key_metadata_confirmed=true`,
`metadata_eligible_new_source_key_ordinals=[1,2]`.

**Conclusion:** Gemini API key setup and basic fallback credentials are not
the presently demonstrated blocker. Successful API `generate_content` and
actual billing/quota remain untested without separate project-authorized
paid-content generation consent. Selenium browser errors and ChatGPT session
authentication are **independent** and are not repaired by key rotation.

`python -m selenium_pipeline.windows_gemini_api_key_pool_preflight --verify-each-key-model-metadata`

All operation and diagnostic paths preserve no-old-request retry, Windows
only, no local model, no student release, and no mass Git merge.
