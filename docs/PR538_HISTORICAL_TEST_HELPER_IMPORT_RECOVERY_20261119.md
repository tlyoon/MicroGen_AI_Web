# PR538 — Automatic package-safe historical test helper imports

**Date / machine:** 19 November 2026, authorized Dell-115 native Windows. **Base:** draft PR537 exact `cca0534ab16afd1e9998a63e91d152e37333bd55`. No merge or student publication.

## Historical failure review

The current SHA-bound history planner enumerates 48 batches (955 commits at PR537), with early batches 1–6 covering original video synchronization, independent source/acoustic review, paid Gemini model/TTS/API authorization, recovery and provider fallback. Focused real Dell-115 code-regression checks found:

- Batch 1: 68/68 source-oriented no-network regression tests passed.
- Batch 2: initial `python -m unittest tests.test_reviewed_element_tts_handoff` failed because its fixture imports `test_element_plan_autodraft` without `tests.` prefix. With `PYTHONPATH=tests`, all 106 Batch 2 tests passed (one intentional skip). Provider speech calls in the fixture are explicit test doubles.
- Batches 4–6: repeated same **test harness import-path** error at `tests.test_tts_fallback_downstream_provenance` importing unqualified `test_tts_qa_promotion`. Explicit correct tests path yielded 93/93 no-network tests PASS. The historical policy switched from fixed-Lite only to strictly conditional whole-batch fallback; current `tts_billing_guard` correctly distinguishes standing routine Gemini authorization from separately authorized experiments and tightly conditioned Cloud escalation.
- An AST inventory of the *actual* current `tests` tree found **516 test files and 67 unqualified sibling test imports targeting 19 local fixture modules**. This is a recurrent harness/discovery portability defect, not evidence that the original media/scientific output passed or failed. Editing all 67 references individually would produce widespread needless churn.

## Source-verified reusable normal-path remedy

A small new *test-only* module `selenium_pipeline/windows_test_helper_import_recovery.py` implements `bootstrap`, called automatically by the existing local `tests/__init__.py` for any normal package-style test invocation:
- requires a registry-enabled `HISTORICAL_TEST_HELPER_IMPORT_RECOVERY` mechanism with exact code-reviewed handler;
- verifies the exact local repository's `tests/__init__.py` path, bounds the AST source scan (up to 1000 test files, 3 MB/file, 1000 unqualified references), resolves all local unqualified sibling imports only to existing non-symlinked `test_*.py` files and refuses unsupported missing references;
- adds exactly one verified source test directory path to the Python test-process import path, which makes bare legacy imports stable under package import and discovery. Does **not** mutate files, source PDFs, browser sessions, process billing, TTS, media or publish;
- rejects retired/missing registry, fake package paths, missing/broken local fixture imports, linked test source and malformed AST. The project already protects against external installed `tests` package shadowing; this mechanism extends that existing protection, not a new arbitrary importer.

Normal .github/workflows/microgen-reliability-tests.yml enrolls `tests.test_windows_test_helper_import_recovery` so regressions recur visibly in real Windows CI. The full historical G2/G3 semantic/scientific/audio/media acceptance remains independent.

## Stress and regression evidence

Dell-115 native original repo's 516/67/19 inventory source-verified. A **separate fresh Python process** without injected `PYTHONPATH=tests` can now import affected test modules using package names, no model/API call. Synthetic source fixtures verify unresolved sibling imports cannot silently pass, fake external tests package is refused, retired registry fails closed, repeated bootstrap is idempotent and no authorization/release is issued. Windows user inability to create symlinks is represented as an explicit skipped symlink case rather than a fake pass. Both existing Dell Miniconda and two separate isolated minimal Python environments exercised with no new package installs. Combined test-only recovery, existing source-format repair, registry, historical disposition, release board and the two previously failing source fixture modules passed **78/78 tests** (one Windows symlink-permission skip). Package-style invocation had no manual PYTHONPATH override. Git diff check exited 0.

Exact commit, final hosted CI and normal pipeline restart must be checked before closing this narrowly scoped test-discovery boundary. This is **test harness portability only**, not a complete semantic review of all 48 historical batches, not G2/G3 academic or media acceptance and not authorization to merge or publish.
