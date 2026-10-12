"""Static safety regressions for the Stage 6 Windows production launcher.

The actual PowerShell parser and dry-run are also checked on authorized Windows PCs.
"""
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "operations" / "Start-MicroGen_AI_Web.ps1"


def test_exact_microgen_ai_web_identity_and_commit_required():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "https://github.com/tlyoon/MicroGen_AI_Web.git" in text
    assert "$release -ne [string]$config.release_sha" in text
    assert "git -C $repo status --porcelain" in text
    assert "Release mismatch:" in text
    assert "Production checkout is dirty" in text


def test_flash_and_isolated_workroot_are_explicit():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "MICROGEN_GEMINI_UI_MODE = 'flash'" in text
    assert "MICROGEN_LLM_MODEL = 'gemini-3.8-flash'" in text
    assert "MICROGEN_COMMUNICATION_MODE = 'selenium'" in text
    assert "MICROGEN_FIGURE_MAPPING_BACKEND = 'api'" not in text
    assert "MICROGEN_NARRATION_BACKEND = 'api'" not in text
    assert "MICROGEN_PIPELINE_PYTHON" in text
    assert "MICROGEN_TTS_PYTHON" in text
    assert "'--work-root', $work" in text
    assert "separate, non-nested directories" in text


def test_local_config_dry_run_and_failure_never_misreported_as_success():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "MicroGen_AI_Web_Production\\worker.json" in text
    assert "if ($DryRun)" in text
    assert "$pipelineArgs += '--dry-run'" in text
    assert "if ($status -ne 0)" in text
    assert "MicroGen_AI_Web stage failed" in text
    assert "source.pdf" in text
