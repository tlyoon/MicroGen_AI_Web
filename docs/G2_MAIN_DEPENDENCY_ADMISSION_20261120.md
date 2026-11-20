# G2 independent scientific-review source closure on modern main

## Purpose and safe boundary
Old PR562 contains an extensive, verified G2 supervisor with exact Neon/High
model/Thinking requirements and source-aware duplicate-Send quarantine. Modern
main (merged PR569/570) contains stronger source-caption/rasterized-slide
and retroactive image fixes. Cherry-picking the whole old branch would delete
or overwrite these recent repairs, so use an **add-only transitive closure**
plus an explicit, regression-tested shared transport ABI reconciliation.

## Evidence and staged integration (Dell-115, 20 November 2026)
- Parent candidate: original main d7d50e7; rebase onto current main after
  source admission. Source for additional modules and fixtures: PR562
  9c22d7d69463a2d199c5c423b0eb321eecded19f.
- Static AST closure from independent source consensus, queue and supervisor:
  171 production modules, 146 absent from original main. All 146 were copied
  without overwriting main files; source bytes and hashes recorded in
  PHASE2_G2_MIGRATION_20261120/g2_candidate_manifest.json.
- The real source-only queue initially failed read-only reconciliation because
  the historical executable recovery registry JSON was absent; copied its
  exact original JSON and Gemini task-model profiles. This is a data
  dependency, not a model-provider failure.
- Independent original Serway 1.3 review reconciliation then passed:
  **26 independently accepted / 85 utterances, 59 pending or disputed**.
  The operation did not create, upload or submit any Gemini requests.
- Runtime API audit identified seven missing source attributes in the shared
  Gemini model and response-recovery modules, plus missing
  Config.existing_session_only in the vendor Selenium layer.
  The historical G2 transport/model/response/vendor implementations were
  staged with SHA-protected backup of original modern-main files. Repeated
  ABI audit found zero missing attributes; the required owned-session flag
  was present.
- Existing Windows test-package import failure was found in historical
  recovery records, not repaired ad hoc. The historical tests/__init__.py
  and windows_test_helper_import_recovery.py were ported. Required helper
  test fixtures were added via an import graph.
- Two modern-main mock tests failed after stronger new pre-Send model
  checks. Historical PR562 versions of exactly those tests corrected
  selector IDs/labels and modeled registered owned Sends instead of retired
  ensure_mode() calls. Updated historical tests preserve stronger no-duplicate
  safeguards and are included as compatibility regressions.
- Focused original G2/Neon/High tests: **20 passed**.
- Combined current figure v3 / source-PDF / media / Gemini bridge tests:
  **127 passed** (five harmless PyMuPDF deprecation warnings).

## Strict admission restrictions
- This branch is not currently a persistent code-developing executor.
- A successful source agreement count does NOT mean G2 is complete.
- Original uncertain Gemini requests are immutable and must NEVER be replayed.
- No live paid Gemini Send was performed by this migration or testing.
- No existing source-only scheduled task was enabled or modified.
- Independent acoustic G3, video, second-subsection and student release
  remain separate requirements.
- Before merge, rebase onto current main and rerun the G2 source reconciliation,
  the 147 focused + combined tests and hosted CI. Independently check original
  current-main figure-v3 regression and any unexpected test conflicts.
- After merge, normal G2 dispatcher may only issue newly eligible Sends
  after source/model/Thinking/one-shot authorization and exact receipt checks.
  A status monitor is not an autonomous development executor.
