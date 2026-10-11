"""Audit LaTeX graphics against published files and the source-PDF extraction inventory.

Read-only by default; never substitute an unverified image.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

GRAPHIC = re.compile(r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}", re.I)
GUARD = re.compile(r"\\IfFileExists\s*\{([^{}]+)\}", re.I)
SUFFIXES = (".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg")

def audit_one(folder: Path) -> dict:
    tex = folder / "slides.tex"
    source = folder / "source.pdf"
    if not tex.is_file() or not source.is_file():
        raise FileNotFoundError(folder)
    content = tex.read_text(encoding="utf-8", errors="replace")
    refs = GRAPHIC.findall(content)
    guards = set(GUARD.findall(content))
    files = [p for p in folder.iterdir() if p.is_file()]
    staged = folder / ".microgen_work"
    if staged.is_dir():
        files += [p for p in staged.rglob("*") if p.is_file() and p.suffix.lower() in SUFFIXES]
    entries = []
    for raw in refs:
        name = Path(raw)
        if name.is_absolute() or ".." in name.parts or "\\" in raw:
            entries.append({"reference":raw,"status":"unsafe"});continue
        variants = [raw] if name.suffix.lower() in SUFFIXES else [raw + s for s in SUFFIXES]
        existing = next((folder / x for x in variants if (folder / x).is_file() and (folder / x).stat().st_size),None)
        if existing:
            entries.append({"reference":raw,"status":"present","filename":str(existing.relative_to(folder))});continue
        # Only exact basename matches in staging are automatically recoverable.
        exact = [p for p in files if p.parent != folder and p.name in variants and p.stat().st_size]
        status = "recoverable_exact" if len(exact)==1 else "ambiguous" if len(exact)>1 else "missing"
        entries.append({"reference":raw,"status":status,"guarded":raw in guards,"candidates":[str(p) for p in exact]})
    return {"subchapter":folder.name,"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"graphics":entries}

def scan(root:Path, output:Path) -> dict:
    results=[]
    for tex in sorted(root.glob("*/*/slides.tex")):
        try: results.append(audit_one(tex.parent))
        except (OSError,ValueError) as exc: results.append({"subchapter":tex.parent.name,"error":str(exc)})
    report={"root":str(root),"scanned":len(results),"missing_references":sum(sum(x.get("status")!="present" for x in r.get("graphics",[])) for r in results),"subchapters":results}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-root",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    result=scan(args.source_root,args.report)
    print(f"Scanned {result['scanned']} LaTeX decks; {result['missing_references']} unresolved image references; report: {args.report}")
    for r in result["subchapters"]:
        missing=[x for x in r.get("graphics",[]) if x["status"]!="present"]
        if missing: print(r["subchapter"],[(x["reference"],x["status"]) for x in missing])

if __name__=="__main__":main()


def enforce_graphics(folder: Path, *, repair: bool = True) -> dict:
    """Fail closed on missing figures, including IfFileExists-guarded ones.

    Recovery only copies an exact, unique staged filename; never invents or
    guesses a figure from captions or visually similar images.
    """
    from .cleanup import _ensure_latex_graphics
    if repair:
        staging = folder / ".microgen_work"
        _ensure_latex_graphics(folder, staging if staging.is_dir() else None)
    result = audit_one(folder)
    missing = [entry for entry in result["graphics"] if entry["status"] != "present"]
    if missing:
        raise ValueError("Missing or unsafe LaTeX graphics: " + ", ".join(
            str(entry["reference"]) for entry in missing))
    manifest = {"source_sha256": result["source_sha256"], "figures": []}
    for entry in result["graphics"]:
        p = folder / entry["filename"]
        manifest["figures"].append({
            "reference": entry["reference"], "filename": entry["filename"],
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "size_bytes": p.stat().st_size,
            "status": "verified_file",
        })
    target = folder / "figures_manifest.json"
    pending = folder / "figures_manifest.json.tmp"
    pending.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pending.replace(target)
    return manifest
