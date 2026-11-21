"""Phase 2C must remain a disabled, approval-gated preview until authorized."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from selenium_pipeline.windows_development_daemon_startup_preview_v71 import (
    TASK_NAME, NS, render_disabled_task_xml,
    require_preview_registry, _write_once, _git_clean_head,
    _safe_string, prepare, REGISTRY,
)


def _render(tmp):
    return render_disabled_task_xml(
        repo=tmp/"repo with space",
        python=tmp/"py tool.exe",
        plan=tmp/"plan name.json",
        state_dir=tmp/"state checkpoint",
        user="DELL-115\\tlyoon",
    )


def _element(tmp):
    doc=ET.fromstring(_render(tmp))
    ns={"t":NS}
    return doc,ns


def test_startup_xml_disabled_in_both_places(tmp_path):
    doc,ns=_element(tmp_path)
    assert doc.findtext("t:Triggers/t:LogonTrigger/t:Enabled",namespaces=ns)=="false"
    assert doc.findtext("t:Settings/t:Enabled",namespaces=ns)=="false"
    assert doc.findtext("t:Settings/t:StartWhenAvailable",namespaces=ns)=="false"
    assert doc.findtext("t:Principals/t:Principal/t:RunLevel",namespaces=ns)=="LeastPrivilege"
    assert doc.findtext("t:Principals/t:Principal/t:LogonType",namespaces=ns)=="InteractiveToken"
    assert doc.findtext("t:Settings/t:MultipleInstancesPolicy",namespaces=ns)=="IgnoreNew"


def test_startup_command_limited_to_verified_offline_daemon(tmp_path):
    doc,ns=_element(tmp_path)
    execute=doc.find("t:Actions/t:Exec",ns)
    assert execute is not None
    assert execute.findtext("t:Command",namespaces=ns).endswith("py tool.exe")
    cmd=execute.findtext("t:Arguments",namespaces=ns)
    assert "selenium_pipeline.development_continuity_daemon_v71" in cmd
    assert '"'+str(tmp_path/"plan name.json")+'"' in cmd
    assert '"'+str(tmp_path/"state checkpoint")+'"' in cmd
    assert "--max-cycles" in cmd and '"0"' in cmd
    assert "powershell" not in cmd.casefold()
    assert "schtasks" not in cmd.casefold()
    assert "gemini" not in cmd.casefold()


def test_bounded_restarts_and_no_parallel_instances(tmp_path):
    doc,ns=_element(tmp_path)
    assert doc.findtext("t:Settings/t:RestartOnFailure/t:Count",namespaces=ns)=="3"
    assert doc.findtext("t:Settings/t:RestartOnFailure/t:Interval",namespaces=ns)=="PT5M"
    assert doc.findtext("t:Settings/t:ExecutionTimeLimit",namespaces=ns)=="PT0S"


def test_xml_is_deterministic(tmp_path):
    assert _render(tmp_path)==_render(tmp_path)
    assert TASK_NAME=="MicroGen_AI_Web_v71_OfflineDevelopment"
    assert TASK_NAME not in ("MicroGen_AI_Web_v71_SourceOnly",
                            "MicroGen_AI_Web_v71_StatusMonitor")


@pytest.mark.parametrize("poison",[
    'G:\\source" --allow-model-sends',
    "G:\\source\nrestart",
    "G:\\source\rstop",
])
def test_command_injection_rejected(tmp_path,poison):
    with pytest.raises(ValueError,match="Untrusted"):
        render_disabled_task_xml(
            repo=Path(str(tmp_path/"repo")+poison),python=tmp_path/"python.exe",
            plan=tmp_path/"plan.json",state_dir=tmp_path/"state",
            user="DELL-115\\tlyoon")


@pytest.mark.parametrize("account",[
    "", "SYSTEM", "NT AUTHORITY\\SYSTEM", "Dell-115\\name with spaces",
    "DELL-115\\name'; Start-Process powershell",
])
def test_unapproved_principal_rejected(tmp_path,account):
    with pytest.raises(ValueError,match="Untrusted"):
        render_disabled_task_xml(
            repo=tmp_path/"repo",python=tmp_path/"python.exe",
            plan=tmp_path/"plan",state_dir=tmp_path/"state",user=account)


def test_registry_is_registered_and_never_enables(tmp_path):
    require_preview_registry()
    data=json.loads(REGISTRY.read_text())
    assert data["may_register_or_enable_task"] is False
    assert data["may_modify_existing_tasks"] is False
    assert data["may_send_model_requests"] is False
    assert data["may_publish_students"] is False


@pytest.mark.parametrize("field,value",[
    ("enabled",False),
    ("may_register_or_enable_task",True),
    ("may_modify_existing_tasks",True),
    ("may_send_model_requests",True),
    ("handler","UNRESTRICTED_TASK_CREATE"),
    ("native_xml_validation","REGISTER_TASK_WITH_HIGH_PRIVILEGES"),
])
def test_registry_tampering_fails_closed(tmp_path,field,value):
    data=json.loads(REGISTRY.read_text())
    data[field]=value
    file=tmp_path/"bad.json"
    file.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        require_preview_registry(path=file)


def test_preview_is_write_once_and_fails_on_mutation(tmp_path):
    file=tmp_path/"preview.xml"
    _write_once(file,b"registered disabled preview")
    _write_once(file,b"registered disabled preview")
    with pytest.raises(ValueError,match="differs"):
        _write_once(file,b"enabled modified task")
    assert file.read_bytes()==b"registered disabled preview"


def test_preview_blocks_symlink_overwrite(tmp_path):
    src=tmp_path/"actual"
    src.write_bytes(b"original")
    dest=tmp_path/"preview.xml"
    try:
        dest.symlink_to(src)
    except (OSError,NotImplementedError):
        pytest.skip("OS denies symlink creation")
    with pytest.raises(ValueError,match="Unsafe"):
        _write_once(dest,b"changed")
    assert src.read_bytes()==b"original"


def test_git_admission_fails_on_dirty_source(tmp_path):
    root=tmp_path/"source_repo"
    root.mkdir()
    subprocess.run(["git","init","-q",str(root)],check=True)
    subprocess.run(["git","-C",str(root),"config","user.email","noreply@example.org"],check=True)
    subprocess.run(["git","-C",str(root),"config","user.name","Test"],check=True)
    (root/"a.txt").write_text("baseline")
    subprocess.run(["git","-C",str(root),"add","a.txt"],check=True)
    subprocess.run(["git","-C",str(root),"commit","-qm","baseline"],check=True)
    assert len(_git_clean_head(root))==40
    (root/"a.txt").write_text("uncommitted unsafe")
    with pytest.raises(ValueError,match="clean"):
        _git_clean_head(root)


def test_prepare_cannot_mutate_native_tasks_on_non_windows(tmp_path):
    if sys.platform=="win32":
        pytest.skip("Real Windows prepare requires source-bound local checkout")
    with pytest.raises(ValueError,match="Dell-115"):
        prepare(repo=tmp_path,plan=tmp_path/"plan",
                state_dir=tmp_path/"state",output_dir=tmp_path/"preview")


@pytest.mark.skipif(sys.platform!="win32",reason="Native Task Scheduler COM requires Windows")
def test_real_native_task_scheduler_parses_preview_without_install(tmp_path):
    import os
    import re
    from selenium_pipeline.windows_development_daemon_startup_preview_v71 import (
        _validate_disabled_xml_with_task_scheduler,
    )
    account=chr(92).join((os.environ.get("USERDOMAIN",""),
                         os.environ.get("USERNAME","")))
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+",account):
        pytest.skip("Hosted Windows principal not a named limited interactive user")
    xml=render_disabled_task_xml(
        repo=tmp_path/"repo",python=tmp_path/"python.exe",
        plan=tmp_path/"roadmap.json",state_dir=tmp_path/"state",user=account)
    path=tmp_path/"DISABLED.xml"
    path.write_bytes(xml)
    _validate_disabled_xml_with_task_scheduler(path)
    assert path.read_bytes()==xml
