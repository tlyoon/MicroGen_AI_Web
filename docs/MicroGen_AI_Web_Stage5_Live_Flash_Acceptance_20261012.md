# MicroGen_AI_Web Stage 5 — Live Gemini Flash Certification (12 October 2026)

**Strict repository scope:** This report and its code changes concern **tlyoon/MicroGen_AI_Web** only. The separately maintained **tlyoon/MicroGen_AI** repository was not modified.

## Source and checkout isolation

The initial Stage 5 end-to-end pilot ran the Stage 4 release SHA `1ff92021cfd1aa2dd05645645a59eed2f0f15f8a`. The actual Serway `source.pdf` inputs were copied from the published Google Drive tree to machine-local `%LOCALAPPDATA%\MicroGenAcceptance\stage5_20261012\source_tree\<chapter>\<subchapter>\source.pdf`. Generated intermediate/final test outputs remain on those local copies, **not** the source-adjacent G: Drive teaching materials.

Each PC's authenticated Chrome debug port 9222 independently reported `Open mode picker, currently Flash High`. Machine-specific Docling interpreters were verified:
- Dell-115: `C:\Users\tlyoon\.conda\envs\docling_dell\python.exe`
- HP: `C:\Users\tlyoo\miniconda3\envs\docling_win\python.exe`
- Yoga6: `C:\Users\User\miniconda3\envs\docling_3\python.exe`

Gemini text model was explicitly `gemini-3.8-flash`, default TTS `gemini-3.8-flash-lite-tts`. These are source-preservation tests, not production queue assignments.

## Actual live pilots and discovered failures

| PC | Local copy | Verified progress | Acceptance |
|---|---|---|---|
| Dell-115 | Serway 8.2 | Source figures passed; generated 23-page slides PDF; Gemini narration submitted, rejected unsafe script preserved, revised script accepted; script QA passed; started Gemini TTS and made WAVs | **In progress**, not end-to-end complete |
| HP | Serway 9.9 | Docling extracted figures, Gemini Flash active; figure-mapping prompt injection succeeded but submission could not be confirmed; native fallback failed due to Win32 pywinauto/pywin32 DLL import | **Failed safe** at figures |
| Yoga6 | Serway 13.6 | Docling extracted figures; existing Gemini UI carried stale attachment chips; later a new-user-turn submission succeeded but mapping response was missing/unparseable; figure stage remained blocked | **Incomplete** at figures |

The receipt gate refused to certify incomplete outputs. There is **no claim of successful full source-to-video production generation on all three PCs**.

## Stage 5 remediation branch

Branch: `fix/stage5-gemini-tab-isolation-20261012`

1. **Isolate borrowed Chrome tabs.** The vendored Gemini client creates a new chat tab owned by the current automation and never selects, closes or mutates unrelated authenticated user conversations. It only closes the previous tab it owns. Browser ownership is cleared on reconnect and on shutdown.
2. **Use the shared verified send routine** in figure mapping, instead of the fragile figure-specific native Windows Enter/click implementation. A successful submission must be evidenced by a new Gemini turn/route and cleared editor or equivalent verified state. This reduces duplicate blind clicking but does not, by itself, solve unresponsive Gemini UIs.
3. **Fail closed on mapping failures.** An unparseable Gemini response is saved for diagnosis and raises an error; per-page errors stop the stage rather than continuing to later pages and logging a misleading success.
4. **Offline regressions:** synthetic tests verify browser tab ownership, safe shutdown, shared submission and figure-stage failure propagation, in addition to the historical full suite.

### Limitations before production deployment

The live HP figure stage failed even after initial tab isolation and the shared send verifier. The Yoga6 mapping watcher sometimes detected a submitted Gemini turn but saw only a short placeholder response (e.g. `Gemini said`). Neither failure is considered resolved without another successful live figure-mapping run. The separate Dell-115 full-source pipeline remains on its earlier, pinned checkout while active. Do not hot-replace it.

**Next production acceptance:** Finish the active Dell-115 isolated lecture test, verify its figure/source correctness, narration/TTS risk review, audio/MP4 and final receipt. Diagnose HP's missing browser send registration and Yoga6's missing mapping response without modifying unrelated Chrome sessions; re-run bounded figure-only pilots before promoting the corrected branch to full production.
