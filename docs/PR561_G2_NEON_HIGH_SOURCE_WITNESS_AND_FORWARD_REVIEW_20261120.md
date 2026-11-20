# PR561 — Continue G2 source review under verified Neon/High without replay

**20 November 2026, Dell-115.** Parent: PR560 exact SHA `a7a85d0f845474c32a01679f9728b56c36085634`. PR560's immutable, real source-free one-shot Neon/High two-PDF result is `NEON_HIGH_TWO_PDF_SOURCE_FREE_RESPONSE_VERIFIED` with exact secrets from **both** synthetic PDFs, true owned new-turn registration, and zero textbook uploads. The two original uncertain slide-10/11 claims and the old failed Pro v1/v2 synthetic PDF claims remain unchanged.

## Historical root cause and targeted executable repair

The old source queue continued to stop at `DEFERRED_SYNTHETIC_PDF_CAPABILITY_EXHAUSTED_NO_RESEND` because it checked only retired Pro proof, even after independently successful Neon/High diagnostic. The original source browser request also called Pro-specific routing on port 9222 even though the authenticated new tab supports Neon/High, and its immutable saved model text did not retain authenticated model/effort identity.

PR561 repairs three real shared production pathways. The exact source-bound selection in `ai_academic_review_queue` now recognizes the verified, **incident-distinct Neon/High two-PDF proof** only after two genuinely prior uncertain original source claims. It chooses exactly one untouched next original slide; no earlier claims are recycled. `ai_academic_web_review` accepts Neon only when the source queue has independently provided that model requirement, forces primary port 9222, demands exact Neon/High in the **real shared Selenium browser transport before upload and Send**, and otherwise preserves the historical Pro behavior. `academic_review_checkpoint` now persists a separate exclusive, write-once `neon_high_owned_model_witness.json` bound to the original source SHA, review mode, immutable request fingerprint, exact source-response SHA, positive owned new user turn, Neon UI identity and checked High effort. A saved text response cannot be promoted to source-reviewed scientific evidence unless this independent witness still matches; all old Pro saved responses retain their original validation mechanism.

The executable registry adds `G2_NEW_SOURCE_REVIEW_AFTER_VERIFIED_NEON_HIGH_TWO_PDF` under the existing `selection_action` dispatch, with finite once-only model request and no source release. A successful new first pass is still one pass only: it cannot count as independent two-reviewer consensus, independent acoustic/video QA, G3 acceptance or student publication.

## Real and fault-injection evidence

- **Live original Serway §1.3 read-only queue selection** returned `ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY`, slide **12**, `INITIAL_REVIEW`, required Neon/High, `FRESH_FIRST_ATTEMPT`, 0 requests, 0 uploads, no old original replay. Receipt `%LOCALAPPDATA%\\MicroGen_AI_Web_Checkpoints\\PR561_READONLY_ORIGINAL_SERWAY12_NEON_G2_SELECTION_20261120.json`.
- **92 focused and historical regression tests passed**, including wrong model, downgraded effort, raw response without actual owned new turn, tampered response/witness, old Pro compatibility, and process crash after model response with zero duplicate Send; syntax and Git whitespace checks clean.
- PR560 hosted CI both jobs passed on the same exact parent SHA. PR560 real v7.1 48-task source-only and 6-stage supervisor verification is a distinct workstream, not academic completion.

## Recovery and continuation

Normal authoritative sequence: preserve original source hashes and source review queue; validate new Neon/High PDF proof and registered recovery; dispatch only the next previously unclaimed original G2 request with the durable request fingerprint; retain all response and model/effort witnesses; independently validate source quotations and mathematical meaning; continue to the independent challenge only when the first source pass passes. If provider response is unaccounted, stop its exact one-use claim and never resend it. Other eligible code work may advance independently; no manufactured G2, G3, or student release. The installed 30-minute PR557 source-only Windows task is left enabled/untouched.
