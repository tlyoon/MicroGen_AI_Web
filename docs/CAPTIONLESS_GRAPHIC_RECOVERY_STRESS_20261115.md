# Captionless graphic recurrence stress — 15 November 2026

Workstream: MicroGen_AI_Web, isolated Dell-115 Windows worktree based on PR529 development commit 53dce13. Original shared Drive checkout and source PDF artifacts were not edited.

## Defect discovered

The ordinary vendor figure worker already calls the source-only, immutable-evidence `figure_uncaptioned_source_recovery.recover_source_uncaptioned_crop` after an exact `MAPPING_REVIEW_REQUIRED` refusal, with no second provider Send. However the separate historical failed-trial salvage path in `figures_failed_source_only_resume.recover` wrote three evidence filenames using literal `page_6_` instead of the detected `page_number`. This was a genuine cross-page generalization defect; it was not an observed live failed recovery on another page.

## Correction

Replace all three hard-coded page-six filenames with page-number-specific f-strings: original refusal, raw reply, and source-only evidence. Keep all original source SHA, uncaptioned label, geometric single-crop, provenance, no-Send and fail-closed gates. This makes failed-trial artifact naming consistent with independently detected PDF page numbers.

New `tests/test_captionless_crosspage_stress.py` checks page-agnostic filename contracts and runs source-only recovery against synthetic selectable-text PDFs with unique captionless crops on pages 1, 7 and 12. It rejects changed crop bytes after source binding, asserts zero model Sends and no student publication permission. Full multi-trial historic salvage remains a separate real-source integration requirement; the filename contract test does not pretend to execute that complete path.

## Actual Windows results

- Initial 2-module ordinary-worker recovery regression: 25 passed.
- Expanded 6-module local figure/crop/checkpoint regression: 55 passed, zero failed.
- Repeated focused regression five times in fresh pytest processes: 12 passed per round, 60 passed total, zero failed.
- Python compilation and `git diff --check`: passed.
- No real Gemini Send, paid TTS, source overwrite, figure semantics acceptance, audio/video generation or publication.
- CI workflow already runs `pytest -q tests selenium_pipeline/tests`, so it discovers the new test module without modifying workflow configuration.

## Status and next acceptance boundary

Scoped engineering regression PASS for captionless recovery and cross-page file identity; real historical failed-trial-to-next-stage reuse, genuine original source crop pixel equivalence, source diagram semantics and complete G2 lecture are **not** established by this test. Confirm hosted exact-commit Windows CI after pushing/PR; do not treat a local passing test as merged production release. The normal inline worker recovery is automatic when the strict source-only conditions hold, but a separate failed-trial recovery is not proven to be automatically scheduled by this evidence.
