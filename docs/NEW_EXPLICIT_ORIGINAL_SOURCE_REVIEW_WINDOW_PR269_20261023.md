# PR269: Explicit separate Thomas Calculus 8.4 review window

Real original source audit on Dell-115, October 23, 2026.

## Why a separate window is necessary

The original Thomas Calculus 8.4 slide-1 independent mathematical review queue
has THREE historical failed-attempt receipts. The third historical attempt
did NOT confirm model submission, but remains an immutable failure receipt.
The existing three-attempt limit MUST NOT silently reset. Following the
user's instruction to proceed with the next suggested corrective step,
a separate, audit-visible new window for slide 1 only was authorized.
It has a distinct external AppData folder and at most three new confirmed
submissions, with an independent retry checkpoint. The original review
records and all source/slide/narration hashes are read-only and fingerprinted.

Window on Dell-115:
%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/20261023_approved_separate_thomas84_slide1_window

The new window currently has ZERO new confirmed submissions.

## Real Gemini health diagnostic

A no-attachment 544-character text-only diagnostic sent successfully to
the owned Gemini browser on October 23 at about 14:44 local time. It did
not yield a complete stable JSON reply over about 149 seconds despite
the strict wait and bounded same-owned-tab recovery. The untrusted response
was quarantined separately, and the diagnostic result was recorded in
%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/20261023_real84_reliability_probe_1510.

This is compatible with temporary Gemini capacity exhaustion but
DOES NOT establish a 429/503 response or backend outage. It may involve
browser UI, model execution, policy processing or response capture.
No scientific conclusion can be inferred from a registered user-turn alone.

## Safety and next eligible action

A new source-mathematics attempt can only be claimed by the scoped dispatcher
after a FRESH (within 30 minutes) text-only transport probe sized
1,200-3,000 characters has completed with exact JSON
{"probe":"microgen_source_transport_ok"} in the SAME owned Gemini session.
The raw response must be persisted outside the original folder and match
the checkpoint receipt SHA256; generation must have stopped. A long
conversation or review still requires all six original textbook pages and
the original slide/utterance/bounding-box schema. Model response capture is
NEVER source-mathematics or academic agreement.

Until an eligible probe exists, the new academic window is BLOCKED and
must not send; no automatic background task is activated by this PR.
If the browser becomes healthy, run one bounded independent math review
at a time and preserve the new window's distinct attempt history.
Unknown outcome, crashed browser, missing old receipt, source hash drift
or an occupied worker stops and requires reconciliation.

No original PDF/slide/script/WAV/MP4 modification, Flash-Lite/Kore
synthesis, YouTube/Moodle publication, main merge, other PCs, or paid
Gemini API use occurred. The previously disabled autonomous development
schedule remains disabled.
