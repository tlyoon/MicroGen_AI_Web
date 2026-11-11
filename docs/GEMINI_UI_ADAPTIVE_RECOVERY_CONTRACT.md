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
   and descriptions such as `All-around help / 3.8 Flash`. Accept
   `Gemini Flash`, `Flash Medium` and changed version numbers as Flash, but
   **never** Flash-Lite, Pro, Argon, Carbon or any mixed-family selection.
3. **Thinking:** For normal lectures the default is
   `MICROGEN_GEMINI_THINKING_LEVEL=medium`; explicitly supported overrides
   are `low`, `medium`, `high`. The dedicated
   `gemini_thinking.select_owned_gemini_thinking_level` finds the unique
   **Thinking level / reasoning effort** submenu, selects only the exact
   requested radio, reopens it and positively verifies the checked state.
   Options such as `Medium / Balanced depth` are identified by their level,
   not their potentially changing descriptive subtitle.
4. **New chat reset:** Verify Flash and the requested thinking level
   **after** opening New chat, not merely before. The real vendor worker and
   the shared direct browser path apply these checks in normal execution.
5. **Pre-Send:** Verify the model, then the thinking level, then the model
   again immediately before the **one** owned click; no prompt retyping or
   fallback provider attempts. Any missing/ambiguous/wrong state raises a
   pre-Send error. A completed Send may **never** be replayed merely because
   response content is blank or slow.
6. **Evidence:** The runner records the explicitly requested thinking level.
   The vendor emits an owned, timestamped
   `[GEMINI-THINKING] PRE_SEND_OWNED_LEVEL_VERIFIED medium` marker.
   The source-bound G2 coordinator reads only the preserved source-stage log.
   A new stage that declares Medium but does not prove Medium before a
   registered Send is **not accepted**; no old stage receipt is overwritten.
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
