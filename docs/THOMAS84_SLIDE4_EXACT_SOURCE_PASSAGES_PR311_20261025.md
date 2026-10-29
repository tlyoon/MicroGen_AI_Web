# PR311 — Exact original-source quotation evidence for five Thomas Calculus 8.4 Slide-4 utterances

**Dell-115 only, Windows-only draft**, based on CI-green PR #310 head `12623cda168fdbd8ec69a7c7bc58ff7da4dfa14a`. Original textbook `source.pdf`, original lecture `slides.pdf`, original narration `script.txt` all remain read-only.

## What actually failed in PR310

The authorized one-use Gemini academic review was submitted, but its returned raw text was malformed JSON. A format-only offline reconstruction recovered five purported SUPPORTED statements; all five claimed physical textbook passages subsequently failed the existing strict `prove_source_quote_occurrence` original PDF spatial validator. Therefore **ZERO** source-grounded first-pass approvals and ZERO independent two-pass substantive mathematics agreements exist for Slide4. The immutable Gemini raw quarantine and earlier historical attempt receipts remain unchanged.

## New actual-source evidence

New `selenium_pipeline.original_slide4_exact_source_evidence` binds the original source/slides/script SHA256, authentic five Slide4 utterance IDs and spoken hashes, and all five previously source-grounded visual REVIEW target identities and PDF rectangles. It supplies **ten bounded exact PDF passage witnesses** (two per original utterance) from the original six-page physical source, each checked by the existing validator for unique occurrence and physical line/block coherence:

- Intro (.001): original PDF physical page 1 Figure 8.2 caption's `Reference triangles for the three basic substitutions` and `identifying the sides labeled x and a for each substitution.`
- Tangent (.002): physical page 1 exact shared substitution sentence and printed `a2 + x2 = a2 + a2 tan2 u = a2(1 + tan2 u) = a2 sec2 u.`
- Sine (.003): physical page 1 substitution sentence and printed `a2 - x2 = a2 - a2 sin2 u = a2(1 - sin2 u) = a2 cos2 u.`
- Secant (.004): physical page 1 substitution sentence plus physical page 2 printed `x2 - a2 = a2 sec2 u - a2 = a2(sec2 u - 1) = a2 tan2 u.`
- Root/absolute value (.005): Figure 8.2 caption on physical page 1 plus physical page 2 explicit source contextual discussion of restricting the secant substitution.

**LIMITATION:** PDF extraction of Figure8.2 radicals/absolute-value glyphs is demonstrably lossy. A physically verified quote of a squared identity or of the secant domain restriction does **NOT** prove the original narrated root/absolute-value assertion. The fifth unit therefore has source CONTEXT ONLY and stays UNRESOLVED for semantic mathematical approval. The other four remain **awaiting independent source math review**, not approved by simple text presence.

The full original 71-unit math review queue remains distinct from the separately scoped title-only Slide1 receipt; it has zero accepted two-pass substantive source-math reviews. Nothing here generates Kore audio, assigns narration timestamps, encodes an approved sub-600-second video, or authorizes student publication.

## Defensive controls

The original source passage table is fixed, SHA-bound and strict about position and order. Fabricated pages, cross-column sentence concatenations, altered passage text, moved utterance IDs or changed original PDFs cannot pass. No file is written to original teaching folder. No Gemini request, new API cost, Whisper, historical MP4/WAV change, other machine, branch merge or publication.

## Next action

PR312 should feed ONLY independently proved original PDF quotation IDs/pages to future academic review and require review responses to refer to that exact set (or explicitly mark unsupported/ambiguous statements UNRESOLVED), while retaining the existing stringent original PDF spatial validator. First validate locally and under GitHub-hosted Windows CI using PR310 quarantined data **without any new provider request**.
