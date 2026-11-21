# MicroGen_AI_Web v7.1 Phase 2B: live offline continuity daemon

## Scope and source contract

This belongs ONLY to tlyoon/MicroGen_AI_Web, not Bosla or MicroGen_AI.
The source contract is:
https://docs.google.com/document/d/17g84vOa3B0GNRgle294BzpR8HQfe48ev/edit

Entry point:
python -m selenium_pipeline.development_continuity_daemon_v71
--plan ABSOLUTE_PLAN_PATH --state-dir ABSOLUTE_STATE_FOLDER
--repo-root ABSOLUTE_CODE_FOLDER
--poll-seconds 120 --heartbeat-seconds 5

max-cycles 0 (default) keeps the explicitly launched process monitoring
its admitted offline roadmap. The bounded --max-cycles switch supports real
fault-injection, inspection and acceptance runs.

## What is implemented

- Persistent, actual Python process polls and executes verified approved
  offline tasks using the Phase 2A project-wide executor. G2 original
  evidence and lecture-media validation are source-bound; no Gemini Send.
- Independently locked OS process prevents a second daemon from taking
  over the same roadmap, including Windows locking errors at file open,
  first-byte initialization and explicit byte-range acquisition.
- Windows duplicate-owner handling is in the executable no-Send
  development_continuity_recovery_registry_v71.json.
- Parent checkpoint-to-real-worker dispatch, crash/partial-result
  reconciliation, finite retries, no-Send quarantines and cross-workstream
  fanout are inherited from Phase 2A without weakening them.
- Periodic fsynced heartbeat includes exact owner PID, run identity, pinned
  original roadmap SHA, last controller status, cycle count, zero provider
  Sends and false student-publication approval.
- attest_live_daemon verifies FRESH heartbeat AND the actual OS process
  command line (Win32_Process on Windows or /proc on Linux) before
  returning LIVE_OFFLINE_EXECUTOR_ATTESTED. A stale, forged, stopped or
  non-existent PID never counts as an autonomous runner.
- A graceful bounded run records STOPPED and running=false. A killed
  process leaves a stale heartbeat but the OS check reports OFFLINE.
- Restart reuses original state and admits the source-locked worker result
  without launching a second worker.

## Real Dell-115 acceptance, 21 November 2026 MYT

Isolated working checkout:
%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\CONTINUITY_DAEMON_V71_20261121\repo

The real published Serway 8.2 source/G2 review/lecture QA roadmap:
%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\CONTINUITY_EXECUTOR_V71_20261121\real_offline_roadmap_20261121.json

Real run state:
%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\CONTINUITY_EXECUTOR_V71_20261121\real_daemon_state_20261121

A live daemon with PID 11660 was independently attested by the
OS-backed liveness check. The run completed two cycles and FOUR real
offline verification subprocesses: Serway 8.2 SHA, original G2
read-only reconciliation (26/85 independently accepted; 59 pending),
figure/G2/status regression suite, and actual 8.2 lecture completion.
The explicitly unauthorized release task remained HELD. On second
cycle, NO extra worker was dispatched, confirming duplicate prevention.
After normal bounded exit, the heartbeat read STOPPED, running=false;
independent attestation read OFFLINE_OR_UNVERIFIED.

Neither intentionally disabled Windows task was re-enabled:
MicroGen_AI_Web_v71_SourceOnly: Disabled
MicroGen_AI_Web_v71_StatusMonitor: Disabled

No new Windows startup schedule was created. No user lecture, Drive
folder, Gemini provider, TTS WAV, MP4 or student-facing publication
was modified.

## Regression and fault injection

Real subprocess and cross-process checks include:
- Two consecutive daemon cycles, same original worker receipt exactly once.
- Forced kill/restart of live daemon, new owner PID but NO duplicate action.
- Two competing daemons on same roadmap: second fails closed, first owns.
- Windows first-byte lock read/write PermissionError is normalized and
  registered as CONCURRENT_DAEMON_OWNER or CONCURRENT_EXECUTOR_OWNER.
- Intentionally held consent: zero worker Sends, no hidden release.
- Live process, stale PID, forged heartbeat and clean stop must be
  distinguished; no imaginary background executor.
- All Phase 2A crash-before/after-worker, SHA-version admission,
  bounded retry and no-Send/fanout tests remain mandatory.

## Remaining boundaries, not claimed complete

This is an executable persistent MODE when explicitly launched,
NOT an already enabled startup service. Boot/reboot auto-resume
requires a separate authorized launcher/Task Scheduler deployment
and real startup/failure-injection acceptance. Do not turn on the
previously disabled tasks as a shortcut.

The daemon still runs only OFFLINE allowed evidence/QA handlers;
it does NOT author code fixes, merge PRs, fill missing 59 G2
independent review units, resolve historically uncertain Gemini
requests, approve G3 acoustic/video/second-subsection checks, or
authorize student release. These remain separate unresolved project
milestones.

Do not claim unattended global project completion until a real
persistent runner is installed, enabled and observed starting the
next eligible workstream with exact accepted evidence, following
historical failure review, targeted repair, fault injection and
registered normal recovery.
