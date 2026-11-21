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
5. **Video:** `slice_pdf.py` plus the maintained `selenium_pipeline/video_ffmpeg.py` encoder, output `slides.mp4`. This replaces the legacy MoviePy encoder (affected by `fps=None`/`NoneType` failures on Dell-115). The new renderer checks numbered PDF/WAV pairing, encodes each slide with H.264/AAC, concatenates with FFmpeg, validates both streams and duration, and only then atomically publishes `slides.mp4`. The previous MP4 is archived in `.history/video_<timestamp>/`.

### Automatic cleanup after complete publication

When all stages finish successfully and a subchapter has its final
`slides.tex`, `slides.pdf`, `script.txt`, and `slides.mp4` published
beside `source.pdf`, MicroGen automatically removes the generated
intermediate files and its managed workspace. It retains the original
`source.pdf`, all editable `*.tex`, every figure and logo needed to
compile them (`*.png`, `*.jpg`, `*.jpeg`, `*.sty`, and other referenced
assets), final slides, narration script, MP4 video, useful QA reports,
unrelated original files, and a small `.microgen_completion.json` receipt.

Transient per-slide WAV/PDF files, temporary TTS data, LaTeX
compilation auxiliaries, stage logs, extracted page caches and
unneeded crops, previous automatic history backups, and
`.microgen_work` staging are removed only **after** successful final
publication. LaTeX-referenced nested graphic folders are preserved,
and any missing referenced image blocks deletion rather than losing
the ability to recompile the slides. The receipt allows completed
lectures to skip costly regeneration on later ordinary runs.
Failed and partially processed jobs retain their workspace and
checkpoints for resumption.

This intentionally trades video-only rebuild convenience for
uncluttered completed source folders: an already-cleaned lecture
will need its per-slide WAV and PDF intermediates regenerated before
another video-only assembly. A deliberate full rebuild can start with
`--force-from figures`; it is not an automatic rerun. This cleanup
does **not** retroactively delete previously generated materials
unless you subsequently run their final stage successfully.

### Video-only regeneration (does not call Gemini)

When a subchapter already has matching `slide1.pdf` … `slideN.pdf` and
`slide1.wav` … `slideN.wav`, it can be assembled independently:

```powershell
# Run in the MicroGen code repository after installing requirements-selenium.txt
.\.venv\Scripts\python.exe -m selenium_pipeline.video_ffmpeg --folder "D:\Physics_Textbook\25\25.4"

# Or run the managed pipeline from its video stage (slices slides.pdf first)
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "D:\Physics_Textbook" --subchapter 25.4 --from-stage video --force-from video
```

The first command never changes the original PDF, WAVs or slide deck. If the
pairs are incomplete, it fails before replacing any existing MP4. It requires
PyMuPDF (`fitz`) and `imageio-ffmpeg` or an external FFmpeg executable.
Configure `MICROVID_FFMPEG` only when a custom FFmpeg is necessary.

**Dell-115 verification, 10 October 2026:** Reference subchapter 25.4 had
11 complete PDF/WAV pairs. Direct FFmpeg-only regeneration finished
successfully, producing a 488.93-second, approximately 10.2 MB MP4 containing
audio and video. The previous MP4 was archived. This validates the video-only
stage, not a full LLM-to-video end-to-end production run.

### Permanent Gemini Flash model policy

**Gemini 3.8 Flash is the permanent default in both development and production** for figure/caption mapping, slide generation and narration. Previous user comparisons showed better lecture output quality with Flash than with Gemini 3.1 Pro. TTS remains on the Flash family via `gemini-3.8-flash-lite-tts`.

`MICROGEN_MODEL_PHASE=production` only changes the diagnostic phase label; it **does not** automatically select Pro. Pro is an explicit optional comparison via `MICROGEN_LLM_MODEL` and `MICROGEN_GEMINI_UI_MODE`. Do not assume a Pro-labelled model is superior.

The normal default is currently `MICROGEN_MODEL_PHASE=development`. An explicit `MICROGEN_GEMINI_UI_MODE=flash|pro` or `MICROGEN_LLM_MODEL=<model>` can override the corresponding selection for diagnostics, but should not be needed for ordinary development runs. The runner now verifies/selects the requested Gemini UI mode automatically in the authenticated persistent browser session.

No Selenium browser quota bypass, account login bypass, proxy evasions, or unrestricted automated scraping is implemented. Use this only when authorized under Google's terms and your institutional account's policies. Selenium web requests may still be rate-limited.

## Dell-115 installation

Open PowerShell on **Dell-115**. Use a dedicated Python 3.11/3.12 virtual environment. Install Chrome, MiKTeX (pdflatex), FFmpeg, and Python packages. Do **not** copy `.env`, credentials, or personal Chrome profiles into the repository.

```powershell
cd "G:\My Drive\Projects\MicroGen_AI_Web"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-selenium.txt
.\.venv\Scripts\python.exe -m selenium_pipeline --doctor
```

### Gemini Chrome account behavior on Dell-115

The production runner now launches/reuses a **persistent MicroGen Gemini Chrome profile automatically**. In normal operation, do **not** pass an account option: the **existing `template_v2` automation profile** at `%LOCALAPPDATA%\gemini_automation_<Dell-115-hostname>` is reused. This is the profile already used by the proven Dell-115 launcher, so its existing authorized Gemini login is preserved and MicroGen does not ask for a username or password. Manual sign-in is needed only if Google itself expires that session.

```powershell
# Normal/default account: no login request generated by MicroGen
.\.venv\Scripts\python.exe -m selenium_pipeline.launch_gemini
```

To deliberately use another Google account, invoke the explicit alternate-profile option. The value is only a local profile label; MicroGen never types a username/password into Google. Chrome opens a separate persistent profile on port 9223 and the user signs in interactively if required.

```powershell
# Explicit alternate account/profile
.\.venv\Scripts\python.exe -m selenium_pipeline.launch_gemini --alternate-user teaching-account
```

The same option can be supplied directly to a production job as `--alternate-gemini-user teaching-account`. Subsequent runs with the same label reuse that alternate profile's login session.

Chrome 136+ intentionally does not honor remote-debugging switches against Chrome's ordinary default data directory. Therefore MicroGen uses its own persistent non-default Chrome data directories rather than trying to attach remote debugging to Dell-115's personal Chrome `Default` directory. This preserves the desired no-prompt behavior after the one-time dedicated-profile authentication while respecting Chrome's security model.

Both development and production select Gemini Flash in the authenticated browser session by default. Pro is never selected implicitly. Do not store Google credentials in the repository or bypass authentication screens.

### Two-root layout and output location

`MICROGEN_ROOT` is the GitHub code checkout and is detected automatically;
`SOURCE_ROOT` is a **separate**, readable/writable directory containing
`<chapter>\<subchapter>\source.pdf`. Example on Dell-115:

```text
MicroGen code: G:\My Drive\Projects\MicroGen_AI_Web
SOURCE_ROOT:   G:\My Drive\Serway\Serway_8_14
Source PDF:    G:\My Drive\Serway\Serway_8_14\8\8.1\source.pdf
```

**This example is for illustration only, not a hard-coded default.**
Each user must configure their own `MICROGEN_SOURCE_ROOT` to point at the
folder containing **their** PDF source directory tree, or pass
`--source-root` every run. Without either setting, MicroGen stops rather
than using the code checkout as the source folder.

```powershell
cd "G:\My Drive\Projects\MicroGen_AI_Web"

# Illustrative example only; replace paths on your computer:
$env:MICROGEN_SOURCE_ROOT = "G:\My Drive\Serway\Serway_8_14"
.\.venv\Scripts\python.exe -m selenium_pipeline --subchapter 8.1 --dry-run

# Or explicitly select the source root for one run:
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "G:\My Drive\Serway\Serway_8_14" --subchapter 8.1 --dry-run

# Optional permanent Windows user setting (applies to new terminals):
[Environment]::SetEnvironmentVariable("MICROGEN_SOURCE_ROOT", "G:\My Drive\Serway\Serway_8_14", "User")
```

A per-PC setting in `%LOCALAPPDATA%\Microvid\.env` is another supported
method; see [`.env.example`](../.env.example). An explicit `--source-root`
overrides the environment variable. Google Drive **browser links and IDs**
are not used as filesystem paths; use the local/mounted Drive folder.

**Recommended for multiple computers:** Keep **both** the MicroGen code
repository and PDF source tree in Google Drive-synchronized directories.
This makes all original PDFs and generated teaching materials accessible
to Dell-115, Yoga6, HP and other PCs. Run **different subchapters** on
different machines for **pseudo-parallel generation**; never run the same
subchapter concurrently. Give every worker read/write permission to the
source root and its nested chapter/subchapter folders, allow Drive time
to synchronize, and set `MICROGEN_GEMINI_LANE_DIR` to the **same shared
Google Drive lane** for cooperating workers. Gemini-heavy calls then
serialize while other independent processing can overlap. Auth and
secrets stay in local `%LOCALAPPDATA%\Microvid`, **not** in Google Drive.
The source root and code checkout must remain separate directories.

Generated stages publish their slide files and audio beside
`source.pdf`. After **all** stages complete successfully, per-slide
WAV/PDF intermediates are removed while final slides, LaTeX sources,
recompilation images, narration script, MP4, and QA reports remain.
Temporary files and copied Selenium scripts remain isolated within the
subchapter's `.microgen_work` directory. Passing `--work-root` only changes
staging; it never changes the published output destination.

For an existing Dell-115 run created with the former workspace, supply
`--work-root "$env:USERPROFILE\Documents\MicroGen_AI_Web_Workspace"` to reuse
its checkpoints and generated WAVs instead of restarting the stages.

Credentials default to `%LOCALAPPDATA%\Microvid\.env` and
`%LOCALAPPDATA%\Microvid\google_cloud_credentials.json`, not either root.
Ensure Windows, Chrome, Python 3.11/3.12, the required pip packages, MiKTeX
(`pdflatex`), FFmpeg, and an authorized Gemini session are available.

### Historical reference dry-run for Serway 22.1 (older OneDrive source tree)

The following Serway 22-27 examples refer to the **earlier reference test dataset**;
they are not the configured source root for Dell-115. For the current shared
Serway 8-14 example, use `--source-root "G:\My Drive\Serway\Serway_8_14"`
and `--subchapter 8.1` as shown above.

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

**Gemini 3.8 TTS SDK/ledger recovery:** Production Gemini 3.8 TTS uses
`client.interactions.create` (not the older `models.generate_content` speech
payload) and requires `google-genai>=2.25,<3`. When Dell-115's protected
default Python still has an older SDK, the normal TTS watchdog checks the
registered `TTS_EXISTING_ISOLATED_SDK_RECOVERY` mechanism and reuses the
existing, preflight-verified `%LOCALAPPDATA%\\MicroGenGeminiSDK\\venv`
interpreter. It does not install software or send a paid request as recovery.
A missing or invalid interpreter fails closed. Every subsequent authorized
Interactions TTS create call is entered in the SQLite cost ledger *before*
the provider send, with tokens from provider usage when available or a
clearly labeled audio-duration estimate; failed/uncertain sends remain
separately visible. This recovery never authorizes paid lecture content,
scientific reviews or unapproved paid TTS audio QA.

### Resume from a failed stage / alternative voice

```powershell
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "<source-root>" --subchapter 22.1 --from-stage tts --tts-provider gemini --tts-model gemini-3.8-flash-tts
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "<source-root>" --subchapter 22.1 --from-stage tts --tts-provider chirp3 --tts-voice en-US-Chirp3-HD-Aoede
```

For Google Cloud, configure `GOOGLE_APPLICATION_CREDENTIALS` to point to a local credential file outside Git, or use application default credentials. The default API TTS voice is **Kore** for Gemini; fallback Chirp 3 uses **Aoede**.

While generation is incomplete, checkpoint state stays in `.selenium_pipeline_state.json` in the hidden staging workspace, with a copy beside `source.pdf` after successful stages. Completed stages are reused only when validation succeeds. After successful final publication, that transient checkpoint is replaced by a compact `.microgen_completion.json` receipt and staging is removed. Rebuilding an already-cleaned lecture requires regenerating any discarded intermediates; a full refresh can use `--force-from figures`. Avoid rerunning the original work directory: the runner prohibits writing in the textbook source or reference script directory. The legacy API-based batch workflow uses a separate video implementation.

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


## Non-negotiable Gemini transport policy (November 2026)

**Selenium only** for all lecture-content generation (figure crop/caption mapping,
slide generation and narration scripts) and independent scientific/pedagogical
review. No failure, timeout, exhausted retry, fallback setting, local API key,
other provider, or historical authorisation permits a chargeable API request
for these stages. If Gemini Selenium is unavailable or a Send is uncertain,
preserve source-bound checkpoints and stop; never switch to paid API.

**Paid Gemini API is permitted for TTS synthesis** (subject to the established
provider/model/cost controls). Paid Gemini API for **TTS fidelity or voice
quality checking** is permitted **only when explicitly approved for that
invocation**. That separate approval does not authorise scientific/text
review or content generation. By default, running a full pipeline through
the `tts_qa` stage without explicit approval fails closed before generating
the QA report or making a billed request.

Example for an explicitly authorised paid audio-QA run:

```powershell
python -m selenium_pipeline.runner --source-root "<source-root>" --subchapter 8.2 --from-stage tts_qa --through-stage tts_qa --confirm-paid-tts-qa
```

The production launcher accepts `-ConfirmPaidTtsQa` for this purpose.
Do not pass it unless this run's TTS quality checking has been approved.
Old `--communication-mode api`, `--communication-mode fallback`,
`MICROGEN_COMMUNICATION_MODE=api|fallback`, and legacy per-stage
text-content API backends are rejected or forced to browser mode.
The central `paid_api_policy.require_paid_gemini_api` gate and versioned
recovery registry prevent accidental paid requests before credentials,
API client construction or failover. All revised guards are regression-tested
with fake clients and **zero real paid requests**.


## Automatic Gemini request accounting (2026-11-21)

The code now writes a **local, restart-safe, one-row-per-Gemini-attempt**
SQLite journal BEFORE potentially submitting requests. The cost ledger does
not replay an uncertain model Send. Its default path on Windows is:

`%LOCALAPPDATA%\MicroGen_AI_Web_Costs\gemini_requests.sqlite3`

Each record contains UTC timestamp, machine, model, purpose, stage, chapter,
subsection, transport (`selenium` or `api`), token counts with provenance,
estimated USD cost, logical request ID, attempt number, retry count and
request outcome. **API keys, prompt contents, attached PDFs, WAV bytes, raw
response contents and email/user identities are never recorded.**

Use in the verified checkout:

```powershell
python -m selenium_pipeline.gemini_request_cost --summary
python -m selenium_pipeline.gemini_request_cost --csv "$env:LOCALAPPDATA\MicroGen_AI_Web_Costs\requests.csv" --summary
```

- For **paid API** TTS and explicitly authorized audio QA, prefer the SDK's
  `usage_metadata.prompt_token_count` and
  `usage_metadata.candidates_token_count` plus thinking tokens. If unavailable,
  estimate text from UTF-8 length and TTS audio at 25 tokens per second of
  returned audio, and explicitly mark the source. PDF/audio input estimates
  without provider usage are **partial**, not measured token totals.
- 2026-11-21 standard rates used until 2026-12-31 (USD per 1 million input /
  output tokens): Gemini 3.8 Flash-Lite TTS **0.50 / 6.00** (audio output);
  Gemini 3.8 Flash TTS **0.50 / 9.00** (audio output);
  Gemini 3.8 Flash **0.75 / 3.75** (text output).
  Source: https://ai.google.dev/gemini-api/docs/pricing .
  Unknown-model or post-expiration paid costs remain `NULL`, never zero.
- For **Selenium**, Google does not expose Developer API billing token metadata;
  text counts are marked as heuristics and `estimated_usd_cost=0` means
  **zero incremental Developer API usage charge**, NOT that the Gemini web
  subscription is free. Uploaded files and hidden reasoning are not fully
  measurable from the browser.
- All outcomes are represented: captured, possibly submitted, registered but
  pending response, or uncertain after timeout. A failed API attempt may have
  incurred a fee; uncertain charges are **excluded from the captured-cost
  subtotal** and shown separately, never represented as a verified $0.
- SDK retries/key rotations and watchdog respawns carry logical attempt
  identities; separate rows account for each possible provider request.
  Concurrent local workers use SQLite WAL and committed pre-send records.
- A missing ledger, unwritable disk or disabled versioned accounting registry
  blocks a new Send. No paid fallback or QA authorization is enabled by this
  feature. Original G2/G3 scientific acceptance and publisher gates remain
  unchanged.

A test environment automatically uses a separate temporary ledger; override
only for explicit controlled diagnostics via `MICROGEN_GEMINI_COST_LEDGER_PATH`.
For multi-PC reports, export/merge the three local ledgers by unique request ID;
**do not point three PCs at one SQLite file on Google Drive**.
