"""Github main branch protection must require actual Windows CI, including admins."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import pytest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"enforce_main_windows_ci_branch_protection_v1.py"
spec=importlib.util.spec_from_file_location("microgen_branch_ci_enforcement",SCRIPT)
module=importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name]=module
spec.loader.exec_module(module)


def receipt():
    return {
        "required_status_checks":{
            "strict":True,"contexts":[
                "offline-regressions","Full offline suite (Windows, Python 3.12)"],
            "checks":[]},
        "enforce_admins":{"enabled":True},
        "required_linear_history":{"enabled":True},
        "allow_force_pushes":{"enabled":False},
        "allow_deletions":{"enabled":False},
        "required_pull_request_reviews":None,
    }


def test_policy_fails_closed_and_requires_two_windows_jobs():
    p=module.policy()
    assert p["required_status_checks"]["strict"] is True
    assert len(p["required_status_checks"]["contexts"])==2
    assert p["enforce_admins"] is True
    assert p["required_linear_history"] is True
    assert p["allow_force_pushes"] is False
    assert p["allow_deletions"] is False


def test_protected_main_verified_without_mutation():
    calls=[]
    def fake(args):
        calls.append(args)
        return 0,json.dumps(receipt()),""
    proof=module.enforce(apply=True,request=fake)
    assert proof["status"]=="GITHUB_MAIN_SERVER_SIDE_WINDOWS_CI_ENFORCED"
    assert proof["operation"]=="ALREADY_PROTECTED_NO_MUTATION"
    assert len(calls)==1


@pytest.mark.parametrize("bad",[
    "strict","missing_job","admin","force","deletion","linear","empty"])
def test_incomplete_or_bypassed_protection_refused(bad):
    d=receipt()
    if bad=="strict":d["required_status_checks"]["strict"]=False
    if bad=="missing_job":d["required_status_checks"]["contexts"]=["offline-regressions"]
    if bad=="admin":d["enforce_admins"]["enabled"]=False
    if bad=="force":d["allow_force_pushes"]["enabled"]=True
    if bad=="deletion":d["allow_deletions"]["enabled"]=True
    if bad=="linear":d["required_linear_history"]["enabled"]=False
    if bad=="empty":d={}
    with pytest.raises(ValueError):
        module.verify(d)


def test_unprotected_read_only_preflight_does_not_apply():
    calls=[]
    def fake(args):
        calls.append(args)
        return 1,'{"status":404,"message":"Branch not protected"}',"HTTP 404"
    proof=module.enforce(apply=False,request=fake)
    assert proof["server_side_gate_installed"] is False
    assert len(calls)==1


def test_installs_once_and_validates_remote_readback():
    calls=[]
    def fake(args):
        calls.append(args)
        if len(calls)==1:
            return 1,'{"status":404,"message":"Branch not protected"}',"HTTP 404"
        if len(calls)==2:
            assert args[2:4]==["--method","PUT"]
            assert "--input" in args
            source=Path(args[-1])
            payload=json.loads(source.read_text())
            assert payload["enforce_admins"] is True
            assert payload["required_status_checks"]["strict"] is True
            return 0,json.dumps(receipt()),""
        return 0,json.dumps(receipt()),""
    result=module.enforce(apply=True,request=fake)
    assert result["operation"]=="INSTALLED_AND_READ_BACK"
    assert len(calls)==3


def test_gh_403_fails_closed_without_mutation():
    calls=[]
    def fake(args):
        calls.append(args)
        return 1,'{"message":"Forbidden","status":403}',"HTTP 403"
    with pytest.raises(ValueError):
        module.enforce(apply=True,request=fake)
    assert len(calls)==1


def test_existing_weak_rule_not_overwritten():
    calls=[]
    def fake(args):
        calls.append(args)
        d=receipt()
        d["enforce_admins"]["enabled"]=False
        return 0,json.dumps(d),""
    with pytest.raises(ValueError):
        module.enforce(apply=True,request=fake)
    assert len(calls)==1


def test_unverified_remote_readback_refuses_success():
    calls=[]
    def fake(args):
        calls.append(args)
        if len(calls)==1:
            return 1,'{"status":404,"message":"Branch not protected"}',"HTTP 404"
        if len(calls)==2:
            return 0,json.dumps(receipt()),""
        changed=receipt();changed["required_status_checks"]["strict"]=False
        return 0,json.dumps(changed),""
    with pytest.raises(ValueError):
        module.enforce(apply=True,request=fake)
    assert len(calls)==3

