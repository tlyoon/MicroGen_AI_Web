# Main-branch Phase 1: status watchdog and G2 admission boundary

## Verified, 20 Nov 2026 MYT (Dell-115)

- Main baseline: d7d50e7ec19da22bf3e1df2dc7e61c540e31b584 (PR569).
- All three dirty files in G:\My Drive\Projects\MicroGen_AI_Web were
  snapshotted, checksummed and preserved in a separate checkpoint directory.
  The production checkout was not reset, overwritten, or switched.
- The old PR563 status/watchdog code was ported without importing the
  unrelated historical G2 branch's broad recovery registry.
- The watchdog now uses an exact allowlisted executable status-only recovery
  registry. Disabled/altered registry entries and unsafe handler names fail
  closed. It never performs model Sends, source-task restarts, PR merges or
  student publication.
- If the original G2 academic-reconciliation module is absent, the monitor
  displays G2_EVIDENCE_UNVERIFIABLE instead of crashing or inventing an
  acceptance count. Historical 26/85 is NOT proof of today's reconciled G2
  status.
- Real native Windows check: source-only task DISABLED; status-monitor task
  DISABLED; persistent full-development worker NOT VERIFIED. Both native
  tasks were left as found. The watchdog generated a local status and wrote
  the status mirror on Google Drive, without claiming cloud sync.
- The project status evaluator/monitor, fail-closed registry and native task
  safety suite passed 24 tests; one non-applicable platform test skipped.

## Critical next boundary: G2 reviewer migration

The original G2 review code lives in long-standing unmerged, stacked
branches, most recently PR562. A deterministic import-graph audit against
current main identified 171 transitive modules for G2 consensus/supervisor,
including **146 missing Python modules**. The historical branch also deletes
or changes current main's verified source-figure recovery files. Therefore
merging PR562/563 wholesale is NOT a safe solution.

Needed Phase 2 sequence:
1. Create a separate, clean PR562 admission worktree, pinned to source SHA.
2. Build and test the transitive dependency closure and its data/config
   files; perform explicit compatibility review for overlapping main files.
3. Preserve original G2 source, uncertain Gemini requests, exact model/
   effort proof and independent consensus receipts. No replay or new Gemini
   Send during migration tests.
4. Apply the historical recovery -> repair -> real test -> fault injection
   -> executable registry -> normal supervisor restart sequence.
5. Resume only independently evidenced eligible G2 source reviews, not G3
   or student release; maintain finite retries and approved paid usage.
6. Publish verified new code through PR/CI; until admission succeeds, the
   project status remains BLOCKED, not RUNNING or COMPLETE.

## User authorization preserved

The source-only scheduled task was intentionally disabled and must NOT be
automatically re-enabled by any migration/monitor operation. The status
monitor also remained disabled on the inspected Dell-115 machine.

No G2/Sci/Acoustic/Video/Release acceptance is implied by this change.
