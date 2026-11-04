"""Native Windows bounded stage subprocess with private raw stdout and scoped cleanup.

Raw binary output avoids CP1252 UnicodeDecodeError. On timeout, terminate
ONLY the child stage's process tree (never search/kill all Chrome processes).
No retry and no model-provider resubmission is performed here.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


class WindowsStageRecoveryError(RuntimeError):
    pass


def _stop_owned_tree(proc: subprocess.Popen, *, command_runner=None) -> None:
    """Best-effort shutdown of a *known* owned child process tree only."""
    if proc.poll() is not None:
        return
    run = subprocess.run if command_runner is None else command_runner
    if os.name == "nt":
        try:
            run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True, timeout=12, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    if proc.poll() is None:
        try:
            proc.kill()
        except OSError:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired as exc:
        raise WindowsStageRecoveryError(
            "Owned stage process could not be reaped after timeout") from exc


def run_bounded(*, command: list[str], cwd: Path, log_path: Path,
                timeout_seconds: float, environ: dict[str, str] | None = None,
                subprocess_popen=None, command_runner=None
                ) -> subprocess.CompletedProcess:
    """Run once; keep source untouched and persist raw stage output as new file.

    The caller is responsible for its immutable PRE-SEND model attempt ledger,
    which must exist before invoking this function on a provider stage.
    """
    if os.name != "nt":
        raise WindowsStageRecoveryError("Native Windows only")
    if not command or any(not isinstance(v, str) or not v for v in command):
        raise WindowsStageRecoveryError("Explicit nonempty command arguments required")
    if not 0.2 <= timeout_seconds <= 3600:
        raise WindowsStageRecoveryError("Finite 0.2 to 3600 second deadline required")
    cwd = Path(cwd).absolute()
    log_path = Path(log_path).absolute()
    if (not cwd.is_dir() or cwd.is_symlink()
            or not log_path.parent.is_dir() or log_path.parent.is_symlink()
            or log_path.exists() or log_path.is_symlink()):
        raise WindowsStageRecoveryError("New external stage log and existing cwd required")
    env = os.environ.copy() if environ is None else dict(environ)
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    opener = subprocess.Popen if subprocess_popen is None else subprocess_popen
    with log_path.open("xb") as output:
        proc = opener(command, cwd=str(cwd), env=env,
                      stdout=output, stderr=subprocess.STDOUT,
                      stdin=subprocess.DEVNULL,
                      creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                      shell=False)
        try:
            exit_code = proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _stop_owned_tree(proc, command_runner=command_runner)
            raise
        finally:
            output.flush()
            os.fsync(output.fileno())
    return subprocess.CompletedProcess(command, exit_code, stdout=None, stderr=None)
