# PR535: Resolve recurring cumulative Git patch-format warnings safely

**Date:** 18 November 2026 MYT. **Host:** Dell-115 native Windows. **Parent:** PR534 exact `94c5bfc96169126fb0d9b877523f76c14992c14e`.

## Grounded historical incident

The PR534 registered offline historical patch checks completed 949 real historical commits in 48 SHA-bound batches with six historical formatting warnings in batches 14, 23 and 41. These historical commits cannot be rewritten without breaking the reviewed PR dependency chain. The same read-only `git diff --check origin/main..HEAD` on the exact PR534 head exposed **five warnings currently present in the cumulative code patch**:

- Four trailing extra blank lines at EOF: `tests/test_figure83_fraction_spatial_identity.py`, `tests/test_figure83_full_expression_pixel_candidates.py`, `tests/test_figure83_equation_operator_registration.py`, `selenium_pipeline/figure83_source_review_packet.py`.
- One trailing single space on line 2674 of `docs/CONTINUATION_CHECKPOINT_LATEST.md`, where the preserved factual text describes unaccepted Thomas 8.4/8.5/8.6 overlength media.
- The sixth historical finding (contract document Markdown whitespace in batch 41) is not in the current cumulative diff and must remain in the immutable history receipts, not be counted as a current source defect.

This is a recurrent **working HEAD patch hygiene** problem, not scientific analysis, model text transport or current runtime failure. Before touching the originals, PyMuPDF-independent Python AST parsing confirmed the four code files are syntactically valid; the fourth file is UTF-8 BOM and CRLF, which must be preserved.

## Targeted reusable remediation

New `selenium_pipeline.windows_head_whitespace_recovery` has two carefully separate paths:

1. Normal read-only `inspect_head_patch`: verifies exact current Git HEAD and tracked main, calls Git `diff --no-ext-diff --check origin/main..HEAD`, parses concrete warnings, and never modifies the source.
2. Explicit **isolated code-development** recovery `repair_safe_current_source`: only clean native Dell-115 isolated worktree, enabled `CURRENT_HEAD_SAFE_FORMAT_RECOVERY` recovery registry entry, at most 50 exact diagnostics. All edits are prevalidated. It removes ONLY extra blank EOF lines in Python files if the **entire AST (including source locations) is identical**, or exactly one trailing ASCII space in Markdown under `docs/`. Markdown two-space hard linebreaks, source PDFs, arbitrary code whitespace, unknown errors, dirty trees, symlinks, malformed Git provenance and wrong OS are blocked. It never commits or rewrites old history, invokes Gemini/ChatGPT/TTS, renders multimedia or approves publication. If post-edit cumulative worktree Git diff check fails, original source bytes are restored.
3. Existing `windows_release_readiness_board.inspect_release` now requires `current_cumulative_git_patch_format_clean` for engineering technical readiness. It **never invokes the mutating repair**; other science/acoustic/media/release guards are unchanged.
4. Windows Git may legitimately emit an LF-to-CRLF conversion warning on stderr when safely checking modified worktree files. Only that exact notice is allowlisted; unrelated errors still fail closed.

## Testing and acceptance contract

- Native synthetic Windows Git tests cover BOM and CRLF preservation, exact AST identity, single Markdown space, intentional two-space hard-break refusal, unsupported Python code-line trailing spaces, dirty source refusal, disabled/retired registry, source PDF refusal, combined safe + unsafe rollback, and normal clean/no-op cases.
- Full selected Dell-115 historical and release-board regression set: **56/56 PASS**, without model or TTS operations.
- Complete real source repair, next commit, final-head Git diff check, follow-up Windows CI and integrated release-board restart must be demonstrated independently. Historical batch 14/23/41 warnings remain preserved and still require proper historical disposition; no semantic code review has been inferred.

## Live Dell-115 correction and regression evidence

The normal registered safe-repair CLI was executed in the exact isolated PR535 worktree after the mechanism was committed on clean SHA `b3c824b954afb69deb5e23709f6832c3044d68b9`. It found and normalized **exactly five** cumulative patch warnings: four Python extra blank EOF lines (including the UTF-8-BOM CRLF Figure8.3 packet) and one single trailing Markdown space in the historical checkpoint. Repair succeeded with exit 0; `git diff --check origin/main` returned exit 0 immediately afterwards. The four independent Python ASTs, including source-location metadata, matched the original committed versions byte-for-byte in AST representation; `git diff --ignore-all-space --ignore-blank-lines --stat` had no semantic diff. No old commit rewritten, no source PDF/media altered, no Gemini/TTS request or student release.

An initial broad run using the historical minimal isolated worker produced **six OpenCV import errors** in Figure8.3 tests because that interpreter lacks `cv2`; this is the historical pre-existing environment/package limitation, not evidence of edited source failure. Dell-115's already installed Miniconda Python 3.12.9 includes OpenCV, NumPy and PyMuPDF. The directly affected Figure8.3 regression group passed **20/20** under Miniconda; combined source/format/registry/historical/release-board suites passed **76/76**. No dependency install or environment mutation. An added fail-closed test specifically rejects unrelated Git stderr even when Windows LF/CRLF informational notices are permitted.

The real repaired current patch must be committed, GitHub exact-head Windows CI must pass, and the same normal release board must be restarted under that final SHA before declaring the current patch-format engineering boundary closed. Immutable historical six-commit findings remain visible in the PR534 48-batch receipts for provenance. Do not confuse current patch hygiene with completed code-science-media review.
