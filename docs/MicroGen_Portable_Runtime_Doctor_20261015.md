# Reliable dependency doctor when Windows default Python is different

The three-PC Thomas Calculus Section 2.2 acceptance run on 15 October
2026 found that HP had a compatible MicroGen interpreter already installed
but a different, system-default Python was unable to import Selenium.
Yoga6 had Docling and Gemini TTS installed in two existing environments,
and Dell-115 already had valid interpreter routing. The package doctor
correctly failed when invoked from an inadequate controller Python.

**Use the new, offline bootstrap command instead of assuming "python"
on PATH is the correct controller:**

    python -m selenium_pipeline.runtime_doctor

The bootstrap uses only the standard library and selects
MICROGEN_PIPELINE_PYTHON from the process environment or from the existing
user-local Microvid configuration (MICROVID_CONFIG_DIR/.env, else
LOCALAPPDATA/Microvid/.env). It then runs the existing full package doctor
with that interpreter, propagating success/failure unchanged.

If no interpreter is configured, it uses the current Python and allows
the doctor to fail rather than guessing or silently installing dependencies.
When an explicit interpreter path is missing, it fails safely. It never
prints any .env keys other than the selected Python path, and never copies
or uploads a .env file.

Example LOCALAPPDATA/Microvid/.env entries (paths are illustrative):

    MICROGEN_PIPELINE_PYTHON=C:\Users\User\miniconda3\envs\docling_3\python.exe
    MICROGEN_TTS_PYTHON=C:\Users\User\miniforge3\python.exe

For actual production runs, launch selenium_pipeline.runner with the
correct controller interpreter. This entry point is intentionally
**doctor-only** and refuses generation arguments. It does not weaken
scientific approval, browser sign-in, actual TTS listening checks or
student publication gates.

On 15 October 2026, all three production PCs passed the package
dependency doctor after using existing installed environments; no
Docling reinstallation was necessary. The APPDATA config changes
were backed up locally on HP and Yoga6. The original textbook PDF
and repository source outputs were not modified.
