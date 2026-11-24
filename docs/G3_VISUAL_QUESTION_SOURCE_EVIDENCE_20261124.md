# G3 original rendered visual questions — independent textbook evidence without fabricated approval

This executable MicroGen_AI_Web recovery follows PR #623 (source-only narration transition classification). It preserves the original Serway §§8.2–8.3 source.pdf, slides.pdf, script.txt and historical rejected Gemini response captures.

## Actual gap

Two originally missing source-quotation narration statements are **narration transitions**, not derivations. They cannot truthfully be given invented textbook equations. However, at least one such narration transition introduces a rendered slide containing **two substantive physics questions**. Declaring the narrator's sentence "non-scientific" MUST NOT waive science review of the visible slide questions.

The original Serway §8.2 slide 15 rendered target `s015.group.002-003` includes two questions: (1) Why the cable length R cancels in the final swing-angle result of Example 8.3; (2) How descriptions of gravity differ for an individual object/nonisolated system versus the object+Earth/isolated system. The original source.pdf contains physically witnessed relevant passages on its pages 4–6 and 3–5 respectively, but **literal quotation presence does not verify a scientific answer or the exact slide wording**. The §8.2 slide 2 target "Summary and Review Questions" is a title with no two numbered questions in that target; do not pretend it contains new physics statements.

## Executable correction

New `selenium_pipeline/g3_original_visual_question_source_audit_v1.py` and executable registry handler `g3_original_visual_question_audit`.

- Read each original source-pin verified navigation-only task V2 and revalidate the original rejected whole-slide Gemini model claim/captured response, exact original source/slides/script hashes, and original rendered slide target ID/hash.
- Select only the actual original visible content. For original two-numbered questions, preserve their exact on-slide words and their own per-question SHA; do NOT fake narrator utterances.
- Search the *same original textbook source.pdf* with bounded, contiguous publisher text windows, require meaningful lexical overlap with the actual visible question and original slide, and independently witness the physical PDF page/quote hash. Stage one source-context worklist per visual question (max 4 passages/question). No open-ended external PDFs or LLM memory.
- Preserve the earlier §8.2 source-only narration navigation distinction. A "Summary and Review Questions" heading gets a visual/title audit worklist with zero invented questions.
- Store **new immutable** `g3_original_visual_question_source_audit_v1` worklists under original isolated G3 state; do not overwrite the original rejected model response or earlier V1/V2 semantic source records.
- Integrate into the *normal* `g3_multisection_autoforward_v71` with `--auto-semantic-source-repair` and `--auto-forward-science` so the next eligible publisher/source task is prepared automatically. Source-only worklists consume **zero** Gemini Sends and zero API budget.
- All academic/scientific review, rendered visual QA, original mapping promotion, TTS/acoustic/video, second-subsection acceptance and student publication remain **fail-closed**. Context excerpts are not textbook answers and do not constitute independent scientific approval.

## Validation boundary

Test with real original Serway 8.2/8.3 slides/PDF and the two actual rendered questions. Run source-only physical witness, deterministic checkpoint restart, tampered PDF/hash and immutable task regressions, then full Dell-115 suite and GitHub hosted Windows/Linux CI. Keep original historical G3 uncertain Sends quarantined. Do not activate old disabled Windows scheduled tasks.

Browser source-science reviews remain unsafe until new, independently witnessed Neon/High model health after the latest uncertain Send; the separate PR #623 post-incident health rule must not be relaxed.
