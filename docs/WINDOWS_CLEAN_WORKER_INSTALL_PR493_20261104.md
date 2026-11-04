# PR493: Native Windows clean worker installation acceptance

**Development target**: solely Dell-115 and native Windows. This PR closes
the previously untested *worker Python installation* blocker, **not** the
sourcebound full lecture acceptance or student-facing release.

## Clean standalone install

```powershell
# First run is read-only: does NOT create a venv
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-MicroGen-Windows.ps1

# Install into a NEW local isolated worker directory (never overwrite)
$venv = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104'
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-MicroGen-Windows.ps1 -Install -TargetVenv $venv

# Later verification: no download/install/model/Gemini/TTS required
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-MicroGen-Windows.ps1 -SmokeOnly -TargetVenv $venv
```

`-Install` refuses existing directories, paths outside `LOCALAPPDATA`, and
missing Windows platform. Default performs no installation. The only package
install uses the disposable venv's pip, never global conda; dependencies from
`requirements-worker.txt` are checked via actual imports plus `pip check`.
FFmpeg and pdflatex are checked as external tools, FFprobe remains optional
for this worker smoke, and no original PDF/audio/video is opened.

### Actual Dell-115 4 Nov 2026 verification

A first attempt found the machine's **global** pip config includes
`https://pypi.ngc.nvidia.com` as an additional index with repeated DNS
failures. Preserved its incomplete environment and changed ONLY the
per-invocation installer to set lowercase `PIP_CONFIG_FILE=nul`
(the exact pip-config disable value on Windows) and use the official
`https://pypi.org/simple` index with bounded retries. No global/user pip
settings were edited.

The second clean independently isolated environment was actually created at:
`%LOCALAPPDATA%\MicroGen_AI_Web\pr493_clean_pypi_20261104`.
Physical native Windows pip installation **exit 0**; all eight imports
(PyMuPDF, Selenium, pypdf, Pillow, google-genai, Cloud TTS,
dotenv, imageio-ffmpeg) **PASS**, `pip check` **PASS**, external FFmpeg
and MiKTeX **PASS**. No provider request, paid TTS or student publication.
This is a **real** worker installation acceptance, not a mocked test.

The read-only `windows_release_readiness_board` accepts
`--worker-python <exact LOCALAPPDATA venv Scripts\python.exe>`
to independently execute the installed worker smoke and close ONLY its
worker dependency gate. Stale user-local `main` remains a reported
informational discrepancy; a fresh `origin/main` is the source of
merge ancestry, never a forced update of the protected dirty shared G:
checkout. The release remains blocked for independent real original-source
end-to-end audio/visual qualifications, cumulative stack review, exact
final-SHA GitHub CI, and explicit final authorization.
