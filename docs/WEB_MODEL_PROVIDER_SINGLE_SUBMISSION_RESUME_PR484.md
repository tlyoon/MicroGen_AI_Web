# PR484 — Authenticated Gemini/ChatGPT web model readiness + exactly-one original job

## Production blocker

The source-bound lecture mapping queue is ready, but a previous authenticated Gemini UI submission returned no valid complete JSON and ChatGPT's separate Dell-115 automation browser profile was logged out. Blindly retrying Gemini or silently switching providers after an uncertain submission risks double charges, lost source provenance and conflicting academic output. Progress must not depend on a prompt being repeatedly resubmitted.

## New production-facing interfaces

`python -m selenium_pipeline.rich_mapping_provider_readiness` INSPECTS only existing locally configured Chrome debug sessions (Gemini port 9222; ChatGPT 9223), without sending prompts or opening/closing user tabs. A ChatGPT guest page is NOT a signed-in account. The selector prefers an authenticated Gemini session; ChatGPT may be selected only if authentically signed in **before the first submission**. An uncertain submission forces same-provider reconciliation, never provider switching.

`python -m selenium_pipeline.rich_mapping_provider_dispatch --source-folder <publisher_lecture> --checkpoint <exact_accepted-rich-map> --fallback-dir <accepted-prose-receipts> --queue-folder <versioned-only-unresolved-queue> --slide N --attempt-root <NEW-external-output> --wait-s 60` performs at most ONE original SHA/author/script-bound unresolved-only request through the established Gemini Flash web UI or logged-in ChatGPT browser UI. Writes a durable `MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND` claim before opening any model submission. On timeout, provider failure, invalid JSON, original/author tamper, wrong utterance ID or hallucinated source quote it leaves the claim to prevent replay. On complete JSON it persists the original captured model response and independently recomputed full-source merge and semantic review, which continues to hold original mathematical/figure semantics for independent proof. No bills for Cloud TTS, no local language models, no student release.

## Real Dell-115 readiness

Read-only verified `gemini: AUTHENTICATED_COMPOSER_READY` at 9222; `chatgpt: LOGIN_REQUIRED` at 9223, guest profile. No attempt to use ChatGPT while logged out. Both Windows/Python readiness and one-shot provider/no-resend mocked integration tests pass. The *new* multiblock candidate inventory across 41 original slides contains 339 physically real targets; all 12 already independently accepted source-prose links remain untouched, and only the 155 unverified originals are in versioned `20261103_PR484_339_TARGETS_ORIGINAL_UNRESOLVED_ONLY_QUEUE`. No previous approved mathematical/image research was rechecked.

## Next acceptance

Attempt exactly ONE previously unsubmitted genuine 8.5 source-bound unresolved-only slide request via Gemini; inspect and preserve its source-bound result or no-resend failure receipt. If response is unavailable, do not start 40 other model jobs or fake a new lecture. Continue the remaining app integration and Windows release engineering without paid TTS. Once provider results and truly independent math/figure source proof exist, advance one original lesson all the way to actual synchronized multipart videos and then a second example.

All existing original textbook files, authored slides, scripts, WAVs, MP4s and three user-owned checkout edits remain immutable.
