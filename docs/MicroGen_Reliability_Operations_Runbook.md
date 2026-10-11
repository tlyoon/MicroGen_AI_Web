# MicroGen reliability and multi-PC operations runbook

## Purpose

Use this guide for a new lecture campaign and for interruption recovery. It applies to properly configured, authorized Windows PCs; it does **not** assume a particular username, a Drive root letter, or an already-authenticated session. Existing production lectures must be protected before new work begins.

## Preconditions

1. Clone or update `tlyoon/MicroGen_AI_Web` to a **local** folder on each Windows PC. A shared Drive folder can hold `source.pdf`, published outputs and checkpoints, but is not a safe location for concurrent Python virtual environments.
2. Install the project's documented Python dependencies for the pipeline and TTS. Supply the local executables explicitly via `--pipeline-python` and `--tts-python`; do not guess another PC's paths.
3. Configure MicroGen account settings and keys using its supported local Windows user profile locations (normally `%LOCALAPPDATA%\Microvid\.env`). Never commit credentials or inspect browser cookies/secret tokens.
4. Verify the source root (e.g., `G:\My Drive\Serway\Serway_8_14`) is readable **and writable** on each worker, and contains a genuine `source.pdf` inside every subchapter directory to be processed.
5. Gemini Flash is the default. Confirm the authenticated UI actually displays Flash, and that the user has not explicitly selected a different model. Do not switch to Pro to escape an error.
6. Verify the chapter assignments are disjoint and that no other MicroGen/Calculus job is controlling the same local Gemini browser. The modern pipeline's per-port **local OS lock** prevents updated cooperating runs from sharing a browser, but cannot protect against older external code that ignores the lock.
7. Check the existing source-adjacent output files and completion receipts. Do not infer completion from a worker's `phase=finished`.

## Campaign invariants

- Exactly one active subchapter per PC. The stage order is `figures → slides → narration → script_qa → tts → tts_qa → video`.
- Verify each stage from the same `source.pdf`, its checkpoint source hash, concrete stage output and any associated QC report. An old status flag alone is insufficient.
- A missing, ambiguous or unsafe LaTeX image reference is a hard blocker. The program may stage candidate textbook pages for review but cannot certify a diagram based on its filename alone.
- A changed PDF, narration or WAV set invalidates downstream synchronization. Check the exact page count, figure references, script blocks, audio hashes, QA and MP4 before publication.
- Previously published MP4s without verified completion receipts are **protected**, not treated as blank files or safe to overwrite. Any reviewed re-generation must be explicitly requested.
- Retain source-adjacent numbered narration WAVs and `.history` archives even after completion. Never use Google Drive ticket files as globally atomic worker locks.
- Watchdogs: 900 seconds without stage output, 3,600 seconds maximum per stage. Blocked jobs are deferred; give each at most one second pass in a single campaign.


## Independent verification: the same procedure on every PC

From the current local repository, run a **read-only audit** before and after work:

```powershell
python -m selenium_pipeline.reliability_audit --source-root "G:\My Drive\Serway\Serway_8_14" --expected 46
```

For a new, permanently stored JSON report, pass `--report <new-local-or-shared-file-path>`. Existing reports are never overwritten. The audit exits with code 2 if any lecture is not receipt-verified; this is a status, not an assertion that files were corrupted. Read the categories `verified_complete`, `published_requires_reconciliation`, `partial_slides` and `no_published_slides`. Do not confuse published slides with a finished lecture.

Check each worker's actual PID and the command line of its Python stage subprocess, not only the last-modified checkpoint. The worker status file is informational. A nonmoving console is not sufficient proof of a stall while FFmpeg or an AI request is legitimately working; consult the child logs, silence watchdog and stage timeout.

## Missing graphics: source-grounded diagnosis

A missing `\includegraphics{...}` reference (including an `\IfFileExists`-guarded one) blocks later stages. The package stages source-PDF page previews under `.microgen_work/figure_review_candidates` when it can; it never silently publishes a guessed crop. To request an explicit independent review bundle:

```powershell
python -m selenium_pipeline.figure_recovery_candidates --subchapter-folder "G:\My Drive\Serway\Serway_8_14\12\12.1" --output-dir "C:\Temp\microgen_12_1_figure_review"
```

Review the source page, figure labels, diagram boundaries and content *before* approving a crop. Keep the original PDF, pre-repair slides and old media in `.history`. Rebuild the PDF and review narration against any figure changes; even unchanged page count is not proof of semantic agreement. Re-run TTS and MP4 only when required by the verified dependency change.

## Browser recovery and portability

When the Gemini mode picker disappears in a stale tab, modern MicroGen may open one clean tab and verify Flash without changing the old draft. If authentication is absent or Flash cannot be positively verified, it fails closed. Never extract credentials, bypass sign-in or downgrade to an unapproved model. If a conflicting older MicroGen process is already using Chrome, wait for it to finish; new OS browser locks cannot retroactively make old versions cooperate.

Keep model, audio, figure, slide and video validations in the standard repository. A one-off repair script is evidence of a workaround, **not** a permanently fixed production bug. Any recurring defect must receive a regression test and an explicit code-path correction before it is closed.

## Release acceptance checklist

- [ ] Failure audit lists incident, cause, permanent protection, test, and remaining risk.
- [ ] Full unit/pytest suite passes on an isolated candidate checkout.
- [ ] Fresh clone and dependency checks pass on the supported PC configurations.
- [ ] Authenticated Gemini Flash UI and a controlled generation are tested without changing Pro settings.
- [ ] Deliberate missing-figure, stale-draft, low-fidelity WAV, corrupt receipt, and interrupt/restart cases fail safely.
- [ ] An interrupted campaign resumes only from validated content and cannot create a duplicate worker.
- [ ] Published audio, valid MP4s and `.history` archives survive cleanup.
- [ ] Regression PR is reviewed and merged; the actual GitHub main SHA is verified.
- [ ] Active PCs are only synchronized after a safe checkpoint (never hot-replace code under a worker).

**Limit:** Structural, codec and hash QA do not alone certify physics correctness. Changes to figures, annotations or meaning require academic/semantic review.
