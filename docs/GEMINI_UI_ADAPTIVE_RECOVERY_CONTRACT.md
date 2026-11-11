# Gemini Selenium UI adaptation and Thinking-level contract

**Scope:** The normal MicroGen Gemini UI interaction path on Dell-115. This is
not a model API fallback, an invitation to resend an already claimed request,
or permission to bypass G2/G3 academic and media acceptance.

## Goal and invariants

All Gemini user-interface interactions are **capability-based**, and must be
verified against the **same owned authenticated tab**. UI controls can change
tag names, CSS roles, option order, marketing descriptions and model version
numbers. Such changes should be recovered automatically **before Send** when
the semantic meaning is still observable.

1. **Identity:** Verify the exact owned tab handle and
   `https://gemini.google.com/` origin. Never borrow a different user's tab.
2. **Model:** Use `gemini_model._owned_picker`,
   `select_owned_gemini_mode`, and `assert_owned_gemini_mode` from both parent
   preflight and copied vendor workers. Recognize semantic
   `aria-label`/`data-test-id` candidates, support radio/option/menuitem roles
   and descriptions such as `All-around help / 3.8 Flash` or
   `Quick answers / 3.5 Flash-Lite`. **Stage-specific identity:** exact
   Flash-Lite is mandatory for figure-caption mapping; exact Flash is the
   normal slides/narration family. Never misclassify Flash-Lite as Flash,
   accept mixed/ambiguous labels or silently switch between their tasks.
3. **Thinking by stage:** **figures have no Thinking-level requirement**.
   The normal figure-caption stage must select **Flash-Lite** and must not
   open or verify the Thinking submenu. For **slides and narration**, retain
   the default `MICROGEN_GEMINI_THINKING_LEVEL=medium`, with explicit
   supported overrides `low`, `medium`, `high`. Only these latter
   stages use `gemini_thinking.select_owned_gemini_thinking_level`
   to verify the checked radio. Any attempt to skip the thinking gate
   outside the genuine figure stage must fail closed.
4. **New chat reset:** Verify the **stage-appropriate exact UI family**
   after New chat, not merely before. For slides/narration also reselect
   and verify their requested Thinking level. For figures the thinking
   menu must remain untouched in both vendor and direct browser paths.
5. **Pre-Send:** Always verify exact owned **stage-specific model**, then
   for slides/narration verify Thinking and recheck the model. For figures
   explicitly record `PRE_SEND_FIGURES_FLASH_LITE_NOT_REQUIRED` in place
   of the unnecessary Thinking control and reverify Flash-Lite. No prompt
   retyping or fallback provider attempts; missing, ambiguous or wrong
   model identity raises a pre-Send error. A possibly accepted Send is never
   replayed merely because response content is blank or slow.
6. **Evidence:** The runner records `browser UI model: flash-lite` and
   `browser thinking level: not_required` for the figure stage, and the
   vendor records `[GEMINI-THINKING] PRE_SEND_FIGURES_FLASH_LITE_NOT_REQUIRED`.
   The source-bound coordinator checks an exact Flash-Lite family and this
   marker when an original figures Send was registered. Slides/narration
   still require timestamped pre-Send Medium or other configured level proof.
   No old SHA-locked receipt is overwritten or reinterpreted as a new Send.
7. **Rights:** No change to original publisher PDFs, claims, source hashes,
   scientific/media QA, AI model authorization, audio/MP4 constraints or
   release rules. Incompatible UI must **fail closed** before Send.

## Future changes and safe adaptation

Supported harmless changes include:

- An updated model version label (for example 3.8 to a different version),
  while keeping a single unambiguous Flash identity
- Rewording `Open mode picker` to a semantically equivalent current-model
  selector, retaining a recognizable accessibility name or stable test id
- Switching model or thinking options among supported
  `menuitemradio`, `option`, `radio` or menuitem host controls
- Reordering menu entries, renaming their marketing descriptions, changing
  aria-checked to aria-selected, or a brief Angular hydration delay
- A New-chat action that resets either model or thinking selection, corrected
  in the newly owned conversation **before Send**

**No automation can guarantee support for an arbitrarily redesigned interface**
that provides no trustworthy control identity or selected-state evidence.
Such an unknown change is *not* automatically assumed harmless: it must be
classified as an unverifiable UI contract and halted without dispatch. New
evidence-based selector adaptations should be committed to this single
shared implementation and its drift regression suite, not patched separately
on a PDF, machine, or stage.

## Regression and live acceptance

The source-free stateful UI regression suite is
`tests/test_gemini_adaptive_ui_thinking.py`. It exercises current Gemini
menu structure, renamed selectors, changed option roles, reordered entries,
dynamic subtitles, explicitly checked Medium state, foreign tabs,
missing/ambiguous Medium options and post-New-chat resets.
The general production transport and historical stage tests exercise the
one-click/no-resend boundary, stage-log SHA preservation, and G2 progression
checks. The real November 11, 2026 Dell-115 no-Send vendor test observed:

- `PRODUCTION_VENDOR_FLASH_AND_MEDIUM_VERIFIED`
- `Open mode picker, currently Flash Medium`
- `[GEMINI-THINKING] OWNED_LEVEL_VERIFIED_AFTER_NEW_CHAT medium`
- Zero prompts, uploads or model requests

This evidence establishes correct browser setup **only**, not successful
slide generation, independent academic QA, acoustic QA or learner release.

## Long-prompt atomic picker snapshot and bounded pre-Send recovery (11 Nov)

**Real G2 discovery:** On distinct Serway 7.7, the three-page Docling
extraction finished and the vendor's owned fresh chat positively selected
Flash + Medium. After uploading two source images and typing the actual
figure-mapping instruction, `_owned_picker` rejected the model control with
`PRE_SEND_MODE_PICKER_NOT_UNIQUE_OR_MISSING`; the SHA-bound figures stage
failed with **zero registered Gemini Sends**. The historical stage may not be
resubmitted. A later read-only analysis cannot categorically exclude a
nonregistered click, but the Python traceback is above the actual Send call.

**Source-free root-cause reproduction:** Disposable owned Gemini tabs with
two neutral PNGs and a short synthetic composer input retained a uniquely
detectable model button. Extending the synthetic composer to a long prompt
reproduced the exact legacy picker exception even though an independent,
single JavaScript DOM snapshot still showed one visible, correctly labelled
`Open mode picker, currently Flash Medium` control. This establishes
inconsistent multi-query Selenium element discovery during a long editor
state, not a proven Gemini service outage or missing Flash model. The
particular Angular/Chrome element-ID transition is not independently proved.

**Production correction:** The shared `gemini_model._owned_picker` now reads
all semantic selectors within one synchronous, read-only DOM evaluation.
A JavaScript `Set` deduplicates actual node identities and tests own-element
visibility, accessibility label and stable model test-id. It returns the
candidate only when **exactly one** semantic control is present. Lightweight
source-free test doubles still use the former semantic Selenium loop when
they do not implement native DOM reads. The normal source vendor and the
shared direct Selenium path now allow up to **four seconds** of bounded
pre-Send re-evaluation only when the picker is temporarily absent/ambiguous
or the element becomes stale. They immediately reject foreign tabs, wrong
Flash-Lite/Pro family and unverifiable labels; neither path sends or replays a
request as a recovery action.

**Live regression evidence:** A second clean disposable Gemini owned tab
with two neutral uploads and a long synthetic prompt now returned the
correct model picker even in the same state that had reproduced the old
exception. This test performed no Send, API, TTS, original-source retry or
student publication. Source-free `test_gemini_model_atomic_picker.py`
exercises atomic control identity, transient missing DOM, false duplicates,
real vendor one-click guard integration, exact Flash rejection and foreign
tab/origin safety. Stage triage independently classifies the trusted local
pre-Send traceback as `GEMINI_UI_PICKER_UNVERIFIED_BEFORE_SEND_NO_RESEND`
and exposes `ATOMIC_OWNED_PICKER_SNAPSHOT_AND_BOUNDED_PRE_SEND_RECHECK`.
Old Serway 7.7 raw attempt and diagnostic receipts remain SHA-bound and
unchanged; any reclassification is read-only. Genuine post-fix G2 acceptance
requires a distinct unclaimed source and remains NOT VERIFIED.
