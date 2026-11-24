# G3 source-review no-replay across campaign IDs — 2026-11-24

## Real failure and diagnosis

After PR #620 (merged at `7fa4f621`), the independently owned original Serway §8.2 Example 8.3 context task `a711ab74057f9e6e9f197e80e0c4fb013fb7f34d65625f8830c175b7c5e76c70` had a registered Gemini Neon/High browser Send but **no independently verified model text**. It was correctly recorded `SUBMITTED_OR_UNCERTAIN`, cannot be replayed, and the global campaign marked `HOLD`. It later automatically advanced another genuinely distinct Serway §8.3 source task and reconciled two independently source-validated `UNRESOLVED` reviews. The 4-possible-Send budget was consumed without scientific/publisher/video/student release.

At the next fresh campaign, the source-task selector still enumerated the held §8.2 task as eligible, because the previous `HOLD` lived only in its original campaign journal while a new campaign ID has a new global journal. The shared immutable academic `request_state.json` still prevents an actual duplicate submission, but **new campaign sends may be wasted by reserving the already-uncertain scope**. This is a development failure, not an academic justification for replay.

## Executable repair

`selenium_pipeline/g3_continuous_advance_v1.py::_prior_uncertain_send` inspects the exact per-task academic checkpoint under the original G3 review owner **before candidate selection and before any new global Send reservation**, regardless of campaign ID/date. It excludes a source scope with an unresolved or rejected owned Send; refuses missing or corrupt request state; and refuses `PREPARED_NOT_SENT` when a dispatch-attempt claim already exists. It can continue only genuinely recoverable model-observation claims, which the existing `_saved` path must independently revalidate against the original publisher/slide PDF hashes, exact prompt fingerprint and Neon/High ownership without transmitting another Send. A previous `SOURCE_VALIDATED_ONE_PASS_UNAPPROVED` can still proceed to a genuinely distinct independent challenge.

The handler `g3_cross_campaign_held_send` is registered in the executable recovery registry. It is used for both the original distinct G3 scientific source task and subsequent new textbook-context source tasks.

## Safety and verification

- No paid Gemini API fallback, source regeneration, fabricated scientific agreement, academic acceptance, video/acoustic QA bypass or student publication
- No re-enabling disabled Windows schedules or resetting existing Send budgets
- Fault-injection tests cover a new source claim, all unresolved/rejected claim states, recovered identity, prior validated first-pass continuation, uncertain independent challenge, interrupted missing state, contradictory prepared/Sent marker, and damaged checkpoint state
- Real Dell-115 original §8.2/§8.3 checkpoint read-only inspection: the held §8.2 scope must disappear from newly eligible tasks, while genuinely distinct §8.3 context and untouched original utterance tasks remain available

The next actual content stage is the newly staged §8.3 source-context review with actual publisher passages; do not launch new Selenium Sends until the no-replay guard is merged/tested and a finite new authorized campaign is eligible.
