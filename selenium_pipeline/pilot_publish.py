"""Safely publish reviewed pilot images and compile slides with rollback on failure."""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from .figure_approval import validate_approval
from .figure_audit import audit_one

def repair(folder: Path, approval: Path) -> dict:
    approved=validate_approval(folder,approval)["approved"]
    if not approved:
        raise ValueError("No approved figures")
    before=audit_one(folder)
    backup=folder/".microgen_figure_candidates"/"repair_backups"/datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup.mkdir(parents=True)
    shutil.copy2(folder/"slides.pdf",backup/"slides.pdf")
    shutil.copy2(folder/"slides.tex",backup/"slides.tex")
    for item in approved:
        shutil.copy2(item["candidate"],backup/("candidate_"+item["reference"]))
    published=[]
    try:
        for item in approved:
            destination=folder/item["reference"]
            if destination.exists():
                raise ValueError(f"Refusing overwrite: {destination}")
            shutil.copy2(item["candidate"],destination)
            published.append(destination)
        result=audit_one(folder)
        unresolved=[x for x in result["graphics"] if x["status"]!="present"]
        if unresolved:
            raise ValueError(f"Unresolved graphics remain: {unresolved}")
        with tempfile.TemporaryDirectory(prefix="microgen_compile_") as td:
            command=["pdflatex","-interaction=nonstopmode","-halt-on-error",
                     "-output-directory="+td,"slides.tex"]
            for _ in range(2):
                run=subprocess.run(command,cwd=folder,text=True,capture_output=True,timeout=180)
                if run.returncode:
                    (backup/"compile_error.log").write_text(run.stdout[-15000:]+run.stderr[-5000:],encoding="utf-8")
                    raise RuntimeError("pdflatex compilation failed; see backup log")
            compiled=Path(td)/"slides.pdf"
            if not compiled.exists() or compiled.stat().st_size<1000:
                raise RuntimeError("Compiled PDF missing or unexpectedly small")
            shutil.copy2(compiled,folder/"slides.pdf")
        report=dict(status="slides_rebuilt_downstream_stale",published=[x.name for x in published],
                    backup=str(backup),previous_missing=len([x for x in before["graphics"] if x["status"]!="present"]),
                    unresolved=0,requires=["narration_review","tts_review","mp4_rebuild"])
        (folder/".microgen_figure_candidates"/"repair_result.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        return report
    except Exception:
        for path in published:
            path.unlink(missing_ok=True)
        shutil.copy2(backup/"slides.pdf",folder/"slides.pdf")
        raise

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path)
    args=p.parse_args()
    print(json.dumps(repair(args.folder,args.folder/".microgen_figure_candidates"/"pilot_reviewed_figures.json"),indent=2))
