# PR316 — Valid constant-square-root arithmetic must not stall future lecture generation

**26 October 2026 — Windows-only Dell-115, stacked on PR315 exact head `091e5cf5b848f40246cd47fe678eb7629910569a`, independently hosted Windows CI green.**

The owner requested a general mathematical defect detector **and corrector**, without falling into endless QA. PR315 added the semantic detector, Gemini regeneration feedback, normal pre-TTS block, and independent storyboard TTS gate. Read-only application to genuine Thomas 8.4, 8.5, 8.6 sources revealed 8.4's signed right-triangle defects but also a new false positive in Thomas 8.6 Slide5:

> "Substituting four gives two over the square root of four, which simplifies to one ..."

That equation `2/sqrt(4) = 1` is **true**. The initial domain-sign detector matched the word "square" in *square root* and a later "simplifies to", incorrectly treating exact positive constant `sqrt(4)` like variable `sqrt(x^2)=|x|`. This would have caused costly, futile Gemini regeneration of already correct narration, contrary to the owner's autonomy and cost goals.

**Permanent narrow fix:** Require an **explicit squared variable/trigonometric quantity** in the same clause (for example `sqrt(x squared)`, `sqrt(secant squared)`) or a clear "taking the square root eliminates the radical" trigonometric substitution shortcut. The latter still requires explicit sign/domain justification. Do not downgrade root/zero-domain safety generally. Strict on detected sign hazards, tolerant of valid constant arithmetic.

**Genuine independent Dell-115 cross-subchapter audit:**
- Original **8.4**: signed-angle/unsigned-leg and root branch hazards still detected and TTS blocked.
- Original **8.5**: 20-slide narration, zero detector blockers.
- Original **8.6**: 17-slide narration, zero detector blockers after fixing false alarm.
- Exact positive constant sqrt cases, actual signed root counterexamples, unrelated physics, stale signature reports, Gemini retry-feedback and no-mutation negative controls: **11 tests passed, no skips or failures** on actual Dell original files.
- These measurements prove **this limited rule detector** behaves better; they **DO NOT** establish all source mathematical statements correct, or permit student publication. Independent AI-source and figure/audio review remain mandatory.

The separately authorized **one** original Slide4 *corrected-script* Gemini academic initial review on Dell-115 submitted original source and slides PDFs at 12:50 local 26 October 2026 but Gemini returned **ZERO text characters** after upload/send verification. Its attempt is permanently recorded as `SINGLE_AUTHORIZED_WINDOW_EXHAUSTED` with no automatic retry; empty raw quarantine saved outside protected G original. This is a **model/server response blocker**, not mathematically approved corrected content. The generic pipeline source QA and valid pre-TTS scripts can progress in other subsections without inventing an academic receipt or resending a potentially processed request.

**Media:** 17 original Thomas 8.4 WAVs total 632.7107s; historical encoded MP4 633.93s, fails <600s. PR314 staged 5 mathematically corrected narration/TTS candidates, not delivered WAV. Final per-unit Kore audio, exact element sync, approved multipart encoded <600s MP4 remain unverified. Protected original source/script/WAV/MP4 and dirty working tree remain untouched. No HP/Yoga/Zenbook, Whisper, paid API, Ubuntu checks, model resend or student release.

**Next:** Keep original-source AI-review case deferred until a NEW explicit window can be initiated without duplicating the ambiguous submission; meanwhile implement stronger general source-provenanced media-timing acceptance and review routing for more generated sections rather than waiting on Gemini.
