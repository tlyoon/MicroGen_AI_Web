# MicroGen_AI_Web — Reliability and Fidelity Hardening Programme (RFH v1)

**Status:** Phase 0 contract and acceptance baseline (12 October 2026)  
**Repository scope:** `tlyoon/MicroGen_AI_Web` only. **Never** alter `tlyoon/MicroGen_AI`.  
**Source of requirements:** Observed three-PC Gemini failures; Thomas Calculus 2.2 Figure 2.10/slide 7; the maths-variable pronunciations on slides 14 and 15; the user's reviewed legacy `sanitize_script.py`; prior Stage 5–7 audits.

## Mission and non-negotiables

A lecture must not be marked complete merely because the model returned text, a LaTeX command exited 0, or a media file exists. Every completed job needs evidence that required figures, slides, scientific narration, speech, audiovisual synchronisation, and output hashes satisfy their stage-specific gates. A known blocker means **no completion receipt**. Ambiguous scientific or acoustic evidence means **review_required**, not an automatic pass.

This programme is incremental. Do **not** merge untested transport changes, hot-swap production workers, modify source.pdf, overwrite published verified MP4s, silently regenerate downstream assets, or start a wide three-PC textbook campaign ahead of acceptance gates. Use isolated copies first and keep roll-backable production pins. Evidence about textbook/lecture material belongs in local, access-controlled acceptance records; do not commit copyrighted textbook PDFs, images, videos, credentials, or private Drive links to this public repository.

## Accepted operator settings

One central setting will control Gemini **content-generation** stages:
`MICROGEN_COMMUNICATION_MODE=selenium|api|fallback`

**Default is selenium**. An explicit CLI/launcher override takes precedence over the environment variable. If no override exists, the environment variable wins; if neither exists, use `selenium`. Invalid mode values fail closed. Figure detection/caption abstraction, slide generation and narration are all covered.

| Mode | Figure/caption abstraction | Slides | Narration | TTS and TTS QA |
|---|---|---|---|---|
| selenium (default) | Selenium only | Selenium only | Selenium only | Existing API-based system |
| api | API only; no Gemini Chrome dependency | API only; no Gemini Chrome dependency | API only; no Gemini Chrome dependency | Existing API-based system |
| fallback | Selenium first; only after configured multiple failed attempts use API | same | same | Existing API-based system |

Default fallback attempt budget: **3 Selenium attempts, then up to 2 API attempts**, per independently validated request. A successful result terminates the plan. The *next independent request starts with Selenium*, even if the previous request fell back to API. Never treat the entire campaign as permanently switched to API. Permanent input errors, missing source, permission issues or unsafe outputs must not be retried as if they were ordinary transient model failures. Fallback must be accompanied by a trace recording the cause, backend, attempts, result hash, and validation outcome.

**Phase 0 implementation boundary:** `selenium_pipeline/communication_policy.py` is an **isolated immutable policy contract only**; it is **not wired to the runner or production launcher** yet. The current production launcher still pins API-backed figure mapping/narration. Do not label the three modes functional until Phase 1 adapters and live tests pass. API TTS remains deliberately separate.

## Failure taxonomy and classification

Record separate machine-readable classes:
- `slow_active`: request acknowledged and activity continues; allow bounded adaptive waiting, no duplicate submission.
- `stalled`: inactivity deadline exceeded; safely abort/recover browser/session, bounded retry.
- `refusal`: explicit “cannot do this”, policy restriction or model inability; never publish text as a valid response; adapt/split prompts only within scientific-content constraints.
- `rate_limited` / `service_unavailable`: honour retry-after where provided, back off and use a cross-PC concurrency budget; do not hammer the service.
- `transport_error`: browser submission/clipboard/connection failure or API request failure; classify and recover.
- `invalid_output`: response incomplete, absent required figures/slides, malformed LaTeX/script, or validation failed; checkpoint accepted upstream stages, retry the defective step only.
- `permanent_input_error`: missing/changed source, unsafe paths or permissions; stop without Gemini retry or API fallback.
- `review_required`: unresolved physics/panel/speech meaning; do not certify.

Design workers so HP, Yoga6 and Dell-115 acquire shared/centrally coordinated Gemini request slots, avoiding duplicate jobs and respecting the actual quota account. Do not infer that every stall proves quota exhaustion; collect evidence before categorising.

## Implementation gates and ordered delivery

| Gate | Required change | Validation/acceptance evidence | Allowed next step |
|---|---|---|---|
| **0. Specification and reproducible cases** | This v1 contract, immutable three-mode plan; baseline audit of existing source/runner/Stage 7 branches | Offline mode tests; record known bug reproductions and unimplemented gaps | Open first isolated PR; no changed production behaviour |
| **1. Full communication adapters** | Shared mode argument (CLI/env/production launcher), pure Selenium/API/fallback executors for **all three content stages**; no hidden legacy API override | Fault-injection tests for attempts, refusal, stop-on-success, output equivalence and next-task Selenium reset; each mode exercises each content stage in a controlled pilot | Deploy only after Windows/Ubuntu CI plus three-PC staged pilots |
| **2. Gemini resilience and scheduling** | Explicit acknowledgement/progress detector, bounded deadlines/backoff, refusal handler, failure taxonomy, remote-worker concurrency lease + circuit breaker | Simulate slow-but-active, stall, refusal, 429/quota, bad input, API failure, worker disconnect; prove no duplicate submits or false completions | Multi-PC concurrency stress test |
| **3. Figure fidelity** | Catalogue parent composite and (a)/(b)/(c) subpanels, immutable source coordinates, caption relationships, source-hash provenance and completeness checks; correct responsive LaTeX placement | Reproduce Thomas 2.2 Figure 2.10: complete three-panel composite survives and each panel separately available; rendered slide has no clipping and remains readable; wrong target blocked | Accept bounded figure repairs |
| **4. Slide/LaTeX integrity** | Rebase/adapt existing Stage 7 two-pass Beamer and safe recompile work atop current `main`, verify accurate footer, missing graphics, PDF page count and media dependency invalidation | First pass exposes denominator bug; two passes fix it; no math/figure drift; backup exists; completed videos not silently rewritten | Resume only structurally passing slides |
| **5. Mathematical speech fidelity** | Preserve scientific `script.txt`, create explicit `speech_ready` artifact and semantic token map, avoid global regex substitutions; phonetic/acoustic QA and selective WAV repair | Correct variable c (“see”) rather than “circa”, u (“you”) rather than “us”, distinguish article a from variable A; unchanged good WAV, consistent voice, proof after repair | Enable pronunciation gate before MP4 |
| **6. Unified fail-closed completion** | Versioned manifest/hash and dependency graph for images → LaTeX/PDF → script → speech-ready/TTS → MP4; states `passed / repaired / review_required / blocked` | Tamper tests for wrong panels, clipped image, changed pages, altered text, wrong spoken symbol, source hash drift; no false receipt | Conditional production release |
| **7. Controlled three-PC rollout** | Clean pinned checkouts, 1 end-to-end representative pilot per PC, then staged ownership-based unfinished lecture campaign | 3× full suites, CI, quality and source comparisons, actual WAV/MP4 checks, identical-output completed-job reuse, final audit | Broader campaign only with clean gates |

**Each gate needs:** automated offline tests; real controlled evidence where AI outputs are necessary; logs without secrets; rollback procedure; written result with exact commit; no partial claim of certification. We should prioritise tests with deterministic mocked failures over repeated live Gemini calls.

## Reproducible defect catalogue (no copyrighted assets committed)

| ID | Observed defect | Essential regression |
|---|---|---|
| GEM-01 | Dell-115 Gemini browser submission was accepted but no usable response before a 420-second inactivity cap | Distinguish acknowledged-but-stalled from still-progressing; finite retries, no false success |
| GEM-02 | HP Gemini browser send/composer failed; Windows native key fallback unavailable | Bounded Selenium retries, API only in fallback mode, no secret leakage |
| GEM-03 | Gemini refuses or returns “cannot do this” | Refusal not treated as content; allow controlled request segmentation |
| GEM-04 | Shared three-PC Gemini sessions may overload service/quota | Global admission control, per-request ownership, backoff/circuit-breaker |
| FIG-01 | Thomas 2.2 slide 7: full Figure 2.10 (a), (b), (c) exists but half-width column with height-only graphics constraint cuts off panels | Composite and subpanel metadata; width-and-height limits; visual PDF-bound check |
| FIG-02 | Caption mapping uses panel identifier but whole figure intended | Explicit parent/child relationships; no accidental substitution |
| SLIDE-01 | Single-pass Beamer last page displays e.g. “18 / 1” instead of “18 / 18” | Two-pass compile, footer verification, preserve existing science and PDFs |
| TTS-01 | Slide 14: mathematical c sounded like “circa” | Context-aware letter pronunciation, acoustic evidence, fail or review if ambiguous |
| TTS-02 | Slide 15: mathematical u sounded like “us” | Context-aware expected “you” in mathematical context, acoustic evidence |
| TTS-03 | Legacy global `sanitize_script.py` forces ordinary article a toward variable A and removes non-ASCII | Original script immutable; article/variable disambiguation; preserve Greek/Unicode mathematics |
| QA-01 | Audio script similarity 100% while a mathematical variable is mispronounced | Separate text-fidelity and pronunciation-fidelity outcomes; no unconditional pass |
| QA-02 | Corrected figure/slide changes downstream narration and MP4 | Dependency invalidation with preserved history; fresh synchronized receipt only |

The labels and acceptance conditions are the permanent test targets. Figure and audio examples must be exercised using user-authorized test copies; their Drive IDs and contents are intentionally omitted from public source.

## Integration and release strategy

1. Start each feature from a **fresh main SHA**, with its own small PR and cross-platform tests. One accepted change set per gate; keep Stage 7 work on its branch until reconciled, never blindly merge an older branch over later Gemini fixes.
2. In the first Phase 1 PR, reconcile `MICROGEN_FIGURE_MAPPING_BACKEND=api` and `MICROGEN_NARRATION_BACKEND=api` with the new single mode. Never announce Selenium as default while the launcher overrides it to API.
3. Validate pure Selenium mode **without content-generation API fallback** for the relevant tasks, API mode **without Selenium Chrome dependency**, and fallback mode with observable Selenium-first escalation. TTS/TTS QA remain API and unaffected in all three modes.
4. Preserve accepted stages, hash-bound receipts and source-file read-only guarantees throughout.
5. After controlled pilots, upgrade pinned deployments at safe job boundaries with configuration backups and recheck acceptance. Make existing older “verified complete” receipts subject to new quality-gate versioning rather than automatically claiming old products meet new visual/acoustic standards.

## Human review boundary

No automated multimodal checker can guarantee every physics equation, figure caption or spoken phoneme is correct. It must publish uncertainty and short review artifacts for the user instead of inventing confidence. The objective is **defects detected → correct what is safely correctable → preserve verified work → refuse unjustified success**.
