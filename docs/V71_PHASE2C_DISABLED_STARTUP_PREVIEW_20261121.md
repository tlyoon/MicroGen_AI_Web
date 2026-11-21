# v7.1 Phase 2C — disabled startup preview, not deployment

Source contract: [auto_cont_dev_prompt_v7.1.md](https://docs.google.com/document/d/17g84vOa3B0GNRgle294BzpR8HQfe48ev/edit).

## Scope

Phase 2A already verifies checkpoint-to-next-task dispatch; Phase 2B verifies
an OS-attested daemon while explicitly launched. Phase 2C requires a distinct
Windows logon/startup ownership and reboot-resume acceptance. Because the two
older v7.1 scheduled tasks were intentionally disabled, this change provides
an **approval-gated, disabled preview**, NOT an active startup deployment.

Production CLI:

    python -m selenium_pipeline.windows_development_daemon_startup_preview_v71
      --prepare --repo <clean local checkout>
      --plan <source-bound offline roadmap>
      --state-dir <local checkpoint> --output-dir <preview folder>

The module has **no task install, enable, Create, Change, Run,
schtasks, launch, or shell-execution code path**. It writes only a disabled
Windows Task Scheduler XML preview and a content-SHA-bound attestation under
LOCALAPPDATA. It never modifies scheduled tasks.

## Hard boundaries

- Device must be Dell-115; user must be a named, limited interactive
  principal, not SYSTEM, service-account or highest-privilege.
- Repo must be inside LOCALAPPDATA, Git-clean and committed; the v7.1
  offline daemon must exist. The original v7.1 roadmap is schema-verified;
  source plan, daemon, Python binary, XML and Git commit are SHA-pinned.
- The dedicated startup task name differs from SourceOnly and StatusMonitor.
  Existing task under the dedicated name blocks preview replacement; existing
  other task states remain untouched.
- Preview XML explicitly disables both logon trigger and task; uses
  InteractiveToken, LeastPrivilege, IgnoreNew, bounded restart policy,
  and direct Python module execution with no shell. It never grants Gemini
  Sends, code authoring/merges or student release.
- Registry must be exactly the allowlisted, **preview-only** no-action
  recovery signature, with all mutations, model Sends and publication false.
- Existing preview files are write-once. Any changed XML or attestation
  must be rejected rather than silently replaced. Symlinks and path escape
  are rejected.
- Real Dell-115 Task Scheduler COM validation initially raised an encoding
  switch error when a UTF-8 XML declaration was passed through Unicode
  XmlText. The production preview now strips the declaration ONLY for an
  in-memory NewTask(0).XmlText schema check, verifies the task and trigger
  are both disabled, the principal remains limited/interactive, and leaves
  the UTF-8 source XML unchanged. No task is registered or launched.

## Acceptance boundary

Local tests must cover both Windows and Linux XML generation, explicit
disabled flags, owner identity, quoting, unknown principal, tampered registry,
mutable source, duplicate preview, symlink and child worker restart behavior.

Actual Phase 2C closure still requires **separate approval** to install an
enabled new startup task and perform a bounded logon/reboot test. Its owner
must be OS-attested and must resume the same checkpoint exactly once.
Even a successful Phase 2C would remain an offline verification daemon,
not an autonomous code-writing agent.

## G2/G3 continuity

Original G2 accepted evidence remains 26/85, 59 pending/disputed. No
historically uncertain model sends may be replayed. G3 academic/acoustic/video
and release remain separate acceptance boundaries. The old disabled tasks
must not be re-enabled or altered.
