"""Ensure the Windows long-horizon task is explicit, fail-closed and parseable."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import pytest


ROOT=Path(__file__).resolve().parents[1]/"scripts"
RUN=ROOT/"run_windows_long_horizon_g3.ps1"
INSTALL=ROOT/"install_windows_long_horizon_g3.ps1"


def test_task_never_dispatches_browser_or_api_or_changes_existing_task():
    runner=RUN.read_text(encoding="utf8")
    installer=INSTALL.read_text(encoding="utf8")
    assert "long_horizon_g3_source_worker_v1" in runner
    assert "MICROGEN_API_ATTEMPTS='0'" in runner
    assert "new_paid_gemini_API_calls" in runner
    assert "new_browser_sends" in runner
    assert "Disable-ScheduledTask" in runner
    assert "Get-ScheduledTask -TaskName $TaskName" in installer
    assert "Refuse to modify an existing source task automatically" in installer
    assert "IgnoreNew" in installer
    assert "StartWhenAvailable" in installer
    assert "-RepetitionInterval (New-TimeSpan -Minutes 15)" in installer
    assert "-RepetitionDuration (New-TimeSpan -Days 365)" in installer
    assert "WindowsIdentity" in installer
    assert "GitHub-certified main" in installer
    assert "-LogonType Interactive" in installer
    assert "student_publication_authorized=$false" in installer
    assert "-NoProfile -NonInteractive" in installer


@pytest.mark.skipif(sys.platform!="win32",reason="Windows scheduled task contract")
def test_powershell_scripts_parse_without_side_effects():
    for script in (RUN,INSTALL):
        command=(
            "$tokens=$null;$errors=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{str(script).replace(chr(39),chr(39)*2)}',"
            "[ref]$tokens,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -ne 0){$errors|Out-String;exit 1}"
        )
        p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                          "-Command",command],
                         capture_output=True,text=True,timeout=20)
        assert p.returncode==0,p.stdout+p.stderr
