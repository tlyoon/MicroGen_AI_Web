# G2 forward execution — source reuse, dry-run distinction and real-source stress (15 Nov 2026)

## Recovered Serway 6.4 milestone

Prior PR530 captionless recovery (source SHA 64b748468e6bdb12ddb127f1d8bea90a7f3f63d270fbb5378ba1d3ddeeb955fd) produced the deterministic local successor `auto_captionless_aff579b03d76a794ff27`. Its source-pinned figure recovery receipt remained valid. The current development run reused truly accepted historical slides, narration and script QA from the same original PDF, without a single new Gemini Send:

- Slides.pdf SHA 814fdbe054f09a3073e3d7c82bd5929d48c46a18255fdd5aeac3a8dbe64
- Slides.tex SHA 7c0b97ba522e5c709fd0b01fa8b2de9ae884a6ed59c292cb1e1739fc4b26be63
- Script.txt SHA 7806b3e006b6727cec1acf9a0c9aeda2318c6e50f6821269fbae5c440223ee59
- QA outputs: math_semantic_report SHA 63b40857e30905e88e19dfbab28559b2e550171ecb958f6bb62fafda5a007163, script_risk_report SHA be62fca8ff375dcf97ecc6e5b6017ec89a4244a295445651b445ac31026bdf52.

Normal `windows_lecture_progression_coordinator.inspect_progress` now genuinely returns `REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS`, rather than an incomplete slides/narration stage. This is only technical source-stage recovery; neither visually correct element timing nor scientific and acoustic G2 acceptance is asserted. The historical script-QA result is explicitly limited-rule math QA; not independent subject-area proof.

## Permanent normal-path fix

New `selenium_pipeline/windows_historical_stage_auto_reuse.py` searches a bounded set of original-source-matching immutable trial receipts. Its non-destructive stage rebindings preserve old evidence and SHA-bind the new target to its own predecessor. Reuse of slides, narration and deterministic script QA is attempted before a new model Send, even when external Gemini provider health is poor. A Windows kernel lease prevents concurrent reuse of a given target. The operator permits a bounded three-stage no-model chain, re-auditing the state between each stage; an actual new model-bearing stage remains separately controlled. Historical source bytes, successful stage receipts, and individual original Send records are never cleared.

## Newly discovered live source claim blocker

On §1.3, the original pre-send check rejected a fresh, never-sent source because a preceding source-only forward campaign had created a `fresh_trial_contract.json` with a verified no-Send `FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY` receipt. This is a false positive if treated as an actual provider Send. The corrected `windows_original_source_candidate_inventory.py` now recognizes an *independently validated inert dry-run*: exact campaign/receipt schema, zero model/TTS, SHA-pinned original and staged PDF, exact original size, no figure or later-stage Send/result, and no suspicious stage claims. Any absent/mismatched dry-run evidence or actual Send intent still stops before model submission. Both the normal first-Send enforcement and read-only candidate inventory share this classification. New `tests/test_windows_dryrun_send_eligibility.py` covers positive and adversarial cases.

## Genuine new-source campaign

- Serway §1.3 original SHA `181f0f361809d90daf72fce1bf50bcf2b88fbf37fc59ed181411266b53cb5ae8` was run through actual Dell-115 Flash-Lite/Selenium figures stage. The previously blocking inert dry-run was correctly ignored; the browser positively registered model sends. On original page 3 the provider returned exact `MAPPING_REVIEW_REQUIRED` for TWO crops (`fig_4.png`, `fig_5.png`); the page contains a printed Figure 1.6 caption. This does NOT satisfy the source-only single-captionless-crop recovery gate. The original stage result is `FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY`, with a SHA-bound terminal triage and no automatic resend, no original PDF mutation. Avoid retry loops on this source.
- Genuine Serway §1.4 source SHA `9dc28034e807304e242101d066790068477865f19d9a4bc04e5e474c2f7df3c5` independently entered the normal figure pipeline. On page 1, Flash-Lite returned `MAPPING_REVIEW_REQUIRED` for two original crops; original provider Send was recorded and the stage failed, safely marked `FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY` with no replay.
- Crucial cross-subchapter finding: §1.3 original page 3 and §1.4 original page 1 have **identical PDF text, identical 612 x 783 point geometry and identical rendered RGB-pixel SHA** `323b652fb4a11b9b2f80f2ffbfd58eb4ba1ff016caaf7d241ec407bbfe7e1038`. Whole-source SHA is different. A future **page-level**, source-pixel-bound duplicate Send guard is needed; current PDF-global once claim does not protect overlapping identical pages across different subsection PDFs. Neither source has a scientifically accepted figure-caption mapping for the two-crop ambiguity, so no technical or semantic success may be fabricated.
- Source-independent forward acceptance moves to different eligible source families instead of treating Serway §1.3, §1.4 or §6.4 as the project's only pace-setter.
- Original §6.4 has 67 rich visual-semantic mappings unresolved and no approved full per-element PCM/acoustic or synchronized MP4 receipt; technical slide/script reuse does not clear those scientific blockers.

## Acceptance boundary

Local Windows source-stage/scoped source claim and source-only recovery regressions must pass. Hosted exact-commit Windows CI and PR merge must be verified separately. G2 as a whole is NOT COMPLETE: fully independent visual/academic source mapping, recorded per-element audio with proof, acoustic QA, actual synchronized under-600s video and final acceptance still need demonstrable evidence. Do not bypass or relabel unavailable proof. One particular PDF failure must not prevent subsequent *different-source* trials.
