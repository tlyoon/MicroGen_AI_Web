# v7.1 Phase 2C — reconcile a prior native CREATE after Git main moves

## Actual historical boundary

On Dell-115, PR #580 created a source-pinned **new** offline logon
task from main a03413f. Windows normalized the display principal,
causing a post-CREATE readback rejection. No duplicate CREATE was
attempted. The new task was Disabled pending recovery; SourceOnly and
StatusMonitor stayed Disabled.

PR #581 corrected principal attribution using the current Windows
identity SID and added a no-create --reconcile-existing path. Merged main
then advanced to 0038313. The original disabled preview deliberately
remained pinned to the old, source-verifiable a03413f and the prior
staged native XML bytes were unchanged.

An actual no-mutation --reconcile-existing trial failed closed on
"Disabled preview must match the exact admitted source and roadmap",
because recovery had no way to prove the prior Git version was a genuine
ancestor of current main. Recreating the native task would duplicate a
verified external CREATE and is prohibited.

## Executable targeted resolution

- The normal security preflight now calls _preview_git_admission.
- For **normal installation** (must_be_absent) ONLY an exact current
  merged-main SHA passes. Source Git ancestry never permits a new task
  CREATE.
- For **existing task reconciliation** (must_be_disabled) a previously
  accepted source SHA may differ from current main ONLY if:
    1. Both hashes are valid full Git SHAs, and
       git merge-base --is-ancestor prior_sha current_main_sha succeeds.
    2. The current Git source is clean and matches the actual remote main.
    3. The old pinned disabled preview manifest is intact and its
       source plan SHA, daemon SHA, Python SHA, XML SHA all match actual
       current bytes; mismatches fail closed.
    4. The original staged enabled native XML remains byte-identical.
    5. The previously registered **same** task is still Disabled,
       exact action and arguments match, current OS identity SID matches
       native principal SID, privileges remain Limited+Interactive,
       original two tasks remain Disabled and no competing daemon runs.
- The explicit recovery registry entry
  partial_create_ancestor_admission permits ONLY Git ancestor admission
  under the no-repeat-CREATE context. The installer registry explicitly
  sets may_repeat_task_creation_after_unknown=false.
- An audit-only reconciliation records both historical preview SHA and
  current Git SHA with no mutation. On authorized --activate, the normal
  controller enables ONLY the exact previously-created task and saves a
  write-once receipt with git_sha=current main,
  registered_from_git_sha=older attested ancestor. No TASK_CREATE/UPDATE
  occurs, and a forged/unknown source cannot be admitted.
- A separate source-bound --start verifies this new receipt and Windows
  task native state/owner against the exact current Git/roadmap/Python.

## Portable regression and fault injection

Actual isolated local Git repositories prove ancestor acceptance only in
must_be_disabled reconciliation mode, rejecting normal installation,
reverse ancestry, divergent branch ancestry, nonexistent hashes, path
injection, malformed SHA and tampered executable recovery registry.
Synthetic native tests prove partial-create SID reconciliation never
calls RegisterTaskDefinition and refuses changed XML/owner/task.

Full regression on Dell and hosted Windows/Linux/offline checks must pass
before merge. After merge, repeat the **real** previously-blocked
read-only reconciliation, then activate and start. Do not reboot Dell
while independent Moodle automations are running.

This is a task provenance/race recovery; it does not approve G2/G3, any
uncertain Gemini retry, student release or a fully self-authoring AI agent.
