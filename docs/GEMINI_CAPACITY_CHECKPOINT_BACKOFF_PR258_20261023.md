# PR258: Checkpointed capacity-aware Gemini retries

## Root cause: server saturation is possible, not proven

The original-source Dell-115 pilot gave mixed evidence on 23 October:
short text-only JSON succeeded; tiny attachment request submitted but
returned zero model characters after wait/grace; longer 3236-character
prompt submitted after normal Send visibility settled but returned zero
characters over 75 seconds; 39,529-character all-source prompt and
5,398-character first-page prompt were refused by the visibility guard
before confirmed submission. This cannot differentiate provider capacity
from backend model generation, browser state, UI or response capture.

## Persisted design

Each logical job uses one external AppData JSON checkpoint and original
source.pdf, slides.pdf, script.txt SHA256 checks. An exclusive no-steal
file lock, durable write-before-send reservation, fsync and atomic
os.replace into the external checkpoint protect against duplicate workers.
Original textbook files, scripts, WAV and MP4 remain untouched.
The PR257 JSONL physical-page acknowledgment journal can retain progress,
but page acknowledgments do NOT prove academic agreement; after a lost
Gemini conversation, do not skip physical source pages without verifying
the same owned session and complete original context.

State machine:
- READY/WAITING -> CLAIMED_NOT_SENT: reserve BEFORE any browser action.
- Proven unsent (hidden Send/no registered turn) -> WAITING, not counted as
  confirmed provider submission, at most three unsent failures.
- Both verified user turn and cleared composer -> IN_FLIGHT; count one
  confirmed submission.
- Real 429, 503 or other VERIFIED terminal failure with original owned
  tab evidence -> WAITING until scheduled UTC next due, max three.
- Timeout while generation may continue, crash, changed/unowned tab or
  unverified response -> RECONCILIATION_REQUIRED. Never auto-resubmit.
- Actual saved complete candidate reply -> RESPONSE_CAPTURED_UNVERIFIED,
  not source-math approval and not student publishing permission.
- Three original academic attempt receipts or three confirmed submissions
  -> EXHAUSTED; do not invent a new attempt budget.

Backoff: 5 minutes, 15 minutes and 45 minutes for successive eligible
terminal failures (with deterministic 0-20 percent stagger).
The internal cap is four hours, except that an explicit provider
Retry-After up to 24 hours overrides it. The worker should poll once
every five minutes and submit at most one due job when all source, account,
budget and browser-ownership guards pass. The intervals are persisted
UTC epoch timestamps; do not hold an unbounded sleep in ChatGPT or Selenium.

The current implementation is a non-dispatching state-machine foundation.
A future local Dell-115 worker may poll it; no Windows scheduled task or
ChatGPT automation has been installed/reactivated by this PR. A read-only
status CLI reports eligibility, not an instruction to send. No paid TTS,
Moodle publication, YouTube upload, or main merge performed.

## Real original Thomas 8.4 proof

Real queue: 71 original narration segments, zero independently agreed
mathematical mappings. Historical slide-1 challenge attempts 1-3 have
failure receipts; third attempt was not confirmed submitted, but it
remains a historical failed academic attempt. The newly created
external checkpoint legitimately starts EXHAUSTED with a quota of three;
it cannot silently call that a new first attempt. A separate user-approved
revised review quota or new audited review window is needed before
further academic attempts. Existing original lesson artifacts unchanged.

A checkpoint can resume the pipeline after a terminal failure, NOT
restore partially generated remote model output or infer lost server
state. Claims of recovery require a genuinely complete and source-
validated mathematical response, original target geometry, genuine
Kore per-element audio, decoded highlight timing and later academic
and listening QA. Offline test coverage verifies fail-closed behavior.
