# HP Serway 1–7 stale Gemini model menu recovery (v3)

**Source:** HP, 28 November 2026. **Repository:** `tlyoon/MicroGen_AI_Web`.

## Observed failure and proven recovery

The exact owned Gemini model picker stated `Open mode picker, currently Neon Medium` and `aria-expanded=true`, but its live individual option snapshot was empty. Closing and reopening **that same uniquely identified picker** restored three atomic model options: 4 Hydrogen, 4 Neon and 4 Carbon. No model request was submitted by the diagnostic.

The router must keep the existing official-Gemini-app documentation, positive exact menu evidence, stage compatibility, explicit medium-or-higher Thinking verification, source/academic requalification, and provider cost boundaries. It must never relabel Neon as Flash or silently use the paid content API.

`gemini_model._reopen_owned_model_menu_if_empty` performs one bounded pre-Send close/reopen only when the picker reports expanded but contains no observable options. Fail closed if ownership, UI control or menu restoration cannot be established.

## Revision-gated retry, not an unlimited loop

`safe_presend_retry_v1.verified_new_code_presend_retry` accepts an exhausted pre-Send job only if its source SHA is unchanged, its latest log contains exact no-Send model-menu errors and no uncertain-response markers, and the **verified code revision differs** from the one that failed. This permits one new attempt per independently verified code fix, preserving all old logs and counters. Quarantined requests never become automatically retryable.

The HP supervisor `scripts/serway_ch1_7_hp_full_horizon_supervisor_v3.py` is tied to the merged, SHA-pinned repository, reads the existing 46-job checkpoint, and does not reset or duplicate completed videos. Do not deploy a speculative unmerged revision to production.

## Validation baseline

Read-only retrospective audit (28 Nov): 42 old pre-Send menu failures eligible on a new code SHA; 1.1 already video-verified; 1.2, 1.3, 1.5 remain quarantined. HP's currently registered generation/publication/DOCX schedules must retain their recurrence.

Regression tests: `tests/test_hp_serway_stale_picker_retry_20261128.py` plus the existing Gemini mode and source-figure tests. Deployment requires real HP owned-tab model/Thinking preflight and successful required Windows CI checks. The success criterion is **a newly verified video or a distinctly classified reproducible blocker**, not just a task that exits zero.
