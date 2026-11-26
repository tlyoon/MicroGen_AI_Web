"""Windows pytest process result classifier."""

def classify_pytest_result(return_code, stdout, stderr):
    """Classify a pytest process outcome strictly from its integer return code."""
    passed = type(return_code) is int and return_code == 0
    return {
    "passed": passed,
    "return_code": return_code,
    "stdout": stdout,
    "stderr": stderr,
    }
