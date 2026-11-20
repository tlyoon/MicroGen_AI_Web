# PR554 — Recovery-registry provenance check at Malaysia midnight

**Date/host:** 20 November 2026 (MYT), Dell-115. **Parent:** PR553 exact SHA `c2ac8ae04a2c003b8b6e4a056ad917b641a90437`, stacked draft/unmerged.

## Historical failure review

PR553 source-only normal v7.1 pipeline ran 48/48 historical code windows and accepted five independent project stages. The sixth CI-gated release board was pending. Its hosted Windows Python 3.12 full suite (run `44563560387`) failed at 50% after 1,916 passed, 56 skipped. Only `VersionSixRecoveryRegistryTests.test_all_entries_have_verification_provenance` failed; new PR553 executable recovery entry had `last_verified_date:2026-11-20` (the actual Dell-115 Malaysian date), while hosted Windows was still on `2026-11-19` in UTC, so `date.today()` gave a false future-dated verdict. This is a timezone-boundary mismatch, not a Gemini failure, scientific QA acceptance, missing provenance, or reason to backdate the real verification.

## Narrow reusable remedy

The registry provenance regression now consistently compares verification metadata with the current date in the authorized project's **Asia/Kuala_Lumpur (UTC+08:00)** timezone, rather than the hosted CI system timezone. A pure deterministic helper takes an optional aware UTC datetime. Injected regression proves that **2026-11-19 16:17 UTC** is **2026-11-20 00:17 MYT** and a same-day Dell verification is accepted, while **2026-11-19 15:59 UTC** still rejects the following Malaysian date as genuinely future. Naive datetimes are rejected. The original registered code-level recovery mechanism and last-verified metadata stay unchanged; no new false provider Send or manual science acceptance is authorized.

## Verification and next acceptance

Source-local actual Dell isolated pytest **11/11** and native unit **51/51** passed; Git diff check clean. After exact clean commit and CI rerun, PR554 must pass both hosted Windows jobs and the full original 48-task source queue, then reconcile all six project-wide stages, independently restart without duplicates, and only then migrate the previously installed but **disabled** owned PR552 `MicroGen_AI_Web_v71_SourceOnly` schedule to the verified new HEAD.

A real exact `.cmd` invocation on PR552 was found to fail with `ImportError` because the script was started directly rather than through a module; PR553 contains the executable absolute-import fix and registered mechanism. Do not enable old PR552 task; verify newly scheduled task action, authenticated limited-user owner, model/TTS/media prohibition and actual source-only JSON receipt after migration. Preserve original G2 Serway §1.3 20/85 source agreement, 65 unresolved, immutable ambiguous Gemini requests, G3 QA and student publication gates.
