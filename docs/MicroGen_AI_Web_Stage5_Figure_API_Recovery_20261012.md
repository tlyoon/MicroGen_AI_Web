# MicroGen_AI_Web Stage 5 — Gemini Flash Figure API Recovery (12 October 2026)

**Repository boundary:** `tlyoon/MicroGen_AI_Web` only. No changes to separately managed `tlyoon/MicroGen_AI`.

## Root cause and field verification

The Stage 5 three-PC acceptance test identified a brittle Gemini browser figure-mapping pathway on HP and Yoga6. The Selenium UI could show a filled prompt and an enabled Send control but fail to register a new user turn; other requests registered successfully but never yielded a parseable mapped response. It also left stale image attachments when requests were retried. The previous UI guard failed closed, but neither lecture could proceed past figures.

A direct **Gemini 3.8 Flash multimodal API** pilot with real copied textbook page and crop PNGs returned valid crop-to-figure mappings:

| Host | First real image API response | Result |
|---|---|---|
| HP | Serway 9.9 page 1, `fig_3.png` → `Figure 9.23.png` | Valid 43-character mapping |
| Yoga6 | Serway 13.6 page 1, `fig_1.png` → `Figure 13.13.png` | Valid 45-character mapping |

Both hosts used their existing two-key `%LOCALAPPDATA%\Microvid\.env` configuration without displaying or transferring secrets. On some requests the first key failed and the shared Gemini key-manager correctly failed over to key two.

## Permanent code improvement

`selenium_pipeline/figure_mapping_api.py` makes figure mapping a bounded, model-specific API request with the actual full-page PNG and every crop as image inputs. A result is accepted only when all expected crop filenames appear exactly once in the expected order, each mapping has a useful label, and output PNG target names are safe. Invalid responses are saved separately as rejected diagnostics; no success file is published.

`map_and_rename_selenium_v8.py` now defaults to `MICROGEN_FIGURE_MAPPING_BACKEND=api` for captions. It invokes the API mapper as a bounded child using the same Gemini-compatible Python as TTS; the image-extraction/rename workflow remains intact. To deliberately use legacy Selenium mapping set `MICROGEN_FIGURE_MAPPING_BACKEND=browser`. It still fails closed on all mapping failures.

`selenium_pipeline.runner` skips unnecessary authenticated Chrome launch/browser lock for API-only figure stages, while preserving Chrome ownership and Flash verification for slide/narration stages. It injects the correct code root and Python interpreter into the child environment. This matters because the three existing Docling interpreters do **not** include `google.genai`, whereas each validated TTS interpreter does.

All text-generation models remain defaulted to **Gemini 3.8 Flash**, not Pro.

## Real PC acceptance

Using unchanged, locally isolated source.pdf copies and source-adjacent test outputs under `%LOCALAPPDATA%\MicroGenAcceptance\stage5_20261012\source_tree`:

| Host | Test | Outcome |
|---|---|---|
| Dell-115 | Serway 8.2 (previous pinned Stage 4 release) | **Complete**: figures, 23-page deck, validated narration and Gemini WAVs, audio QA, 1522.84 s MP4, 26,081,048-byte validated video, completion receipt, exit 0 |
| HP | Serway 9.9, updated API figure branch | **Figure stage passed**; mapped 3 crops from 4 page images, source folder preserved |
| Yoga6 | Serway 13.6, updated API figure branch | **Figure stage passed**; mapped 8 figures from 7 page images, source folder preserved |

The API branch additionally passed **262 offline regression tests on HP and 262 on Yoga6**, with nine nonfatal warnings each, including new strict mapping tests. Actual slides/narration/MP4 on HP and Yoga6 remain separate acceptance gates.

## Operational caveat

At approximately 16:37 Malaysia time, an attempted Yoga6 continuation into Gemini browser slide generation correctly refused to acquire `gemini_port_9222.lock`: an already running separate calculus job for subchapter **3.2** owned that Chrome port. **Do not delete the lock or kill that job.** Resume Yoga6 slide/narration only at the next safe browser availability window. The API figures stage does not require this port.

HP's slide generation continuation began from the mapped-figure checkpoint and remained active when this report was drafted.

## Final production gates

1. Confirm HP Serway 9.9 actual slide/narration/QA/TTS/MP4 completion and matching receipt; correct any remaining browser faults.
2. After the existing Yoga6 Chrome owner exits, resume Serway 13.6 from slides and complete the same acceptance.
3. Verify scientific figure placement and narration meanings against source.pdf. Automated crop mapping, receipt hashes and presence of a playable MP4 alone cannot certify scientific accuracy.
4. Only when real host tests and GitHub CI pass, pin/roll out one accepted release revision to production queues and run an idempotent repeatability test.

No source PDFs or existing verified production lecture outputs were overwritten. The independent `MicroGen_AI` code package was not touched.
