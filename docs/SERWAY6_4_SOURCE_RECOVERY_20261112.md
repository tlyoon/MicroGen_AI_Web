# Serway 6.4 source-locked recovery — 2026-11-12 (Dell-115)

## Current verified state

- Project: MicroGen_AI_Web, Windows-only, authorized device Dell-115.
- Repository: feature/pr528-autonomous-ai-lecture-acceptance (PR #528).
- Source: G:\My Drive\Serway\Serway_1_7\6\6.4\source.pdf
- Original source SHA-256: `64b748468e6bdb12ddb127f1d8bea90a7f3f63d270fbb5378ba1d3ddeeb955fd`
- Original figure failure: `20261111_PR528_G2_SERWAY6_4_PANEL_CORROBORATION_DISTINCT_V1` (unchanged, Gemini response `MAPPING_REVIEW_REQUIRED` on page 6, original result SHA `fe6b9856484b2163c8eb7bc7c6b813f144fca60407da4935d5bb5767ce684638`).
- One new isolated slides Send in `20261112_PR528_G2_SERWAY6_4_SLIDES_MENU_RECOVERY_V5`: successful and source-SHA-bound; `slides.pdf` SHA `814fdbe054f09a3073e3d7c82bd5929d48c46a18255fdd5aeac3f7adcd4d1e72`.
- One new isolated narration Send in `20261112_PR528_G2_SERWAY6_4_NARRATION_SAFE_REUSE_V6`: complete 14-block Gemini response captured but locally rejected due four false-positive capital-`A` flags; old failure receipt retained unchanged.
- Most recent complete text-stage trial: `C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7`.
- V7: page 6 source-only generic-graphic mapping independently reverified; previously accepted 14-page slide deck byte-identically reused; existing 14-block narration recovered without any new Gemini Send; all local title, structural, citation, TTS risk and math-domain checks passed; deterministic `script_qa` stage returned `STAGE_COMPLETED_AND_SOURCE_SHA_BOUND`.
- Final V7 `script.txt` SHA `7806b3e006b6727cec1acf9a0c9aeda2318c6e50f6821269fbae5c440223ee59`.
- Latest coordinator state: `REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS`; no paid TTS, no WAV, no video, no publication, and no G2/G3 release acceptance claim.

## General fixes encoded in normal source tree

1. `figure_uncaptioned_source_recovery.py` (earlier PR528 implementation) and new `figures_failed_source_only_resume.py`: preserve original rejected model result; repair only when PDF, crop geometry, text and original refusal prove one truly uncaptioned source graphic. Never send a duplicate Gemini prompt. Verified via separate receipt.
2. `windows_original_stage_sequence.py` and `windows_lecture_progression_coordinator.py`: require the locally re-verifiable source-only figure rescue before progressing. Do not mark original provider figure stage as successful.
3. `gemini_thinking.py`: remember a genuinely selected Medium radio for the same owned tab when visible family+level label remains unchanged briefly; avoid reopening non-interactable model picker after uploads. Includes already-selected branch.
4. `windows_source_stage_reuse.py`: byte-verify accepted original slides and reuse them in a distinct immutable trial without re-sending.
5. `vendor_template_v2/script_tts_risk.py`: maintain a source-script-scoped, explicit `area A` symbol declaration across slides; a later capital `A` receives an acoustic warning, not a false ambiguous-article blocking error. Unexplained `A` remains blocking.
6. `windows_narration_local_salvage.py`: verify source, slide, raw-capture and prior-failure hashes and rerun all 10 narration validation checks before adopting a rejected-but-complete prior script locally in a new trial.

## Validation and integrity

- On Dell-115, 68 focused pytest tests passed on 2026-11-12, nine nonfatal warnings; `git diff --check` passed.
- Genuine V4–V7 source-only recovery and SHA checks exercised on actual original Serway 6.4 material.
- V5 slides returned success, compiled PDF, and citation/source-artifact gate passed.
- V7 script QA produced `script_risk_report.json` SHA `be62fca8ff375dcf97ecc6e5b6017ec89a4244a295445651b445ac31026bdf52`, `math_semantic_report.json` SHA `63b40857e30905e88e19dfbab28559b2e550171ecb958f6bb62fafda5a007163`.
- Original source SHA is unchanged, original failure receipts are preserved. Local-only recovery requests made **zero** additional provider/TTS calls; V5 and V6 each made one new authorized Selenium Gemini request.

## Still pending

- Independent science and diagram review (not asserted by structural map tests).
- Source-bound audio/WAV voice generation and acoustic QA, synchronized highlighting, bounded MP4 and release/publishing acceptance. Existing coordinator deliberately stops at the audio handoff. Do not assert full lecture or release completion.
- Keep user no-manual-intervention preference where automation is technically authorized; never bypass existing paid API or public release authorization gates.
- Next codebase priority: generalize automated source-grounded audio generation, acoustic QA and media acceptance from the verified V7 handoff, without repeating PDF-specific fix loops.
