"""Safe cross-PC entry point to launch the full MicroGen dependency doctor.

This standard-library-only bootstrap reads ONLY MICROGEN_PIPELINE_PYTHON from
the existing user-local config. It does not print or copy credentials, test
Chrome logins, produce content, call Gemini, or modify configuration.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


class RuntimeDoctorError(ValueError):
    """The configured interpreter cannot be used safely."""


def _configured_interpreter(environ: dict[str, str]) -> str | None:
    """Use the same config-file priority and non-overriding semantics as runner."""
    value = environ.get("MICROGEN_PIPELINE_PYTHON", "").strip()
    if value:
        return value
    possible = []
    custom = environ.get("MICROVID_CONFIG_DIR", "").strip()
    if custom:
        possible.append(Path(custom).expanduser() / ".env")
    local = environ.get("LOCALAPPDATA", "").strip()
    if local:
        possible.append(Path(local).expanduser() / "Microvid" / ".env")
    for config in possible:
        if not config.is_file():
            continue
        values = []
        for row in config.read_text(encoding="utf-8-sig").splitlines():
            stripped = row.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, val = stripped.split("=", 1)
            if key.strip() != "MICROGEN_PIPELINE_PYTHON":
                continue
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1]
            if val:
                values.append(val)
        if len(set(values)) > 1:
            raise RuntimeDoctorError("Conflicting pipeline Python settings in local config")
        if values:
            return values[0]
        # The main runner reads only the first available local .env file.
        return None
    return None


def select_runner_python(environ: dict[str, str] | None = None,
                         current_python: str | None = None) -> str:
    """Use explicitly configured interpreter; otherwise current Python."""
    environ = dict(os.environ if environ is None else environ)
    raw = _configured_interpreter(environ)
    if raw:
        resolved = Path(raw).expanduser()
        if resolved.is_file():
            return str(resolved)
        found = shutil.which(raw)
        if found:
            return found
        raise RuntimeDoctorError(
            "Configured MICROGEN_PIPELINE_PYTHON is unavailable; fix user config"
        )
    return str(sys.executable if current_python is None else current_python)


def main(argv: list[str] | None = None) -> int:
    """Run dependency diagnosis only; never accept generation-stage arguments."""
    args = [] if argv is None else list(argv)
    if args:
        raise RuntimeDoctorError("Runtime doctor accepts no generation commands")
    try:
        python = select_runner_python()
    except (RuntimeDoctorError, OSError) as exc:
        print("[runtime-doctor] configuration error:", exc, file=sys.stderr)
        return 2
    print("[runtime-doctor] selected pipeline interpreter:", python, flush=True)
    try:
        result = subprocess.run(
            [python, "-m", "selenium_pipeline.runner", "--doctor"],
            cwd=Path(__file__).resolve().parent.parent,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("[runtime-doctor] timed out", file=sys.stderr)
        return 124
    except OSError as exc:
        print("[runtime-doctor] could not start selected Python:", exc,
              file=sys.stderr)
        return 2
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
