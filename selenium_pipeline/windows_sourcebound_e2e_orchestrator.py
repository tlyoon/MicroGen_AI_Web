"""Windows-only, source-safe, resumable real end-to-end MicroGen run.

Runs ORIGINAL source.pdf through existing production runner's actual
Gemini Selenium figures/slides/narration/math checks; only after that
passes, routine owner-authorized Gemini Flash-Lite TTS + tolerant QA;
then the SOURCE-BOUND highlighted multipart video (never legacy static
MP4). All results stay in a new isolated local PDF tree. Explicitly
NO student publication or alteration of the existing G: source tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PHASES = (
    ("source_content", ("--from-stage", "figures", "--through-stage", "script_qa"), 2700),
    # A whole-voice batch may exhaust Lite, Flash, and Cloud under source-
    # bound fallback. Never kill the stage before its own breaker/retry plan.
    ("narrated_audio", ("--from-stage", "tts", "--through-stage", "tts_qa"), 5400),
    ("sourcebound_video", ("--from-stage", "video", "--through-stage", "video"), 1200),
)
TRANSIENT = re.compile(
    r"(?:429|503|temporarily unavailable|rate limit|server busy|"
    r"gemini.*(?:timeout|timed out|unresponsive|encountered an error)|"
    r"network connection reset)", re.I
)
STATE = "WINDOWS_ORIGINAL_SOURCE_BOUNDED_E2E_CHECKPOINT_V1"
class SourceboundE2EError(ValueError):
    pass

def require(ok:bool, message:str)->None:
    if not ok:raise SourceboundE2EError(message)

def sha(path:Path)->str:
    # Dell-115 validated Docling/Selenium interpreter may be Python 3.10;
    # hashlib.file_digest exists only on newer Python versions.
    digest=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1048576),b""):
            digest.update(chunk)
    return digest.hexdigest()

def atomic_json(path:Path,payload:dict)->None:
    target=path.with_suffix(path.suffix+".tmp")
    with target.open("x",encoding="utf8") as f:
        json.dump(payload,f,indent=2,ensure_ascii=False)
        f.write("\n")
    target.replace(path)

def stage_tree(*,source_root:Path,snapshot_root:Path,subchapter:str)->dict:
    require(re.fullmatch(r"\d+\.\d+",subchapter) is not None,
            "Only an exact numbered subchapter is eligible")
    source=source_root/subchapter.split(".")[0]/subchapter/"source.pdf"
    new=snapshot_root/subchapter.split(".")[0]/subchapter/"source.pdf"
    require(source.is_file() and not source.is_symlink(),
            "Real original textbook source.pdf required")
    require(source_root.resolve()!=snapshot_root.resolve()
            and not snapshot_root.resolve().is_relative_to(source_root.resolve())
            and not source_root.resolve().is_relative_to(snapshot_root.resolve()),
            "New local isolated output PDF tree must not intersect protected source tree")
    before=sha(source)
    if not new.exists():
        require(not new.parent.exists() or not list(new.parent.iterdir()),
                "Do not clobber any existing isolated lecture output")
        new.parent.mkdir(parents=True,exist_ok=True)
        try:
            with source.open("rb") as orig,new.open("xb") as out:
                shutil.copyfileobj(orig,out,1048576)
        except Exception:
            if new.is_file():new.unlink()
            raise
    require(new.is_file() and not new.is_symlink() and sha(new)==before
            and sha(source)==before,
            "Original and local test source must remain byte-identical")
    return {"source":str(source),"test_source":str(new),"original_sha256":before}

def _recover_exhausted_tts_after_code_fix(state:dict)->dict:
    """One explicit code-repair retry epoch, preserving old failure evidence.

    No process may silently reset its retry budget after a provider outage.
    This exceptional transition requires a developer-approved source-safe
    change; subsequent repeats need a NEW code review, never another flag.
    """
    earlier=state.get("phases",{}).get("narrated_audio",{})
    if (earlier.get("outcome")=="stage_failed"
            and earlier.get("return_code")==124
            and earlier.get("attempt")>=3
            and earlier.get("transient") is True
            and state.get("phases",{}).get("source_content",{}).get("outcome")=="stage_pass"
            and not state.get("repair_history")
            and not state.get("published_to_students")):
        state["repair_history"]=[{"phase":"narrated_audio",
            "old_phase_receipt":dict(earlier),
            "reason":"source-preserving outage circuit and fallback repair",
            "old_logs_retained":True}]
        state["repair_epoch"]=1
        del state["phases"]["narrated_audio"]
        return state
    if state.get("repair_epoch")==1 and "narrated_audio" not in state.get("phases",{}):
        return state
    raise SourceboundE2EError(
        "No eligible exhausted TTS checkpoint or repair epoch already used; "
        "never silently reset the verified retry budget")


def _launcher(python:Path,root:Path,topic:str,work:Path,phase:tuple[str,tuple[str,...],int])->list[str]:
    name,from_to,_=phase
    command=[str(python),"-m","selenium_pipeline.runner",
             "--source-root",str(root),"--subchapter",topic,
             "--work-root",str(work),"--communication-mode","selenium",
             *from_to]
    if name in {"narrated_audio","sourcebound_video"}:
        command.append("--confirm-gemini-api-cost")
    return command

def execute_windows(*,source_root:Path,snapshot_root:Path,
                    work_root:Path,subchapter:str,pipeline_python:Path,
                    tts_python:Path,repo:Path,
                    allow_live:bool=False,max_retries:int=3,
                    resume_after_code_repair:bool=False,
                    retry_seconds:int=90,
                    run_command=None,sleep=None)->dict:
    require(sys.platform=="win32","No Ubuntu/Linux/macOS production: Windows required")
    require(type(max_retries) is int and 1<=max_retries<=3,
            "Automatic retry budget must be 1 to 3")
    require(type(retry_seconds) is int and 0<=retry_seconds<=300,
            "Bounded transient Gemini backoff required")
    require(repo.is_dir() and (repo/"selenium_pipeline"/"runner.py").is_file()
            and pipeline_python.is_file() and tts_python.is_file(),
            "Required Windows-local code and both validated Python interpreters missing")
    source_proof=stage_tree(source_root=source_root,snapshot_root=snapshot_root,
                            subchapter=subchapter)
    statepath=work_root/subchapter.split(".")[0]/subchapter/"windows_e2e_checkpoint.json"
    statepath.parent.mkdir(parents=True,exist_ok=True)
    old=json.loads(statepath.read_text(encoding="utf8")) if statepath.is_file() else None
    require(old is None or (old.get("status")==STATE
            and old.get("original_sha256")==source_proof["original_sha256"]
            and old.get("test_source")==source_proof["test_source"]),
            "Checkpoint identity differs from original immutable textbook PDF")
    state=old or {"status":STATE,**source_proof,"phases":{},
                  "student_publication_authorized":False,
                  "published_to_students":False}
    runner=run_command or subprocess.run
    pause=sleep or time.sleep
    env=os.environ.copy()
    env.update({"MICROGEN_TTS_PYTHON":str(tts_python),
        "MICROGEN_PIPELINE_PYTHON":str(pipeline_python),
        "MICROGEN_COMMUNICATION_MODE":"selenium",
        "PYTHONNOUSERSITE":"1","PYTHONUTF8":"1","PYTHONIOENCODING":"utf8"})
    if resume_after_code_repair:
        require(allow_live,"Cannot unlock a retry epoch in planning mode")
        state=_recover_exhausted_tts_after_code_fix(state)
    state["last_invocation_mode"]="live" if allow_live else "source_only_plan"
    atomic_json(statepath,state)
    if not allow_live:
        state["dry_run_commands"]=[
            _launcher(pipeline_python,snapshot_root,subchapter,work_root,phase)
            for phase in PHASES]
        atomic_json(statepath,state)
        return state
    for phase in PHASES:
        name,_,timeout=phase
        if state["phases"].get(name,{}).get("outcome")=="stage_pass":
            continue
        previous=state["phases"].get(name,{})
        if (previous.get("outcome")=="stage_failed"
                and previous.get("transient") is False):
            raise SourceboundE2EError(
                f"{name} is a recorded nontransient blocker; do not repeat "
                "billable or browser calls without a source/code repair")
        already=int(previous.get("attempt",0))
        require(already<max_retries,
                f"{name}: saved retry budget of {max_retries} already exhausted")
        command=_launcher(pipeline_python,snapshot_root,subchapter,work_root,phase)
        for attempt in range(already+1,max_retries+1):
            suffix=(f"_repair{state['repair_epoch']}" if
                    name=="narrated_audio" and state.get("repair_epoch") else "")
            log=statepath.parent/f"windows_e2e_{name}{suffix}_attempt{attempt}.log"
            with log.open("x",encoding="utf8") as stream:
                try:
                    outcome=runner(command,cwd=str(repo),env=env,
                                   stdout=stream,stderr=subprocess.STDOUT,
                                   timeout=timeout,check=False)
                    code=outcome.returncode
                except subprocess.TimeoutExpired:
                    code=124
            observed=log.read_text(encoding="utf8",errors="replace")
            source_ok=(sha(Path(source_proof["source"]))==
                       source_proof["original_sha256"]
                       and sha(Path(source_proof["test_source"]))==
                       source_proof["original_sha256"])
            require(source_ok,"Original source/test PDF changed; abort")
            state["phases"][name]={"outcome":"stage_pass" if code==0 else "stage_failed",
                                  "return_code":code,"attempt":attempt,
                                  "log":str(log),"transient":bool(TRANSIENT.search(observed))}
            atomic_json(statepath,state)
            if code==0:break
            if not TRANSIENT.search(observed) or attempt==max_retries:
                raise SourceboundE2EError(
                    f"{name} stopped safely; see {log}; not approved or published")
            pause(retry_seconds)
        require(state["phases"][name]["outcome"]=="stage_pass","Unfinished stage")
    from .runner import check_valid
    produced=Path(source_proof["test_source"]).parent
    require(check_valid("video",produced),
            "No genuine source-bound, audio-synchronized multipart video passed final QA")
    state["complete_technical_video_QA_pass"]=True
    state["independent_academic_acceptance_required"]=True
    state["published_to_students"]=False
    atomic_json(statepath,state)
    return state

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-root",type=Path,required=True)
    p.add_argument("--snapshot-root",type=Path,required=True)
    p.add_argument("--work-root",type=Path,required=True)
    p.add_argument("--subchapter",required=True)
    p.add_argument("--pipeline-python",type=Path,required=True)
    p.add_argument("--tts-python",type=Path,required=True)
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--execute-live",action="store_true")
    p.add_argument("--resume-after-code-repair",action="store_true",
                   help="One auditable source-hash-locked exhausted TTS retry epoch")
    p.add_argument("--max-retries",type=int,default=3)
    p.add_argument("--retry-seconds",type=int,default=90)
    a=p.parse_args(argv)
    result=execute_windows(source_root=a.source_root,snapshot_root=a.snapshot_root,
        work_root=a.work_root,subchapter=a.subchapter,
        pipeline_python=a.pipeline_python,tts_python=a.tts_python,
        repo=a.repo,allow_live=a.execute_live,
        max_retries=a.max_retries,retry_seconds=a.retry_seconds,
        resume_after_code_repair=a.resume_after_code_repair)
    print(json.dumps({k:v for k,v in result.items() if k not in ("dry_run_commands",)},
        indent=2))
    return 0
if __name__=="__main__":raise SystemExit(main())
