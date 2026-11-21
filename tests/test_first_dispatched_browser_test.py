from selenium_pipeline.development_coding_provider_health_v71 import is_host_readonly

def test_detects_codex_sandbox_readonly_blocked_by_policy():
    assert is_host_readonly("Codex CLI warning\nsandbox: read-only\nOperation blocked by policy")

def test_ignores_sandbox_workspace_write():
    assert not is_host_readonly("Codex CLI warning\nsandbox: workspace-write\nOperation blocked by policy")

def test_ignores_readonly_denial_lacking_codex():
    assert not is_host_readonly("Agent CLI warning\nsandbox: read-only\nOperation blocked by policy")
