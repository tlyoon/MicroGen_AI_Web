# PR490 - Independent new-source bounded original Windows trial

Release-engineering objective: advance the general pipeline using **a separate
original textbook section** rather than repeating one Thomas PDF defect. The
existing native seven-stage runner is used; no surrogate or legacy video
renderer is introduced.

## Source choice and immutable versioning

Dell-115 has genuine source-only `G:\My Drive\Serway\Serway_22_27\22\22.1\source.pdf`.
It is a **different source** from the Thomas §8.4–8.6 input-specific sourcebound
mapping backlog, and contains no authored `slides.pdf` / `script.txt` yet.
The tool stages a byte-exact source copy in a separate new versioned Windows
checkpoint and SHA-locks both original and copied publisher source.

```powershell
$trial = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints\20261104_PR490_FRESH_SERWAY22_1_V1'
New-Item -ItemType Directory -Path $trial -ErrorAction Stop
python -m selenium_pipeline.windows_fresh_source_trial --source-root 'G:\My Drive\Serway\Serway_22_27' --subchapter 22.1 --trial-dir $trial
```

This command is a real original source *dry-run*: it confirms the seven-stage
pipeline plans a genuine source, but **does not** perform authoring, invoke a
browser model, synthesize speech or produce a video. A dry-run pass is NOT a
full source-to-video pass.

One *explicitly authorized* bounded browser figure-stage attempt is available
using `--attempt-figures-once --timeout-seconds 180`. It runs ONLY the general
source-to-figure stage, through the existing Selenium runner, never TTS.
An immutable send-intent ledger is created **before** starting the browser:
timeout, disconnected browser or uncertain provider send cannot trigger an
automatic second submission. If a partial authoring stage is produced,
subsequent progress must use new versioned receipts rather than fabricate
success or blindly restart the stage.

This PR is *not* a complete original lecture, mathematical or audio acceptance,
or an authorized student release. It gives the next milestone a reproducible
independent original-source trial and preserves the one-PDF anti-loop rule.

Strict controls:
- Sole development Dell-115, native Windows.
- Source PDF never overwritten, staged copy SHA reverified.
- No Ubuntu/HP/Yoga/local model.
- No secret values logged; no paid TTS or publication.
- A new versioned attempt is required to reconcile ambiguous provider action.
- No test mocks count as a genuine full sourcebound video.

## Actual Dell-115 source trial, 4 November 2026

- Distinct publisher Serway §22.1 physical original SHA:
  `02848ebd523b746117877ec1b5889671b8a056e969776e125cc690f9b9061673`.
- External staged source matches original byte-for-byte; original folder remains
  source-only and unchanged.
- Existing seven-stage runner dry-run **PASS** (all seven planned).
- Single figure-only Selenium attempt under an immutable *pre-send ledger*:
  **TIMEOUT at 180 seconds; no figures generated**. No automatic retry.
  Browser model send status cannot be inferred safely after that timeout;
  no paid TTS or video performed.
- Windows subprocess reader revealed cp1252 UnicodeDecodeError on model's
  UTF-8 output. Fixed the **general Windows wrapper** with explicit UTF-8
  `errors="replace"` in both dry-run and bounded real subprocess calls,
  plus regression assertions. No second provider submission for this input.
- This PR is an application infrastructure / failure-recovery milestone,
  **not** genuine source-to-video production qualification. PR491 must
  continue general recovery/release QA without repeating this blocked source.
