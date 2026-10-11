"""Fail-closed approval record for source-PDF figure candidates.

Approval is explicit and bound to source/candidate SHA256. No auto-publishing.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_approval(folder: Path, approval: Path) -> dict:
    data=json.loads(approval.read_text(encoding="utf-8"))
    source=folder/"source.pdf"
    if data.get("source_sha256") != digest(source):
        raise ValueError("Source PDF changed after figure review")
    approved=[]
    for item in data.get("figures",[]):
        reference=item["reference"]
        if Path(reference).name != reference or not reference.lower().endswith(".png"):
            raise ValueError("Invalid figure reference")
        candidate=Path(item["candidate"])
        candidates_root=(folder/".microgen_figure_candidates").resolve()
        if not candidate.is_absolute():
            candidate=folder/candidate
        candidate=candidate.resolve()
        if not candidate.is_relative_to(candidates_root):
            raise ValueError("Candidate must be inside quarantine directory")
        if not candidate.is_file() or digest(candidate)!=item.get("sha256"):
            raise ValueError("Candidate missing or modified after review")
        if item.get("reviewed") is not True:
            raise ValueError("Figure lacks explicit review approval")
        if (folder/reference).exists():
            raise ValueError("Will not overwrite an existing figure")
        approved.append(dict(reference=reference,candidate=str(candidate),sha256=digest(candidate)))
    if len({x["reference"] for x in approved})!=len(approved):
        raise ValueError("Duplicate figure references")
    return dict(approved=approved,source_sha256=digest(source))

def make_review_template(folder: Path) -> Path:
    root=folder/".microgen_figure_candidates"
    gallery=json.loads((root/"cluster_gallery"/"gallery.json").read_text(encoding="utf-8"))
    template=dict(source_sha256=digest(folder/"source.pdf"),
                  figures=[dict(reference="",candidate=x["image"],sha256=digest(Path(x["image"])),
                                reviewed=False,source_page=x["page"]) for x in gallery["candidates"]])
    target=root/"figure_review_template.json"
    target.write_text(json.dumps(template,indent=2),encoding="utf-8")
    return target
