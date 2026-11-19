# PR544 — v7.1 actual checkpoint-to-dispatch handoff on Dell-115

**Source:** user-attached `auto_cont_dev_prompt_v7_to_v7.1.diff` dated 19 Nov 2026. This change is a contract supplement to the established `auto_cont_dev_prompt_v7.md`, not a replacement of its scientific, paid, source or authorization rules.

**Parent:** draft PR542 exact source HEAD `b7de6028a22fdffaf936fe13dafc50d4f987713f`. All source edits in a dedicated isolated Dell-115 `%LOCALAPPDATA%\MicroGen_PR544_20261119` worktree. PR543 source development was separately active and dirty at the time; none of its work or original Drive G: checkout was touched. PR544 must remain draft and be reconciled with PR543 before any merge.

## Historical failure / why v7.1 exists

PR539 implemented a registered, SHA-bound **inner** offline development controller; PR540–542 expanded the curated queue and verified 30/30 source-only historical regression tasks. On completion the inner controller correctly returned `pending_roadmap_task_count=0`, but it did **not** dispatch the next project-level action. A prose recommendation to audit missing history or check the G2/G3/release gates was not an executable handoff. Under v7.1 an exhausted local queue is not global completion, and an observed dispatch (PID/result/event) is mandatory while safe work remains. This problem is independent of the single-Source-Send restriction in the Gemini/lecture stage worker, which must remain intact.

## Executable outer supervisor and normal launcher

New registry signature `V71_CHECKPOINT_WITHOUT_VERIFIED_PROJECT_NEXT_DISPATCH`, allowlisted handler `NORMAL_V71_PROJECT_WIDE_OBSERVABLE_SUPERVISOR`, code `selenium_pipeline/windows_v71_project_supervisor.py`, and normal history CLI opt-in:

`python -m selenium_pipeline.windows_historical_stack_batch_plan --supervise-project-v71 --max-v71-new-dispatches 3`

This **outer** supervisor is explicitly distinct from the one-stage model worker. It source-locks a repository SHA, policy module and LOCALAPPDATA worktree, acquires an OS lock, scans three verified safe project workstreams, and starts approved workers by an actual bounded Windows Python child process. Each child start is backed by OS PID and a fsynced, hash-chained append-only `next_task_dispatched` event. After a source-verified child result, an immutable stage receipt and `checkpoint_committed` event persist the outcome. The supervisor immediately scans and dispatches the next eligible task. The source and event journal are outside the Git tree and original teaching media. Restart reuses source-locked results; claimed-but-unresolved child work is quarantined rather than replayed.

Initial safe project workstreams:
1. **Existing exact-head curated offline regression queue:** reuse/execute the source-bound inner controller, with finite checks and no external model Sends.
2. **Independent global original-Git history-gap inventory:** enumerate all history batches and note source-test coverage still missing (batch1–18 at PR542 parent). Its successful completion is an evidence **inventory only**, NOT historical semantic code approval.
3. **Independent normal read-only release board:** only dispatched after both previous workstreams and independently verified *exact HEAD hosted Windows CI* are satisfied; it reuses the source-bound PR489/PR490/PR362 historic inputs and existing 48-batch source-format receipts. Even a successful **inspection** explicitly keeps all scientific/media/release gates unchanged.

Global pending/blocked workstreams are explicitly included in the output: full historical semantic/dependency review, original G2 source-reviewed scientific acceptance, independently accepted G3 speech/video, and separate student release authorization. Source-risk, external uncertainty, and paid authorization block the appropriate work only; independent eligible offline tasks continue.

If hosted exact-head CI is pending, **the release-board worker is not started**, which is reported in `next_not_started_stages`; after CI succeeds a subsequent normal invocation can dispatch it. When no accessible persistent scheduler has been deployed, the supervisor must report `background_continuation_verified=false` and `persistent_supervisor_installed_and_running_after_exit=false`; it never invents an after-chat runner. The default normal historical CLI remains unchanged unless the explicit supervisor flag is used.

## Mandatory anti-stall and safety tests

`tests/test_windows_v71_project_supervisor.py` covers:
- ordinary task A checkpoint immediately dispatching B and C with observable child PIDs;
- completion of a local inner queue leading to global source-gap inventory;
- quarantined A while independent B begins; dependent release board blocked;
- process-boundary restart after checkpoint A and B, next job exactly once and no duplicate completed work;
- uncertain prior intent without a verified result quarantined and not replayed, while independent work continues;
- actual child-launcher adapter emits PID, durable `next_task_dispatched` followed by `checkpoint_committed`;
- hash-chain event-log tampering fails closed;
- missing exact-head CI leaves the dependent read-only board **not started**;
- a foreign worker-result directory and retired recovery registry fail closed;
- no fictional background supervisor claim in returned status;
- normal historical CLI routing and mutual exclusion with other historical command modes.

The targeted unit suite contains mock launchers; **it is not enough by itself**. Engineering acceptance additionally requires a real source-bound three-workstream Windows process run from the production normal CLI, independent restart, final exact-head hosted CI, a real read-only board at the same HEAD, and a preserved checkpoint. The live runner must actually show child PID(s) and event logs, not merely say it would dispatch.

## Narrow scope / mandatory continuing work

This is a finite initial v7.1 outer supervisor for **three** verified safe workstreams. It does not silently discover or autonomously program every future code change, deploy a persistent Windows background scheduler, replay a possibly consumed Gemini request, run paid providers, mark original G2/G3 accepted, auto-merge draft PRs or release student media. Exhausting its local task set **must not** be reported as completion of the full project. Any further expansion should use historical evidence, targeted patch, real test, faults/regressions, executable registry, and actual restart rather than generic statements of autonomy.
