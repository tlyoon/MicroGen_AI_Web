# PR494 - Native Windows bounded stage process isolation and recovery

**General codebase production reliability.** This corrects a Windows/process
controller defect seen during the independent Serway §22.1 attempt, NOT
the physics or figures of that specific PDF. It is stacked on PR493.

## Implementation

`selenium_pipeline.windows_bounded_stage_process.run_bounded`
runs one subprocess directly with raw UTF-8 file logging and finite
deadline. It deliberately avoids `subprocess.run(capture_output=True)`
and Python's CP1252-decoding reader thread, which actually failed on
UTF-8 mathematical characters in PR490's real browser-stage output.

Each log is created with `xb` (never overwrite), stored *outside*
original textbook/author folders in the existing versioned trial.
On timeout, Windows taskkill targets only the known launched stage PID
and its owned descendants. It does not enumerate or kill all Chrome,
and never touches unrelated sessions. The stage caller already persists
an immutable **pre-send** intent receipt; after any ambiguous send,
timeout or process failure, resending the model is categorically disabled
until a NEW, separately authorized versioned attempt.

The real `windows_fresh_source_trial` now uses this bounded runner
for its *one* figures-only attempt. Existing unit tests can inject a
dummy subprocess seam, so no provider/model is called in CI.

## Independent native Dell-115 acceptance

- Real Windows Python child printing non-ASCII mathematical glyphs to
  raw log: UTF-8 readback PASS, no CP1252 decode crash.
- Real sleeping child: strict 0.6-second timeout and scoped kill PASS.
- Immutable log collision and invalid timeout refusal PASS.
- Existing future Serway/Thomas prior source evidence remains unchanged;
  **do NOT retry previous unknown Gemini send** in the PR490 trial.
- This does not itself produce a new complete academic slide/audio/video.

No local LLM, no Ubuntu/alternate computer, no new TTS/provider spend,
no student publication or user-source overwrite.
