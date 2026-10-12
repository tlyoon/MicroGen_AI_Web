# MicroGen_AI_Web Stage 6 — final three-PC production acceptance

**Date:** 12 October 2026 (Malaysia, UTC+08:00)  
**Scope:** `tlyoon/MicroGen_AI_Web` exclusively. No modification to the separate `tlyoon/MicroGen_AI` repository.

## Certified release and deployment

The operational code in GitHub main and on Dell-115, HP and Yoga6 is pinned to the same reviewed commit:

`df0ca12700e7fe71b7f3e0bcdef69802cd5c0cd2` — **PR #44, Gemini Flash API narration recovery**.

Every PC has a clean, machine-local checkout at `%LOCALAPPDATA%\MicroGen_AI_Web_Production\repo` and a private `worker.json` with the exact release SHA, its validated Python interpreters and a separate local work directory. Backups of the previous worker JSON files were retained. Each machine's launcher verified its repository origin, clean checkout, model, source path, local work path and pinned release. `MICROGEN_NARRATION_BACKEND=api` and Gemini Flash are production defaults. The previous shared Google Drive Git checkout remains **untouched**.

The **278-test full suite passed independently on all three Windows PCs**, with eight non-blocking warnings per PC. The exact PR #44 head also passed GitHub Actions' full Windows, Ubuntu, reliability and unit-test workflows. The merged main commit's Windows, Ubuntu and regression workflows all succeeded.

## Actual source-to-video acceptance

Each job used a distinct **Google Drive-mounted acceptance tree** containing a byte-for-byte copy of a real Serway textbook source PDF. Existing teaching materials in `G:\My Drive\Serway\Serway_8_14` were **not overwritten**. The sources and generated outputs lived beside each other within the subchapter directories; intermediate work remained in machine-local `stage6_work`.

| Worker | Source subchapter | Slides, script and WAVs | Final MP4 | Audio QA | Structural proof and completion |
|---|---|---:|---:|---|---|
| Dell-115 | Serway 8.2 | 18 | 813.70 seconds; 14,150,549 bytes | 18 of 18 passed, 100% after targeted slide 10 repair | Verified |
| HP | Serway 9.9 | 14 | 769.38 seconds; 13,129,659 bytes | 14 of 14 passed, 100% | Verified |
| Yoga6 | Serway 13.6 | 15 | 1,026.30 seconds; 17,590,052 bytes | 15 of 15 passed, 100% | Verified |

Every final MP4 passed actual video+audio stream and duration validation. After publication/cleanup, an **independent check** on each PC called both `slide_narration_sync.verify` and `cleanup.completed_lecture` against its published Google Drive folder and confirmed the exact page count, numbered WAVs, hashes and QA report. Re-running the pinned production launcher with the same already-complete subchapter skipped generation and left each MP4's SHA-256 **byte-for-byte unchanged**.

## Real failures reproduced and corrections confirmed

- On the previous UI narration route, HP failed to submit a Gemini turn (including a Windows `win32api` DLL failure), while Dell-115 registered a turn but never received a usable response in a 420-second inactivity window. Neither unsuccessful attempt stamped a false completion.
- PR #44 switches production narration to Gemini Flash's API with the source PDF, exact slides PDF, fully rendered source-grounded instruction, existing ordered API-key failover and bounded response validation. The original strict narration cleanup, title checks, script-risk gate, TTS QA and video QA remain active. **Both HP and Dell-115 independently generated valid full narration scripts through the API**, with no Chrome submission or copy interaction.
- Dell-115's first API narration draft contained ambiguous use of “A,” was **archived and rejected**, and the second draft passed. During audio QA, slide 10 initially scored **98.246%**, below the strict 99% threshold. The package regenerated **only slide 10**, reused the other 17 audio files, and subsequently passed **all 18 at 100%** before encoding and publication.
- Yoga6 successfully completed its full source-to-video pipeline through the previously deployed browser route. After updating to the PR #44 production release, Yoga6 independently passed the new full regression suite, verified its structural completion record, and passed the identical-media completed-job reuse check. It was not separately re-run through API narration; API narration itself has direct live evidence on HP and Dell-115.

## What remains beyond Stage 6

**Functional deployment and structural/audio acceptance have passed on three PCs.** This does **not** certify textbook figure selection, visual legibility of every Beamer slide, scientific derivation accuracy, or semantic pronunciation of every physics symbol. Those need source-to-slide content review and targeted corrections before wide publication.

A separate read-only audit of the original 46 Serway subchapters remains at **17 verified complete, 1 published requiring reconciliation, 26 partial slide outputs and 2 without published slides**. These were not silently treated as completed. The recommended next campaign is to validate scientific content, then assign the remaining incomplete subchapters among the three PCs with distinct ownership and proof-gated final publishing. Do not start a bulk rerun before reviewing this acceptance report and the task assignments.

See [Stage 6 Gemini API narration recovery](MicroGen_AI_Web_Stage6_Gemini_API_Narration_Recovery.md) for the implementation and fallback contract and [Stage 5 receipt reconciliation](MicroGen_AI_Web_Stage5_Legacy_Receipt_Reconciliation.md) for the structural-proof repair.
