# v7.1 Phase 2C — approved native offline startup admission (Dell-115)

## Contract, authorization and scope

On 21 November 2026, the user expressly authorized native startup
installation on Dell-115 and safe progression to subsequent development
phases. This must not be interpreted as authorization to enable or overwrite
two previously disabled v7.1 tasks, send ambiguous Gemini requests, modify
student-facing lecture content, or approve scientific/acoustic QA.

Previous Phase 2C PR #579 only generated a **disabled** startup preview
and used native Windows Task Scheduler COM XML parsing without installing.
This change adds a separate explicit install and start action with its own
allowlisted recovery registry. The installed task is limited to the exact
read-only offline v7.1 daemon with one owner and bounded restart policy.
No code authoring, arbitrary shell execution, Gemini Sends, or publication.

## Two explicit operations

Run from a clean, isolated checkout of the verified GitHub main commit:

    python -m selenium_pipeline.windows_development_daemon_install_v71 \
      --install --preview-dir <merged SHA-pinned disabled_preview> \
      --repo <merged clean isolated repository> \
      --plan <original source-bound offline roadmap> \
      --state-dir <local execution checkpoint> \
      --output-dir <new write-once native receipt directory>

Only after verifying the new Windows task and its attestation:

    python -m selenium_pipeline.windows_development_daemon_install_v71 \
      --start --state-dir <same checkpoint> \
      --output-dir <same installed receipt directory>

The native installer uses Task Scheduler COM RegisterTaskDefinition
with **TASK_CREATE only**, never CREATE_OR_UPDATE, and only the unique
MicroGen_AI_Web_v71_OfflineDevelopment task name. If a task already
exists, or either SourceOnly or StatusMonitor is not Disabled, fail closed.
The installer verifies account is the current named interactive user,
limited run level, original roadmap SHA, exact Python and daemon source
SHAs, Git HEAD equals remote main, XML SHA, one Exec action, and its
native task readback. Its saved installation receipt is write-once.

The start path separately verifies the installed receipt, repo SHA,
Git cleanliness, original roadmap, interpreter and daemon SHA, disabled
status of the two original tasks, and registered native action, arguments,
principal and logon type. Unknown/drifted/replaced tasks cannot be started
through this installer. No scheduled task can be silently overwritten.

The installed startup task is a **logon trigger**. An OS reboot without
the user's interactive Windows logon is not proof that the daemon ran.
Full Phase 2C requires start, OS-PID/heartbeat check, forced-exit recovery,
restart with same checkpoint and no duplicated child operation, and genuine
logon/reboot verification. The original G2 and G3 gates remain separate.

## Historical failure recovery

The UTF-8 XML declaration to Unicode COM XmlText failure diagnosed during
PR #579 is reused. The original on-disk XML retains UTF-8; only in-memory
COM schema parsing removes that declaration. Never use task-registration
failure as permission to change unrelated tasks or run as SYSTEM.

Tests must inject forged registry, altered startup XML, elevated principal,
duplicate task ownership, already enabled old tasks, corrupted plan,
changed source Git revision, modified Python/daemon bytes, wrong checkpoint
and switched native Windows action. A verified remedy enters the
production installer path and test suite before any installation is claimed.

## Exit and constraints

Registry: windows_development_daemon_install_registry_v71.json.
Safety must be checked against actual Dell native task snapshots and
observed OS PID. No assistant status note substitutes for a real start.
SourceOnly and StatusMonitor must remain disabled. A persistent *offline*
daemon is not a persistent autonomous *code-writing* developer.
