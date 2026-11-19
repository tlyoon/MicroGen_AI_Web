# PR550 — Native Dell-115 limited-user scheduled continuation for v7.1 source-only work

**Date:** 19 November 2026. **Host:** Dell-115 only. **Parent:** PR549 exact source SHA `6fa60d09db10ac57e25f5a00c4b53adae0672178`, draft/unmerged. PR550 is a separate isolated AppData Git worktree.

## Historical failure and design boundary

Across repeated code-development sessions the verified finite v7.1 supervisor correctly dispatches successive source-only and read-only stages, but its exact-HEAD run exits after each finite backlog. Its own result states `persistent_supervisor_installed_and_running_after_exit=false` and `background_continuation_verified=false`. A checkpoint, a CLI example or a promised scheduled reminder is not evidence that Windows will restart this work. The user-supplied v7.1 contract requires a **real, verifiable runner** for cross-session continuity.

The new `selenium_pipeline.windows_v71_scheduled_resume` is a deliberately restricted continuation helper. It **cannot autonomously author, review, merge or publish new source code**. It can only rerun the already installed v7.1 normal CLI on an isolated, clean local Git worktree to pick up previously registered eligible source-only and read-only tasks, CI prerequisites and checkpointed retries. Each new Git HEAD has its own SHA-bound immutable stage receipts.

## Executable production requirements

The installer checks that the active device identifies as Dell-115, the current user is an existing logged-in non-elevated user, the Git repository is an unlinked clean `%LOCALAPPDATA%\MicroGen_PR<digits>_20xxxxxx` worktree and the recovery registry contains the enrolled signature `V71_PERSISTENT_SOURCE_ONLY_RUNNER_NOT_INSTALLED`. Only one known task name `MicroGen_AI_Web_v71_SourceOnly` is permitted. If the task already exists, installation refuses overwriting it; no SYSTEM account or elevated rights and no new credentials. It saves a source-bound .cmd wrapper in the private AppData checkpoint tree and registers a limited-user interactive Windows Task Scheduler trigger every 30 minutes.

At each scheduled run, the source-lock and real enabled Task Scheduler action are rechecked, the actual `selenium_pipeline.windows_historical_stack_batch_plan --supervise-project-v71` CLI is invoked and a fresh bounded JSON receipt is written. Bounded worker timeout 4800 seconds, process locks, 500 KB log cap, max 5000 immutable run receipts and existing fail-closed Windows per-stage supervisor claims apply.

A dedicated `MICROGEN_V71_BACKGROUND_SOURCE_ONLY=1` gate **omits** the browser-owned `original_g2_v1_synthetic_presend_inventory` stage from unattended launches; it remains pending for a future authorized interactive run. The source-only scheduled runner never Sends Gemini prompts, uploads textbook files, calls paid TTS, operates student media or merges PRs. Source-only G2 checkpoint reconciliation and Git/CI board checks are still allowed. A verified Windows schedule is **not** evidence of full project-autonomous coding or of after-logout/background reliability.

## Required verification before installation

Focused and broader regression/fault-injection tests for known host, clean SHA, documented six-stage CLI, no-GUI environment, actual enabled task/action audit, unknown task refusal, false science flag rejection, immutable receipts and restart/no-duplicate dispatch. Commit source, push draft PR550, obtain hosted exact-HEAD CI. Execute a real normal six-stage v7.1 run on the clean PR550 SHA and verify original G2 science remains blocked and 48/48 local regression results. **Only then** install a real Windows user task and trigger it through Task Scheduler to verify an actual new process/receipt and zero provider Sends or duplicate source test dispatch.

If task installation fails due to Windows permission or user-login constraints, record `PERSISTENT_RUNNER_INSTALLATION_BLOCKED` and keep the finite normal CLI functional. Never weaken security or bypass a UAC/login boundary.

## Controls

Use Windows Task Scheduler to inspect or disable `MicroGen_AI_Web_v71_SourceOnly`. To permanently remove it, run a separately authorized Windows task removal command; installation code does not force-replace or auto-delete existing tasks.

**Outstanding boundaries:** Original Serway §1.3 G2 20/85 source-agreed, 65 pending; uncertain source and prior diagnostic Sends are immutable; G3 independent academic/acoustic/video QA, historical semantic review, draft PR stack integration and student publication remain unapproved.
