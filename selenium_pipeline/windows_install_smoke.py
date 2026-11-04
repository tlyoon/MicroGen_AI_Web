"""Native Windows isolated worker install acceptance (offline, no credentials).

Run under the target virtual environment's Python, not the global conda Python.
An import smoke is stronger than find_spec, and pip check catches incompatible
worker dependencies. This does NOT mean a source lecture has been generated.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


REQUIRED_IMPORTS = (
    "fitz", "selenium.webdriver", "pypdf", "PIL",
    "google.genai", "google.cloud.texttospeech", "dotenv", "imageio_ffmpeg",
)


def inspect(*, import_module=None, pip_checker=None, tools=None,
            platform: str | None = None, executable: str | None = None,
            prefix: str | None = None, base_prefix: str | None = None) -> dict:
    platform = sys.platform if platform is None else platform
    executable = sys.executable if executable is None else executable
    prefix = sys.prefix if prefix is None else prefix
    base_prefix = sys.base_prefix if base_prefix is None else base_prefix
    load = importlib.import_module if import_module is None else import_module
    imports = {}
    for name in REQUIRED_IMPORTS:
        try:
            load(name)
            imports[name] = "PASS"
        except (Exception,) as exc:
            # Never echo exception text: provider imports might include secrets
            # in their error details. Only class name for safe diagnostics.
            imports[name] = type(exc).__name__
    if pip_checker is None:
        try:
            proc = subprocess.run(
                [executable, "-m", "pip", "check"], capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=90)
            pip_ok = proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pip_ok = False
    else:
        pip_ok = bool(pip_checker())
    tool_path = shutil.which if tools is None else tools
    external = {
        name: bool(tool_path(name)) for name in ("pdflatex", "ffmpeg")
    }
    python_ok = (3, 11) <= tuple(sys.version_info[:2]) < (3, 14)
    isolated = Path(prefix).resolve() != Path(base_prefix).resolve()
    complete = (platform == "win32" and python_ok and isolated
                and pip_ok and all(v == "PASS" for v in imports.values())
                and all(external.values()))
    return {
        "schema_version": 1,
        "status": ("WINDOWS_ISOLATED_WORKER_INSTALL_PASS" if complete
                   else "WINDOWS_WORKER_INSTALL_INCOMPLETE"),
        "native_windows": platform == "win32",
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "isolated_virtual_environment": isolated,
        "import_checks": imports,
        "pip_dependency_check_pass": pip_ok,
        "external_tools": external,
        "ffprobe_optional_and_not_certified": True,
        "sourcebound_full_lecture_production_certified": False,
        "model_or_paid_tts_called": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.parse_args(argv)
    report = inspect()
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "WINDOWS_ISOLATED_WORKER_INSTALL_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
