# Exact source-example / figure-label geometry — initial visual mapping advance

Real Dell-115 original-source production inspection, 30 October 2026. This automated module establishes the **label's visible rectangular position** on the compiled PDF **only** where the original PDF also contains exactly one corresponding source header.

Read-only input contracts: immutable original source.pdf, slides.pdf and script.txt; slide/page count and exact ordered slide numbering; source/header uniqueness; single rendered-label bbox; hash-check before and after. Ambiguous source-page matches and duplicated/multiline visual geometry fail closed. It is integrated into the complete 41-slide `visual_element_mapping_readiness.inspect_all` report and a standalone out-of-tree JSON evidence manifest; original textbook/PDF/WAV outputs are untouched.

Real source results:
- Thomas §8.4: 17 slides, 10 numbered labels seen; 9 unique source-anchored label geometries; 1 ambiguous.
- Thomas §8.5: 11 slides, 5 labels; 2 source-anchored; 3 ambiguous.
- Thomas §8.6: 13 slides, 4 labels; 4 source-anchored; 0 ambiguous.
- Total: 41 slides, 19 candidate labels, **15 unique labelled rectangles** and 4 rejected ambiguities.
- Only **1 of those 15** numbered labels is referred to explicitly by matching label/number words in its narration script. The other 14 are **not** assumed to be narrated merely because they appear on the slide. A literal spoken reference is still not a proven ASR word timestamp, and no highlight is approved.

**Not yet proven:** the content of a scientific figure or subfigure, complete equation geometry or equivalence, narration-to-element timing, encoded visual highlights or MP4 duration. Even a unique Example/Figure label is not enough to authorize audio/video. The existing full-deck inspection still rejects 41/41 slides for inadequate exact source/script correspondence; do not silently relax this gate.

Future hardening should match actual figure-image panels and equation objects to source evidence and then map word-aligned genuine PCM timing to highlighted object coordinates; independent decoded-pixel QA must be performed on the final encoded MP4. No manual academic-review blockade, publication or false acceptance is introduced.
