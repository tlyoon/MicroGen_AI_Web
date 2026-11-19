"""Fault-injection tests: limited-user scheduled v7.1 restarts cannot Send or replay."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline import windows_v71_scheduled_resume as schedule

SHA="a"*40


class SourceOnlyWindowsSchedulerTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.local=Path(temp.name)
        self.repo=self.local/"MicroGen_PR550_20261119"
        self.repo.mkdir()
        (self.repo/".git").write_text("existing original clean source")
        self.home=self.local/"MicroGen_AI_Web_Checkpoints"/"v71_scheduled_resume_v1"
        self.home.mkdir(parents=True)
        env=patch.dict(os.environ,{
            "LOCALAPPDATA":str(self.local),"COMPUTERNAME":"DELL-115",
            "USERDOMAIN":"USM","USERNAME":"tlyoon"})
        env.start(); self.addCleanup(env.stop)
        clean=patch(
            "selenium_pipeline.windows_offline_development_forward_controller._verify_repo",
            return_value=None)
        clean.start();self.addCleanup(clean.stop)
        wrapper=patch.object(schedule,"_wrapper_content",
                             return_value="@echo off\r\nTEST-SOURCE-ONLY\r\n")
        wrapper.start();self.addCleanup(wrapper.stop)

    def _wrapper(self):
        p=self.home/"sourceonly_v71.cmd"
        p.write_bytes(b"@echo off\r\nTEST-SOURCE-ONLY\r\n")
        return p

    def _proc(self,*,task_installed=True,source=SHA):
        wrapper=self.home/"sourceonly_v71.cmd"
        def invoke(cmd,**kwargs):
            if cmd[0]=="schtasks.exe":
                if not task_installed:
                    return subprocess.CompletedProcess(cmd,1,stdout="",stderr="")
                return subprocess.CompletedProcess(cmd,0,stdout=(
                    f"TaskName: {schedule.TASK_NAME}\n"
                    "Scheduled Task State: Enabled\n"
                    f"Task To Run: {wrapper}\n"),stderr="")
            if cmd[0]=="git":
                return subprocess.CompletedProcess(cmd,0,stdout=source+"\n",
                                                   stderr="")
            self.fail("Unexpected process in source-only scheduler")
        return invoke

    def test_real_source_only_runner_invokes_actual_normal_cli_with_no_gui(self):
        self._wrapper()
        invoked=[]
        def fake_normal(cmd,**kwargs):
            invoked.append((cmd,kwargs))
            self.assertEqual(kwargs["env"]["MICROGEN_V71_BACKGROUND_SOURCE_ONLY"],"1")
            self.assertEqual(kwargs["env"]["PYTHONDONTWRITEBYTECODE"],"1")
            # Hosted Windows runneradmin and RUNNER~1 lexical aliases must
            # refer to the same authorized clean source path.
            self.assertEqual(kwargs["cwd"].resolve(),self.repo.resolve())
            self.assertIn("--supervise-project-v71",cmd)
            self.assertEqual(cmd[-1],"6")
            return subprocess.CompletedProcess(cmd,0,stdout=json.dumps({
                "status":"V71_GLOBAL_HANDOFF_VERIFIED_REVIEW_PENDING",
                "source_head_sha":SHA,"verified_stage_receipts":5,
                "new_stage_dispatches_this_process":0,
                "next_not_started_stages":[
                    "original_g2_v1_synthetic_presend_inventory"],
                "scientific_qa_approved":False,
                "student_publication_authorized":False,
                "persistent_supervisor_installed_and_running_after_exit":False}),
                stderr="")
        with patch.object(schedule.subprocess,"run",side_effect=self._proc()):
            result=schedule.run(self.repo,runner=fake_normal)
        self.assertEqual(result["status"],
                         "PERSISTENT_SOURCE_ONLY_CHECKPOINT_CYCLE_RECONCILED")
        self.assertEqual(len(invoked),1)
        self.assertTrue(result["background_continuation_verified"])
        self.assertFalse(result["student_publication_authorized"])
        self.assertEqual(len(list(self.home.glob("run_*.json"))),1)
        self.assertEqual(len(list(self.home.glob("*.claim"))),0)

    def test_lexical_repo_alias_canonicalized_at_normal_cli_launch(self):
        self._wrapper()
        nested=self.repo/"source_alias"
        nested.mkdir()
        aliased_repo=nested/".."
        def owned_normal(cmd,**kwargs):
            self.assertEqual(kwargs["cwd"].resolve(),self.repo.resolve())
            self.assertEqual(Path(cmd[0]).resolve(),
                             Path(schedule.sys.executable).resolve())
            self.assertEqual(kwargs["env"]["MICROGEN_V71_BACKGROUND_SOURCE_ONLY"],"1")
            self.assertFalse(any("gemini" in x.casefold() for x in cmd))
            return subprocess.CompletedProcess(cmd,0,stdout=json.dumps({
                "status":"V71_GLOBAL_HANDOFF_VERIFIED_REVIEW_PENDING",
                "source_head_sha":SHA,"verified_stage_receipts":6,
                "new_stage_dispatches_this_process":0,
                "next_not_started_stages":[],
                "scientific_qa_approved":False,
                "student_publication_authorized":False,
                "persistent_supervisor_installed_and_running_after_exit":False}),stderr="")
        with patch.object(schedule.subprocess,"run",side_effect=self._proc()):
            status=schedule.run(aliased_repo,runner=owned_normal)
        self.assertEqual(status["status"],
                         "PERSISTENT_SOURCE_ONLY_CHECKPOINT_CYCLE_RECONCILED")
        self.assertEqual(len(list(self.home.glob("run_*.json"))),1)

    def test_scheduler_action_lexical_path_alias_canonicalized(self):
        # Windows CI tempfile may show an unnormalized/short alias while
        # the authorized wrapper has a canonical resolved source location.
        self._wrapper()
        alias_dir=self.home/"source_alias"
        alias_dir.mkdir()
        original=self._proc()
        alias=alias_dir/".."/"sourceonly_v71.cmd"
        def task_query(cmd,**kwargs):
            result=original(cmd,**kwargs)
            if cmd[0]=="schtasks.exe":
                result.stdout=result.stdout.replace(
                    str(self.home/"sourceonly_v71.cmd"),str(alias))
            return result
        with patch.object(schedule.subprocess,"run",side_effect=task_query):
            schedule._audit_installed(self.repo,self.home)
        self.assertEqual(alias.resolve(),
                         (self.home/"sourceonly_v71.cmd").resolve())

    def test_foreign_and_argument_bearing_task_actions_fail_closed(self):
        self._wrapper()
        base=self._proc()
        for action in (
            str(self.home/"foreign.cmd"),
            str(self.home/"sourceonly_v71.cmd")+" --send",
            str(self.home/"sourceonly_v71.cmd.bak"),
        ):
            def changed(cmd,**kwargs):
                response=base(cmd,**kwargs)
                if cmd[0]=="schtasks.exe":
                    response.stdout=response.stdout.replace(
                        str(self.home/"sourceonly_v71.cmd"),action)
                return response
            with self.subTest(action=action):
                with patch.object(schedule.subprocess,"run",
                                  side_effect=changed):
                    with self.assertRaisesRegex(
                            RuntimeError,"not exact and enabled"):
                        schedule._audit_installed(self.repo,self.home)

    def test_duplicate_or_disabled_scheduler_action_rejected(self):
        self._wrapper()
        base=self._proc()
        for duplicate in (True,False):
            def corrupted(cmd,**kwargs):
                response=base(cmd,**kwargs)
                if cmd[0]=="schtasks.exe":
                    if duplicate:
                        response.stdout+=("Task To Run: "+
                            str(self.home/"sourceonly_v71.cmd")+"\n")
                    else:
                        response.stdout=response.stdout.replace(
                            "Scheduled Task State: Enabled",
                            "Scheduled Task State: Disabled")
                return response
            with self.subTest(duplicate=duplicate):
                with patch.object(schedule.subprocess,"run",
                                  side_effect=corrupted):
                    with self.assertRaises(RuntimeError):
                        schedule._audit_installed(self.repo,self.home)

    def test_native_direct_script_registry_import_without_package_context(self):
        # The scheduled .cmd invokes a Python file, not python -m.
        script=Path(schedule.__file__).resolve()
        source = """
from pathlib import Path
import runpy
import sys
from unittest.mock import patch
ns = runpy.run_path(sys.argv[1], run_name="not_a_package")
assert ns["_audit_installed"].__globals__["__package__"] == ""
with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
           return_value=None):
    try:
        ns["_audit_installed"](Path("."), Path("."))
    except RuntimeError as error:
        assert "direct-script scheduler recovery missing" in str(error)
    else:
        raise AssertionError("Source-only gate did not reject retired registry")
print("NONPACKAGE_SCRIPT_ENTRY_SAFE")
"""
        finished=subprocess.run(
            [schedule.sys.executable,"-B","-c",source,str(script)],
            cwd=script.parent.parent,capture_output=True,text=True,timeout=40)
        self.assertEqual(finished.returncode,0,finished.stderr)
        self.assertIn("NONPACKAGE_SCRIPT_ENTRY_SAFE",finished.stdout)

    def test_real_native_schtasks_padded_state_and_root_name_pass(self):
        # Observed on Dell-115: 'TaskName: \\MicroGen...'; many spaces
        # between the Scheduled Task State colon and Enabled.
        self._wrapper()
        native=self._proc()
        def padded(cmd,**kwargs):
            response=native(cmd,**kwargs)
            if cmd[0]=="schtasks.exe":
                response.stdout=response.stdout.replace(
                    "TaskName: "+schedule.TASK_NAME,
                    "TaskName: \\"+schedule.TASK_NAME)
                response.stdout=response.stdout.replace(
                    "Scheduled Task State: Enabled",
                    "Scheduled Task State:                     Enabled")
            return response
        with patch.object(schedule.subprocess,"run",side_effect=padded):
            schedule._audit_installed(self.repo,self.home)

    def test_duplicate_state_field_fails_closed(self):
        self._wrapper()
        native=self._proc()
        def duplicate(cmd,**kwargs):
            response=native(cmd,**kwargs)
            if cmd[0]=="schtasks.exe":
                response.stdout += "Scheduled Task State:     Enabled\n"
            return response
        with patch.object(schedule.subprocess,"run",side_effect=duplicate):
            with self.assertRaisesRegex(RuntimeError,"not independently enabled"):
                schedule._audit_installed(self.repo,self.home)

    def test_retired_native_path_alias_registry_blocks_before_task_query(self):
        from selenium_pipeline.recovery_registry import lookup_mechanism as real_lookup
        self._wrapper()
        with patch(
            "selenium_pipeline.recovery_registry.lookup_mechanism",
            side_effect=lambda kind, signature: (None if signature ==
                "V71_WINDOWS_SCHEDULE_TASK_ACTION_PATH_ALIAS_UNVERIFIED"
                else real_lookup(kind, signature))):
            with patch.object(schedule.subprocess,"run") as task:
                with self.assertRaisesRegex(
                        RuntimeError,"path-alias recovery missing"):
                    schedule._audit_installed(self.repo,self.home)
                task.assert_not_called()

    def test_uninstalled_task_does_not_claim_background_progress(self):
        self._wrapper()
        with patch.object(schedule.subprocess,"run",
                          side_effect=self._proc(task_installed=False)):
            with self.assertRaisesRegex(RuntimeError,"not independently enabled"):
                schedule.run(self.repo,runner=lambda *a,**k:
                             self.fail("Fake scheduler invoked uninstalled runner"))
        self.assertEqual(len(list(self.home.glob("run_*.json"))),0)

    def test_wrong_host_or_unauthorized_source_refused(self):
        with patch.dict(os.environ,{"COMPUTERNAME":"UNAUTHORIZED-PC"}):
            with self.assertRaisesRegex(RuntimeError,"Dell-115"):
                schedule._native_context(self.repo)
        outside=self.local/"../elsewhere"
        with self.assertRaisesRegex(RuntimeError,"Dell-115"):
            schedule._native_context(outside)

    def test_corrupt_normal_result_cannot_promote_science_or_release(self):
        self._wrapper()
        bad=subprocess.CompletedProcess(
            [],0,stdout=json.dumps({
                "status":"V71_GLOBAL_HANDOFF_VERIFIED_REVIEW_PENDING",
                "source_head_sha":SHA,"scientific_qa_approved":True,
                "student_publication_authorized":True}),stderr="")
        with patch.object(schedule.subprocess,"run",side_effect=self._proc()):
            result=schedule.run(self.repo,runner=lambda *a,**k:bad)
        self.assertEqual(result["status"],"PERSISTENT_SOURCE_ONLY_CYCLE_BLOCKED")
        self.assertFalse(result["student_publication_authorized"])

    def test_install_non_elevated_interactive_task_no_overwrite(self):
        seen=[]
        def fake(cmd,**kwargs):
            seen.append(cmd)
            if "/Create" in cmd:
                self.assertIn("/IT",cmd)
                self.assertIn("LIMITED",cmd)
                self.assertNotIn("/F",cmd)
                self.assertNotIn("SYSTEM",cmd)
                self.assertIn("USM\\tlyoon",cmd)
                return subprocess.CompletedProcess(cmd,0,stdout="SUCCESS")
            if "/V" in cmd:
                p=self.home/"sourceonly_v71.cmd"
                return subprocess.CompletedProcess(cmd,0,stdout=(
                    f"TaskName: {schedule.TASK_NAME}\n"
                    "Scheduled Task State: Enabled\n"
                    f"Task To Run: {p}\n"))
            return subprocess.CompletedProcess(cmd,1,stdout="",stderr="Not Found")
        with patch.object(schedule.subprocess,"run",side_effect=fake):
            result=schedule.install(self.repo)
        self.assertEqual(result["status"],
                         "NATIVE_WINDOWS_INTERACTIVE_USER_SCHEDULE_INSTALLED")
        self.assertFalse(result["running_after_logout_verified"])
        self.assertTrue((self.home/"sourceonly_v71.cmd").is_file())
        self.assertEqual(len([x for x in seen if "/Create" in x]),1)

    def test_existing_task_never_force_replaced(self):
        self._wrapper()
        with patch.object(schedule.subprocess,"run",
                          side_effect=self._proc()):
            with self.assertRaisesRegex(RuntimeError,"Existing scheduler task"):
                schedule.install(self.repo)


if __name__=="__main__":
    unittest.main()
