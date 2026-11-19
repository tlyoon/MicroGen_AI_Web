# PR537 — Crash-safe, restartable source-format repair journal

**Project:** MicroGen_AI_Web, Dell-115 only. **Parent:** draft PR536, SHA `d2ad6ad1127a16f321d8d522ceb70971ed713eea`. No automatic Git merge, paid provider/TTS operations, original textbook/media modification, or student publication.

## Historical problem, prior remedies and remaining gap

PR534 created immutable per-batch Git history receipts and automatic advance. PR535 introduced registered `CURRENT_HEAD_SAFE_FORMAT_RECOVERY` for current cumulative Git whitespace defects, preserving Python AST and Markdown intentional hard-breaks, with ordinary `try/except` rollback. PR536 classified source-grounded historic warnings and retained original quarantines. But the live PR535 source-repair implementation previously used sequential `Path.write_bytes` on multiple files. If the process terminated after the first file and before the second, Python exception handlers would never execute. A subsequent run would see a dirty checkout, refuse repair, and require manual intervention. That is a genuine automatic-recovery architectural gap, not a scientific/media acceptance defect.

Existing `g2_forward_recovery_engine` already records write-ahead intent and results; existing `three_pc_worker.LocalInstanceLock` releases the exclusive lease on termination. This PR reuses those patterns for the narrowly scoped developer-only safe-format repair.

## Executable repair contract

1. `windows_head_whitespace_recovery.repair_safe_current_source` still requires the installed/active `CURRENT_HEAD_SAFE_FORMAT_RECOVERY` registry entry and safe isolated native Dell-115 checkout. A process-scoped lock serializes concurrent same-repo attempts.
2. BEFORE touching a source file, the new `windows_head_format_repair_journal` writes a size-bounded source-HEAD-locked, repository-locked, checker-source-sha-locked **immutable intent**, including exact original and accepted replacement source bytes, SHA-256s and original Git diagnostic inventory, outside the Git/publisher tree.
3. The replacement file is written and fsynced to a separate file in LOCALAPPDATA on the same Windows volume and atomically installed with `os.replace`. Only a known before/after byte state may be resumed.
4. If the process terminates between replacements, the next normal invocation consults the journal **before** the default clean-checkout refusal. It accepts only original or planned replacement file bytes, no staged files, no unrelated dirty/untracked files, matching HEAD/source module and registry, then applies remaining changes. Completed repairs are verified against an immutable result receipt and cannot be silently replayed after further edits.
5. Original Git diagnostics must still be exactly reproduced; Python AST and Markdown single-space conditions are reverified by the original normalizer. Final cumulative Git patch must pass; no Python AST, original content, paid request, scientific/QA approval or release gate may be bypassed. Missing, retired, linked, tampered, stale, oversized or contradictory journal evidence stops rather than inventing recovery.

The release-readiness board still invokes ONLY the read-only `inspect_head_patch`, not the mutating journal-backed developer repair. The existing active recovery registry entry is updated with write-ahead and finite-source constraints.

## Actual test evidence

Native Dell-115 real-Git synthetic tests include Python UTF-8 BOM/CRLF preservation, Markdown line breaks, normal source repair, interrupted after first of two replacements, exact restored byte identity, duplicate restart, journal tampering, missing Git base, staged/unrelated dirty checkout, and completed-result alteration. A **separate child Python process was forcibly exited with `os._exit(87)` after actually installing the first source file**. The following independent process recovered the immutable intent, installed the second exact source byte sequence, verified cumulative Git patch and preserved the original HEAD. The test passed on Dell-115, with zero model/TTS/media operations.

The combined Dell-115 source-format crash tests, historical-format disposition, historical batch planner and executor, release-readiness board, and registry suites passed **75/75 native tests**; cumulative local Git diff check exit 0. This includes genuine separate-process death, same-source restart and repeat-idempotence, and foreign-dirt/tampered-journal fail-closed cases. Exact final-head hosted Windows CI and normal release-board restart remain required before this engineering boundary is accepted. The full 951+ historical semantic PR review, G2/G3 source/science/acoustic/media verification and publication permission remain open.
