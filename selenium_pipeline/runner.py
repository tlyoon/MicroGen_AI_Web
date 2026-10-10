"""Selenium-first MicroGen pipeline using the validated template_v2 scripts.

The vendored scripts are invoked in isolated working folders. This module does
not import the legacy selenium.py, which would shadow the Selenium distribution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass

# Legacy template_v2 scripts emit Unicode status symbols.  Windows may start
# this parent process on cp1252 even when child processes are explicitly UTF-8.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor_template_v2"
REPO = ROOT.parent
DEFAULT_TTS = "gemini-3.8-flash-lite-tts"

# Default model policy: every text-generation stage uses Gemini 3.8 Flash.
# Pro remains available only through an explicit override, primarily for
# controlled A/B benchmarks. Changing MICROGEN_MODEL_PHASE alone never changes
# the selected model.
MODEL_PHASE = os.getenv("MICROGEN_MODEL_PHASE", "development").strip().lower()
if MODEL_PHASE in {"development", "dev", "debug", "testing", "test"}:
    MODEL_PHASE = "development"
elif MODEL_PHASE in {"production", "prod", "release"}:
    MODEL_PHASE = "production"
else:
    raise ValueError("MICROGEN_MODEL_PHASE must be 'development' or 'production'")

DEFAULT_LLM_MODEL = "gemini-3.8-flash"
PRODUCTION_LLM_MODEL = "gemini-3.1-pro-preview"
ACTIVE_LLM_MODEL = os.getenv("MICROGEN_LLM_MODEL", DEFAULT_LLM_MODEL).strip()
DEFAULT_CAPTION_MODEL = ACTIVE_LLM_MODEL
CAPTION_BENCHMARK_MODEL = DEFAULT_LLM_MODEL
DEFAULT_SLIDE_MODEL = ACTIVE_LLM_MODEL
DEFAULT_NARRATION_MODEL = ACTIVE_LLM_MODEL
DEFAULT_PRO = PRODUCTION_LLM_MODEL
DEFAULT_BROWSER_UI_MODE = os.getenv("MICROGEN_GEMINI_UI_MODE", "flash").strip().lower()
if DEFAULT_BROWSER_UI_MODE not in {"flash", "pro"}:
    raise ValueError("MICROGEN_GEMINI_UI_MODE must be 'flash' or 'pro'")

STAGES = ("figures", "slides", "narration", "script_qa", "tts", "tts_qa", "video")
CHROME_STAGES = {"figures", "slides", "narration"}
SCRIPTS = {
    "figures": ("crop_figs_v3.py", "map_and_rename_selenium_v8.py", "merge_lettered_figs_v3.py"),
    "slides": ("gen_slides_selenium_v11.py",),
    "narration": ("gen_script_selenium_v15.py",),
    "video": ("slice_pdf.py", "gen_video.py"),
}
RESOURCE_FILES = ("beamerthemeGelugor.sty", "usmlg.jpg", "usmemb.jpg", "logotype.jpg")
OUTPUTS = {
    "slides": ("slides.tex", "slides.pdf"),
    "narration": ("script.txt",),
    "script_qa": ("script_risk_report.json", "script_risk_report.md"),
    "tts_qa": ("tts_fidelity_report.json", "tts_fidelity_report.md"),
    "video": ("slides.mp4",),
}


def load_microvid_env() -> Path | None:
    """Load non-committed Microvid secrets into this process without overriding explicit env vars."""
    candidates: list[Path] = []
    config_dir = os.getenv("MICROVID_CONFIG_DIR", "").strip()
    if config_dir:
        candidates.append(Path(config_dir) / ".env")
    localappdata = os.getenv("LOCALAPPDATA", "").strip()
    if localappdata:
        candidates.append(Path(localappdata) / "Microvid" / ".env")

    seen: set[Path] = set()
    for path in candidates:
        path = path.expanduser()
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        loaded = 0
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            if name not in os.environ:
                os.environ[name] = value
                loaded += 1
        print(f"[microgen] loaded {loaded} environment setting(s) from {path}")
        return path
    return None


def pipeline_python_executable() -> str:
    """Return a Python executable with the dependencies required by vendored stages."""
    override = os.getenv("MICROGEN_PIPELINE_PYTHON", "").strip()
    candidates = [Path(override)] if override else []
    if os.name == "nt":
        candidates.extend([
            REPO / ".venv" / "Scripts" / "python.exe",
            Path.home() / ".conda" / "envs" / "docling_dell" / "python.exe",
        ])
    else:
        candidates.extend([
            REPO / ".venv" / "bin" / "python",
            Path.home() / ".conda" / "envs" / "docling_dell" / "bin" / "python",
        ])
    candidates.append(Path(sys.executable))

    probe = "import docling, selenium, pypdf"
    for candidate in candidates:
        if not candidate or not candidate.is_file():
            continue
        check = subprocess.run(
            [str(candidate), "-c", probe],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if check.returncode == 0:
            return str(candidate)
    raise RuntimeError(
        "No Python environment with docling, selenium, and pypdf is available "
        "for MicroGen generation stages. Install the pipeline dependencies or "
        "set MICROGEN_PIPELINE_PYTHON."
    )


def tts_python_executable() -> str:
    """Return a Python executable that can import google.genai for Gemini TTS."""
    override = os.getenv("MICROGEN_TTS_PYTHON", "").strip()
    candidates = [Path(override)] if override else []
    if os.name == "nt":
        candidates.append(REPO / ".venv" / "Scripts" / "python.exe")
    else:
        candidates.append(REPO / ".venv" / "bin" / "python")
    candidates.append(Path(sys.executable))

    for candidate in candidates:
        if not candidate or not candidate.is_file():
            continue
        check = subprocess.run(
            [str(candidate), "-c", "import google.genai"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if check.returncode == 0:
            return str(candidate)
    raise RuntimeError(
        "No Python environment with google.genai is available for Gemini TTS. "
        "Install requirements-selenium.txt or set MICROGEN_TTS_PYTHON."
    )


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def blocks(script: str) -> list[tuple[int, str]]:
    """Read the exact template_v2 '**Slide N [duration]:' format."""
    matches = list(re.finditer(r"(?m)^\*\*Slide\s+(\d+)\s+\[[^\]\r\n]+\]:", script))
    result = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(script)
        text = script[match.end():end].strip().strip("*").strip()
        result.append((int(match.group(1)), text))
    if not result or [n for n, _ in result] != list(range(1, len(result) + 1)):
        raise ValueError("Narration lacks consecutive template_v2 slide headers")
    if any(not text for _, text in result):
        raise ValueError("Empty slide narration block")
    return result


def slide_pages(folder: Path) -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    return len(PdfReader(str(folder / "slides.pdf")).pages)


def valid(stage: str, folder: Path) -> bool:
    if stage == "figures":
        return (folder / "crops").is_dir() and any(folder.glob("Figure*.png"))
    if stage in OUTPUTS and not all((folder / name).is_file() and
                                    (folder / name).stat().st_size > 0 for name in OUTPUTS[stage]):
        return False
    if stage == "slides":
        return slide_pages(folder) > 0
    if stage == "narration":
        return len(blocks((folder / "script.txt").read_text(encoding="utf-8"))) == slide_pages(folder)
    if stage == "script_qa":
        report = json.loads((folder / "script_risk_report.json").read_text(encoding="utf-8"))
        return int(report.get("summary", {}).get("blocking", 1)) == 0
    if stage == "tts":
        count = len(blocks((folder / "script.txt").read_text(encoding="utf-8")))
        return all((folder / f"slide{i}.wav").is_file() and
                   (folder / f"slide{i}.wav").stat().st_size > 44 for i in range(1, count + 1))
    if stage == "tts_qa":
        report = json.loads((folder / "tts_fidelity_report.json").read_text(encoding="utf-8"))
        return int(report.get("summary", {}).get("blocking_failures", 1)) == 0
    if stage == "video":
        return (folder / "slides.mp4").stat().st_size > 0
    return False


def check_valid(stage: str, folder: Path) -> bool:
    try:
        return valid(stage, folder)
    except (OSError, ValueError, RuntimeError, ImportError):
        return False


def prepare(source: Path, folder: Path, *, refresh_code: bool = True) -> None:
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise FileNotFoundError(f"Missing source PDF: {source}")
    if folder.resolve() == VENDOR.resolve() or folder.resolve() == source.parent.resolve():
        raise ValueError("Never run the pipeline inside the original source or reference folder")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "source.pdf"
    if target.exists() and digest(target) != digest(source):
        raise RuntimeError("Existing job contains a different source.pdf; use another workspace")
    if not target.exists():
        shutil.copy2(source, target)
    if refresh_code:
        if not VENDOR.is_dir():
            raise FileNotFoundError(f"Missing vendored template_v2: {VENDOR}")
        for item in VENDOR.iterdir():
            if item.is_file() and item.suffix.lower() in (".py", ".txt", ".sh"):
                shutil.copy2(item, folder / item.name)
        for name in RESOURCE_FILES:
            file = REPO / name
            if file.exists():
                shutil.copy2(file, folder / name)


def run_cmd(command: list[str], cwd: Path, log_path: Path, env: dict[str, str],
            timeout_s: int = 3600) -> None:
    """Stream progress without allowing a silent Selenium child to hang forever."""
    from queue import Empty, Queue
    from threading import Thread
    stream: Queue[str] = Queue()
    with log_path.open("a", encoding="utf-8") as logfile:
        logfile.write("\n$ " + " ".join(command) + "\n")
        logfile.flush()
        with subprocess.Popen(command, cwd=str(cwd), env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, encoding="utf-8", errors="replace",
                              text=True, bufsize=1) as proc:
            assert proc.stdout is not None
            def drain() -> None:
                for line in proc.stdout:
                    stream.put(line)
            worker = Thread(target=drain, daemon=True)
            worker.start()
            started = time.monotonic()
            while True:
                try:
                    line = stream.get(timeout=0.5)
                    print(line, end="", flush=True)
                    logfile.write(line)
                    logfile.flush()
                except Empty:
                    pass
                if time.monotonic() - started > timeout_s:
                    proc.terminate()  # Only the child, never all Chrome windows.
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    raise TimeoutError(f"Stage timed out after {timeout_s}s; see {log_path}")
                if proc.poll() is not None and not worker.is_alive() and stream.empty():
                    break
            code = proc.wait()
        if code:
            raise RuntimeError(f"Command failed ({code}): {' '.join(command)}")


def archive_existing_outputs(stage: str, folder: Path) -> None:
    """Move old outputs aside when a stage is explicitly being regenerated."""
    names = {
        "slides": ("slides.tex", "slides.pdf"),
        "narration": ("script.txt",),
        "script_qa": ("script_risk_report.json", "script_risk_report.md"),
        "tts_qa": ("tts_fidelity_report.json", "tts_fidelity_report.md"),
        "video": ("slides.mp4",),
    }.get(stage, ())
    existing = [folder / name for name in names if (folder / name).is_file()]
    if not existing:
        return
    dest = folder / ".history" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f") / stage
    dest.mkdir(parents=True, exist_ok=True)
    for item in existing:
        item.replace(dest / item.name)
    print(f"[microgen] archived prior {stage} files to {dest}")


def job_source(root: Path, key: str) -> Path:
    if not re.fullmatch(r"[0-9]+\.[0-9]+", key):
        raise ValueError("Use subchapter notation like 22.1")
    chapter = key.split(".")[0]
    return root / chapter / key / "source.pdf"


@dataclass
class Settings:
    source_root: Path
    work_root: Path
    subchapter: str
    tts_provider: str = "gemini"
    tts_model: str = DEFAULT_TTS
    tts_voice: str = "Kore"
    tts_qa_model: str = ACTIVE_LLM_MODEL
    tts_qa_threshold: float = 99.0
    chrome_port: int = 9222
    alternate_gemini_user: str | None = None
    confirm_pro: bool = False
    dry_run: bool = False
    force_from: str | None = None
    from_stage: str = "figures"
    through_stage: str = "video"

    def directory(self) -> Path:
        return self.work_root / self.subchapter.split(".")[0] / self.subchapter

    def source(self) -> Path:
        return job_source(self.source_root, self.subchapter)


def execute(s: Settings) -> Path:
    source, folder = s.source(), s.directory()
    if not source.is_file():
        raise FileNotFoundError(source)
    first, last = STAGES.index(s.from_stage), STAGES.index(s.through_stage)
    if first > last:
        raise ValueError("--from-stage must precede --through-stage")
    planned = STAGES[first:last + 1]
    print(f"[microgen] production host: Dell-115 | job: {s.subchapter}")
    print(f"[microgen] input: {source} | work: {folder}")
    print(f"[microgen] model phase: {MODEL_PHASE}")
    print(f"[microgen] browser UI model: {DEFAULT_BROWSER_UI_MODE}")
    print(f"[microgen] caption model: {DEFAULT_CAPTION_MODEL} (benchmark alternative: {CAPTION_BENCHMARK_MODEL})")
    print(f"[microgen] slide model: {DEFAULT_SLIDE_MODEL}")
    print(f"[microgen] narration model: {DEFAULT_NARRATION_MODEL}")
    print(f"[microgen] TTS: {s.tts_provider} / {s.tts_model}")
    if "tts_qa" in planned:
        print(f"[microgen] TTS QA: {s.tts_qa_model} | threshold {s.tts_qa_threshold:.3f}%")
    for stage in planned:
        print(f"[microgen] stage: {stage}")
    if s.dry_run:
        return folder
    if any(x in CHROME_STAGES for x in planned):
        from .launch_gemini import launch
        requested_port = s.chrome_port
        # Keep 9222 for the normal persistent account. If alternate mode is
        # requested without an explicit non-default port, isolate it on 9223.
        if s.alternate_gemini_user and requested_port == 9222:
            requested_port = 9223
        actual_port, _ = launch(s.alternate_gemini_user, requested_port)
        s.chrome_port = actual_port
        from .gemini_model import ensure_mode
        print(f"[microgen] verified Gemini mode: {ensure_mode(s.chrome_port, DEFAULT_BROWSER_UI_MODE)}")
    prepare(source, folder)
    stamp = folder / ".selenium_pipeline_state.json"
    state = json.loads(stamp.read_text(encoding="utf-8")) if stamp.exists() else {}
    signature = digest(source)
    if state.get("source_sha256") not in (None, signature):
        raise RuntimeError("Checkpoint/source mismatch")
    state["source_sha256"] = signature
    state["requested_models"] = {
        "phase": MODEL_PHASE,
        "browser_ui": DEFAULT_BROWSER_UI_MODE,
        "caption": DEFAULT_CAPTION_MODEL,
        "caption_benchmark": CAPTION_BENCHMARK_MODEL,
        "slides": DEFAULT_SLIDE_MODEL,
        "narration": DEFAULT_NARRATION_MODEL,
        "ui_selection_verified_automatically": any(x in CHROME_STAGES for x in planned),
        "tts": s.tts_model,
        "tts_provider": s.tts_provider,
        "tts_qa": s.tts_qa_model,
        "tts_qa_threshold": s.tts_qa_threshold,
    }
    state.setdefault("completed", {})
    if s.force_from:
        for key in STAGES[STAGES.index(s.force_from):]:
            state["completed"].pop(key, None)
    env = os.environ.copy()
    env.update({
        "SAFE_CHROME": "1",
        "GEMINI_DEBUG_PORT": str(s.chrome_port),
        "MICROGEN_MODEL_PHASE": MODEL_PHASE,
        "MICROGEN_GEMINI_UI_MODE": DEFAULT_BROWSER_UI_MODE,
        "MICROGEN_LLM_MODEL": ACTIVE_LLM_MODEL,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        # Prevent incompatible per-user Python packages from shadowing the
        # validated pipeline environment (notably decorator 5.x breaking
        # MoviePy 1.0.3's fps wrapper on Dell-115).
        "PYTHONNOUSERSITE": "1",
    })
    changed_upstream = False
    for stage in planned:
        # A changed stage invalidates every downstream stage, including final video.
        browser_model = {"figures": DEFAULT_CAPTION_MODEL, "slides": DEFAULT_SLIDE_MODEL,
                         "narration": DEFAULT_NARRATION_MODEL}.get(stage, "deterministic-local")
        if stage == "script_qa":
            model_stamp = "script-risk-v1"
        elif stage == "tts":
            model_stamp = f"{s.tts_provider}:{s.tts_model}:{s.tts_voice}"
        elif stage == "tts_qa":
            model_stamp = f"{s.tts_qa_model}:threshold={s.tts_qa_threshold:.3f}:v1"
        else:
            model_stamp = browser_model
        if changed_upstream:
            state["completed"].pop(stage, None)
        if state["completed"].get(stage, {}).get("model") == model_stamp and check_valid(stage, folder):
            print(f"[microgen] reuse validated {stage}")
            continue
        state["completed"].pop(stage, None)
        changed_upstream = True
        log_file = folder / f"microgen_{stage}.log"
        try:
            if stage in CHROME_STAGES:
                from .gemini_model import ensure_mode
                print(f"[microgen] {stage} Gemini mode: {ensure_mode(s.chrome_port, DEFAULT_BROWSER_UI_MODE)}")
            if stage != "tts":
                archive_existing_outputs(stage, folder)
            if stage == "script_qa":
                run_cmd(
                    [
                        sys.executable,
                        "script_tts_risk.py",
                        "--script",
                        "script.txt",
                        "--json",
                        "script_risk_report.json",
                        "--markdown",
                        "script_risk_report.md",
                        "--strict",
                    ],
                    folder,
                    log_file,
                    env,
                )
            elif stage == "tts":
                tts_python = tts_python_executable()
                print(f"[microgen] TTS Python: {tts_python}")
                run_cmd(
                    [
                        tts_python,
                        "-m",
                        "selenium_pipeline.tts",
                        "--folder",
                        str(folder),
                        "--provider",
                        s.tts_provider,
                        "--model",
                        s.tts_model,
                        "--voice",
                        s.tts_voice,
                    ],
                    REPO,
                    log_file,
                    env,
                )
            elif stage == "tts_qa":
                qa_python = tts_python_executable()
                print(f"[microgen] TTS QA Python: {qa_python}")
                run_cmd(
                    [
                        qa_python,
                        "-m",
                        "selenium_pipeline.tts_fidelity",
                        "--folder",
                        str(folder),
                        "--model",
                        s.tts_qa_model,
                        "--threshold",
                        str(s.tts_qa_threshold),
                        "--strict",
                    ],
                    REPO,
                    log_file,
                    env,
                )
            else:
                stage_python = pipeline_python_executable()
                print(f"[microgen] pipeline Python: {stage_python}")
                for script in SCRIPTS[stage]:
                    if not (folder / script).is_file():
                        raise FileNotFoundError(f"Missing reference entrypoint: {script}")
                    run_cmd([stage_python, script], folder, log_file, env)
            if not check_valid(stage, folder):
                raise RuntimeError(f"Validation failed at {stage}; see {log_file}")
            state["completed"][stage] = {"at_utc": utc(), "model": model_stamp}
            stamp.write_text(json.dumps(state, indent=2), encoding="utf-8")
            print(f"[microgen] {stage} OK")
        except Exception:
            state["failed_stage"] = stage
            state["failed_at_utc"] = utc()
            stamp.write_text(json.dumps(state, indent=2), encoding="utf-8")
            raise
    state.pop("failed_stage", None)
    state.pop("failed_at_utc", None)
    stamp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return folder


def doctor() -> None:
    import importlib.util
    for name in ("selenium", "pypdf", "google.genai", "google.cloud.texttospeech"):
        try:
            importlib.util.find_spec(name)
            outcome = "available"
        except (ModuleNotFoundError, ValueError):
            outcome = "missing"
        print(f"[doctor] {name}: {outcome}")
    for command in ("pdflatex", "ffmpeg"):
        print(f"[doctor] {command}: {shutil.which(command) or 'missing'}")
    print(f"[doctor] vendored template: {'available' if VENDOR.exists() else 'missing'}")
    print(f"[doctor] model phase: {MODEL_PHASE}")
    print(f"[doctor] required Gemini browser mode: {DEFAULT_BROWSER_UI_MODE}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MicroGen Selenium pipeline for Dell-115")
    p.add_argument("--source-root", type=Path)
    p.add_argument("--work-root", type=Path, default=Path.home() / "Documents" / "MicroGen_AI_Web_Workspace")
    p.add_argument("--subchapter", help="One or comma-separated subchapters, e.g. 22.1,22.2")
    p.add_argument("--chapter", help="Process all subchapters with source.pdf in chapter, sequentially")
    p.add_argument("--tts-provider", choices=("gemini", "chirp3"), default="gemini")
    p.add_argument("--tts-model", default=DEFAULT_TTS)
    p.add_argument("--tts-voice", default="Kore")
    p.add_argument("--tts-qa-model", default=ACTIVE_LLM_MODEL)
    p.add_argument("--tts-qa-threshold", type=float, default=99.0)
    p.add_argument("--chrome-port", type=int, default=9222)
    p.add_argument("--alternate-gemini-user", metavar="PROFILE_LABEL",
                   help="Use a separate persistent Chrome profile; sign-in is interactive only if needed")
    p.add_argument("--from-stage", choices=STAGES, default="figures")
    p.add_argument("--through-stage", choices=STAGES, default="video")
    p.add_argument("--force-from", choices=STAGES)
    p.add_argument("--confirm-pro", action="store_true", help="Deprecated compatibility flag; browser model selection is now automatic")
    p.add_argument("--dry-run", action="store_true", help="Print plan; do not write files or call Gemini")
    p.add_argument("--doctor", action="store_true", help="Inspect local dependencies")
    args = p.parse_args(argv)
    load_microvid_env()
    if args.doctor:
        doctor()
        return 0
    if not args.source_root or (not args.subchapter and not args.chapter):
        p.error("--source-root and --subchapter or --chapter are required unless --doctor")
    if args.subchapter and args.chapter:
        p.error("Choose --subchapter or --chapter, not both")
    if args.chapter:
        if not re.fullmatch(r"[0-9]+", args.chapter):
            p.error("--chapter must be numeric, for example 22")
        chapter_path = args.source_root / args.chapter
        if not chapter_path.is_dir():
            p.error(f"Missing chapter directory: {chapter_path}")
        jobs = [p.name for p in chapter_path.iterdir()
                if p.is_dir() and re.fullmatch(r"[0-9]+\.[0-9]+", p.name)
                and (p / "source.pdf").is_file()]
        jobs.sort(key=lambda x: (int(x.split(".")[0]), int(x.split(".")[1])))
        if not jobs:
            p.error(f"No source.pdf subchapters under {chapter_path}")
    else:
        jobs = [x.strip() for x in args.subchapter.split(",") if x.strip()]
    for job in jobs:
        execute(Settings(source_root=args.source_root, work_root=args.work_root,
                         subchapter=job, tts_provider=args.tts_provider,
                         tts_model=args.tts_model, tts_voice=args.tts_voice,
                         tts_qa_model=args.tts_qa_model,
                         tts_qa_threshold=args.tts_qa_threshold,
                         chrome_port=args.chrome_port, alternate_gemini_user=args.alternate_gemini_user,
                         from_stage=args.from_stage,
                         through_stage=args.through_stage, force_from=args.force_from,
                         confirm_pro=args.confirm_pro, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
