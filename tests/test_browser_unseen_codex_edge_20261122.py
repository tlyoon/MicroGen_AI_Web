from selenium_pipeline.development_coding_provider_health_v71 import is_host_readonly

def test_genuine_multiline_codex_readonly_policy_denial():
    assert is_host_readonly('OpenAI Codex CLI\nsandbox: read-only\nError: write blocked by policy\n')

def test_readonly_line_without_blocked_by_policy_rejected():
    assert not is_host_readonly('OpenAI Codex CLI\nsandbox: read-only\nError: write denied by host\n')

def test_blocked_by_policy_without_standalone_sandbox_readonly_line_rejected():
    assert not is_host_readonly('OpenAI Codex CLI\nsandbox: read-only mode enabled\nError: write blocked by policy\n')
