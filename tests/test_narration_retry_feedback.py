"""Offline regressions for targeted narration retry feedback."""
import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "selenium_pipeline/vendor_template_v2/gen_script_selenium_v15.py"

def _retry_function():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "retry_instruction")
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace["retry_instruction"]

def test_first_attempt_unchanged():
    assert _retry_function()("base", []) == "base"

def test_targeted_feedback_and_fail_closed():
    result = _retry_function()("base", ["Slide 14: ambiguous_capital_a", "Slide 14: ambiguous_capital_a"])
    assert result.count("Slide 14: ambiguous_capital_a") == 1
    assert "COMPLETE script" in result
    assert "never guess" in result
    assert "speech-safety" in result

def test_feedback_bounded():
    result = _retry_function()("base", ["x" * 1000] * 30)
    assert len(result) < 1100

def test_rejected_output_is_archived_before_retry():
    text = SOURCE.read_text(encoding="utf-8")
    assert 'OUT_SCRIPT.replace(archive)' in text
    assert 'refusing destructive retry' in text
    assert 'retry_instruction(instruction, last_warnings)' in text
