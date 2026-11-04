# PR508 — Verified second-source technical candidate and Windows CI contract

This is a general lecture-generation milestone. It does **not** re-run
the failed Serway content, Thomas figure checks, Gemini, TTS or FFmpeg.

## Windows-only CI recovery

PR507 CI run 41817068977 failed in BOTH Windows jobs because
`microgen-reliability-tests.yml` accidentally contained two entries for
`tests.test_windows_sourcebound_e2e_orchestrator`. The pre-existing
`tests.test_windows_only_github_actions_contract` correctly refused
duplicate regression modules (158 entries, 157 unique). All preceding
reported individual tests had otherwise passed: 1,013 unittest cases
in the fast job, and 2,265 pytest passes in the full job up to the
deduplication contract failure.

PR508 removes only the added duplicate entry, retains the original
historical module, and preserves the permanent Windows-only/unique-module
CI contract test. It also registers new second-source acceptance tests.

## A truly independent second original-source candidate

The 2026-10-29 independently accepted historical Thomas §8.4 lesson
(PR362) remains one **specific** SHA-bound example, not evidence of a
newly generated lesson. PR507 independently verifies the original
source, slide/script, reviewed WAV proof and encoded MP4 for a candidate.

PR508 adds a read-only `compare_source_provenance` between these TWO
verified sources. It accepts a second technical candidate only when:

- The first reference is the specifically scoped, SHA-verified and
  previously accepted original lecture (not an arbitrary JSON label).
- A separate source-specific original-slide/script/WAV-to-MP4 technical
  evidence has passed the PR507 independent inspector.
- Both source SHA-256 digests are well-formed and **different**.
- The second candidate has at least one verified encoded MP4 part,
  and neither source declares a publication or self-release approval.

The release-readiness board now reports a separate
`second_distinct_original_technical_candidate_verified` gate and a
`second_independent_original_candidate` summary. This gate is
**purely technical/provenance**. It NEVER sets the existing
`second_distinct_new_original_full_lecture_accepted` academic gate to
true. Independent scientific/figure review, full spoken narration review,
the human voice checks and explicit signoff are still required.

A same-source recheck can never be mistaken for the second lecture.
Missing or tampered evidence leaves the gate blocked. This addresses the
user's repeated concern that development should not count another
round of individual-PDF corrections as a new independent E2E milestone.

## No new paid execution or publication

The current PR implements acceptance evidence handling, not generation
of the missing second genuine original lecture. Actual new generation
must use the safer PR505 one-stage dispatch with explicit provider
authorization, and PR506's previously reviewed audio-to-video mode.
The historical 503/504 unknown-submission guards remain in force.

Native Dell-115 Windows only. No Ubuntu CI, local LLM, HP/Yoga device,
publisher original modification, G: dirty worktree, paid model or TTS
request, or student publication.
