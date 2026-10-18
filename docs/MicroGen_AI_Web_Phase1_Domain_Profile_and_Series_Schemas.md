> **SUPERSEDED FOR NORMATIVE USE — 18 October 2026:** This historical design contains obsolete 600–630-second allowances. Every published MP4 must be **strictly less than 600 seconds, with no exception**. See [the effective contract](EFFECTIVE_CONTRACT_AND_SUPERSESSION_20261018.md). Retained below for historical traceability, not as live authorization.

# MicroGen_AI_Web Phase 1A — domain profile registry and series schemas

**Implementation status:** Proposed infrastructure / PR candidate; **no generation behaviour change**. This phase lays the foundation for the [integrated architecture blueprint](MicroGen_AI_Web_Integrated_Architecture_and_Implementation_Blueprint_v1.md), without replacing the current production `runner.py` or the physics-specific vendor prompts.

## Currently in scope

Physics and mathematics are the development priorities. The built-in `general` teaching guidance is deliberately neutral. Built-in profiles `physics` and `mathematics` are explicitly marked `development`, **not pedagogically certified**; they require real-textbook tests before making quality claims.

For a future history user, `examples/history_profile.example.json` demonstrates a declarative, `experimental` custom profile without editing the shared engine. No history generation or history-source quality benchmark has yet been performed.

## Read-only CLI (does not launch Gemini or change outputs)

```powershell
python -m selenium_pipeline.domains list
python -m selenium_pipeline.domains inspect --domain mathematics
python -m selenium_pipeline.domains guidance --domain physics --stage narration
python -m selenium_pipeline.domains inspect --profile-file examples/history_profile.example.json
python -m selenium_pipeline.domains guidance --domain history --profile-file examples/history_profile.example.json --stage lesson_planning
```

The command only loads/validates JSON or formats guidance text. It **does not** activate a new `--domain` flag in `runner.py`, generate slides, record a lesson plan, execute plugin Python code, or imply that the chosen subject has passed educational acceptance.

## Stable initial contract

- Domain profiles are declarative, versioned JSON validated in the Python standard library, with a corresponding `schemas/domain_profile.schema.json`.
- Profile fields: `schema_version=1`, safe `id`, semantic `profile_version`, `display_name`, `maturity`, `content_types`, `review_checks` and six `prompt_sections` (`source_analysis`, `lesson_planning`, `slides`, `narration`, `highlighting`, `quality_review`).
- The registry fails closed on unknown built-in domains, invalid IDs, unknown JSON keys, duplicate JSON keys, missing stages, wrong schema versions and mismatch between requested domain and a custom profile ID.
- Custom JSON profiles require an **explicit file path**; the loader never imports or executes arbitrary Python, YAML tags or entry points. Declared `review_checks` are metadata for future QA adapters, **not implemented validators**.
- `render_stage_guidance` combines general fidelity rules with the selected subject's stage rules for future planners/prompts. Until Phase 2+, calling this function alone has no effect on legacy slide/narration output.
- Six source-/media-contract JSON Schemas live under `schemas/`: `domain_profile`, `source_inventory`, `lesson_plan`, `storyboard`, `alignment` and `series_manifest`. They specify the basic structural and versioning contracts. Cross-record references, concept coverage, monotonic event timestamps, subject expert validation, actual MP4 duration and true AV synchronization require **additional semantic checks** in later phases.

## Future extension workflow: History (illustration only)

Copy `examples/history_profile.example.json` into a separately managed file. Edit its terminology, teaching preferences, visual types and review checks. Run the read-only `inspect` command, fix any errors and later submit the profile to semantic/profile-specific QA before treating it as supported. No edits to `selenium_pipeline/runner.py` or FFmpeg should be required when the future loader/adapters are completed. The validated *interface* does not mean a validated *history lecture*.

## Rollout and migration protection

- Current runner retains `figures → slides → narration → script_qa → tts → tts_qa → video`; do not silently switch the production pipeline to a newly proposed series format.
- Phase 2 must implement source inventory and top-down concept-aware planning, including strict `< 630 seconds` final MP4 duration and upstream part planning, **before any new production series generation**.
- Phase 3 must compose slide/narration storyboards and reconcile outstanding RFH figure PRs #56–#58 with the latest GitHub main branch.
- Phase 4 must implement actual TTS timestamp extraction/alignment, semantic element geometry and synchronized highlight rendering.
- Later phases must enforce real MP4 duration via FFprobe, coherent Part i/N continuity, full-media QA and atomic outputs in each selected `source.pdf` subchapter folder.
- Current source-acceptance root remains `G:\My Drive\Projects\Thomas_calculus_13ed`, separate from the cloned code repository. This test-path setting must never become a hard-coded package default.

## Offline acceptance checklist

1. All built-ins parse, have distinct subject guidance and remain marked development.
2. External history example loads as experimental only; no automatic registration or code execution.
3. Incomplete/duplicated/unknown keys, incorrect versions and subject mismatch are rejected.
4. Six JSON schemas pass Draft 2020-12 meta-schema validation, and representative valid/invalid fixture records behave as expected.
5. New tests pass on local clean clones and GitHub Actions on both Windows and Ubuntu; existing historical tests remain passing.
6. No source textbook file, existing subchapter output, authentication profile or production checkout changes.
