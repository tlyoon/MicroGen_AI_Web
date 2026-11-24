# G3 untouched original slide source preflight — Dell-115, 24 November 2026

This repair is for **MicroGen_AI_Web** only. It follows merged PRs #623 and #624 and implements the user's automatic-forward rule without replaying any old browser request or exceeding approved model Send budgets.

## Actual blocker and verified source status

The original source-bound G3 reviewer for Serway §8.2 and §8.3 contains **20 source-audited slides, 4 source-rejected slides, 2 uncertain slides and 6 original untouched slides**. Two historical original source-review Sends have uncertain outcomes and trigger the global original-source reviewer circuit breaker. The browser-science health for new §8.3 tasks is also stale following a verified post-Send Gemini UI error. No further old original source request may safely be re-sent without authoritative disambiguation and genuine new eligibility.

The untouched slides, independently enumerated from the original reviewer state by `_inspect_one(reconcile=False)`, are:
- Serway §8.2 original slides **1 and 14**
- Serway §8.3 original slides **1, 6, 8 and 17**

Prior saved accepted, rejected, uncertain and partially captured source reviews are **not** recast as untouched, because that would replay or overwrite a prior source/model request.

## Executable correction

New `selenium_pipeline/g3_unreviewed_source_preflight_v1.py` registered through `g3_unreviewed_source_preflight` in the executable recovery registry.

1. Reverify the **accepted original rich slide/narration mapping checkpoint**, original `source.pdf`, `slides.pdf`, `script.txt` hashes, original model response owner identity and original source state.
2. For each `ELIGIBLE_FRESH_SOURCE_REVIEW_NO_SEND_YET` slide only, derive the exact original source request SHA, original utterance IDs and text hashes, original visible target IDs/kinds/text hashes and mapping checkpoint hash. No new narration, picture, equation, answer, or outside PDF is introduced.
3. Save an immutable, scope-SHA-bound one-slide source-review preflight under `g3_original_unreviewed_source_preflight_v1`. A restart rederives and byte-for-byte verifies the same report; a changed PDF/script, target or a newly acquired model-send claim fails closed.
4. Automatically run this preflight in the normal G3 multi-section source-only recovery path when `--auto-semantic-source-repair` or `--auto-forward-science` is requested, even when the browser science circuit breaker remains open.
5. Explicitly retain `scientific_approval=false`, `audio_QA=false`, `video_QA=false`, `student_publication_authorized=false` and `new_browser_sends=0` on all tasks. The preflight **does not** authorize or initiate the next source/model Send. It prepares a genuinely new original source request for the existing independently health-checked, finite source-first reviewer in a future eligible run.

## Real source-only test and acceptance boundaries

On original Dell-115 Serway §8.2/8.3 state, with original publisher PDF and model history:

| Subsection | Original slide | Original utterances | Original visible targets |
|---|---:|---:|---:|
| §8.2 | 1 | 1 | 1 |
| §8.2 | 14 | 4 | 9 |
| §8.3 | 1 | 1 | 1 |
| §8.3 | 6 | 5 | 12 |
| §8.3 | 8 | 5 | 8 |
| §8.3 | 17 | 4 | 3 |

**Six immutable source-prepared tasks**, zero original source-science approvals, zero Gemini browser Sends, zero paid API requests, zero student publications. Saved real receipt `G3_UNTOUCHED_SOURCE_PREFLIGHT_REAL_20261124.json` in the Dell checkpoint directory.

Remaining acceptance barriers: these six slides still need **independent actual source-science reviewer results**, and all G3 independent acoustic, video/highlight and second-subsection acceptance remain incomplete. This preflight does not silently fill missing scientific review or start disabled scheduled processes. Reviewer health must be genuinely independently requalified after the latest uncertain Send, and old original scientific Send reservations may never be replayed.
