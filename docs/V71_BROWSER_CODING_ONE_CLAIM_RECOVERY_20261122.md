# v7.1 Selenium browser coding model: independently authorized, one claim

This bounded coding model transport recovers code-generation development
without bypassing Codex's **actual host-enforced read-only** policy. The
existing Codex provider-denial file is not modified, cleared or ignored by
the old Codex worker. The always-on continuity daemon remains read-only.

## Boundaries and permissions

1. An authorized development job identifies the original Git HEAD, isolated
   feature branch, existing exact source path and SHA256, a new test target,
   an explicit task, model family (`hydrogen` or `neon`) and a finite wait.
   There is no arbitrary prompt, target, Git publication or unrestricted
   program authoring. The approved initial profile is **pure read-only tests
   of the historical `is_host_readonly` classifier only**.
2. `--preflight` verifies authenticated existing Chrome, selected owned
   Gemini model and its Medium or non-downgrading Thinking level **without
   a Send**. A family/model mismatch blocks the claim; none is inferred to
   be equivalent to the obsolete Flash default.
3. `--run` writes a source/job-bound `SEND_CLAIMED_UNCERTAIN` checkpoint
   **before** interacting with Gemini. It uses existing Selenium and its
   single-registered-Send mechanism; never Gemini's Developer API or local
   models. One click and registration are required; a click alone is not
   acceptance. Any possible Send with no saved reply is not replayable.
4. Save the original untrusted browser response and SHA256, with a matching
   receipt. A received reply is **not executable authority**. A strict AST
   allowlist restricts output to the pinned import and two–six side-effect-
   free functions asserting only `is_host_readonly` on constant strings.
   No arbitrary library, file I/O, attribute access, shell, network,
   environment or data-processing expression may enter from the model.
5. The previously registered `development_authorized_patch_handoff_v71`
   verifies source SHA256, immutable browser receipt, exact model-response
   SHA256 and content-addressed new-file blob *before any file write*. It
   applies only to a clean isolated feature worktree with the right HEAD
   and runs real pytest before marking candidate verified.
6. `--reconcile` may use the same already-saved original model reply with
   **zero new Sends**, even after a parser rejection. A registered narrowly
   defined repair strips the literal Gemini UI header `Gemini said` and
   inserts four spaces only before bare `assert` lines inside recognized
   `test_...` definitions. It cannot translate arbitrary prose into Python.
   Invalid AST or test failure remains quarantined.

## Real Dell-115 failure/recovery evidence, 22 November 2026

- First legacy Flash coding job: live model menu offered Carbon, Hydrogen
  and Neon, not Flash; failed **before** sending; no retry.
- Separate Hydrogen attempt: owned browser turn was registered, but Windows
  CP1252 output raised `UnicodeEncodeError` during a subsequent progress
  log; the original request remains uncertain, **not replayed**.
- A third distinct authorized Hydrogen/Medium task: one genuine Selenium
  Send registered. Its original answer was saved, but Gemini's plain-text
  response had a `Gemini said` heading and flattened `assert` indentation.
  The original source was preserved and initially rejected rather than
  executed. The registered, purely offline normalization reconciled this
  **same** response and produced `tests/test_browser_unseen_codex_edge_20261122.py`
  (three test functions), SHA256
  `679c71c28aee5ab2bcc9ee346d5af030ee49d09f2f0b38c72155164857cb3390`.
  Actual Git worktree + pytest passed, checkpoint
  `CODE_CANDIDATE_VERIFIED`, model requests=1, paid API requests=0,
  Codex host-policy denial cleared=false, no automated PR push/release.
- Fixes are baked into the executable registry: registered one-Send
  Selenium coding transport, Windows-safe browser logger that escapes
  nonencodable characters, original-reply UI/indent recovery, and a bounded
  128 KiB registry byte cap (while retaining all 200-entry and schema gates).

## Example explicit commands (only for new authorized, SHA-pinned jobs)

```powershell
python -m selenium_pipeline.development_browser_code_transport_v71 --preflight --job C:\verified\job.json --repo C:\verified\worktree
python -m selenium_pipeline.development_browser_code_transport_v71 --run --job C:\verified\job.json --repo C:\verified\worktree --state-dir C:\verified\claim
# For an already saved original response only:
python -m selenium_pipeline.development_browser_code_transport_v71 --reconcile --job C:\verified\job.json --repo C:\verified\worktree --state-dir C:\verified\claim
```

No broad autonomous coding agent, arbitrary multi-file edits, paid scientific
model requests, G2 academic-review acceptance or G3 independent acoustic/video
acceptance is implied. Those gates remain separate and require their own
source-bound evidence. Prior uncertain academic sends are never replayed.
