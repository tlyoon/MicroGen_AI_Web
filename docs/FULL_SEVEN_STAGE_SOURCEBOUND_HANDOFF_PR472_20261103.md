# PR472 — Complete runner-to-sourcebound-video handoff (Windows)

## Engineering problem closed

Before this change, the ordinary seven-stage runner request (figures, slides, narration, script QA, TTS, TTS QA, video) failed at admission because the old static-slide encoder violated synchronized multipart video requirements. A separately developed compliant element-audio and video renderer already existed. The paths were disconnected; there was no need for more per-glyph scientific audits.

## Implemented bridge

The runner executes the six original source-bound generation/QA stages with their previously implemented source/artifact SHA-256 reuse. On a request through video, after publishing upstream materials and checking genuine original TTS QA and structural synchronization, it hands off to the existing source-bound element-audio producer and strict synchronized multipart renderer.

The bridge preserves accepted existing videos without regeneration, refuses old static MP4 overwrite, refuses partial element audio or video installations, and does not infer segment narration from ordinary whole-slide WAVs. Existing source-grounded element-planning requirements, full decoded video pixel/audio integrity checks, multipart <600 s constraints and student-publication restrictions remain unchanged.

## What passed and what remains

Windows offline integration tests exercise the real runner with a small generated PDF, stage SHA-bound cached source/WAV outputs, a guarded output installation, and mocks solely at paid/network/real encoded operations. They check no legacy encoding, no repeated TTS for completed videos, no partial batch rerun, exact technical finish dispatch, and original source preservation.

This is engineering integration validation, **not yet** a successful fresh real publisher-to-complete-multipart lecture. Source-rich diagrams and ambiguously source-bound narrated elements can still be rejected by the existing production element planner. Those must be addressed as general production integration failures; do not reopen accepted individual Figure 8.3 pixel similarity or glyph findings.

## Next completion gates

Run one fresh supported original textbook source end-to-end in an isolated Dell-115 Windows location, preserving and reusing source-bound evidence. Fix the first actual production blocker, not another speculative scientific detail. Then test checkpoint recovery, a second representative source, a clean pinned Windows deployment and an integration merge plan. Release remains prohibited without separate authorization.
