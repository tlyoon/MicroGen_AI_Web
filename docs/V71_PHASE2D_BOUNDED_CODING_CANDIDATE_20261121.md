# Phase 2D1 — bounded source-only coding candidate; no automatic merge

## Contract and distinction

The governing auto_cont_dev_prompt_v7.1.md requires a complete
historical-failure-review -> targeted repair -> real test -> fault injection
-> executable recovery -> restart -> next eligible action contract.

Phase 2C has a live Dell-115, limited-user **offline verification daemon**
and passed real process interruption/restart. That daemon must NOT silently
gain code-writing, GitHub PR, model Send or student-release authorization.

This Phase 2D1 executable is a **separate on-demand coding candidate**.
It must run in a clean isolated branch under LOCALAPPDATA, pinned to the
exact GitHub main source SHA and immutable job manifest. It never modifies
the production runner checkout and has no scheduled Windows task.

## Job admission

A single JSON job supplies explicit task ID, clean source SHA and feature
branch, bounded natural-language instruction, 1–12 exact allowlisted source
files, 1–12 existing exact Python regression test modules, explicit
authorization, a pinned Codex CLI SHA, and a 30–1200 second time limit.
Untrusted fields, release files, shell parameters, path escape/symlinks,
wrong source revision or a dirty first-run branch fail closed.

The real Dell CLI is pinned to current-user APPDATA/npm/codex.cmd. Invoke
Codex only in workspace-write sandbox, ephemeral mode, with user config
ignored, no model-generated shell network access, and a strong no-provider,
no-credential, no-Git-push, no-student-publishing guard in the prompt.
Host code invokes exactly one fixed CLI command without shell interpolation.

An immutable durable coding_job_state.json is written with
EXTERNAL_MODEL_RESULT_UNCERTAIN **before** any Codex model invocation.
If the CLI times out/exits abnormally, never replay the possibly consumed
model request. Fail closed, preserve claim and select independent work.
Only a successful, attributable response advances to
MODEL_RESPONDED_UNVERIFIED, which may be revalidated after restart with
**zero further model calls**.

The exact modified files must be nonempty, only allowlisted relative source
files, regular non-linked files, and Git diff --check clean. Mandatory
specified local pytest modules must pass. A verified candidate retains
hashes, tests, exact main source and job identities in a durable receipt.
**No git push, PR creation, merge, release, scheduling or provider upload
is performed by this executable.** Any subsequent PR admission/CI/merge
requires a separately tested boundary and independent acceptance. Model
output never serves as proof of scientific/acoustic correctness.

## Tests and fault injection

Local fault-injection tests use a simulated Codex worker, not a paid
model call, and cover:
- Original clean branch/source/job admission and exactly one bounded
  workspace-write CLI request with network-off command setting.
- Duplicate invocation returns same accepted receipt without new model
  Send, and timed-out/possibly consumed requests persist immutable
  uncertainty and cannot be resent.
- Test failure after verified model response can be retested/recovered
  without reissuing the same model request.
- Source modifications outside explicit allowlist and empty changes fail.
- Changed original job, changed Codex CLI bytes, dirty source, path escape,
  unapproved Windows Task Scheduler/release paths, unauthorized job and
  injected arbitrary pytest arguments all fail closed.
- No test falsely claims student publication, G2, G3 or PR acceptance.

## Remaining Phase 2D acceptance

Real bounded Codex execution in a disposable clean branch, source diff
and real pytest validation; independent hosted CI; tested PR staging,
authorization and release boundaries; bounded repair selection from
the global backlog; repeatable cross-session ownership and visible
next-task dispatch. Phase 2D1 alone is not a self-authoring persistent
development system and must never be reported as one.

The original G2 has 26/85 accepted; 59 pending/disputed, including
historically uncertain Gemini Sends that must not be replayed. G3
independent acoustic/video/second-subsection and final release remain open.
