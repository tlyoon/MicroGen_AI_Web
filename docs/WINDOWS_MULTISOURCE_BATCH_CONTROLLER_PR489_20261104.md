# PR489 - resumable Windows multi-source status orchestration

General codebase progress, **not** a new Figure 8.3 or Thomas single-PDF
scientific review. This is a native Dell-115 Windows-only release engineering
stage stacked on PR488 and reusing the original immutable PR486/487 evidence.

## Run status and independently resume

Create an *external*, new, non-symlink job directory outside both the
immutable source campaign and all original author/publisher folders.

```powershell
$campaign = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints\20261103_PR486_TWO_REAL_ORIGINAL_SOURCE_IDEMPOTENT_RESTART_V1'
$job = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints\20261104_PR489_WINDOWS_MULTISOURCE_JOBS_V1'
New-Item -ItemType Directory -Path $job -ErrorAction Stop
powershell -NoProfile -ExecutionPolicy Bypass -File .\MicroGen-Windows.ps1 -Mode BatchStatus -Campaign $campaign -JobsDir $job
```

The same command, repeated after interruption, revalidates fast original SHA
and PR487 readiness (without repeating scientific PDF inspections) then
reuses existing byte-exact, canonical, independently persisted per-section job
records. A test-only failure injected immediately after section A leaves A's
record intact, and the next run creates only B's missing record.

Each original section's job ledger pins the canonical immutable PR486 campaign
contract SHA, source fingerprint, PR487 original-ready or blocked status, and
overall immutable payload digest. New media, altered source, changed mapping
receipts or tampering is rejected (nonzero result), not silently accepted.
Independent **blocked source input** is a normal operational state, not a
reason to halt other source status checks. The security rejection is explicitly
distinguished from ordinary mapped/academic blockers.

This controller deliberately **does not batch-render** lessons, submit models,
perform TTS, rescan previously accepted scientific PDFs, or approve student
publication. For a single already-authorized and fully ready section the user
must use the separate PR487 `RenderPrepared` command with explicit section,
which is subject to its own exact source and PCM gate.

## Release distinction

- Multi-source orchestration status/restart PASS is not video completion.
- Existing Thomas §§8.4 and 8.5 remain source-specific BLOCKED inputs unless
  a new independently reviewed/versioned source campaign becomes eligible.
- The 155 historical unresolved mappings are not a prerequisite for the next
  general installation, unrelated eligible source qualification or CI work.
- The next major priority is an *independent genuine eligible source* full E2E
  qualification, then adversarial process-recovery and cumulative release stack.
- No Ubuntu, HP, Yoga, local LLM or shared G: checkout mutations.
