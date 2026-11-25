"""Strict v7.1 offline checkpoint pin-migration tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest
from selenium_pipeline.v71_checkpoint_revision_migration import migrate, _ALLOWED_DELTA


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(tmp_path):
    src=tmp_path/"source"
    src.mkdir()
    (src/"handoffs"/"g2").mkdir(parents=True)
    old=tmp_path/"old.py"
    new=tmp_path/"new.py"
    plan=tmp_path/"plan.json"
    old.write_text("RECOVERY_ACTIONS = {\n}\n")
    new.write_text("RECOVERY_ACTIONS = {\n"+_ALLOWED_DELTA+"}\n")
    plan.write_text('{"project":"MicroGen_AI_Web"}')
    s=_hash(old)
    for p in [src/"state.json",src/"handoffs"/"g2"/"state.json"]:
        p.write_text(json.dumps({"schema_version":1,"executor_sha256":s,
                                 "plan_sha256":_hash(plan),"tasks":{}}))
    (src/"daemon_heartbeat.json").write_text(json.dumps({
        "plan_sha256":_hash(plan),"provider_sends":0,
        "student_publication_authorized":False,"running":False}))
    (src/"executor.lock").write_text("1")
    return src,old,new,plan


def test_valid_migration_preserves_source_and_other_data(tmp_path):
    src,old,new,plan=fixture(tmp_path)
    before=[_hash(p) for p in sorted(src.rglob("state.json"))]
    target=tmp_path/"migrated"
    receipt=migrate(source=src,destination=target,old_executor=old,
                    new_executor=new,primary_plan=plan)
    assert receipt["checkpoint_count"]==2
    assert receipt["status"]=="V71_EXACT_REGISTRY_ONLY_EXECUTOR_PIN_MIGRATED"
    assert [_hash(p) for p in sorted(src.rglob("state.json"))]==before
    assert all(json.loads(p.read_text())["executor_sha256"]==_hash(new)
               for p in target.rglob("state.json"))
    assert not (target/"executor.lock").exists()
    assert not (target/"daemon_heartbeat.json").exists()


def test_unapproved_semantic_change_cannot_migrate(tmp_path):
    src,old,new,plan=fixture(tmp_path)
    new.write_text(new.read_text()+"print('unapproved')\n")
    with pytest.raises(ValueError,match="beyond the exact"):
        migrate(source=src,destination=tmp_path/"out",old_executor=old,
                new_executor=new,primary_plan=plan)
    assert not (tmp_path/"out").exists()


def test_wrong_old_executor_pin_refused(tmp_path):
    src,old,new,plan=fixture(tmp_path)
    p=src/"handoffs"/"g2"/"state.json"
    j=json.loads(p.read_text());j["executor_sha256"]="0"*64
    p.write_text(json.dumps(j))
    with pytest.raises(ValueError,match="Mixed or unexpected"):
        migrate(source=src,destination=tmp_path/"out",old_executor=old,
                new_executor=new,primary_plan=plan)


def test_existing_destination_preserved(tmp_path):
    src,old,new,plan=fixture(tmp_path)
    target=tmp_path/"out";target.mkdir()
    (target/"protected").write_text("untouched")
    with pytest.raises(ValueError,match="Existing destination"):
        migrate(source=src,destination=target,old_executor=old,
                new_executor=new,primary_plan=plan)
    assert (target/"protected").read_text()=="untouched"


def test_wrong_plan_or_paid_boundary_refused(tmp_path):
    src,old,new,plan=fixture(tmp_path)
    hb=src/"daemon_heartbeat.json"
    j=json.loads(hb.read_text());j["provider_sends"]=1
    hb.write_text(json.dumps(j))
    with pytest.raises(ValueError,match="authorization boundary"):
        migrate(source=src,destination=tmp_path/"out",old_executor=old,
                new_executor=new,primary_plan=plan)



def test_nested_destination_refused(tmp_path):
    src,old,new,plan=fixture(tmp_path)
    with pytest.raises(ValueError,match="nested"):
        migrate(source=src,destination=src/"unsafe_child",old_executor=old,
                new_executor=new,primary_plan=plan)
    assert not (src/"unsafe_child").exists()
