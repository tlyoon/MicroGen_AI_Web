# MicroGen_AI_Web v7 contract: G3 multi-section autonomous continuation

Date: 22 November 2026. Scope: Serway §§8.2 and 8.3, Dell-115.
This is a **development/orchestration capability**, NOT a G3 scientific,
acoustic or highlighted-video acceptance.

## Historical blocker and reused remedy

The existing source-grounded mapping reviewer correctly checks original PDF,
author slide geometry, unchanged narration fragments and real publisher
quotations. PR #605 made individual sections restart-safe with original
Gemini Selenium browser request claims and exact-response reconciliation.
However, an invocation ended after one section's bounded Send. The separate
offline-only v7.1 development daemon intentionally cannot send model requests.
It must remain offline-only: simply adding API calls or broad browser access
to the daemon would violate its established authorization boundary.

The added `selenium_pipeline.g3_multisection_autoforward_v71` reuses the
*existing* G3 reviewer rather than creating an additional model transport.
It performs the v7 sequence across multiple independently source-pinned
sections, from the actual existing local checkpoint state.

## Executable production properties

- One strict immutable campaign manifest with each subsection's original
  source PDF, author slides, narration script and approved checkpoint. Each
  section's file hashes and candidate identity are revalidated before any
  new request. All receipts are separate from original source folders.
- One exclusive **campaign-wide** operating-system lock, plus the previous
  per-section lock. The worker cannot use someone else's Gemini tab.
- The normal academic browser path performs model-family and Thinking-level
  preflight before its single registered provider Send. Only the existing
  Selenium browser transport is called; Developer API cost/fallback remains 0.
- Previously verified source replies are revalidated from original bytes
  *without another provider request*. Previously claimed, uncertain or
  source-rejected requests are never resubmitted, including after a crash.
- Source sections are selected fairly by number of prior dispatches and then
  outstanding slides. One successfully completed review automatically moves
  to the next eligible section without another user message. The controller
  recovers a crash using its original browser claims, not conversational state.
- A **global**, cross-section, across-restart safety circuit breaker stops
  new provider requests after two uncertain/rejected claims, even when those
  claims occurred in different textbook subsections.
- Each real browser dispatch produces a write-once, SHA-linked event receipt.
  The manifest and historical receipts cannot be silently replaced.
- Each explicit execution is bounded to at most 32 distinct new original-slide browser dispatches.
  Default zero-Send mode permits safe inspection and reconciliation. On
  exhaustion of the request budget, the checkpoint is preserved.
- The existing executable recovery registry contains an exact failure
  signature and approved handler; regression and fault-injection tests cover
  missing receipts, changed manifest, duplicate owners, cross-section circuit
  breaker, real next-section dispatch and crash-before-checkpoint recovery.

## Actual Dell source-locked worklist before this campaign

- Serway §8.2: 15 slides, 2 source-audited slide reviews, 13 untouched.
- Serway §8.3: 17 slides, 1 source-audited slide review, 16 untouched.
- Three physically verified source-and-authored-text anchors across 20
  previously reviewed original narration fragments, with 17 needing more
  science/figure/semantic review.
- A lexical matching flag is not proof of a scientific error or a valid
  geometry-to-meaning match. No lexical threshold relaxation is permitted.

## Invoking the bounded controller

Run on Dell-115 from the verified Git repository. Do not use HP/Yoga 6
as the browser execution owner for these specific Dell-115 original receipts.

```powershell
python -m selenium_pipeline.g3_multisection_autoforward_v71 \
    --manifest <SOURCE-PINNED-CAMPAIGN-MANIFEST> \
    --state-dir <LOCAL-IMMUTABLE-CAMPAIGN-RECEIPTS> \
    --max-new-sends 0
```

With the exact authenticated Dell Chrome and user authorization, select a
finite positive `--max-new-sends` up to six. The same source/claim reviewer
is invoked one original slide at a time, with the results persisted after
each step. Never start multiple independent browser workers concurrently.

## Unresolved acceptance boundaries

A source-audited model association only shows that selected original words
match the captured source and authored PDF text anchors under the strict
review rules. It does not establish all mathematical equivalence, diagrams,
figure-panel identity, audio correctness or time-accurate highlighted video.
The G2 historical scientific/acoustic uncertainties and G3 independent
acceptance are distinct. Student release, TTS and paid API requests remain
unauthorized by this controller. No unlimited or recurring paid operations
are installed.
