"""Independent specification for generated Windows pytest-result classifier.

A successful pytest process is determined by its exit status. A harmless
deprecation warning on stderr is never a failure, and a printed 'passed' line
cannot override a nonzero process exit. No subprocess or API is called.
"""
from selenium_pipeline.windows_pytest_result_v1 import classify_pytest_result


def test_zero_exit_with_swig_deprecation_warning_is_success():
    message = "sys:1: DeprecationWarning: builtin type swigvarlink has no __module__"
    result = classify_pytest_result(0, "1694 passed, 8 skipped\n", message)
    assert result["passed"] is True
    assert result["return_code"] == 0
    assert "swigvarlink" in result["stderr"]
    assert "1694 passed" in result["stdout"]


def test_nonzero_exit_remains_failure_even_with_passed_stdout():
    result = classify_pytest_result(1, "100 passed\n", "")
    assert result["passed"] is False
    assert result["return_code"] == 1


def test_nonzero_exit_remains_failure_even_with_only_warnings():
    result = classify_pytest_result(4, "5 passed", "DeprecationWarning")
    assert result["passed"] is False


def test_zero_exit_without_ansi_and_without_stdout_is_success():
    result = classify_pytest_result(0, "", "")
    assert result["passed"] is True


def test_noninteger_exit_never_implicitly_succeeds():
    for code in (None, False, "0"):
        result = classify_pytest_result(code, "passed", "")
        assert result["passed"] is False


def test_preserves_original_stderr_and_stdout_in_report():
    stdout = "progress...\n3 passed"
    stderr = "DeprecationWarning: harmless\n"
    result = classify_pytest_result(0, stdout, stderr)
    assert result["stdout"] == stdout
    assert result["stderr"] == stderr
