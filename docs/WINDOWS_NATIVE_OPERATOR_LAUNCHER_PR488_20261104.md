# PR488 - Native Windows original-source operator launcher

This is **application release engineering**, not another Thomas PDF audit.
Development and testing: sole authorized Dell-115, native Windows, isolated Git
worktrees. The launcher does not automatically launch Chrome, Google/Gemini,
generate paid speech, publish student material, or change source PDFs.

## Invoke from any working directory

From a checked-out code tree:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\MicroGen-Windows.ps1 -Mode Doctor
powershell -NoProfile -ExecutionPolicy Bypass -File .\MicroGen-Windows.ps1 -Mode Inspect -Campaign "$env:LOCALAPPDATA\MicroGen_AI_Web_Checkpoints\20261103_PR486_TWO_REAL_ORIGINAL_SOURCE_IDEMPOTENT_RESTART_V1"
```

The launcher resolves its source checkout from `$PSScriptRoot`, chooses the
isolated optional `%LOCALAPPDATA%\MicroGen_AI_Web\venv` if available, otherwise
the selected Windows Python, and propagates the program's exit code.
`-Mode Doctor` is read-only and never loads source material.
`-Mode Inspect` calls the existing PR487 immutable, SHA-verifying read-only
campaign inspection. It is **successful as an inspection** even if its
individual original-source section reports are BLOCKED; this is not release
approval.

The only video dispatch option is an explicit single section:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\MicroGen-Windows.ps1 -Mode RenderPrepared -Campaign "VERSIONED_CAMPAIGN_FOLDER" -Section "8.4"
```

That mode delegates to existing PR487/485 strict recorded-audio/multipart
production checks. A blocked section returns exit code 2, no render. The
launcher never authorizes a batch render, regenerates models/TTS, or issues
publication instructions.

## Optional installation

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-MicroGen-Windows.ps1
```

Default is read-only diagnostics and installation instructions.
`-Install` is a deliberately explicit opt-in to create a virtual environment
under `%LOCALAPPDATA%\MicroGen_AI_Web\venv` and install requirements-worker.txt
there. The installer refuses to overwrite an existing environment. No
installation is performed by test runs or ordinary inspection.

The diagnostic lists Python/OS, module availability and FFmpeg PATH detection.
This does not certify the external browser login, PDF fidelity, pronunciation,
sourcebound element PCM, video playback, or academic completeness.
A tool missing from PATH should be fixed as a general dependency diagnostic,
not by reopening PDF-specific scientific inspections.

## Contract and next general milestones

- Preserve existing PR362 scoped Thomas accepted evidence and immutable receipts.
- Historical 155 unresolved mapping decisions are **per-input blocked records**,
  not a blocker for application packaging or multi-source orchestration.
- Next PR: multi-source input controller that resumes independently per-section,
  does not bill or resubmit ambiguous providers, and skips blocked sections.
- A real independent original-source full technical qualification must precede
  release or merge acceptance; synthetic tests do not satisfy that criterion.
- Never reset the three dirty user files in the shared G: checkout. No
  installation to HP, Yoga, Linux, Ubuntu or additional local AI models.
- Publication/student release remains unauthorized.
