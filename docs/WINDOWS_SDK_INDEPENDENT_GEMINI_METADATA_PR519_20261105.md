# PR519 — SDK-independent, single-request Gemini key-pool metadata check (5 Nov 2026)

**Workstream:** MicroGen_AI_Web (Selenium), Dell-115 native Windows; stacked on PR518 head `425c77d88920e6240b79d7d627fd3511180c7b1d`. Not MicroGen_AI (API-only).

## Live blocker and correction

- The previous PR517/PR518 key-pool metadata code instantiated `google.genai.types.HttpRetryOptions(attempts=1)`.
- Current Dell-115 default interpreter: `C:\Users\tlyoon\AppData\Local\miniconda3\python.exe`, `google-genai 1.4.0`, which does not expose `HttpRetryOptions`. Both keys therefore failed with local `AttributeError` during metadata preflight; this was NOT Gemini HTTP 503/504, not evidence of bad keys or insufficient credit.
- New `_one_shot_model_metadata_get` performs exactly one standard-library GET to the vetted Google `/v1beta/models/gemini-3.8-flash` endpoint per configured distinct key; sends API key **only as a request header**, not in the URL. Rejects HTTP redirects, large responses and unvetted models; 10-second deadline; no SDK retry dependency and no `generate_content`.
- Synthetic tests verify single request, secret-absent URL/result, no redirect, 503 status extraction without retry, oversized response and model allowlist. Existing key rotation/single-send contract unchanged: no resubmission or key switch after an uncertain original-source send.

## Dell-115 live verification

Before fix: **2/2 keys** produced `METADATA_LOOKUP_FAILED` with `AttributeError`, code `null` (local SDK problem).

After fix: **2/2 keys** returned `VETTED_MODEL_METADATA_REACHABLE`; key-pool status `KEY_POOL_METADATA_CHECKED_AT_LEAST_ONE_REACHABLE`; `fallback_key_metadata_confirmed=true`; `model_generate_content_calls=0`; `new_tts_calls=0`. Focused native Windows tests **21/21 PASS**, `py_compile` and `git diff --check` PASS.

## Independent Selenium evidence

PR518 exact-head CI run #663 passed both Windows jobs. A same-session, direct read-only Dell-115 login test still reports `CHATGPT_MANUAL_LOGIN_REQUIRED_IN_EXISTING_PROFILE` on Chrome port 9223; the existing ChatGPT tab was successfully focused. Gemini port 9222 composer is authenticated. Gemini browser's earlier SHA-verified UI error and unverified one-send canary remain quarantined; an authenticated composer is **not** proof of generation health.

## Constraints and next steps

Never re-run failed Serway/Thomas sources to chase a single PDF; do not switch API keys after an uncertain send; no paid API/TTS without separate project consent; no local models, Ubuntu/HP/Yoga, dirty G: repo overwrite, user login bypass, mass historical PR merge or student publication.

Next: commit/push PR519 and exact-head Windows CI; then use a genuinely new source only after deliberate stage/cost review and independently verify audio/MP4 scientific acceptance. The historic stacked draft PR chain still requires bounded dependency review before production release.
