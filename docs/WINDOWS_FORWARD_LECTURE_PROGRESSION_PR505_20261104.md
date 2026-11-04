# PR505 — General Windows one-source lecture progression coordinator

This PR addresses the **general missing integration** between independently
implemented stages. It does not recheck Thomas Figure 8.3, attempt another
Serway §24.4 slide request, or recertify an already accepted PDF.

## Operator interface

A new module, `windows_lecture_progression_coordinator`, reads existing
original-source receipts and actual staged artifacts **before** deciding what
is eligible to happen next. It reuses the real PR490/499 source staging,
PR500 single-send guards, PR502–504 provider health/key selection, and the
strict `windows_original_stage_sequence` SHA-bounded stage runner.

Read-only default command (no network, no model, no TTS, no FFmpeg):

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR505_20261104'
$python = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
Set-Location $repo
& $python -m selenium_pipeline.windows_lecture_progression_coordinator `
  --source-root 'EXACT_ORIGINAL_TEXTBOOK_ROOT' `
  --section 'EXACT_NEW_SECTION' `
  --trial-dir 'EXACT_EXISTING_EMPTY_EXTERNAL_VERSIONED_TRIAL'
~~~

Alternatively, the existing native PowerShell launcher now exposes the same
source-locked logic as a first-class operator mode:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\MicroGen-Windows.ps1 `
  -Mode LectureStatus -SourceRoot 'EXACT_ORIGINAL_TEXTBOOK_ROOT' `
  -Section 'EXACT_NEW_SECTION' `
  -TrialDir 'EXACT_EXISTING_EMPTY_EXTERNAL_VERSIONED_TRIAL' -Python $python
~~~

Its separate, explicitly chosen `-Mode LectureAdvance` runs **at most
one** newly eligible stage per invocation. Gemini API mode additionally
requires `-CommunicationMode api -ConfirmContentApiCost` and remains
subject to the shared provider health gate.

An *operator-authorized* individual stage may be run with
`--execute-next-one-stage`. It must be a new eligible stage, backed by
the actual publisher PDF and a separate existing external trial directory.
For Gemini API use, both `--communication-mode api` and
`--confirm-content-api-cost` are required. A browser send may still
consume quota; never pass the flag on an earlier ambiguous request.

### Finite progression and what counts as complete

1. `figures`: original PDF copied to an external source tree; model send
   intent saved before the attempt, actual source-map and technical QA
   verified before slides are admitted.
2. `slides`: accepted Beamer PDF/TEX, strict source SHA, stage receipt SHA,
   physical checksums, and technical QA.
3. `narration`: actual generated script with SHA and technical QA.
4. `script_qa`: deterministic script-risk and math-semantic reports
   (not another Gemini submit), SHA checked.
5. `reviewed_audio`: **explicit review and authorization** of the original
   math, figures, script and per-element audio plan; this coordinator
   does not automatically generate TTS or bypass independent human voice
   and academic checks.
6. `video`: reviewed sourcebound-element media bridge independently
   verifies recorded WAV and encodes H264/AAC; audio/video approval and
   student publication remain distinct gates.

The first four stages are now linked by one general, source-independent
state machine. The fifth and sixth are reported as an exact-source
handoff, not falsely inferred as complete. No bogus full E2E claim is
made from successful slides/script alone.

Each invocation launches **at most ONE source stage**, then returns.
A subsequent invocation must rescan SHA-pinned original PDF, immutable
pre-send claim, prior stage result, its predecessor hash and real outputs.
A crash after the send but before the result is always a stop: no repeated
provider request or “resume and fix this particular PDF” loop. A successful
old stage is reused only when the real output hashes remain equal.

### Admitted and blocked statuses

- `NEXT_SOURCE_STAGE_READY_EXPLICIT_ONE_SHOT_ONLY`: read-only state
  recommends exactly one eligible stage; permission not inferred.
- `EXACTLY_ONE_SOURCE_STAGE_ATTEMPT_FINISHED_NO_AUTO_CHAIN`: one
  operator-invoked source stage completed or stopped; the underlying
  original-stage status is still reported honestly.
- `HALTED_PRIOR_FIGURES_SEND_UNRESOLVED`,
  `HALTED_PRIOR_STAGE_SEND_UNRESOLVED`,
  `HALTED_PREVIOUS_FIGURES_FAILED_NO_RESEND`, or
  `HALTED_PREVIOUS_STAGE_FAILED_NO_RESEND`: preserve the exact old
  attempt and proceed with other general development instead.
- `HALTED_PROVIDER_CAPACITY_NO_NEW_SUBMISSION`: PR503's verified 503
  and other provider health controls block a new send; never auto-retry.
- `REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS`: successful
  original-source figures/slides/narration/script QA and exact source/slide/
  script SHAs exist; next milestone is reviewed per-element audio and video,
  with no invented scientific certification or publication permission.

## Evidence and tests

Native Dell-115 synthetic and mocked tests use a **new unrelated** section
77.9; no publisher PDF or Gemini key is transmitted. They exercise
figures → slides → narration → script_qa → reviewed audio handoff, no
repeated model calls, API consent, provider halt, changed source or output
SHA, unresolved started receipts, and a successful *one-stage* dispatch.
A physical CLI dry-run on a new synthetic source can be used without any
model call. Windows GitHub CI is updated with the new tests.

The existing old `windows_sourcebound_e2e_orchestrator` was not invoked;
its historical multi-retry path must NOT be used as an automatic source
recovery mechanism. This new operator coordinator is the documented
safe forward path for new original sources. No historic 770+ draft commits
are merged or published as part of this PR.

This is a concrete step toward end-to-end production, but a **second
independent original full narrated media lecture has not been generated**,
and strict independent academic review, stack consolidation and formal
release approval remain outstanding.
