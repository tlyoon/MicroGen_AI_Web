# Stage 6: MicroGen_AI_Web controlled Windows production deployment

**Scope:** `tlyoon/MicroGen_AI_Web` only. The separately maintained `tlyoon/MicroGen_AI` project must never be changed by this procedure.

## Why local production releases

The older shared Drive checkout at `G:\My Drive\Projects\MicroGen_AI_Web` was verified on three PCs with local edits to `selenium_pipeline/runner.py`, `tts.py`, and `vendor_template_v2/selenium.py`. On Yoga6 Git also could not read those modified files. Never reset, overwrite or update this dirty Drive clone to deploy a release. The shared checkout remains intact as historical evidence.

Instead install a distinct clean Git clone under each Windows user's `%LOCALAPPDATA%\MicroGen_AI_Web_Production\repo`, and require its exact release SHA. Authentication remains at existing, non-committed per-user AppData paths. The PDF source root is a separately mounted directory, and transient work is local, never inside the code repo.

## One-time local deployment

For each authorized Windows PC, after confirming no running job is using the target release directory:

1. `git clone https://github.com/tlyoon/MicroGen_AI_Web.git "$env:LOCALAPPDATA\MicroGen_AI_Web_Production\repo"` if the production repo is missing. Use `git fetch origin main` and a reviewed fast-forward or detached checkout to pin the latest **validated** main commit only when no production process is using that checkout.
2. Configure the existing, independently tested runtime Python (`selenium`, `pymupdf`, `google-genai`, `pypdf`, `imageio-ffmpeg`) and Docling interpreter. Never copy an API key, OAuth token, or Chrome profile into Git or the source tree.
3. Store the following JSON in `%LOCALAPPDATA%\MicroGen_AI_Web_Production\worker.json`, using absolute paths for that PC and the **exact** reviewed main SHA. This file lives OUTSIDE the checkout and will not be tracked by Git:

```json
{
  "release_sha": "REPLACE_WITH_EXACT_VALIDATED_40_CHARACTER_MAIN_SHA",
  "runtime_python": "C:\\Users\\USER\\AppData\\Local\\MicroGenAcceptance\\stage4_20261012\\testvenv\\Scripts\\python.exe",
  "pipeline_python": "C:\\Users\\USER\\miniconda3\\envs\\docling_win\\python.exe",
  "work_root": "C:\\Users\\USER\\AppData\\Local\\MicroGen_AI_Web_Production\\work"
}
```

4. With that user's normal authenticated Chrome debug profile available, confirm the browser is set to **Gemini Flash**. Do not switch to Pro. The managed launcher enforces `MICROGEN_GEMINI_UI_MODE=flash`, `MICROGEN_LLM_MODEL=gemini-3.8-flash`, and API-backed figure mapping.
5. Always dry-run before a production campaign:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\MicroGen_AI_Web_Production\repo\operations\Start-MicroGen_AI_Web.ps1" -SourceRoot "G:\My Drive\Serway\Serway_8_14" -Subchapter "8.2" -DryRun
```

6. To run a real, assigned subchapter, omit `-DryRun`. The launcher validates the repo's remote URL, clean state, pinned SHA, source availability, absolute interpreters and separate work directory before calling the runner. Running two jobs in one Chrome session is also guarded by the runner's OS-level browser lock. Do not assign the same source folder to two PCs.

## Live Stage 6 production-path campaign

On 12 October 2026, the same pinned `7054d9fbed1573460241f679e2e0e9fd87a2936e` code was installed and its dependency doctor passed on **Dell-115, HP, and Yoga6**. All three launched a real seven-stage Selenium/Gemini Flash pipeline from **distinct Google Drive acceptance folders**. Each folder contains a byte-for-byte copy of one original textbook `source.pdf`; this deliberately tests actual mounted-drive publication without changing already-published Serway teaching lectures.

| Host | Distinct acceptance root | Pilot |
|---|---|---|
| Dell-115 | `G:\My Drive\MicroGen_AI_Web_Stage6_Acceptance_20261012\dell115\Serway` | 8.2 |
| HP | `G:\My Drive\MicroGen_AI_Web_Stage6_Acceptance_20261012\hp\Serway` | 9.9 |
| Yoga6 | `G:\My Drive\MicroGen_AI_Web_Stage6_Acceptance_20261012\yoga6\Serway` | 13.6 |

Local staging resides in `%LOCALAPPDATA%\MicroGen_AI_Web_Production\stage6_work`. Outputs are expected beside each copied `source.pdf`, not in the code checkout or an unrelated PC folder. **A start or dry-run does not establish campaign success.** Verify the produced slide PDF, source-grounded graphics, numbered script and WAVs, completed per-slide TTS QA, `slide_narration_sync.json`, MP4 audio/video streams, and a hash-bound `.microgen_completion.json`. Any failure leaves the original source and earlier published lecture outputs intact and requires a checked recovery.

Stage 5 acceptance and hardening are documented in `docs/MicroGen_AI_Web_Stage5_Legacy_Receipt_Reconciliation.md`. Full scientific correctness and visual legibility require independent content review beyond hash and audio tests.

## Post-deployment audit

From a certified checkout, run read-only checks such as:

```powershell
python -m selenium_pipeline.reliability_audit --source-root "G:\My Drive\Serway\Serway_8_14" --expected 46
```

Do not assume 46/46 completion from a prior worker checkpoint or MP4 filename alone. Stage 6 is not a license to publish the separate `MicroGen_AI` outputs or to replace unknown uncommitted changes in the old Drive code checkout.
