# v7.1 Phase 2C — Native owner-SID recovery for a partially completed startup task

## Actual Dell-115 failure, 21 Nov 2026

PR580 merged SHA a03413f94c04e9ee63cd0184f72572c090a10601.
The first *explicitly authorized* native install executed its Task Scheduler COM
RegisterTaskDefinition(TASK_CREATE), successfully creating the **new and unique**
MicroGen_AI_Web_v71_OfflineDevelopment task as Ready. Both
MicroGen_AI_Web_v71_SourceOnly and MicroGen_AI_Web_v71_StatusMonitor remained
Disabled. No daemon run was requested or observed.

The post-register attestation **failed closed** because the incoming XML
principal was USM\tlyoon but Get-ScheduledTask normalized the displayed
Principal.UserId to "tlyoon". The original caller and native task user both
resolve to the **same Windows security identifier (SID)**
S-1-12-1-3320004299-1286749613-1083153805-460156068.
The original native action and arguments exactly matched the pinned XML;
run level was Limited, logon was Interactive, and logon trigger Enabled.

This is a Windows principal display-name normalization discrepancy, not
permission to reset an external result or issue another CREATE request.

For safety the new offline task was **temporarily Disabled** while reconciling;
both older source-only and monitor tasks remained Disabled and untouched.

## Executable targeted repair

1. The normal Windows task snapshot now resolves each principal's SID via
   Security.Principal.NTAccount.Translate(SecurityIdentifier) instead of
   trusting Get-ScheduledTask display names. The current interactive user's
   SID is also independently read from WindowsIdentity.GetCurrent().User.
   Unknown/unresolved/mismatched SIDs must block admission and startup.
2. Normal --install post-registration attestation and --start verify SID,
   exact task executable/arguments, original plan + Python + daemon SHA,
   Git source SHA, Limited/Interactive, and native trigger state.
3. A separate --reconcile-existing entry point is allowed ONLY when a
   previously-created *same-named* task remains Disabled, with its exact
   staged enabled XML source bytes, matching source-bound SHA manifest,
   matching current SID, exact action and argument string, original two
   tasks Disabled, and no competing live daemon.
4. A no-change read-only reconciliation returns
   EXISTING_NATIVE_CREATE_ATTESTED_REMAINING_DISABLED. With --activate,
   it enables ONLY the same previously-created exact task (no new task
   registration, no overwrite) and independently rechecks Windows native
   attributes; it then persists a write-once native installation receipt.
5. Later --start refuses any changed source, owned task, principal SID,
   command, arguments, roadmap, interpreter or checkpoint directory.
6. If the native task appears unexpectedly enabled, foreign-owned, modified,
   or its previous provider outcome is uncertain, the controller must not
   create, overwrite, reset or start another task. It records the blocker.

## Tests

- Original focused Windows startup/installer suite remains mandatory.
- Synthetic native SID normalization: USM\tlyoon and "tlyoon" resolve to
  the same SID. Positive install/start/reconciliation must pass without
  weakening SID verification.
- Fault injections: mismatched SID, enabled-already task, missing original
  staged XML, malicious arguments, elevated RunLevel, and changed action
  must fail closed with **zero** native registration/enable operations.
- Reconciliation on the real disabled Dell task must first run audit-only
  (no activation); after source admission and CI, activate it and require
  the original Windows SHA/owner proof plus fresh OS PID heartbeat.
- Full repo tests and hosted Windows/Linux/offline CI required before
  merging this recovery into main.

## Release boundary

Even successful source-bound task restart establishes only a persistent
OFFLINE verifier. It does not establish automatic code-authoring/PR merging,
G2 scientific review completion, G3 acoustic/video acceptance, Gemini
resend permission, or authorized student publication.

Actual Dell-115 OS reboot/logon acceptance is withheld while other unrelated
Moodle automation and MicroGen processes are running; a forced OS reboot
could interrupt those operations. Task process restart/checkpoint recovery
can be tested without risking the other jobs.
