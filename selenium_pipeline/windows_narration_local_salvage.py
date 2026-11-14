"""Recover a complete captured narration after a fixed deterministic lint false positive.

Never regenerate or resubmit the old Gemini request. Only promotes a
byte-identical previously captured script when every current local script,
title, math and pronunciation-risk check passes on an isolated new trial.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import _new_atomic, _verified_json, require
from .figures_failed_source_only_resume import verify_recovery_receipt
from .runner import check_valid


def _locally_audit_script(workspace: Path) -> tuple[int, list]:
    # Importing legacy narration module normally triggers an old top-level
    # early exit when script.txt exists. Supply a nonexistent dummy OUT_SCRIPT
    # for import only; main() is never invoked and no provider call is made.
    original_cwd=os.getcwd()
    original_env=os.environ.get("OUT_SCRIPT")
    old_sys_path=list(sys.path)
    try:
        os.chdir(workspace)
        os.environ["OUT_SCRIPT"]=".__microgen_preflight_never_written__.txt"
        require(not Path(os.environ["OUT_SCRIPT"]).exists(),
                "Unsafe existing dummy output path")
        sys.path.insert(0,str(workspace))
        spec=importlib.util.spec_from_file_location(
            "microgen_narration_local_qa_only",
            workspace / "gen_script_selenium_v15.py")
        require(spec is not None and spec.loader is not None,
                "Cannot load readonly narration validator")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        titles=module.extract_exact_slide_titles(Path("slides.pdf"))
        warnings=module.collect_all_warnings(
            Path("script.txt"),Path("slides.pdf"),titles)
        return len(titles), warnings
    finally:
        os.chdir(original_cwd)
        sys.path[:]=old_sys_path
        if original_env is None:
            os.environ.pop("OUT_SCRIPT",None)
        else:
            os.environ["OUT_SCRIPT"]=original_env


def salvage(*, prior_trial: Path, new_trial: Path) -> dict:
    prior_trial, new_trial = Path(prior_trial).absolute(), Path(new_trial).absolute()
    require(os.name == "nt" and prior_trial != new_trial
            and prior_trial.parent == new_trial.parent
            and prior_trial.is_dir() and new_trial.is_dir()
            and not prior_trial.is_symlink() and not new_trial.is_symlink(),
            "Only separate Windows trial directories permitted")
    old=_verified_json(prior_trial / "fresh_trial_contract.json")
    new=_verified_json(new_trial / "fresh_trial_contract.json")
    sha=old.get("source_sha256")
    require(sha == new.get("source_sha256")
            and old.get("source_path") == new.get("source_path")
            and new.get("paid_tts_authorized") is False
            and new.get("student_publication_authorized") is False,
            "Narration sources or permission constraints differ")
    verify_recovery_receipt(prior_trial)
    verify_recovery_receipt(new_trial)
    old_slides=_verified_json(prior_trial / "stage_slides_result.json")
    new_slides_path=new_trial / "stage_slides_result.json"
    new_slides=_verified_json(new_slides_path)
    require(old_slides.get("status") ==
            new_slides.get("status") == "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND"
            and old_slides.get("source_sha256") ==
                new_slides.get("source_sha256") == sha
            and old_slides.get("output_sha256") ==
                new_slides.get("output_sha256"),
            "Slides are not byte-identical to the rejected narration's slides")
    old_res_path=prior_trial / "stage_narration_result.json"
    old_res=_verified_json(old_res_path)
    old_started=_verified_json(prior_trial / "stage_narration_started.json")
    old_log=prior_trial / "stage_narration_stdout.raw.log"
    old_work=Path(old["staged_source_path"]).parent / ".microgen_work"
    new_lecture=Path(new["staged_source_path"]).parent
    new_work=new_lecture / ".microgen_work"
    rejected=old_work / "script.rejected_selenium_attempt_1.txt"
    raw=old_work / "gemini_raw_response.txt"
    script=new_work / "script.txt"
    audit=old_log.read_text(encoding="utf8", errors="replace")
    require(old_res.get("status") == "STAGE_FAILED_OR_OUTPUT_INCOMPLETE_NO_RETRY"
            and old_res.get("stage") == "narration"
            and old_res.get("source_sha256") == sha
            and old_res.get("exit_code") != 0
            and old_started.get("stage") == "narration"
            and old_started.get("single_attempt_no_provider_resend") is True
            and old_started.get("predecessor_receipt_sha256") ==
                file_sha256(prior_trial / "stage_slides_result.json")
            and "click_send_with_fallbacks returned True" in audit
            and "Accepted fresh complete narration from stable model-response" in audit
            and "Final failure: TTS-risk" in audit
            and "ambiguous_capital_a" in audit
            and rejected.is_file() and raw.is_file()
            and not rejected.is_symlink() and not raw.is_symlink()
            and script.is_file() and not script.is_symlink()
            and file_sha256(rejected) == file_sha256(script)
            and check_valid("slides",new_work)
            and check_valid("narration",new_work),
            "Prior complete response, later local failure, or staged script not proven")
    corrected_linter=(Path(__file__).resolve().parent /
                      "vendor_template_v2" / "script_tts_risk.py")
    require(file_sha256(new_work / "script_tts_risk.py") ==
            file_sha256(corrected_linter),
            "Current corrected TTS lint not installed in isolated workspace")
    count,warnings=_locally_audit_script(new_work)
    require(count > 1 and not warnings,
            "Local narration QA still blocks: " + repr(warnings[:3]))
    target=new_lecture / "script.txt"
    began=new_trial / "stage_narration_started.json"
    finished=new_trial / "stage_narration_result.json"
    require(not target.exists() and not target.is_symlink()
            and not began.exists() and not finished.exists()
            and not any(new_trial.glob("stage_script_qa_*")),
            "Local reuse destination or stage claim is already occupied")
    shutil.copy2(script,target)
    require(file_sha256(target) == file_sha256(rejected),
            "Local narration published file differs from verified source")
    claim={
        "schema_version":1,"stage":"narration","source_sha256":sha,
        "predecessor_receipt_sha256":file_sha256(new_slides_path),
        "single_attempt_no_provider_resend":True,
        "paid_tts_authorized":False,"student_publication_authorized":False,
        "reused_existing_captured_response_only":True,
        "new_model_sends":0,
        "original_rejected_narration_receipt_sha256":file_sha256(old_res_path)}
    result={
        "schema_version":1,"stage":"narration","source_sha256":sha,
        "predecessor_receipt_sha256":file_sha256(new_slides_path),
        "status":"STAGE_COMPLETED_AND_SOURCE_SHA_BOUND",
        "exit_code":0,"output_sha256":{"script.txt":file_sha256(target)},
        "new_model_or_tts_calls":False,"new_tts_calls":False,
        "new_video_rendered":False,"student_publication_authorized":False,
        "local_recovery_from_captured_narration":True,
        "original_rejected_narration_receipt_sha256":file_sha256(old_res_path),
        "original_narration_log_sha256":file_sha256(old_log),
        "original_gemini_raw_capture_sha256":file_sha256(raw),
        "original_rejected_script_sha256":file_sha256(rejected),
        "original_script_blocks":count,"blocking_local_qa_warnings":0,
        "independent_academic_audio_qa_verified":False}
    _new_atomic(began,claim)
    _new_atomic(finished,result)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prior-trial",type=Path,required=True)
    p.add_argument("--new-trial",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        result=salvage(prior_trial=a.prior_trial,new_trial=a.new_trial)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        result={"status":"NARRATION_LOCAL_SALVAGE_REJECTED",
                "reason":str(exc),"new_model_or_tts_calls":False}
    print(json.dumps(result,indent=2))
    return 0 if result.get("status")=="STAGE_COMPLETED_AND_SOURCE_SHA_BOUND" else 2


if __name__=="__main__":
    raise SystemExit(main())
