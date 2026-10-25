# PR307 — Actual original Slide4 untimed highlight pixel evidence

Dell-115 Windows-only isolated draft stacked on PR306 exact head `33afb019c453b9c5b3f68b34f22f33bbb2989913`.

## Real original-source observation

PR304 witnessed FIVE original Slide4 narrated text/figure review candidates, and PR305 propagated these through the source-bound audio-readiness gate. Prior to this PR no static-highlight rendering had demonstrated that the exact proposed five source PDF rectangles would produce visible, correctly localized focus frames using the actual MicroGen renderer style.

On Dell-115, PR307 rendered original Thomas8.4 Slide4 PDF page4 at 2x into an **explicit empty review-only directory under Windows LocalAppData**, outside all protected textbook/WAV/MP4 material. Each of the five candidate regions was highlighted independently and compared pixel by pixel with the original unhighlighted slide render. Five distinct PNG previews were created; all five altered-pixel bounding boxes fell within a small border around their previously source-authenticated target rectangles, and each preview has a stable SHA256. The source/slides/script original SHA values were rechecked unchanged.

## Permanent code reuse

The existing normal `highlight_frames.render_highlight_frames` historically contained the standard yellow translucent emphasis drawing code inlined. PR307 extracts its **same styling and geometry** into shared `emphasize_source_rectangles` and makes the normal renderer call it. The new read-only `original_slide4_untimed_highlight_preview` calls that same function, requiring original source hashes and PR304's five original visual review targets. This avoids a second, visually divergent highlighter.

Each output is `UNAPPROVED_source_slide4_candidate_###.png`. The auditor refuses output inside original source directories, existing/stale output files, missing/changed source identities, malformed/out-of-slide rectangles, empty changes, or altered pixels outside target/border. It creates NO WAV, video, timed FFmpeg schedule, new model call, paid provider request or publication.

**This is real original-source STATIC pixel QA only**, not speech-aligned AV validation: actual narration timing, acoustic Kore identity, scientific figure semantics, independent source mathematics review, real encoded <600-second MP4 and YouTube approval remain separately unverified. Full original 71-unit source math queue remains 0 accepted; separate Slide1 title-only scope is not merged.

## Verified test evidence

The actual original Slide4 CLI completed successfully and reported **five distinct PNG SHA hashes and five bounded visible focus regions**. Existing/test fixtures under isolated Windows temp directories do not replace that original run. A focused and neighboring Dell-115 test run passed **11 tests**, including changed source hash, invalid/unbounded targets, stale/reused output folder and render-style sanity; normal existing highlight video preview regression tests still passed.

Original Thomas8.4 source SHA b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068 unchanged. Output files remain only in local review checkpoint folder, not in repository or original teaching folder. Windows-only GitHub Actions enforced by PR303. No historical WAV/MP4 edits, main merge or publication.

**Next meaningful priority:** Wire new source-bound visual/audio gating regressions into fast Windows CI and test all new code under hosted Windows. Real synchronized production must still wait for actual source-approved mathematics, genuine complete Kore narration per unit, and original decoded audio/frame alignment.
