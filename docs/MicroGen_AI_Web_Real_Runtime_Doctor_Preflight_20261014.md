# MicroGen_AI_Web — Real runtime preflight and dependency gates

**Engineering date:** 14 October 2026. This is a package-level correction found during the isolated Thomas Calculus 2.2 acceptance pilot.

## Failure discovered on HP

The legacy `python -m selenium_pipeline.runner --doctor` printed `selenium: available` even though the launcher's active Python environment had **no Selenium package installed**. The code merely called `importlib.util.find_spec("selenium")` and interpreted *no exception* as a positive result. However, `find_spec` legitimately returns `None` for an unavailable package. The first real figure-stage launch consequently failed with `ModuleNotFoundError: No module named 'selenium'` before rendering any figures.

After Selenium was installed in a separate isolated pilot virtual environment, the runner next correctly blocked on the absence of a complete `docling + selenium + pypdf` pipeline interpreter. That second requirement was not visible in the original doctor output.

## New contract

`--doctor` now verifies real importability of `selenium.webdriver` and `pypdf`, and also reports whether an interpreter can be resolved for `pipeline_python_executable()` (must import Docling, Selenium, pypdf) and `tts_python_executable()` (Google Gemini TTS). It also checks the visible `pdflatex`, `ffmpeg` and vendored-template dependencies. Optional Cloud Text-to-Speech is reported separately. The doctor prints a clear full-pipeline PASS/FAIL result and exits **2** if incomplete; successful readiness exits **0**.

An end-to-end job still needs a usable Chrome persistent authentication session, writable staging and source permissions, Gemini model selection and sufficient disk space. The preflight does not claim to verify those external conditions.

## Portable, user-controlled environment choices

Avoid forcibly installing Docling in every system Python. Use an existing compatible dedicated Python environment where possible and supply it through `MICROGEN_PIPELINE_PYTHON`. A separate Python with `google.genai` may be supplied via `MICROGEN_TTS_PYTHON`. The launcher must be able to import `selenium.webdriver` for its own browser mode preflight.

Examples (PowerShell):

~~~powershell
$env:MICROGEN_PIPELINE_PYTHON = 'C:\Users\User\miniconda3\envs\docling_3\python.exe'
$env:MICROGEN_TTS_PYTHON = 'C:\Users\User\miniforge3\python.exe'
python -m selenium_pipeline.runner --doctor
if ($LASTEXITCODE -ne 0) { throw 'MicroGen environment not ready' }
~~~

The paths above are illustrative only. On Yoga 6 the actual existing `docling_3` environment was confirmed to import Docling, Selenium and pypdf. Avoid replacing it or installing another large Docling distribution when it already works. The Thomas source PDF was copied into a disposable local pilot tree with SHA-256 comparison and no source file overwrite.

## Regression tests

`tests/test_runner_doctor_gates.py` verifies that a `None` module spec cannot falsely report installed Selenium, missing Docling/TTS subprocess interpreters are blocking, a valid dependency matrix passes, and the CLI reports exit code 2 on a failed doctor.

This change fixes a **preflight false positive**; it does not certify the full Thomas multi-video generation pipeline or release science QA, and it must not mark the unreviewed concept outline as approved.
