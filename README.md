# MicroGen_AI

## New Dell-115 Selenium integration candidate

A standalone Selenium-first pipeline has been added in [`selenium_pipeline/`](selenium_pipeline/README.md). It uses the **working Dell-115 `template_v2` source scripts** rather than inherited Selenium code from this repository. The package targets Gemini 3.1 Pro for caption/figure abstraction, slide generation, and narration through the authorized browser UI, plus Gemini 3.8 Flash-Lite API TTS (with Flash TTS and Chirp 3 HD options). It includes per-stage checkpoints, limited-time subprocess execution, and a Windows production guide. Run `python -m selenium_pipeline --doctor` or see the linked guide. This is an **integration candidate** until a fresh end-to-end run is validated; the existing API workflow below remains available.

MicroGen_AI is an AI-assisted educational media generation toolkit developed for producing source-grounded teaching materials from a textbook or course PDF. The current package combines the strongest parts of the earlier v6/v7 workflow with the improved pedagogical and media-generation ideas developed in the newer `pri` pipeline.

The main workflow converts a `source.pdf` into extracted textbook figures, LaTeX Beamer slides, slide-by-slide narration, Google Cloud text-to-speech audio, per-slide PDF/WAV assets, and a final narrated MP4 video.

## Design goals

MicroGen_AI is built around two complementary priorities:

- **Source fidelity and completeness.** The v6/v7 lineage contributes strict subchapter isolation, source-order preservation, anti-omission checks, figure matching, deterministic output conventions, and LaTeX robustness.
- **Pedagogical quality.** The newer hybrid instructions add learner orientation, big-picture framing, intuition before formalism, explicit technical bridges, equation interpretation, misconception handling, reasoning checks, visual teaching strategy, and continuous narration across slides.

The result is intended to behave like a reproducible educational production pipeline rather than a generic slide-generation prompt.

## Directory architecture: separate code and teaching-material roots

MicroGen uses **two independent local folders**, never a Google Drive URL:

- **`MICROGEN_ROOT` (automatic)** — the local clone of
  [tlyoon/MicroGen_AI_Web](https://github.com/tlyoon/MicroGen_AI_Web).
  The package locates its code by `__file__`; no configuration is required.
- **`SOURCE_ROOT` (user-defined)** — a separate folder containing a chapter /
  subchapter / `source.pdf` tree. Provide it with `--source-root`, or set
  `MICROGEN_SOURCE_ROOT` once on each PC. This is a **local filesystem path**;
  Google Drive is optional and does not require its browser URL.

Example:

```text
C:\Projects\MicroGen_AI_Web\         # Git clone: MicroGen code only
D:\Physics_Textbook\                # Separate SOURCE_ROOT
  22\
    22.3\
      source.pdf
      slides.tex
      slides.pdf
      script.txt
      slide1.wav  slide2.wav ...
      slide1.pdf  slide2.pdf ...
      slides.mp4
      Figure*.png
      .microgen_work\               # Hidden Selenium staging and checkpoints
```

From inside the cloned repository on Windows:

```powershell
# Choose the source PDF tree for the current shell
$env:MICROGEN_SOURCE_ROOT = "D:\Physics_Textbook"
.\.venv\Scripts\python.exe -m selenium_pipeline --subchapter 22.3 --dry-run
.\.venv\Scripts\python.exe -m selenium_pipeline --subchapter 22.3

# Or specify the same source root directly, without a setting
.\.venv\Scripts\python.exe -m selenium_pipeline --source-root "D:\Physics_Textbook" --subchapter 22.3
```

The package checks write access to `SOURCE_ROOT` and the selected subchapter
before launching paid generation stages. The original `source.pdf` is never
overwritten. All **published** generated teaching media (slides, narration, WAVs,
individual slide PDFs, figures, MP4, QA reports and logs) are written beside
the corresponding `source.pdf`; copied scripts and temporary assets stay in
the hidden work folder. An optional `--work-root` changes only the internal
staging location, **not** the output destination.

The API batch runner has the same two-root convention:

```powershell
python microgen_batch.py --source-root "D:\Physics_Textbook" --targets "22.3,22.4"
```

The batch runner uses a separate `.microgen_batch_work` staging folder for
each subchapter and writes its individual report beside the PDF. It preserves
numbered WAVs and individual slide PDFs as well as `slides.mp4`.

Secrets remain outside both roots in `%LOCALAPPDATA%\Microvid` (or the optional
`MICROVID_CONFIG_DIR`). During development the Selenium browser stages use
Gemini Flash; this change does not switch them to Pro. See
[selenium_pipeline/README.md](selenium_pipeline/README.md) for setup details.

## Current active pipeline

```text
source.pdf
   |
   +--> Figure abstraction
   |      crop_figs_v3.py
   |      map_and_rename_v5.py
   |      merge_lettered_figs_v2.py
   |
   +--> Hybrid slide generation
   |      gen_slides_v20.py
   |      gen_slides_prompt_v20_hybrid.txt
   |
   +--> Hybrid narration
   |      gen_script_v13.py
   |      gen_script_prompt_v8_hybrid.md
   |      narration_polish.md
   |      system_microcredential_architect.md
   |
   +--> TTS
   |      text_to_speech_v25.py
   |
   +--> Per-slide PDF generation
   |      slice_pdf_v21.py
   |
   +--> MP4 assembly
          gen_video_v22.py
          FFmpeg
```

`functions.py` resolves versioned modules automatically and selects the highest available `*_vNN.py` implementation for each pipeline stage.

## Principal outputs

A completed run normally produces:

```text
pages/                  page-level extraction workspace
crops/                  retained image crops
Figure *.png             mapped textbook figures
slides.tex               generated Beamer source
slides.pdf               complete slide deck
script.txt               v7-compatible narration text
script_tts.json          narration/TTS sidecar
slide1.pdf ...            individual slide PDFs
slide1.wav ...            individual narration audio
slides.mp4               final narrated video
```

Generated artifacts are intentionally excluded from version control by `.gitignore`.

## Main entry points

For long, resumable multi-subchapter production, prefer:

```powershell
python microgen_batch.py --help
```

For a simple one-directory source-to-video run:

```powershell
python run_gen_slides_videos.py
```

This orchestrates the existing v7 stages:

```text
run_gen_slides.py
  -> image abstraction
  -> hybrid slide generation

run_gen_video.py
  -> hybrid narration
  -> text-to-speech
  -> slide splitting
  -> MP4 generation
```

For staged execution, the two commands can also be run separately:

```powershell
python run_gen_slides.py
python run_gen_video.py
```

## Installation

MicroGen_AI is currently Windows-first and has been used with Windows 11, Python 3.11/3.12, MiKTeX and FFmpeg.

### 1. Create an environment

```powershell
conda create -n microgen_ai python=3.11
conda activate microgen_ai
pip install -r requirements.txt
```

The requirements now constrain `google-genai>=2.25,<3`, matching the API surface tested on the current Yoga6/Dell/HP workers. Narration also contains a compatibility fallback for older SDKs that do not expose `ThinkingConfig.thinking_level`.

### 2. Install LaTeX and FFmpeg

Install a LaTeX distribution that provides `pdflatex` (MiKTeX is currently used in production).

Install FFmpeg or install `imageio-ffmpeg`. The video stage resolves FFmpeg in this order:

1. `MICROVID_FFMPEG`
2. packaged `imageio-ffmpeg`
3. system `PATH`

### 3. Figure abstraction dependencies

`crop_figs_v3.py` uses Docling and `pdf2image` for textbook figure extraction. Docling can be dependency-sensitive, so a dedicated environment is sometimes preferable.

Typical additional packages are:

```powershell
pip install docling pdf2image pillow
```

On Windows, `pdf2image` also requires Poppler to be installed and available on `PATH`.

The figure-size threshold `ikB` in `crop_figs_v3.py` may need to be adjusted for a textbook family. For example, Thomas' Calculus 13th edition has been run successfully with a threshold around 4.0 kB.

## Gemini API key pool

For resilient production runs, configure Gemini credentials in priority order in the local `%LOCALAPPDATA%\\Microvid\\.env` file:

```text
GEMINI_API_KEY_1=...
GEMINI_API_KEY_2=...
GEMINI_API_KEY_3=...
```

MicroGen_AI tries key 1 first. Key/account-specific failures such as invalid credentials, billing depletion, permission failure, or quota exhaustion fall through to the next configured key. Temporary Gemini service errors such as `503 UNAVAILABLE` retry the same key with exponential backoff rather than rotating credentials. The shared billing circuit opens only after the configured key pool is exhausted by billing failures. The legacy single `GEMINI_API_KEY` variable remains supported.

## Default Gemini models

MicroGen_AI uses stage-specific Gemini defaults so that high-volume visual matching is cheaper while teaching-content generation remains on the more reliable Pro model:

```text
figure mapping:   gemini-3.8-flash
slide generation: gemini-3.1-pro-preview
narration:        gemini-3.1-pro-preview
```

Figure mapping defaults to `gemini-3.8-flash`. Slide generation and narration remain on `gemini-3.1-pro-preview`. Defaults can be overridden globally with `MICROGEN_LLM_MODEL` or per stage with `MICROVID_FIGURE_MODEL`, `MICROVID_SLIDE_MODEL`, and `MICROVID_NARRATION_MODEL`.

## Multi-PC Gemini coordination

When several computers generate subchapters against the same Gemini project, do not let the Gemini-heavy stages run independently. MicroGen_AI now includes `gemini_lane.py`, a cooperative FIFO lane that serializes figure mapping, slide generation, and narration across participating machines while still allowing Docling extraction, LaTeX compilation, Google Cloud TTS, PDF slicing, and FFmpeg work to proceed independently.

Enable the lane by setting the same synced directory on every worker, for example on machines that share the same Google Drive mount:

```text
MICROGEN_GEMINI_LANE_DIR=G:\My Drive\MicroGen_AI\coordination\gemini_lane
```

The lane uses queue tickets, a synchronization settling window, a heartbeat, stale-ticket recovery, and a post-request cooldown. It also tolerates short Google Drive/Desktop mount interruptions by waiting for the shared lane path to reappear instead of immediately failing the subchapter. Gemini requests use conservative exponential backoff for transient `429`, `500`, `502`, `503`, `504`, `RESOURCE_EXHAUSTED`, `UNAVAILABLE`, and related capacity errors. Useful tuning variables are `MICROGEN_GEMINI_LANE_SETTLE_SECONDS`, `MICROGEN_GEMINI_LANE_CLAIM_GRACE_SECONDS`, `MICROGEN_GEMINI_LANE_COOLDOWN_SECONDS`, `MICROGEN_GEMINI_LANE_STALE_SECONDS`, `MICROGEN_GEMINI_MAX_RETRIES`, `MICROGEN_GEMINI_BACKOFF_BASE_SECONDS`, and `MICROGEN_GEMINI_BACKOFF_MAX_SECONDS`.

For a single-PC run, leave `MICROGEN_GEMINI_LANE_DIR` unset and the coordination layer is disabled. For multi-PC work, every participating machine must point it at the same shared directory; otherwise the workers are not in the same lane.

Billing/prepayment failures are treated differently from ordinary rate or capacity limits. A Gemini `402` prepayment-credit failure is non-retryable: the first worker that encounters it opens a shared circuit breaker, releases the lane immediately, and causes the other workers to pause Gemini stages instead of wasting repeated API calls. The circuit automatically allows a serialized probe after `MICROGEN_GEMINI_BILLING_RECHECK_SECONDS` (default 1800 seconds), and it can also be inspected or cleared manually with `python gemini_lane.py --status` or `python gemini_lane.py --clear-circuit`.

Figure mapping now acquires the lane per Gemini request rather than for an entire subchapter. This preserves the one-request-at-a-time safety rule while allowing fairer interleaving across Yoga6, Dell-115, HP, or other workers.

## Resumable batch runner

`microgen_batch.py` is the preferred entry point for long multi-subchapter production. It keeps a persistent `.microgen_checkpoint.json` for every subchapter and resumes at the earliest incomplete stage. A narration failure therefore does **not** repeat Docling extraction, figure mapping, or slide generation; similarly, a TTS/video failure resumes only from the failed downstream stage.

Example:

```powershell
python microgen_batch.py \
  --source-root "G:\My Drive\Textbook_Project" \
  --targets "1.1,1.2,1.3" \
  --main-py "C:\path\to\python.exe" \
  --docling-py "C:\path\to\docling_env\python.exe" \
  --commit main
```

The runner performs a startup environment check, validates outputs at every stage, pauses rather than fails when the shared Gemini billing circuit is open, publishes final `slides.pdf`, `script.txt`, and `slides.mp4` atomically, and retains numbered slide PDFs and narration WAV files in each source subchapter after successful publication.

## Credentials

Credentials are deliberately kept outside the repository.

By default MicroGen_AI reads shared API configuration from:

```text
%LOCALAPPDATA%\Microvid\
```

The default files are:

```text
%LOCALAPPDATA%\Microvid\.env
%LOCALAPPDATA%\Microvid\google_cloud_credentials.json
```

A minimal `.env` is:

```text
GEMINI_API_KEY=your_key_here
```

Optional legacy providers may also use:

```text
OPENAI_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here
```

The credential directory can be overridden with:

```text
MICROVID_CONFIG_DIR
```

For Google Cloud TTS, `GOOGLE_APPLICATION_CREDENTIALS` takes precedence when explicitly set.

**Never commit real API keys or Google Cloud service-account JSON files.**

## Quick start — recommended Selenium runner

Clone the **MicroGen_AI_Web code repository** into one local folder, separate from the textbook PDF tree:

```powershell
git clone https://github.com/tlyoon/MicroGen_AI_Web.git
cd MicroGen_AI_Web
$env:MICROGEN_SOURCE_ROOT = "D:\\Physics_Textbook"   # Local PDF tree on this computer
.\\.venv\\Scripts\\python.exe -m selenium_pipeline --subchapter 22.3 --dry-run
.\\.venv\\Scripts\\python.exe -m selenium_pipeline --subchapter 22.3
```

Follow the [Selenium setup instructions](selenium_pipeline/README.md) first to create the virtual environment, install dependencies, and configure the browser. Use `microgen_batch.py` for the separate API-based batch workflow. Both supported orchestration entry points publish verified media beside their input `source.pdf`.

**Legacy low-level scripts:** `run_gen_slides_videos.py` and `run_gen_slides.py` still operate on their current working directory. They are internal/legacy components, not the recommended two-root entry points. Run them only within an isolated subchapter staging workspace if debugging.

## Codex batch-generation prompt

For automated multi-subtopic production on a local PC, use:

[`prompts/CODEX_Textbook_to_Video_Lecture_Set_Prompt.md`](prompts/CODEX_Textbook_to_Video_Lecture_Set_Prompt.md)

This prompt is designed to be submitted directly to Codex. Normally the user only needs to define the local `SOURCE_ROOT_DIRECTORY`. By default it:

- pulls the current `main` branch of this repository,
- installs missing Python and external dependencies when possible,
- uses the v7/hybrid model defaults,
- selects all valid `source.pdf` subtopics under the first top-level source folder,
- runs figure abstraction, slides, narration, TTS, and MP4 generation,
- publishes verified outputs back into each source subtopic directory, and
- retains verified `slideN.pdf`, `slideN.wav`, `slides.mp4` and checkpoint files in each subchapter; working caches stay isolated.

The prompt also accepts explicit subtopic ranges, an alternate code-package URL/ref, and a common LLM override. A local folder path identifies the textbook source tree; no Google Drive browser link is necessary. GitHub `main` is the default authoritative package source.

### Runtime LLM override

Leaving the Codex prompt at `LLM_MODEL = V7_DEFAULT` preserves the package's stage-specific defaults. To use one explicit model for the active Gemini stages during a run, set:

```text
MICROGEN_LLM_MODEL=<model-name>
```

Stage-specific variables such as `MICROVID_SLIDE_MODEL`, `MICROVID_FIGURE_MODEL`, and `MICROVID_NARRATION_MODEL` take precedence when deliberately supplied.

## Hybrid slide-generation approach

The current slide-generation prompt intentionally merges two instruction systems rather than replacing one with the other.

The v6/v7 framework remains authoritative for:

- source isolation and content coverage
- macro source order
- anti-omission checks
- figure identity and provenance
- LaTeX/Beamer validity
- density and overflow control
- deterministic output structure

The newer pedagogical layer adds:

- an Orientation & Roadmap rather than a purely administrative outline
- an explicit big idea and governing question
- intuitive framing before formal derivation
- technical bridge explanations between compressed reasoning steps
- interpretation of equations, not just display of equations
- source-supported misconception handling
- deliberate visual-representation choices
- reasoning-based concept checks
- a conclusion that reconnects formalism to the motivating idea

Major source units are not freely reordered. The system may insert local bridge, comparison, concept-check or figure-focus slides where they improve understanding without changing the source's substantive sequence.

## Hybrid narration approach

Narration preserves the v7 requirement of exactly one narration block per slide while using the stronger `pri`-style teaching logic.

The narration stage therefore aims to:

- remain grounded in `source.pdf`
- correspond exactly to the fixed slide order
- explain rather than merely read the slide
- connect slides into a continuous lesson
- interpret equations in spoken language
- direct attention to important features of figures
- make hidden reasoning steps explicit
- produce TTS-friendly `tts_text`

`script.txt` remains the v7-compatible human-readable output, while `script_tts.json` preserves structured narration and TTS-specific wording.

## Video generation

The current MP4 stage uses a pri-derived FFmpeg workflow adapted to v7's PDF-based slides:

```text
slideN.pdf + slideN.wav
        -> rendered PNG
        -> H.264/AAC segment
        -> exact narration-duration constraint
        -> FFmpeg concat
        -> slides.mp4
```

Each segment duration is derived from the WAV sample count, avoiding the multi-second timing drift observed with older `-shortest` behavior on some FFmpeg versions.

## Repository contents

This repository intentionally contains both the active hybrid pipeline and selected legacy utilities from the v7 package. Some older modules remain for compatibility, rollback, MCQ/XML workflows, and historical utility functions.

The active versions for the main video workflow are currently:

- `map_and_rename_v5.py`
- `gen_slides_v20.py`
- `gen_script_v13.py`
- `text_to_speech_v25.py`
- `slice_pdf_v21.py`
- `gen_video_v22.py`

## Security and source-material policy

This repository does **not** include textbook `source.pdf` files, generated textbook figures, finished videos, or credentials.

Users are responsible for ensuring that any source material processed with MicroGen_AI is used in accordance with applicable copyright, licensing, institutional and privacy requirements.

## Status

MicroGen_AI is an actively evolving teaching/research automation package. The pipeline has been exercised on real university-level textbook subchapters and is being hardened through production runs. Some legacy scripts are less standardized than the current hybrid video workflow.

## Author

**Yoon Tiem Leong**  
School of Physics  
Universiti Sains Malaysia (USM)

## License

Released under the MIT License. See `LICENSE`.
