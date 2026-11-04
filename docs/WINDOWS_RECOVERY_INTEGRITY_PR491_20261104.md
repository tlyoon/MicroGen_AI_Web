# PR491 - General Windows multi-source + browser-attempt recovery audit

This is a read-only release-engineering qualification of the **existing**
source job ledger from PR489 and the independent original-source trial from
PR490. It neither recalculates prior accepted Thomas mathematics, reopens
Figure8.3 checks, submits Gemini prompts, synthesizes paid TTS nor renders.

```powershell
$base = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints'
python -m selenium_pipeline.windows_recovery_integrity `
  --jobs-dir (Join-Path $base '20261104_PR489_WINDOWS_MULTISOURCE_JOBS_V1') `
  --fresh-trial-dir (Join-Path $base '20261104_PR490_FRESH_SERWAY22_1_V1')
```

It revalidates each existing PR489 section job against *current* original
source/mapping SHA under PR487's strict inspector. An absent job is separately
marked resumable only if the underlying original evidence still verifies.
A damaged job is rejected for that one section, with the others preserved.

It independently verifies that the staged Serway §22.1 source still matches
its original physical SHA. The pre-send figure attempt receipt remains
authoritative even if a Python process crashed before writing a result; an
uncertain send always disables automatic provider retry. A timeout does not
mean that the model did not receive the request.

The result does **not** certify new full original lecture completion. Full
academic source review, word-matched TTS, actual synchronized under-600s media,
second eligible independent source and strict GitHub integration remain
mandatory before any student-facing release.

The checker performs no network actions and does not mutate the publisher,
author, source campaign, existing job ledger or browser attempt receipts.
