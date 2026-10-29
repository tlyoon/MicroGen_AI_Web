# PR313 — Bind source-locked academic review to each exact visual target

26 October 2026. Windows-only, Dell-115-only offline change stacked on PR #312 head `f61304d0906eb13c41225929c13c7d2859a5fac2`. No Gemini submission or new TTS/media/publication permissions.

## Original issue

PR312 verified that each textbook quotation came from the correct one of five original Thomas' Calculus 8.4 Slide-4 utterances, but it accepted *any* existing Slide-4 target ID for any utterance. A response could therefore pass the target-existence check while pointing to an unrelated triangle/text region. Packet quote digests were also checked only for SHA-like length, and Python `bool` values could compare equal to integer source page numbers.

## Repair in normal validator

`selenium_pipeline.source_locked_academic_review.assert_original_slide4_source_packet` now requires each packet's `review_target_id` and PDF rectangle to match its exact original-source registered review region, including Figure8.2 crop strips not present in the raw PDF text target list, and each `source_quote_sha256` to equal SHA256 of the spatial verifier's whitespace-normalized quote. `require_quote_locked_model_reply` accepts a nonnull response target ONLY when it equals that exact preverified review region for the corresponding narration (not a different normal element or source-derived crop region on the slide); source-page values must be exact integers rather than boolean values. Null targets and source quotations remain allowed for honest UNRESOLVED replies. The principal-root/absolute-value fifth narration remains mandatory UNRESOLVED.

## Tests and safety

Synthetic Windows-only focused unittest suite executed on Dell-115 from an isolated AppData Git clone: 17 total with 11 passed, 6 expected original-asset skips, 0 failures, before adding the real-packet regression. Added adversarial tests for in-slide cross-utterance visual target swaps, forged packet target IDs, quotation tampering without updated hash, and boolean page IDs; these rejected as intended. A genuine original-source packet fixture test now covers all five real review-only regions. Authentic geometry revealed that the three Figure8.2 crop strip IDs and one combined radical text ID are intentionally NOT among the six raw slide text element IDs. A newly added source-locked result mapping admits only their five exact immutable registered region IDs and PDF rectangles, without changing the normal generic slide element validator. Hosted CI and genuine original tests require independent confirmation before acceptance.

Original `G:\My Drive\Projects\MicroGen_AI_Web` dirty worktree, source PDF, slides/script, historical WAV/MP4, source review queue, immutable PR310 Gemini quarantine and protected main remain untouched. No paid API, Whisper, other PC, Ubuntu job or publication. This PR is mathematical-review input/output hardening, NOT academic proof. Full original independent queue stays 0/71 accepted; genuine Kore audio, frame/word-level sync, encoded strictly shorter-than-600-second student video and release are still unverified.

## Next steps

Verify original Dell source-packet compatibility and all Windows hosted tests; do NOT send Gemini again without an explicitly new scoped owner authorization. Then pursue independent mathematical review and genuine audio/video acceptance while retaining fail-closed publication gates.
