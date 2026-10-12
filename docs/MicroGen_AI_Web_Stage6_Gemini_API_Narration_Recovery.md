# MicroGen_AI_Web Stage 6 — Gemini Flash API narration recovery

**Scope:** `tlyoon/MicroGen_AI_Web` only. Do not modify the separately maintained `tlyoon/MicroGen_AI` project.

## Production failure reproduced on 12 October 2026

The production launcher and its 272 offline tests passed independently on Dell-115, HP and Yoga6, but live browser narration was unreliable: Dell-115 Serway 8.2 accepted a Gemini Flash user turn yet produced no extractable response for 420 seconds; HP Serway 9.9 twice failed to submit a prompt to Gemini despite editor/button visibility and suffered a pywin32 `win32api` DLL mismatch in the native-key fallback. The user-visible source, slides and previous accepted media were preserved. Yoga6 Serway 13.6 successfully completed the entire original browser pipeline and published a valid MP4 and completion receipt.

## Implemented behavior

- Production launcher selects `MICROGEN_NARRATION_BACKEND=api` and `gemini-3.8-flash` as the narration default, independent of Chrome, Selenium composer state, or Windows native key bindings.
- API-backed narration receives **both exact** `slides.pdf` and `source.pdf` in order, plus the fully rendered existing `gen_script_prompt_v10_rendered.txt` and the stage's normal strict spoken-narration instruction. It uses the proven Gemini key-pool failover and rejects empty, incomplete and non-STOP responses.
- The API child writes **raw** numbered narration to the isolated workspace; the existing vendored `sanitize_and_rebuild_script`, post-processor and `collect_all_warnings` run unchanged. Failed/unsafe scripts never get a success stamp or published video.
- A browser UI opt-in remains available with `MICROGEN_NARRATION_BACKEND=ui` for controlled diagnosis, but not from the pinned production launcher. For API-only narration, there is **no** browser startup, model-picker action, or Chrome port-lock requirement.
- The helper uses the existing non-committed per-user AppData Gemini keys; secrets are not embedded in source code, prompts, or Git commits.

## Acceptance criteria

1. Offline unit tests exercise both PDFs, rendered prompt inclusion, Flash-only model, malformed slide numbering, non-STOP responses and browser bypass; the full suite must pass on Windows and Ubuntu.
2. Run a controlled HP Serway 9.9 API-only narration pilot against the separately isolated Google Drive Stage 6 acceptance root and existing valid 14-page slide deck. The old failure must not recur, and the completed script must pass title/slide/speech QA.
3. Where practical, repeat Dell-115 Serway 8.2 as an independent second-machine narration sample without touching production teaching materials.
4. Continue from the accepted narration through TTS, audio-fidelity checks, structural sync proof and MP4. Do **not** label the end-to-end route certified until actual outputs and final hash-bound receipts pass.
5. Preserve the previous production release and existing successful lecture outputs until acceptance; never hot-swap an active job. Any new MP4 should be published only through existing validation and non-destructive archival.

This hardening solves a browser transport dependence; it does not, alone, establish scientific accuracy or slide readability. Those require separate content review.
