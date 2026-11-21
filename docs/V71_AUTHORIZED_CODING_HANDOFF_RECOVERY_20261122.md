# MicroGen_AI_Web: Codex-independent authorized code patch recovery (v7.1)

This is the executable recovery for a **Codex-specific effective read-only
host sandbox**. It does **not** bypass or remove Codex host policy. The original
source-pinned policy denial at
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\microgen_coding_cli_policy_block_v71.json`
is retained and prevents further unsafe Codex model retries.

## Separation of responsibility

- The **always-on continuity daemon** stays read-only, verifying immutable
  independent roadmaps. Its `code_authoring_executor=false` is accurate.
- An **authorized connected coding session** (for example, the current
  authenticated remote-computer control session) may author replacement source
  blobs. It must never infer authorization merely from a model response.
- The **sidecar** `selenium_pipeline.development_authorized_patch_handoff_v71`
  validates an immutable, authorized manifest and payload digests, makes an
  atomic source edit in an **isolated feature worktree**, and performs explicit
  mandatory regression tests. It does not launch a model, make paid calls,
  push, merge, or release lecture materials.
- The sidecar's separate registry signature is
  `HOST_READONLY_USE_AUTHORIZED_ATOMIC_CODE_HANDOFF`. An absent/disabled
  registry or inconsistent source state prevents all writes.
- Publishing a PR and updating a production machine remain separately
  gated by the project-level GitHub CI and checkpoint-preserving deployment.
  The user's historical Codex denial is **not** cleared by this workflow.

## Input contract

The connected coding session supplies a JSON manifest **outside** the repo:

```json
{
  "schema_version": 1,
  "project": "MicroGen_AI_Web",
  "job_id": "specific_repair_20261122",
  "base_sha": "<40-character current Git HEAD>",
  "branch": "feature/repair-unique-job",
  "authorized": true,
  "source": "trusted_connected_coding_session",
  "files": [
    {
      "path": "tests/test_some_verified_fix.py",
      "old_sha256": null,
      "new_sha256": "<64-character SHA256 of UTF-8 source bytes>"
    }
  ],
  "tests": ["tests/test_some_verified_fix.py"]
}
```

For each entry, create the payload file named
`<new_sha256>.blob` in a separate local payload directory. For existing
files, `old_sha256` must be the exact current source SHA256. Source paths
must be within `selenium_pipeline/`, `tests/`, or `docs/`. Protected
Codex-security and paid-API policy files are not writable via the sidecar.

Example explicit invocation by a trusted connected coding session:

```powershell
python -m selenium_pipeline.development_authorized_patch_handoff_v71 --run `
  --job "C:\local-checkpoints\candidate\manifest.json" `
  --payload-dir "C:\local-checkpoints\candidate\payload" `
  --repo "C:\local-checkpoints\candidate\isolated-feature-repo" `
  --state-dir "C:\local-checkpoints\candidate\run-state"
```

The worktree must be clean, on the declared feature branch, and have the
declared HEAD. The sidecar first persists an immutable claim, then writes
only allowed files using atomic replace, verifies exact final content digests
and Git status, runs pytest with a deadline, and persists test results.
A crash after one file is recoverable from exact old/new SHA256 identities.
An altered manifest, foreign source edit or failed test fails closed;
a failed-test candidate is quarantined, not automatically replayed.

## Important limits and independent scientific work

This worker is a **code-change execution and recovery path**, not itself
an autonomous coding LLM. Full unattended model authoring requires an
independently authorized working model transport; the denied Codex CLI must
not be circumvented by disabling its host sandbox.

G2 original scientific reviews remain controlled by their own source-backed
Selenium claim and provider receipt history. Uncertain model sends cannot
be replayed to improve acceptance counts. G3 requires independent acoustic
and decoded-video QA plus a separate eligible subsection. Completing this
code handoff does not imply G2/G3 acceptance or student release.
