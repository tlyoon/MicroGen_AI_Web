# Binding owner amendment — verified-evidence reuse and no redundant defect campaigns

**Effective 2 November 2026. Applies to:** all MicroGen_AI_Web development, coding, issue fixing, academic/figure/math/TTS/media QA, PRs, retries and checkpoints. This owner-approved amendment supersedes older conflicting development instructions, without weakening safety or student-publication gates. It supplements the effective contract and autonomous development protocol.

## Mandatory procedure: evidence first, new work second

Before starting a fix, the agent/runner/reviewer **MUST** search prior PRs, verified checkpoint files, hashes of original publisher and authored artifacts, prior immutable QA receipts, historical fixes, known acceptance limitations and outstanding requirements. New work is only permitted after a recorded preflight classifies the task:

- **REUSE_VERIFIED** — Identical publisher/source, author, and target artifact SHA-256; identical explicitly defined verification scope and acceptance standard; independent source-grounded proof physically exists with matching receipt SHA. Reuse the prior result, proceed downstream; do not repeat a figure similarity campaign, rerender or rebill TTS, resubmit to Gemini, or retest the same finding just because another weaker checker disagrees.
- **COMPLETE_UNVERIFIED_SCOPE** — Earlier proof is narrower (e.g., original figure artwork matched, but axis labels or word timing remain unproved). Work **only** on the missing scope. Do not relabel this as reopening the solved artwork issue.
- **TARGETED_REVALIDATION** — A materially changed source, author, figure, narration, or video fingerprint, an explicit stronger scientific acceptance standard, or new independently reproducible contradictory source evidence affects a *specific* accepted claim. State exact old/new hashes, changed requirement, contrary witness and dependency chain; re-evaluate only affected claims. Preserve all earlier evidence.
- **BLOCK_UNJUSTIFIED_REOPEN** — No validated change, contradiction or new requirement, or merely a wrong slide number, different numeric similarity metric, checker implementation failure, stale/incomplete history search or model outage. Stop the duplicate attempt and repair the checker/reuse registry, rather than recreating the problem.

## Binding engineering and safety requirements

1. **Scope separation:** publisher figure identity, component/panel similarity, complete mathematical axis/label/graph correctness, word-by-word original PCM synchronization, audible phoneme correctness, encoded MP4 pixels, and formal release are separate claims. No proof of one automatically certifies another.
2. **Physical proof, not PR title:** record exact publisher/source SHA-256, author SHA-256, target artifact SHA-256, immutable evidence receipt and its SHA, verification method, tested scope/standard, prior PR/checkpoint and limitations. Historical tests or captions alone never certify complete textbook semantics.
3. **Preservation:** accepted originals and QA receipts are append-only/versioned. A correction creates a new linked receipt identifying scope, changed inputs and invalidation reason, never silently overwrites historical accepted results or erases old defects.
4. **Machine-enforced preflight:** run the generic exact-scope gate in selenium_pipeline/evidence_reuse_contract.py before new source-artwork repair/reverification work. Fail closed for absent/tampered receipts, unjustified reopening, unknown evidence and mismatched versions. Adapt its rule to mathematics, audio and multimedia work as their pipelines are extended.
5. **Windows CI regression:** adversarial tests must verify exact-identity reuse, partial evidence (no false promotion), changed inputs, new acceptance standard, genuine contrary evidence, falsified receipt hash, weaker-detector false alarm and safe no-source-rewrite behavior. CI must execute these tests on Windows.
6. **Review/PR/continuation requirements:** every proposed corrective PR or autonomous next-step should explicitly identify reused prior evidence, genuinely missing acceptance scope, and justified source invalidations. Consult current GitHub PR state and latest durable checkpoint before creating another PR, and update the checkpoint after genuine progress.
7. **Efficiency:** prefer immutable cached evidence over repeated Gemini/API/TTS requests, reencoding, scientific rediscovery, reviewer work and needless computer time; new verification is justified by a new scientific question or actual changed evidence, not a novel test name.
8. **Fail-closed release:** evidence reuse must never authorize an absent graph axis, mathematically incorrect label, fabricated WAV word timing, unapproved paid voice, original source overwrite, premature PR merge or student/Moodle publication. Previously unverified broader requirements remain open.

## Regression: original Thomas §8.4 Figure 8.3

October 2026 PR #188 and successive figure/source checks had already investigated original inverse-function graph correspondence. The SHA-pinned actual 17-slide author original uses **slide 6**, not a legacy slide-5 assumption. PR #451 found a mismatch in the old one-versus-three graph-run detector. PR #452 independently established physical original textbook-to-author three-panel source artwork matching: 42 geometric RANSAC inliers distributed across all three panels. PR #454 reconciled that result with the other five original author images.

**Unchanged-input Figure 8.3 publisher-artwork identity MUST return REUSE_VERIFIED.** Work on still unverified axes, mathematical label/domain meaning, and original WAV word timing must return COMPLETE_UNVERIFIED_SCOPE, not a false new artwork-similarity defect. Material source changes, a stronger explicit rule or independently reproducible contradictory physical evidence can legitimately trigger TARGETED_REVALIDATION.

The same rule applies to Figure 8.2, all other original figures, lecture formulas, source passages, WAVs and actual encoded media. It remains binding across sessions even when only the versioned checkpoint remains.

## Code and enforcement

The generic preflight engine is selenium_pipeline/evidence_reuse_contract.py; the current six-figure source identity ledger is selenium_pipeline/original_all_six_figure_source_evidence_ledger.py; the Windows adversarial regression module is tests/test_verified_evidence_reuse_contract.py; and the GitHub workflow is .github/workflows/microgen-reliability-tests.yml.

**Scientific status remains limited:** all six original author figure artworks have source provenance, not exhaustive per-axis, mathematical symbol, speech or student-publication acceptance. These draft developments are not merged production.
