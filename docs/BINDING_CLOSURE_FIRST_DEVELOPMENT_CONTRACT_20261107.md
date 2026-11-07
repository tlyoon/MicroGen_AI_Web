# MicroGen_AI_Web — Binding Closure-First Development Contract

**Version:** 4.0 / 7 November 2026  
**Status:** Owner-directed, effective immediately for subsequent development turns and
automated development prompts.  
**Applies only to:** `tlyoon/MicroGen_AI_Web` (Windows/Selenium). The separate
API-based `microgen_ai` project must never inherit this agreement by accident.  
**Recorded implementation base:** draft PR #528, Dell-115 isolated worktree,
commit `67f49ca68fce7519b1c031752cb21e0ce28f5e41` (both hosted Windows
CI jobs successful). Subsequent commit IDs are resolved afresh each turn.

## 1. Authority, continuity and non-regression

This is a **procedural supersession** of any earlier instruction that would
permit endless new feature PRs, repeated per-PDF perfection, repeated provider
canaries, or treating CI-green as full production closure. It refines the
18-October standing autonomous-development protocol, the 2-Nov evidence-reuse
amendment, and the user's Autonomous Continuous Development Prompt v3.0.
A future invocation of that prompt MUST use this newer contract as its
development strategy, even if the uploaded prompt itself remains version 3.0.

The latest explicit owner decision has precedence when older records conflict.
Preserve the underlying technical, source/science, security, pricing, device,
TTS, video and publication requirements and their historical evidence.
Do **not** retroactively rewrite old runs or conflate independent stages.
This contract does not authorize merging protected branches, expenditure,
new account access, bypassing a browser challenge, or student publication.

## 2. Change of objective: acceptance and closure, not more activity

**Primary goal:** finish a usable, tested, reproducible, general-purpose
Windows lecture-generation product. Each change MUST materially improve one
of three unfinished closure gates, with observable evidence of that gain.

- **G1 — Operational generation transport.** Demonstrate a new, safely
  claimed source-free or truly new-source request with verified ownership,
  exactly-once submission and a complete attributable response, at an
  appropriate source-sized workload. Authentication, short canaries and
  models.get metadata alone do not establish this gate. Gemini browser,
  ChatGPT browser and paid API routes are separately classified. No automatic
  interchange or duplicate Send after an uncertain outcome. Do not attempt
  to bypass authentication or anti-bot verification; when an external
  barrier persists, mark G1 blocked and proceed with other eligible work.
- **G2 — Independent complete-lecture acceptance.** Generate a genuinely
  different, unattempted source from physical original PDF through figure
  extraction and all panels, source-faithful Beamer slides, correct narration,
  audio/WAV, and truly synchronized encoded MP4, with every part **strictly
  shorter than 600 s**. Verify source-grounded figure/math meanings, timed active
  highlights, PCM and voice consistency, relaxed-but-consequential pronunciation,
  and full media provenance using the established *autonomous AI-based*
  scientific and audiovisual QA. Existing immutable receipts must be reused
  where scope and SHA match. Passing a component test or one historic
  partial pilot does not complete G2. No mandatory human academic review
  for internal technical progression.
- **G3 — Reproducible, reviewed Windows codebase closure.** Freeze unrelated
  feature work, review release-critical code/dependencies with risk-based
  historical PR reconciliation (not blanket merge of hundreds of drafts),
  validate an isolated build and installation, pass the exact final-HEAD
  Windows CI, and publish a truthful release evidence manifest/known
  limitations. An *engineering technical candidate* and a *production-ready
  accepted candidate* are different states. Protected-main merge, tagging
  and student-facing release remain separately governed operations.

**Meaning of closure:** G1 + G2 + G3 supported by actual evidence. A
source-only engineering review package may be closed separately as an
engineering milestone; it MUST NOT be labeled a fully operational generator.

## 3. Mandatory admission test before any new task

At the start of every future autonomous continuation, read the existing
`docs/CONTINUATION_CHECKPOINT_LATEST.md` and this contract, verify the
correct Dell-115 checkout, branch, dirty status, actual Git SHA, current
PR/CI outcome and release board, and reconcile any newer authoritative
evidence. Reuse test evidence at exact SHA and scope; an older green build
is not a newer head's CI result.

For each proposed action, record in the checkpoint or PR:
1. **Target gate (G1/G2/G3)** and which specific acceptance gap it removes.
2. **Prior proof/history consulted:** exact source/job SHA, existing fixes,
   attempts, statuses and blockers. Use `evidence_reuse_contract` where relevant.
3. **New evidence or new dependency** making the action necessary.
4. **Bounded implementation/test plan:** success criteria, prohibited side
   effects and explicit cut-off. Prefer a small correction to existing code.
5. **Measured result:** changed executable behavior or accepted evidence,
   not merely number of commits, PRs, documentation pages or new checks.

If an action cannot satisfy these conditions, **do not implement it** just
because a previous prompt says to keep proceeding.

## 4. Strict anti-loop and failure policy

- **One justified targeted corrective cycle per unchanged blocker signature**
  before deferring. Inspect past solutions first; reuse them rather than
  writing parallel detectors. A second cycle requires material new evidence:
  changed independent failure trace, inputs, code, provider status, source
  fingerprint, safety requirement or accepted alternate strategy.
- **Persistent across sessions:** preserve attempts and exhausted budgets in
  immutable receipts/checkpoints; new chats, device restarts, PR numbers and
  model keys do not reset them. No source-specific indefinite Figure 8.3,
  Thomas or Serway loops.
- **Defer with precision:** record `DEFERRED_EXTERNAL`, `BLOCKED_INPUT_SPECIFIC`,
  `UNRESOLVED_AMBIGUOUS_SEND` or another precise status, cause category,
  affected acceptance gate and the factual condition permitting reopening.
  Advance an independent gate when safe. Genuine safety-critical failure
  still blocks release of the affected lecture; do not weaken acceptance.
- **No speculative canary campaigns:** run another external model test only
  when it discriminates a new concrete hypothesis or verifies a material
  changed route; it must use a fresh one-time claim and no old prompt/source
  replay. Avoid repeated health checks that merely restate G1 failure.
- **Transport diagnosis:** distinguish Gemini model-side UI failure from a
  verified HTTP 429/503/504, Selenium selector/focus fault, authorization,
  ChatGPT `Just a moment...` verification, and uncertain send. Login is not
  generation success. Follow existing safe retry, cooldown and key-rotation
  logic only within the relevant authorization boundary. Browser challenges
  are respected, never bypassed.

## 5. Default bounded execution and PR discipline

Use **one critical-path goal at a time** where practical; up to three
substantial independent priorities per user invocation is a maximum, never
a quota. Do not create a new draft PR when the existing verified PR #528
branch can safely carry a focused improvement. Continue along the established
isolated draft chain only when needed; never mass merge or rebase dirty
production worktrees. Preserve code/history, original source PDFs, slide
TeX/PDFs, narration scripts, PCM/WAV, MP4 and immutable logs.

No unrequested local LLM, Ubuntu/Linux CI, HP, Yoga6 or Zenbook:
**Dell-115 is the sole authorized local MicroGen_AI_Web development machine**.
Hosted Windows GitHub Actions remain allowed.

Before starting new production generation, use a **different exact-source SHA**
with globally credible attempt history; the scoped candidate inventory is
not evidence that a source was never attempted anywhere. The latest
production-stage SHA / sibling-intent guard and per-stage one-Send journal
must remain enabled. Do not repurpose a claimed PDF, reopen uncertain
submissions or rotate an API key to resend the same uncertain task.

Use Gemini/ChatGPT according to the current approved routing; retain Gemini
Flash-Lite TTS as the primary path and Google Cloud TTS as a *conditional*
fallback only under the latest effective voice and cost contract (do not
hardcode a disputed default Cloud voice). No Whisper/ASR substitution and no
local models. Explicitly authorized experimental/paid calls only; normal
contracted production billing rules are unchanged, not expanded. TTS QA
accepts similar intelligible pronunciations while rejecting clear errors
such as letter `c` read as `circa` and wrong mathematical meaning.

## 6. What does and does not count as evidence

Use this graded, noninterchangeable reporting vocabulary:

- `CODE_PRESENT`: capability exists, no runtime proof.
- `OFFLINE_TESTED`: targeted synthetic/regression tests passed.
- `EXACT_HEAD_CI_GREEN`: Windows hosted checks passed on matching SHA.
- `REAL_STAGE_VERIFIED`: original source and completed real stage,
  outputs, provenance and status externally rechecked.
- `FULL_ORIGINAL_ACCEPTED`: genuinely distinct complete lecture passes
  all contracted autonomous source, figure, science, audio and media checks.
- `RELEASE_CANDIDATE_READY`: build/install, exact head CI, relevant
  historical dependencies and actual accepted lecture verified; all
  outstanding scope/authorization limits disclosed.
- `RELEASED_OR_PUBLISHED`: separate verified external action and receipt
  under the existing publication agreement. Never infer from a test.

Never assign unsupported percentage complete, claim a model/provider outage
from a browser exception, call an engineering-only package a full student
release, or turn a false release gate true by editing acceptance constants.

## 7. Final freeze and closure decision rules

**Feature freeze now in force.** Only defects or missing integration directly
blocking G1, G2 or G3 may justify a code change. Packaging, tests and
documentation are useful only if they close a named acceptance gap.
If the same gate is externally blocked after the bounded investigation,
record it and work on an *independent* legitimate gate—not endless
incremental hardening for its own sake.

For the extensive historical draft stack, establish the **actual release
dependency closure** for code that will ship: identify required commits and
risk, inspect branch provenance and diffs, verify corresponding current
regressions and scientific/media effects, document omitted unrelated drafts.
Do not call GitHub many-to-many commit/PR membership an independent approval,
or assert hundreds of PRs individually approved. No merges without required
authorization.

At each meaningful checkpoint, report `G1 / G2 / G3` as **Verified,
Partial, Blocked or Not started**, with one concrete missing acceptance
artifact per gate, latest HEAD/PR/CI, specific changed functionality and
next single highest-impact action. If a remaining blocker is external,
state exactly which evidence would enable resumption and do not invent an
estimated completion date.

## 8. Current evidence baseline and next allowed work

At adoption, PR #528 HEAD `67f49ca` has two green Windows CI jobs and a
clean isolated Dell-115 worktree. The source-only Windows review ZIP and
engineering technical readiness had passed at earlier exact verified SHAs.
The latest live source-free provider preflight is
`NO_GENERATION_TRANSPORT_CERTIFIED_FOR_AUTOMATIC_DISPATCH`.
A second source-bound, fully accepted lecture and autonomous QA evidence
are missing; a large historical PR/dependency stack is not closed.
Therefore **G1 blocked, G2 blocked by G1, G3 partial**. Recheck all states
on the new HEAD and never assume adoption alone changed any gate.

**Next decisive step:** restore or qualify ONE legitimately usable
generation route, then perform ONE safely claimed distinct-source
end-to-end lecture acceptance. Parallel independent G3 integration work
is permitted only where it directly reduces release risk.

## 9. How to invoke from future conversations

An invocation of `@Autonomous_Continuous_Development_Prompt_v3.0.md`,
"Proceed", or any cross-session continuation for **MicroGen_AI_Web** MUST
first apply this binding v4.0 contract, consult the latest verified repository
checkpoint, select a G1/G2/G3 critical-path task and act within its bounds.
Do not restart the workplan or silently undo owner policy. At the end,
update the same checkpoint rather than proliferating alternative trackers.
Do not promise background development when no live scheduled process exists.
