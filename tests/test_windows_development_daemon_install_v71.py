"""Explicit native Phase 2C installer is single-task and non-overwriting."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from selenium_pipeline import windows_development_daemon_install_v71 as n
from selenium_pipeline.windows_development_daemon_startup_preview_v71 import (
    render_disabled_task_xml,NS,TASK_NAME,
)


def preview(tmp_path):
    return render_disabled_task_xml(
        repo=tmp_path/"repo with space",python=tmp_path/"python.exe",
        plan=tmp_path/"some plan.json",state_dir=tmp_path/"state",
        user="USM\\tlyoon")


def test_install_registry_allowlist():
    n.require_install_registry()


def test_exact_xml_enables_only_dedicated_task(tmp_path):
    source=preview(tmp_path)
    enabled=n.enabled_xml_from_disabled_preview(source)
    before=ET.fromstring(source)
    after=ET.fromstring(enabled)
    ns={"t":NS}
    assert after.findtext("t:Settings/t:Enabled",namespaces=ns)=="true"
    assert after.findtext("t:Triggers/t:LogonTrigger/t:Enabled",namespaces=ns)=="true"
    assert after.findtext("t:Principals/t:Principal/t:RunLevel",namespaces=ns)=="LeastPrivilege"
    assert after.findtext("t:Principals/t:Principal/t:LogonType",namespaces=ns)=="InteractiveToken"
    assert after.findtext("t:Settings/t:MultipleInstancesPolicy",namespaces=ns)=="IgnoreNew"
    assert before.findtext("t:Settings/t:Enabled",namespaces=ns)=="false"
    assert b"selenium_pipeline.development_continuity_daemon_v71" in enabled
    assert b"MicroGen_AI_Web_v71_SourceOnly" not in enabled
    assert b"MicroGen_AI_Web_v71_StatusMonitor" not in enabled


def test_double_enabling_is_rejected(tmp_path):
    s=n.enabled_xml_from_disabled_preview(preview(tmp_path))
    with pytest.raises(ValueError,match="disabled"):
        n.enabled_xml_from_disabled_preview(s)


@pytest.mark.parametrize("xpath,text",[
 ("t:Principals/t:Principal/t:RunLevel","HighestAvailable"),
 ("t:Principals/t:Principal/t:LogonType","Password"),
 ("t:Settings/t:MultipleInstancesPolicy","Parallel"),
 ("t:Triggers/t:LogonTrigger/t:Enabled","true"),
])
def test_untrusted_task_preview_fails_closed(tmp_path,xpath,text):
    tree=ET.fromstring(preview(tmp_path))
    tree.find(xpath,{"t":NS}).text=text
    with pytest.raises(ValueError):
        n.enabled_xml_from_disabled_preview(ET.tostring(tree))


def test_arbitrary_command_fails_closed(tmp_path):
    tree=ET.fromstring(preview(tmp_path))
    tree.find("t:Actions/t:Exec/t:Command",{"t":NS}).text="powershell.exe"
    with pytest.raises(ValueError,match="restricted"):
        n.enabled_xml_from_disabled_preview(ET.tostring(tree))


def test_missing_daemon_flags_fails_closed(tmp_path):
    tree=ET.fromstring(preview(tmp_path))
    tree.find("t:Actions/t:Exec/t:Arguments",{"t":NS}).text="-m rogue.worker"
    with pytest.raises(ValueError,match="restricted"):
        n.enabled_xml_from_disabled_preview(ET.tostring(tree))


@pytest.mark.parametrize("change",[
 ("may_modify_existing_v71_tasks",True),
 ("may_send_model_requests",True),
 ("may_author_code_changes",True),
 ("may_release_students",True),
 ("can_create_only_when_absent",False),
 ("installer_action","OVERWRITE_DISABLED_SOURCEONLY"),
 ("allowed_role","SYSTEM"),
])
def test_mutated_registry_not_executable(tmp_path,change):
    contents=json.loads(n.REGISTRY.read_text())
    contents[change[0]]=change[1]
    path=tmp_path/"foreign.json"
    path.write_text(json.dumps(contents))
    with pytest.raises(ValueError):
        n.require_install_registry(path=path)


def fixtures(root):
    user="USM\\tlyoon"
    old={
        "MicroGen_AI_Web_v71_SourceOnly":{
            "name":"MicroGen_AI_Web_v71_SourceOnly",
            "state":"Disabled","action":"C:\\original-source.cmd"},
        "MicroGen_AI_Web_v71_StatusMonitor":{
            "name":"MicroGen_AI_Web_v71_StatusMonitor",
            "state":"Disabled","action":"C:\\original-monitor.cmd"}}
    return user,old


def _pinned_native_start_fixture(tmp_path):
    user,old=fixtures(tmp_path)
    p=tmp_path/"repo"
    daemon=p/"selenium_pipeline"/"development_continuity_daemon_v71.py"
    daemon.parent.mkdir(parents=True)
    daemon.write_text("offline daemon source")
    py=tmp_path/"python.exe"
    py.write_bytes(b"interpreter binary")
    plan=tmp_path/"roadmap.json"
    plan.write_text('{"schema_version":1}')
    state=tmp_path/"state"
    xml=n.enabled_xml_from_disabled_preview(preview(tmp_path))
    xml_path=tmp_path/"offline_daemon_ENABLED_approved.xml"
    xml_path.write_bytes(xml)
    node=ET.fromstring(xml)
    args=node.findtext("t:Actions/t:Exec/t:Arguments",namespaces={"t":NS})
    own={"name":TASK_NAME,"state":"Ready","action":str(py),
         "arguments":args,"principal":user,
         "run_level":"Limited","logon":"Interactive"}
    receipt={
        "status":"NATIVE_OFFLINE_LOGON_TASK_INSTALLED",
        "task":TASK_NAME,
        "git_sha":"a"*40,
        "repository":str(p),
        "source_plan":str(plan),
        "state_dir":str(state),
        "python":str(py),
        "user":user,
        "approved_roadmap_sha256":n._sha(plan),
        "python_sha256":n._sha(py),
        "daemon_sha256":n._sha(daemon),
        "enabled_xml_sha256":n._sha(xml_path),
        "registered_action":str(py),
        "registered_arguments":args,
    }
    (tmp_path/"native_installed_attestation.json").write_text(
        json.dumps(receipt),encoding="utf8")
    return old,own,state,p,plan,py,receipt


def test_approved_start_never_reinstalls_and_verifies_other_tasks(tmp_path):
    old,own,state,p,plan,py,receipt=_pinned_native_start_fixture(tmp_path)
    with patch.object(n,"_git_clean_head",return_value=receipt["git_sha"]),patch.object(
        n,"_native_snapshot",return_value={**old,TASK_NAME:own}),patch.object(
        n,"_powershell",return_value="OFFLINE_TASK_START_REQUESTED") as send,patch.object(
        n,"attest_live_daemon",return_value={"running_verified":False}):
        result=n.start_approved(installation_dir=tmp_path,state_dir=state)
    assert result["status"]=="NATIVE_OFFLINE_TASK_START_REQUESTED"
    assert send.call_count==1
    assert "Start-ScheduledTask" in send.call_args.args[0]
    assert "MicroGen_AI_Web_v71_SourceOnly" not in send.call_args.args[0]


def test_approved_start_fails_if_original_task_enabled(tmp_path):
    old,own,state,p,plan,py,receipt=_pinned_native_start_fixture(tmp_path)
    old["MicroGen_AI_Web_v71_SourceOnly"]["state"]="Ready"
    with patch.object(n,"_git_clean_head",return_value=receipt["git_sha"]),patch.object(
        n,"_native_snapshot",return_value={**old,TASK_NAME:own}),patch.object(
        n,"_powershell") as send:
        with pytest.raises(ValueError):
            n.start_approved(installation_dir=tmp_path,state_dir=state)
    send.assert_not_called()


@pytest.mark.parametrize("alter",["python","roadmap","daemon","taskargs","commit","state"])
def test_approved_start_fails_closed_on_restart_drift(tmp_path,alter):
    old,own,state,p,plan,py,receipt=_pinned_native_start_fixture(tmp_path)
    head=receipt["git_sha"]
    if alter=="python":
        py.write_bytes(b"modified interpreter binary")
    elif alter=="roadmap":
        plan.write_bytes(b"changed tasks")
    elif alter=="daemon":
        (p/"selenium_pipeline"/"development_continuity_daemon_v71.py"
         ).write_text("changed code")
    elif alter=="taskargs":
        own["arguments"]+=" --allow-sends"
    elif alter=="commit":
        head="b"*40
    elif alter=="state":
        state=tmp_path/"another_state"
    with patch.object(n,"_git_clean_head",return_value=head),patch.object(
        n,"_native_snapshot",return_value={**old,TASK_NAME:own}),patch.object(
        n,"_powershell") as send:
        with pytest.raises(ValueError):
            n.start_approved(installation_dir=tmp_path,state_dir=state)
    send.assert_not_called()


@pytest.mark.skipif(os.name!="nt",
                    reason="Native task creation requires actual Windows")
def test_unknown_native_task_install_fails_closed(tmp_path):
    user,old=fixtures(tmp_path)
    # This is a mocked *Dell-115* native-integration test. A real hosted
    # Windows CI runner is not Dell-115 and must otherwise fail closed.
    with patch.dict(os.environ,{"COMPUTERNAME":"DELL-115",
                               "LOCALAPPDATA":str(tmp_path)}),patch.object(
        n,"_security_preflight",return_value=(
        {"source_git_sha":"a"*40,"source_plan_sha256":"b"*64},b"xml",user,old
    )),patch.object(n,"_register_new_native_task") as create,patch.object(
        n,"_native_snapshot",return_value={**old,TASK_NAME:{
            "name":TASK_NAME,"state":"Disabled","principal":user,
            "run_level":"Limited","logon":"Interactive",
            "action":str(tmp_path/"python.exe")}}):
        with pytest.raises((ValueError,KeyError)):
            n.install(preview_dir=tmp_path,repo=tmp_path/"repo",
                      plan=tmp_path,state_dir=tmp_path/"state",
                      output_dir=tmp_path/"out",python=tmp_path/"python.exe")
    assert create.call_count == 1


@pytest.mark.skipif(os.name!="nt",reason="Windows native owner guard")
def test_native_install_refuses_other_windows_computer_before_sends(tmp_path):
    with patch.dict(os.environ,{"COMPUTERNAME":"WINDOWS-CI"}),patch.object(
        n,"_register_new_native_task") as create:
        with pytest.raises(ValueError,match="Dell-115 only"):
            n.install(preview_dir=tmp_path,repo=tmp_path,
                      plan=tmp_path,state_dir=tmp_path/"state",
                      output_dir=tmp_path/"out",python=tmp_path/"python.exe")
    create.assert_not_called()


@pytest.mark.skipif(os.name=="nt",reason="Unix-specific admission check")
def test_native_installer_rejects_linux_without_attempting_register(tmp_path):
    with patch.object(n,"_register_new_native_task") as create:
        with pytest.raises(ValueError,match="Dell-115 only"):
            n.install(preview_dir=tmp_path,repo=tmp_path,
                      plan=tmp_path,state_dir=tmp_path/"state",
                      output_dir=tmp_path/"out",python=tmp_path/"python.exe")
    create.assert_not_called()


def test_duplicate_task_refused_during_security_preflight(tmp_path):
    with patch.object(n,"require_preview_registry"),patch.object(
        n,"require_install_registry"),patch.object(
        n,"_git_clean_head",return_value="a"*40),patch.object(
        n,"_native_snapshot",return_value={TASK_NAME:{"state":"Ready"}}):
        with pytest.raises(ValueError):
            n._security_preflight(tmp_path,tmp_path,tmp_path,tmp_path,tmp_path)
