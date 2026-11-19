# PR536 — Source-verified historical Git warning disposition

**Host:** Dell-115 native Windows. **Parent:** draft PR535 exact head `96efb198594c6c75491e4ed279b61137a96d9ad2`. No merge or student publication.

## Historical failure review

PR534 established a restartable offline patch-integrity check for the historical stack; PR535 corrected five formatting defects still present in the cumulative current source patch. The previous summaries conflated six failing historical **commits** with six warning **diagnostics**.

A direct native Dell `git show --no-ext-diff --no-renames --format= --check <exact SHA>` reconstruction of the six quarantined commits shows **eight exact Git diagnostics**:
- Batch 14: four commits (2026-10-21) with one extra end-of-file blank line each in three Figure 8.3 Python test files and the source-review packet. Current cumulative code has normalized each without altering any AST or old commit.
- Batch 23: one commit (2026-10-26) with a single trailing ASCII space in a historical Thomas 8.4–8.6 continuation Markdown line. The present source patch normalized this without changing facts, no media accepted.
- Batch 41: one commit (2026-11-07) with **three separate** trailing-space Git diagnostics in `docs/BINDING_CLOSURE_FIRST_DEVELOPMENT_CONTRACT_20261107.md`. Each diagnostic is a deliberate two-space Markdown hard line break. These are **not defective hardbreaks to remove**; the current cumulative patch is clean because these were already part of the historical source content and no new whitespace was introduced.

The original three quarantined batches remain quarantined in the immutable offline patch-integrity receipts. They must not be silently relabeled as clean historical commits.

## Remedy in executable production review path

`selenium_pipeline.windows_historical_format_disposition` is a **read-only** code-reviewed and registry-backed independent source classification step. It:
- reuses exact-head, source-hashed results from `windows_historical_stack_batch_executor`;
- requires a clean cumulative current Git patch and the enabled `HISTORICAL_SOURCE_FORMAT_DISPOSITION` registry mechanism;
- obtains each quarantined commit's Git warning output and exact SHA-locked Git blob, validates the path and reported source line, counts distinct warnings per commit, compares Python AST with and without extra blank EOF lines, and recognizes intentional Markdown hard breaks only when the actual source has two or more trailing spaces;
- keeps single-space Markdown warnings separate and never labels them intentional;
- writes a size-bounded, exact-source-HEAD and implementation-hash addressed immutable receipt outside the source and teaching assets; restart verifies byte identity, never overwrites conflicts;
- declines unknown Git diagnostic forms, stale/missing blobs, forged source samples, unparseable Python AST, unsupported file paths, dirty or malformed history, disabled registry, or mismatched saved evidence.

The normal `windows_release_readiness_board` exposes this by optional `--classify-historical-format-findings`, which requires both the existing `--include-stack-batches` and `--execute-historical-batch-checks` switches. The normal board remains read-only and blocked for release. No semantic code review, Gemini request, scientific/acoustic/media acceptance, paid API operation, PR merge or student publication is authorized by this classification.

## Evidence and limits

Native Windows synthetic real-Git tests check one intentional Markdown hardbreak, one ordinary trailing-space warning and one AST-invariant Python EOF warning across distinct historical commits; exact source-line verification, cached restart, forged samples, tampered receipts, missing Git source, missing registry, unknown extensions, unparseable Python, current HEAD formatting regression, and no content/publication actions.

Exact real PR536 history run, first + second process restart, combined offline tests, final-head hosted CI and independent release-readiness-board evidence must be attached before closing this bounded historical warning disposition. Historical semantic review of all source changes and independent G2/G3 QA remain separate unresolved boundaries.
