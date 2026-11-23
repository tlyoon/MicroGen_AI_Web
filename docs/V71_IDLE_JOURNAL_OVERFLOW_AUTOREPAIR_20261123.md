# v7.1 persistent development daemon journal overflow: verified recovery

**23 November 2026**, MicroGen_AI_Web, Dell-115. Scope: offline-only
autonomous development continuity; NOT a model/provider transport change.

## Real root cause and historical context

The authorized Windows Scheduled Task
`MicroGen_AI_Web_v71_OfflineDevelopment` previously owned a true
offline-only v7.1 daemon, but stopped after 433 daemon cycles. A new scheduled
restart exited with Windows LastTaskResult=1. Running the exact original
command once reproduced:

`ValueError: Unbounded JSON input`

The real state.json contained **240,137 bytes, 946 serialized events**.
The historical read guard is **240,000 bytes**. Of the 946 events, 928 were
`execution_checkpoint` observations; 18 were materially meaningful
admission, worker ownership, completion, or authorization events.
Repeated blocked-state polling had appended the same idle event for hours,
until the daemon could no longer read its own state.

No permission, API credit, Selenium login or release issue caused this
failure. The existing code correctly refused an oversized file, but failed
to compact its own allowed repeated event journal before the refusal.

## Integrated executable repair

The new `development_continuity_journal_recovery_v71.py` is registered in
`recovery_registry_v1.json` and activated by the NORMAL daemon
`development_continuity_daemon_v71.py` **before each executor cycle**.

The exact steps are:
1. Obtain the existing same OS-exclusive executor byte lock. Verify the
   immutable original plan SHA, original executor SHA, task identities,
   task state, ordered event sequence and JSON size bound.
2. If size reaches 180,000 bytes (below the 240,000-byte original read
   guard), preserve the **complete original state.json bytes** in an
   SHA-addressed, write-once journal archive. Publish its final filename
   only after writing, flushing and fsyncing a temporary file.
3. Remove **only identical, adjacent `execution_checkpoint` idle events**.
   Every actual task claim, worker start, recovery decision, result, source
   identity and authorization gate remains in the active state. Local
   compacted event sequence is renumbered; full original sequence remains
   in the immutable archived JSON.
4. Record original SHA and original event count in the compact state,
   atomically replace the checkpoint, and independently read it back.
   Every future poll validates the prior historical archive link, even if
   the archive directory was removed.
5. On any SHA mismatch, unsafe link, invalid task identity, archive
   conflict, record corruption, absence of redundant idle events, or
   out-of-bound state, fail closed. Never replay previous worker results,
   provider Sends, or change publication rights.

**Crucially, the old `development_continuity_executor_v71.py` is not
modified**. Its exact SHA is pinned inside all original live checkpoint
records and child receipts. Consequently this repair does not break
historical executor admission merely by changing the normal daemon.
The offline-only nature, paid Gemini API prohibition, and no student
publication restriction remain unchanged.

## Actual failed Dell-115 journal test

A byte-identical isolated copy of the REAL failed journal was repaired,
with the original production journal left untouched during testing.

- Original source bytes: 240,137; historical events: 946.
- SHA of original entire journal:
  `eb7a936736aa51bd3226fc4db16d775871a40032cc8a5a07fac48e63e13baebc`.
- New active state size: **6,224 bytes**, with **20** events.
- Removed **926** duplicate idle polling events. All original bytes remain
  in the SHA archive.
- Exact original task states, 27/85 G2 accepted evidence, 58 pending G2,
  authorization gate and source/review hashes were unchanged.
- Calling original offline executor on the compact state returned
  `BLOCKED_OR_AWAITING_EVIDENCE`, without new child dispatches,
  request replays, paid provider calls or student release.

Fault injection covers failure during immutable archival commit, failure
after archive creation before atomic state replacement, tampered or absent
archive, source SHA mutation, executor SHA change, record sequence
corruption, concurrency protection, no redundant event storm, idempotent
restart and normal multi-cycle daemon integration.

## Explicit residual boundaries

This repair restores the **offline-only development supervisor**.
The separate G3 Selenium source-review campaign still correctly has two
uncertain original browser requests (§8.2 slide 6 and §8.3 slide 4) and
must never replay them without evidence of genuinely new task identities.
Chapter 11 independently observed PDF parser/structural receipt
disagreement remains a separate unresolved source-integrity issue.
Neither scientific nor acoustic/video acceptance is conferred.

Do not tamper with original source.pdf, slides.pdf, script.txt, WAV, MP4,
Google Drive files, or prior model captures to solve a journal issue.
