# MicroGen_AI_Web — Persistent Status Monitoring and Watchdog Contract v1.0

**Authority:** Autonomous Continuous Development, Recovery and Forward Progress Contract v7.1 (Google Doc `17g84vOa3B0GNRgle294BzpR8HQfe48ev`). Implemented only on **Dell-115** in PR564. Monitoring is not a replacement for autonomous coding or scientific QA.

## Requirements and independently observable meanings

- `RUNNING`: a current, explicitly authorized **development** worker has an attributable live process, heartbeat and accepted dispatch. The finite v7.1 source-only supervisor must **never** satisfy this.
- `PENDING`: required work remains without a proven live development worker. No completed workstream is inferred merely from a clean local queue.
- `BLOCKED`: native Task Scheduler disabled/unknown, invalid Task Scheduler principal, failed source-only receipts, missing monitor, or unverified G2 evidence.
- `STALLED`: more than 75 minutes since the last native source-only run, or the source-only supervisor left a RUNNING heartbeat older than 75 minutes. This exceeds two 30-minute schedule intervals with grace.
- `COMPLETE`: never inferred from six source-only stages, passing CI, a saved PR, the original two-PDF transport proof, a two-pass subset, or a positive monitoring run. A separate independent full roadmap, scientific G2, G3 acoustic/video/second-subsection, integration and release authority verifier is still needed. Until one is proven and integrated, the watchdog fails closed with `project_complete=false`.

## Execution model

`selenium_pipeline.project_development_status` reads the **real native** Task Scheduler states for `MicroGen_AI_Web_v71_SourceOnly` and `MicroGen_AI_Web_v71_StatusMonitor`, the last native scheduled source-only cycle receipt, source-only supervisor heartbeat and the independently reconciled original Serway source review queue. It records explicit missing authorization or execution capabilities. No Google/Gemini or API provider requests occur.

`windows_v71_project_supervisor` writes advisory atomic source-only phase heartbeats at project scan, worker handoff, and orderly stop. The heartbeat itself does not confer a project RUNNING state or scientific acceptance. Heartbeat failures never weaken QA or restart an uncertain original request.

The dedicated `MicroGen_AI_Web_v71_StatusMonitor` Windows scheduled task runs **every 15 minutes** under the same limited interactive account, independently of the pre-existing source-only 30-minute task. Install through `windows_project_status_monitor_task --repo <verified-clean-worktree> --install`. Installation refuses wrong host, elevated/foreign Task Scheduler principal, unknown task action, modified launcher or dirty/nonisolated repository. Installation does not enable or replace the existing source-only task or configure release/paid model operations.

Reports are atomically persisted to:
- Local: `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\development_status_v1\STATUS.md` and `STATUS.json`
- Google Drive desktop mirror: `G:\My Drive\MicroGen_AI_Web_Development_Status\STATUS.md` and `STATUS.json`
- Status transition receipt: local `ALERT_STATUS_CHANGE.json`, containing old/new states and explicit `notification_delivered=false`.

Copying bytes to Drive for Desktop is not proof that Google Drive cloud synchronization succeeded. Users should see the file in the Drive web UI before treating it as externally available. No email, push notification or GitHub issue alert is claimed or sent by this version. If reliable notification delivery is later added, it must provide a separate independently verifiable delivery receipt.

## Mandatory safety and recovery

Historical causes: the v7.1 source-only task can finish successfully but the whole project stays open; a native task may become Disabled after having been Ready; model changes can strand G2 behind a stale Pro-only path; source test success is not proof of an actual next Gemini scientific request. The executable registry maps `V71_PROJECT_TASK_DISABLED_STALE_OR_HEARTBEAT_MISSING` to read-only native inspection and persistent stall status without unsafe request replay.

No remedy silently reenables a task that another authorized operator may intentionally have disabled during a migration. A disabled task is **BLOCKED**, not **RUNNING**, until verified source/ownership and change provenance allow a safe restoration under the project’s existing migration contract. Other independent work may continue.

Fault injection must test disabled and foreign tasks, missed windows, stale vs idle heartbeats, failed source-only exit codes, false six-stage completion, unverifiable G2, tampered/linked status inputs, atomic Drive output, deduplicated alert receipts and the production heartbeat hook. The monitor must run from the installed native task (not merely a mocked read) before being reported as persistent. Native task success must be checked independently in Windows Task Scheduler.

## After implementation: recommended user workflow

Open the **STATUS.md** file in Google Drive. Check `Observed` to ensure it updates on the expected 15-minute cadence, plus overall status, native scheduled states, blockers, original G2 progress and next action. **RUNNING** needs verified full development-worker evidence, **PENDING** means the project still needs an actual developmental executor/handoff, **BLOCKED/STALLED** needs a registered recovery or different authorized workstream, and **COMPLETE** requires the separate verified project closure evidence. On a stale status file, check Dell-115 Task Scheduler or request a live check: a static file cannot prove ongoing progress.

This iteration establishes visibility and source-only heartbeat evidence. **A separate persistent autonomous development executor is not installed by this watchdog**; installing such a worker must be independently designed, verified and authorized before it can truthfully run tasks beyond the six finite source-only workstreams.
