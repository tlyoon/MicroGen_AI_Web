# MicroGen_AI_Web: Dell-115 Selenium production adapter

**Status:** Integration candidate; local offline tests and dry-run are possible. A live end-to-end lecture has **not** been certified yet. The original `main` and the source `template_v2` remain untouched.

## Authority and scope

This implementation deliberately **does not use** inherited Selenium logic in the original MicroGen_AI_Web code. The 58 active, non-credential scripts/prompts in `vendor_template_v2/` were copied from the proven **Dell-115** folder:

`C:\Users\tlyoon\OneDrive - Universiti Sains Malaysia\MicroGen_AI\llm_selenium\template_v2`

The reference Serway 22–27 outputs are at:

`C:\Users\tlyoon\OneDrive - Universiti Sains Malaysia\MicroGen_AI\llm_selenium\Serway_22_27`

The original files are not edited. We run a *copy* of the reference scripts in an isolated work folder per subchapter. Thus local `selenium.py` is executed solely from that workspace, preventing collision with the upstream Selenium dependency in the repo's own Python modules.

## Processing stages

1. **Figure and caption abstraction:** `crop_figs_v3.py`, `map_and_rename_selenium_v8.py`, `merge_lettered_figs_v3.py`. Uses the existing Gemini browser integration.
2. **Slides:** `gen_slides_selenium_v11.py` and `gen_slides_prompt_v23.txt`, output `slides.tex` and `slides.pdf`.
3. **Narration:** `gen_script_selenium_v15.py`, output `script.txt`.
4. **TTS:** Gemini API model `gemini-3.8-flash-lite-tts` by default. Select `gemini-3.8-flash-tts` for higher quality or `chirp3` for Google Cloud Chirp 3 HD. Output `slideN.wav`.
5. **Video:** `slice_pdf.py`, `gen_video.py`, output `slides.mp4`.

Gemini **3.1 Pro** is the desired **browser** model for the first three text/figure stages. The Gemini web UI does not expose an API-stable model ID; **this runner cannot force or independently verify the selected UI model**. Before any Selenium stage, the operator must select Pro in the Gemini browser and pass `--confirm-pro` as a human attestation. The checkpoint records a *requested* model rather than a false claim of machine verification.

No Selenium browser quota bypass, account login bypass, proxy evasions, or unrestricted automated scraping is implemented. Use this only when authorized under Google's terms and your institutional account's policies. Selenium web requests may still be rate-limited.

## Dell-115 installation

Open PowerShell on **Dell-115**. Use a dedicated Python 3.11/3.12 virtual environment. Install Chrome, MiKTeX (pdflatex), FFmpeg, and Python packages. Do **not** copy `.env`, credentials, or personal Chrome profiles into the repository.

```powershell
cd "G:\My Drive\Projects\MicroGen_AI_Web"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-selenium.txt
.\.venv\Scripts\python.exe -m selenium_pipeline --doctor
```

If using the Gemini web UI via the reference script, first start its dedicated Chrome debugging session (the existing reference launcher is also included):

```powershell
.\.venv\Scripts\python.exe .\selenium_pipeline\vendor_template_v2\launch_gemini_chrome.py
```

Log in **interactively** when needed. Select the requested Gemini Pro model in the browser before proceeding. Do not store your Google credentials in the repository or bypass authentication screens.

The default output location is local to Dell-115:

`%USERPROFILE%\Documents\MicroGen_AI_Web_Workspace\<chapter>\<subchapter>`

You can override this using `--work-root`. The input folder need not be copied to the production repo.

### Read-only dry-run for Serway 22.1

```powershell
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "C:\Users\tlyoon\OneDrive - Universiti Sains Malaysia\MicroGen_AI\llm_selenium\Serway_22_27" --subchapter 22.1 --dry-run
```

### Chapter-wide dry-run (sequential; one Chrome profile)

```powershell
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "C:\Users\tlyoon\OneDrive - Universiti Sains Malaysia\MicroGen_AI\llm_selenium\Serway_22_27" --chapter 22 --dry-run
```

For individual jobs, `--subchapter 22.1,22.2` runs them sequentially. Never run concurrent workers against one browser profile. A 60-minute watchdog limits a stuck external Selenium child, and a changed upstream stage invalidates downstream checkpoints. If slide, narration or video output must be regenerated, old outputs are archived under `.history/` before replacement.

### Production candidate command (only after permissions, dependencies, and browser model selection)

```powershell
$env:GEMINI_API_KEY = "<YOUR_GEMINI_API_KEY>"
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "C:\Users\tlyoon\OneDrive - Universiti Sains Malaysia\MicroGen_AI\llm_selenium\Serway_22_27" --subchapter 22.1 --confirm-pro
```

The Gemini web subscription covers web-side interaction; **Gemini Flash-Lite TTS is a separate API call**, which requires its own API credentials, quota and billing rules. The `GEMINI_API_KEY` example above is a placeholder. Use Windows credential storage or an environment secret, never a committed key.

### Resume from a failed stage / alternative voice

```powershell
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "<source-root>" --subchapter 22.1 --from-stage tts --tts-provider gemini --tts-model gemini-3.8-flash-tts
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "<source-root>" --subchapter 22.1 --from-stage tts --tts-provider chirp3 --tts-voice en-US-Chirp3-HD-Aoede
```

For Google Cloud, configure `GOOGLE_APPLICATION_CREDENTIALS` to point to a local credential file outside Git, or use application default credentials. The default API TTS voice is **Kore** for Gemini; fallback Chirp 3 uses **Aoede**.

State is stored in `.selenium_pipeline_state.json` per subchapter. Completed stages are reused only when validation succeeds; stages can be rerun with `--force-from narration`, etc. Avoid rerunning the original work directory: the runner prohibits writing in the textbook source or reference script directory. Existing `main` API-based workflows are unchanged.

## Acceptance checklist

- [x] Dell-115 source and reference output paths verified.
- [x] Selenium reference files copied without credentials.
- [x] Configurable pipeline, safe Chrome flag, checkpointing and stage validation added.
- [x] TTS providers Gemini Flash-Lite, Flash and Chirp 3 selectable in code.
- [ ] Fresh environment dependency installation on Dell-115 completed.
- [ ] Authorized browser login + specific Gemini Pro selection verified.
- [ ] Fresh slide and narration generation completed without interaction errors.
- [ ] Fresh end-to-end Serway subchapter produces matching slides, audio and video.
- [ ] Pedagogical/phonetic quality evaluated before merge into `main`.

Known limitations: the Selenium UI may change; the manual Pro-model attestation is not automated verification; a failed browser stage can require an operator to restore login/model selection; old scripts have their own per-stage retry/wait behavior. Avoid running two Selenium workers simultaneously against one Chrome debug port/profile.
