# G3 continuous recovery and source-science advancement — 2026-11-24

This is an **executable behavior** of `selenium_pipeline.g3_continuous_advance_v1`, not a future prompt asking the user to say "proceed". It applies to **MicroGen_AI_Web**, not Bosla or MicroGen_AI.

## Forward contract
After each stage, the running controller automatically advances to the next eligible stage without a new human prompt, subject to the explicit per-run finite budget and strict source/author/reviewer authorization. Source, slide and script are always pinned to original files. The normal G3 multi-section source-recovery launcher can call the controller in the **same run** via `--auto-forward-science`.

1. Reconcile original whole-slide source-rejected and uncertain model attempts from their immutable artifacts, without replay. Source-first G3 inventory, figure/slide mappings, and academic source quotations are rechecked before any new Send.
2. Reuse completed separate source-science reviews only after verifying actual original model reply bytes, exact original request fingerprints, witnessed Neon/High family and effort, original textbook PDF SHA, and original rendered slide/utterance identities.
3. If two genuine reviewer passes have independently found the supplied quotation irrelevant or insufficient, automatically retrieve a *different*, physically witnessed publisher context from the same original textbook subsection (the Serway 8.2 / Example 8.3 final R cancellation is the real pilot).
4. Stage a separate `G3_DISTINCT_EXAMPLE_CONTEXT_SCIENCE_REVIEW_READY_NO_SEND` task, SHA-bound to the old double-UNRESOLVED reviewer evidence, original source PDFs, and the new actual publisher quotation(s). This is not a retry of any old request; passages are **not** scientific proof.
5. Automatically requalify exact owned Neon/High using a **new source-free** diagnostic only if fresh health is missing and a finite one-day per-source health budget remains. The diagnostic attaches no textbook. Content/science uses **Selenium web only**, never paid Gemini API fallback.
6. Reserve the finite **global** two-pass source-science budget in a hash-chained campaign before the next model attempt. Perform an independent first and challenge review of the distinct new claim, retaining the raw responses under separate one-Send checkpoints. After genuine completion or source-science disagreement, move to the next eligible task rather than ask for another user turn.
7. On crash, recover the *same immutable* campaign, original owner source, Send reservations, and original saved model responses. Never replay an ambiguous/possibly consumed Send. A same-day restart uses the same derived campaign ID. Do not silently increase a previously committed maximum or change the source.
8. Stop **only** when budget is exhausted, no eligible source/QA task remains, model health or provenance cannot be established, source evidence is insufficient, an unreconciled Send is uncertain, or human/publisher/paid authorization is actually required. Report the exact stop reason, not a vague next-priority request.
9. **Never** promote an unverified mathematical quotation or a two-model opinion into human science acceptance. Original G3 source mapping, acoustic, video/highlight, second-subsection and student publication gates remain separate and fail-closed.

## Invocation — Dell-115, foreground

```powershell
python -B -m selenium_pipeline.g3_multisection_autoforward_v71 `
  --manifest '<G3 original source_manifest.json>' `
  --state-dir '<G3 original state directory>' `
  --max-new-sends 0 `
  --auto-forward-science `
  --science-max-sends 4 `
  --science-max-tasks 2 `
  --science-max-health-probes 2
```

This invocation automatically includes previous `--auto-offline-source-repair` and `--auto-semantic-source-repair`. The per-day source-manifest campaign ID is generated automatically, avoiding another user input and preserving restart reservations. A manual `--science-campaign-id` remains available for exactly pinned audit and restart.

The standalone controller can also be invoked through `python -m selenium_pipeline.g3_continuous_advance_v1` with the same manifest/state, finite caps and a fixed campaign ID; `--dry-run` produces no model Send.

The disabled historical Windows Scheduled Tasks are **not** re-enabled by this controller. This command continues only during an authorized invoked run. The user explicitly did not request an always-on background scheduled job; the controller must not claim to continue processing after a chat turn ends or resume unauthorized host processes.


## Real browser stall recovery (November 24)

The real first new context source-science Send on Dell-115 registered with Gemini Neon/High and both original PDFs but produced no attributable model text. The legacy source watcher had a nominal 240-second inactivity limit yet a separate vendor **1800-second default absolute cap**, prolonging the failure. The original `initial_request` remains immutable `SUBMITTED_OR_UNCERTAIN` with `can_auto_retry=false`; there is no source-science acceptance and no paid API fallback.

The executable registry handler `g3_owned_browser_wall_recovery` applies a **scoped 180-second absolute vendor cap** and **120-second source-science idle window** only to new G3 one-utterance browser science and synthetic model-health checks. It restores the previous environment even after exception; all other model stages retain their existing settings. A no-text or ambiguous Send is quarantined and its **global** Send reservation is consumed. The forward controller now automatically skips a task already marked `HOLD` and chooses a **different** source-eligible task without waiting for the user to say `proceed`, respecting its remaining finite model and health budgets. Never replay the original uncertain question.
