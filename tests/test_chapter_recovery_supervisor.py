"""No-network restart/fault tests for persistent chapter supervisor."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

from selenium_pipeline import chapter_recovery_supervisor as s


def make_tree(tmp_path):
    root = tmp_path / "serway"
    sub = root / "10" / "10.1"
    sub.mkdir(parents=True)
    (sub / "source.pdf").write_bytes(b"%PDF-1.7\nfake source")
    return root


def simulated_worker(status, code=2):
    def launch(cmd, manifest):
        control = manifest.parent
        run_id = control.name
        assert cmd[cmd.index("--run-id") + 1] == run_id
        worker = json.loads(manifest.read_text())["assignments"]
        assert worker == {"HP": [10]}
        (control / "HP.json").write_text(json.dumps({
            "phase": "recovery_pending",
            "jobs": {"10.1": {"status": status, "stage": "slides",
                              "error": f"stage exited 1; see C:/runs/{run_id}/log"}}}))
        return code
    return launch


def test_unfinished_pass_remains_pending_and_does_not_repeat_before_deadline(tmp_path, monkeypatch):
    root = make_tree(tmp_path)
    monkeypatch.setattr(s, "completed_lecture", lambda *a: False)
    t = datetime(2026, 11, 21, 0, 0, tzinfo=timezone.utc)
    directory = tmp_path / "state"
    result = s.cycle(source_root=root, chapter=10, worker="HP",
                     run_prefix="hp_ch10", python=Path(sys.executable),
                     state_dir=directory, now=t,
                     launch=simulated_worker("unfinished"))
    assert result["phase"] == "recovery_pending"
    assert result["unfinished"] == ["10.1"]
    assert result["next_retry_utc"] == (t + timedelta(hours=6)).isoformat()
    assert s.cycle(source_root=root, chapter=10, worker="HP",
                   run_prefix="hp_ch10", python=Path(sys.executable),
                   state_dir=directory, now=t + timedelta(hours=2),
                   launch=lambda *a: pytest.fail("Must not relaunch early")) == result


def test_new_recovery_cycle_and_backoff_on_same_failure(tmp_path, monkeypatch):
    root = make_tree(tmp_path)
    monkeypatch.setattr(s, "completed_lecture", lambda *a: False)
    directory = tmp_path / "state"
    t = datetime(2026, 11, 21, 0, tzinfo=timezone.utc)
    for i, hours in enumerate((0, 6, 12), 1):
        result = s.cycle(source_root=root, chapter=10, worker="HP",
                         run_prefix="hp_ch10", python=Path(sys.executable),
                         state_dir=directory, now=t + timedelta(hours=hours),
                         launch=simulated_worker("unfinished"))
        assert result["attempt"] == i
        assert result["phase"] == "recovery_pending"
    assert result["unchanged_failure_rounds"] == 2
    assert result["next_retry_utc"] == (t + timedelta(hours=36)).isoformat()


def test_completion_receipt_ends_chapter_and_stops_retry(tmp_path, monkeypatch):
    root = make_tree(tmp_path)
    done = {"value": False}
    monkeypatch.setattr(s, "completed_lecture", lambda *a: done["value"])
    def launch(cmd, manifest):
        done["value"] = True
        return 0
    result = s.cycle(source_root=root, chapter=10, worker="HP",
                     run_prefix="hp_ch10", python=Path(sys.executable),
                     state_dir=tmp_path / "state", launch=launch)
    assert result["phase"] == "completed"
    assert result["completed"] == ["10.1"]
    assert result["unfinished"] == []


def test_manifest_mismatch_fails_without_launch(tmp_path, monkeypatch):
    root = make_tree(tmp_path)
    monkeypatch.setattr(s, "completed_lecture", lambda *a: False)
    control = root / ".microgen_coordination" / "hp_ch10_r0001"
    control.mkdir(parents=True)
    (control / "assignments.json").write_text(json.dumps(
        {"assignments": {"Dell-115": [10]}, "source_roots": {}}))
    with pytest.raises(RuntimeError, match="differs"):
        s.cycle(source_root=root, chapter=10, worker="HP",
                run_prefix="hp_ch10", python=Path(sys.executable),
                state_dir=tmp_path / "state", launch=lambda *a: pytest.fail("No launch"))


def test_backoff_caps_exact_repeat_failures():
    assert s._next_delay_hours(0, 6) == 6
    assert s._next_delay_hours(1, 6) == 6
    assert s._next_delay_hours(2, 6) == 24
    assert s._next_delay_hours(4, 6) == 72


def test_verified_code_change_wakes_deferred_job_before_retry_deadline(tmp_path, monkeypatch):
    root = make_tree(tmp_path)
    monkeypatch.setattr(s, "completed_lecture", lambda *a: False)
    fingerprint = {"value": "old"}
    monkeypatch.setattr(s, "_code_fingerprint", lambda: fingerprint["value"])
    directory = tmp_path / "state"
    t = datetime(2026, 11, 21, 0, tzinfo=timezone.utc)
    first = s.cycle(source_root=root, chapter=10, worker="HP",
                    run_prefix="hp_ch10", python=Path(sys.executable),
                    state_dir=directory, now=t, launch=simulated_worker("unfinished"))
    assert first["next_retry_utc"] == (t + timedelta(hours=6)).isoformat()
    fingerprint["value"] = "repaired"
    second = s.cycle(source_root=root, chapter=10, worker="HP",
                     run_prefix="hp_ch10", python=Path(sys.executable),
                     state_dir=directory, now=t + timedelta(hours=1),
                     launch=simulated_worker("unfinished"))
    assert second["attempt"] == 2
    assert second["code_fingerprint"] == "repaired"
    assert second["unchanged_failure_rounds"] == 0
