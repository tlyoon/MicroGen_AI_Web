# MicroGen_AI_Web Stage 5 — Flash API Slide Recovery (12 October 2026)

**Strict repository scope:** `tlyoon/MicroGen_AI_Web`. Do not apply this work to separate `tlyoon/MicroGen_AI`.

## Problem found in the real three-PC acceptance

The figure-mapping fix (PR #39) allowed HP Serway 9.9 and Yoga6 Serway 13.6 to pass real figure extraction and mapping. Resuming HP slides through Gemini Chrome still failed with `Could not send the prompt after retries`. Yoga6's browser was correctly unavailable while an unrelated already-running calculus 3.2 job owned port 9222. Neither situation can be solved by blindly retrying a user-visible Gemini tab.

An independent real source test on HP passed a PDF/document-grounded Gemini Flash API request, producing a complete 13-frame Beamer LaTeX document. It passed the existing `beamer_stack_sanity_check`, pdflatex compilation and page-count gates. No invalid candidate was published.

## Durable correction

- Added `selenium_pipeline/slide_generation_api.py`: bounded multimodal Gemini Flash request with source.pdf, the complete rendered slide prompt, PNG layout metadata, and original verified figure images. It uses the same existing `gemini_keys` API-key failover already used for Gemini TTS. No secrets are copied to files.
- `gen_slides_selenium_v11.py` defaults to `MICROGEN_SLIDES_BACKEND=api`; `browser` remains an explicit compatibility choice. Crucially, the response is still an **untrusted draft** and must pass the original strict Beamer sanity checker, pdflatex compilation, figure-layout checks and citation/provenance gates before the final `slides.tex` and `slides.pdf` are published.
- Failed Beamer attempts retain rejected source and diagnostics; follow-up API requests receive bounded deterministic validation feedback.
- `selenium_pipeline.runner` acquires the Chrome port lock only when browser control is actually needed; the API-only figures/slides stages no longer interfere with another user's Gemini tabs or another active machine-local browser job.
- Different Docling and Gemini/TTS Python environments are selected explicitly, since the Docling environments on the three PCs lack `google.genai`.
- Gemini **3.8 Flash** remains the default text model; Pro is not selected.

## Live field results

| Host | Lecture | Figure stage | Slide stage | Result |
|---|---|---|---|---|
| HP | Serway 9.9 | Gemini Flash API mapped all extracted crops | Gemini Flash API compiled/published a 13-slide PDF | **Pass** |
| Yoga6 | Serway 13.6 | Gemini Flash API mapped all extracted crops | Gemini Flash API compiled/published a 15-slide PDF | **Pass** |
| Dell-115 | Serway 8.2 | Previously pinned source-to-video run | 23-slide deck and complete video/receipt | **Pass on earlier release** |

HP's real generated slide API draft was accepted on its first integrated attempt (8,302 LaTeX characters). Yoga6's was accepted on its first integrated attempt (10,936 characters). Both also passed final citation/source-tracking checks. Lecture artifacts remain in the isolated AppData acceptance tree; original Drive source PDFs have not been altered.

## Scope of certification and remaining gates

At this stage HP and Yoga6 have **not yet** completed new narration, script QA, Gemini speech, speech QA and video assembly with the new slide API release. The older complete Dell-115 run is separate evidence, not permission to stamp the new code as fully certified.

After completing these tests, a human/semantic review is still required to confirm that figure numbers, physics statements and spoken descriptions accurately reflect source.pdf. Automated presence of a valid PDF or MP4 cannot establish scientific correctness.

The new Windows and Ubuntu regression suites should run with updated browser-lock expectations: browser-mode figures/slides and narration still lock Chrome, whereas API-only stages must not.
