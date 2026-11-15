# 15 November 2026 — Independent-source forward progress

## Objective and limits

Advance the general MicroGen_AI_Web Windows codebase without returning to
uncertain Serway 6.4 Gemini Send claims. New native Windows forward-source
campaign exercises only existing seven-stage DRY-RUN, never a Gemini/ChatGPT
model Send, paid TTS, video encoding, scientific approval or release.
Separate production model stages retain the existing one-Send and source/
provider evidence gates. The forward campaign is not a full PDF-to-MP4 PASS.

## Reusable integration

- selenium_pipeline/windows_forward_source_campaign.py: normal,
  restart-safe multi-source source-only dry-run controller.
- MicroGen-Windows.ps1: new ForwardSourceDryRuns mode accepting SourceRoot,
  TrialRegistryRoot (external LOCALAPPDATA directory), CampaignName and
  MaxNewSources (1 to 12). All API cost and media-render flags are forbidden.
- Source inventory uses the existing verified candidate-finder, excluding
  already logged source SHA claims. Candidate list is frozen in an immutable
  source/version contract on first invocation and cannot silently change.
- Each selected source is SHA/size-checked and gets a distinct external
  immutable dry-run result. On restart, recorded results are reused; source
  hashes and current stage readiness are checked again, but the dry-run
  producer is never called again for that source.
- Failure, timeout, tampered receipt and source mutation on one PDF are
  isolated from unrelated source PDF processing. No terminal failure is
  relabeled successful.
- Native Windows kernel file lease disallows concurrent runs of the same
  campaign across terminals/sessions; it is released on process termination.
- Before and after a dry-run, local source-stage model Send-intents are
  inspected; a purported dry-run that created one is rejected.
- No original publisher files are modified, and no old ambiguous model
  request is resubmitted.

## Actual Dell-115 evidence

Scoped publisher inventory read-only for G:\My Drive\Serway\Serway_1_7:
46 source.pdf files, 25 prior trial contracts and 35 send-intent receipts.
Sections 1.1 and 1.2 had prior source trial records, so they were excluded.
Sections 1.3 and 1.4 had distinct PDF SHA values and were selected.

A REAL Windows source-only run under external
LOCALAPPDATA\MicroGen_AI_Web_Checkpoints\MG_20261115_NON64_FORWARD_V1
recorded two independent FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY statuses,
zero rejected sources, zero Gemini/TTS/video calls and no release.
Their next-stage inspection was NEXT_SOURCE_STAGE_READY_EXPLICIT_ONE_SHOT_ONLY,
not a generation success. Original 6.4 was never staged or sent.
All prior source-locked claims are unchanged.

The initial native two-PDF synthetic launcher test passed, including
byte-exact staged copies and proof that a restart reuses receipts.
Broader Windows source-candidate, progression, historical claim,
release-readiness, runtime and crash-recovery suite: 142 passed.
The exact-head GitHub Windows CI should be verified after this code is pushed.

## Supported invocation

PowerShell, from an isolated MicroGen checkout:

    .\MicroGen-Windows.ps1 -Mode ForwardSourceDryRuns
        -SourceRoot "G:\My Drive\Serway\Serway_1_7"
        -TrialRegistryRoot "$env:LOCALAPPDATA\MicroGen_AI_Web_Checkpoints"
        -CampaignName "MG_20261115_NON64_FORWARD_V1"
        -MaxNewSources 2

A repeat invocation reuses the same exact PDF hashes and receipts.
A different campaign requires a NEW name and selects only from still
unclaimed sources in the specified scoped registry. Absence of a claim from
the specified registry is not proof of global never-submitted history.

## Forward boundary

The next general engineering milestone is a guarded cross-source
stage-continuation planner with explicit durable one-source Send claims and
finite stop rules, not an automatic repeat of blocked source jobs.
Actual original academic mappings, true per-element PCM/phonetic QA,
synchronized sub-600-second MP4 and publication remain separately gated.
