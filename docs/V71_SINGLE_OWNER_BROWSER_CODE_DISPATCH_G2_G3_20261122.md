# MicroGen_AI_Web v7.1 — bounded Selenium code dispatch and G2/G3 evidence

**Date:** 22 November 2026 (Asia/Kuala_Lumpur)
**Development base:** GitHub `main` `827b9ae64e3a83a3d81ff8889ce0e6c3cc10d2b3` (PR #600).

## 1. Single-owner, exactly-once *claim*, independently dispatched

This addition **does not mutate** the existing offline-only continuity daemon,
its schedule, roadmap, student-release gate, or Codex host sandbox restriction.
The new CLI, `selenium_pipeline.development_browser_code_dispatch_v71`,
is a separate, explicitly invoked bounded work dispatcher.

An enrollment file under `<queue>/inbox/dispatch_<id>.json` requires an
exact authorized project, single permitted browser claim, Gemini **Selenium**
transport (not the Developer API), no student release, and the SHA256 of
`<queue>/jobs/<id>/job.json`. The job pins original Git HEAD, isolated
feature branch, original existing source SHA256 and one new test path.
The existing transport supports only pure, statically constrained tests of
the historical `is_host_readonly` classifier; generated arbitrary Python
is **not** admitted.

Dispatcher rules:

1. Acquire a real OS-exclusive lock on the queue. No duplicate owners.
2. Scan at most eight immutable enrollment entries; execute at most three
   eligible distinct jobs per invocation. Invalid, completed, quarantined
   and changed jobs cannot occupy all finite dispatch slots.
3. Write a durable `WORKER_DISPATCH_CLAIMED_UNCERTAIN` ledger entry **before**
   invoking any potentially consuming model worker, including a possible
   crash between outer and inner checkpoints.
4. The existing Selenium worker then writes its own claim **before** one
   registered browser Send, requires independently verified model and
   Thinking selection, records requests in the existing cost ledger, and
   saves raw response and SHA256.
5. A crash or timeout with no genuine saved response never permits a second
   browser Send for that identifier. Previously captured response evidence
   can be reconciled offline without a paid API or a second Send. Unsafe
   model source and failed tests remain quarantined.
6. The original protected source stays unchanged. The independently
   registered atomic handoff applies a verified AST-limited test in one
   isolated worktree and runs real pytest. Only a verified file and matching
   source hash mark a job complete. No automatic push/merge/publication.
7. A separate registry entry and tests enforce the lock, bounded scan,
   write-ahead claim, corrupted receipts, original-response reconciliation,
   independent queue work and no starvation.

To inspect safely (no model dispatch):
```text
python -m selenium_pipeline.development_browser_code_dispatch_v71 --inspect --queue-root <queue>
```
To explicitly dispatch up to one new authorized browser model request:
```text
python -m selenium_pipeline.development_browser_code_dispatch_v71 --dispatch --queue-root <queue> --max-jobs 1 --allow-one-browser-send
```
Default `--dispatch` without `--allow-one-browser-send` may only reconcile
original existing claims. This CLI is on-demand, not a new Windows scheduled
task. The old daemon continues its offline-only handoffs independently.

### Live Dell-115 evidence

Fresh source-pinned live enrollment: `first_dispatched_browser_test`.
Hydrogen with Medium Thinking was checked in a zero-Send Selenium preflight.
The dispatcher then admitted exactly **one** authentic Gemini web request,
captured its response, validated its restricted AST, and applied its test in
an isolated Git worktree; the real test passed. On second dispatcher
invocation, `new_browser_claims=0` and the accepted source SHA256 remained
`66700db0b10c733ca7494265032b19dfdb7c015bcb9c11179f1a4f7fb6057925`.
Persistent result: `CODE_CANDIDATE_VERIFIED`; paid API requests=0,
Codex host-denial unchanged, no student publication, no other PCs touched
by the live Selenium job.

A real Windows CRLF-reconstituted original browser text was previously
incompatible with the LF-only pure-test parser; the registered format-only
repair now canonicalizes CRLF for AST parsing without changing original
saved bytes or their SHA256. Fault injection demonstrates that an old
rejected response can be recovered without a new model request.

## 2. G2 original historical review inventory — no new Send

Source-bound, read-only original Serway §1.3 review queue: **13 slides,
85 utterances**. Original queued G2 consensus remains **27 accepted / 58
pending**, not completed. A fresh eligibility check identified nine
slide-level completed review stages (do not repeat); three slides with
historical attempts requiring reconciliation (**3, 10, 11**); and one
ambiguous old Send (**slide 4**). **Zero** slides were eligible for a fresh
scientific-model Send. Therefore no G2 Send was attempted and no science
acceptance was fabricated. Original claim reconciliation is the next
admissible step; each historical ambiguous Send remains blocked from replay.

Evidence: Dell checkpoint
`G2G3_READONLY_AUDIT_20261122.json` (no source mutation).
G2 academic review may use Selenium only; paid API fallback forbidden.

## 3. Independent G3 technical input inventory — not acceptance

The read-only local file check covered Serway §§8.2 and 8.3, confirming:

| Original evidence | §8.2 | §8.3 |
|---|---:|---:|
| `source.pdf`, `slides.pdf`, `script.txt` | present and hashed | present and hashed |
| Consecutive numbered `slide*.wav` | 15 | 17 |
| WAV decode | mono, 24 kHz, 16-bit PCM | mono, 24 kHz, 16-bit PCM |
| `slides.mp4`, `slides_part01.mp4`, `slides_part02.mp4` | 3 decode | 3 decode |
| Video first-frame decode resolution | 1280×720 | 1280×720 |

These are **technical input readiness checks only**. Independent speech
accuracy, acoustic defects, video synchronization and second-subsection
scientific QA were **not** established; G3 remains open. No TTS QA paid
requests and no student release were performed.

Evidence: Dell checkpoint
`G3_READONLY_MEDIA_TECHNICAL_20261122.json`.

## 4. Remaining boundaries

The single-owner dispatcher closes a **strictly bounded test-authoring
subtask**, not arbitrary unsupervised code authoring. More general
authoring would need a separately tested safe profile, not an unsafe
extension of this AST allowance. G2 historical source-math acceptance
and G3 independent acoustic/video and subsection acceptance remain
distinct, incomplete gates. No code silently promotes metadata or
file presence to release authorization.
