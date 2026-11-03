"""Multi-source Windows original lecture campaign with idempotent recovery.

The source-to-video workflow needs more than passing individual PR tests.
This persists per-section REAL original-source release-readiness findings as
exact source/author/script and model-evidence SHA-bound immutable checkpoints.
A process crash after section A cannot cause A to be reprocessed just because
section B failed. New evidence starts a NEW versioned campaign; the original
records are never overwritten. No Gemini/ChatGPT, paid TTS or FFmpeg is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Callable

from .evidence_reuse_contract import file_sha256


class CampaignRecoveryBlocked(ValueError):
    pass


def require(ok:bool,message:str)->None:
    if not ok:raise CampaignRecoveryBlocked(message)


def _encode(value)->str:
    return json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,
                      allow_nan=False)+"\n"


def _digest(data)->str:
    return hashlib.sha256(_encode(data).encode("utf8")).hexdigest()


def _verified_json(path:Path)->dict:
    require(path.is_file() and not path.is_symlink(),
            "Missing or unsafe immutable section checkpoint")
    raw=path.read_text("utf8")
    try:
        obj=json.loads(raw)
    except (ValueError,OSError) as exc:
        raise CampaignRecoveryBlocked("Malformed original checkpoint") from exc
    require(type(obj) is dict and raw==_encode(obj),
            "Immutable original checkpoint's physical bytes were modified")
    return obj


def _new_atomic(path:Path,data)->None:
    require(not path.exists() and not path.is_symlink()
            and path.parent.is_dir() and not path.parent.is_symlink(),
            "Existing source-bound checkpoint may never be overwritten")
    fd,name=tempfile.mkstemp(prefix=".microgen_pending_",suffix=".json",
                            dir=path.parent)
    pending=Path(name)
    try:
        with os.fdopen(fd,"w",encoding="utf8",newline="\n") as file:
            file.write(_encode(data))
            file.flush()
            os.fsync(file.fileno())
        # os.rename is no-overwrite on native Windows on same volume;
        # all PR486 original work happens in a Windows-local checkpoint.
        os.rename(pending,path)
    finally:
        if pending.exists():pending.unlink()


def _fingerprint(spec:dict)->dict:
    require(type(spec) is dict and type(spec.get("section")) is str
            and spec["section"] and len(spec["section"])<=30,
            "Each original academic section requires a stable ID")
    lecture=Path(spec["lecture"]).absolute()
    require(lecture.is_dir() and not lecture.is_symlink(),
            "Original section publisher/author folder unavailable")
    inputs={}
    for name in ("source.pdf","slides.pdf","script.txt"):
        f=lecture/name
        require(f.is_file() and not f.is_symlink(),
                "Original publisher/author/script missing: "+name)
        inputs[name]=file_sha256(f)
    evidence={}
    for key,filename in (
            ("checkpoint","mapping_checkpoint.json"),
            ("fallback_dir","SAFE_PROSE_FALLBACK_MANIFEST.json"),
            ("queue_dir","UNRESOLVED_ONLY_MODEL_QUEUE_MANIFEST.json")):
        folder=Path(spec[key]).absolute()
        require(folder.is_dir() and not folder.is_symlink()
                and not folder.is_relative_to(lecture)
                and not lecture.is_relative_to(folder),
                "Review evidence must be outside frozen publisher/author assets")
        f=folder/filename
        require(f.is_file() and not f.is_symlink(),
                "Missing original source-bound review evidence: "+key)
        evidence[key]={"path":str(folder),
                       "manifest_sha256":file_sha256(f)}
    optional=spec.get("model_responses")
    if optional is not None:
        folder=Path(optional).absolute()
        require(folder.is_dir() and not folder.is_symlink()
                and not folder.is_relative_to(lecture),
                "Verified model responses must be stored outside original")
        files=sorted(folder.glob("slide_*.json"))
        require(files and all(p.is_file() and not p.is_symlink()
                              for p in files),
                "Incomplete or unsafe source-bound AI response evidence")
        evidence["model_responses"]={
            "path":str(folder),
            "file_sha256":{p.name:file_sha256(p) for p in files},
        }
    return {"section":spec["section"],
            "lecture":str(lecture),
            "original_files_sha256":inputs,
            "original_mapping_evidence":evidence}


def run_campaign(*,specs:list[dict],outdir:Path,
                 inspector:Callable|None=None,
                 after_section:Callable|None=None)->dict:
    require(type(specs) is list and 1<=len(specs)<=12
            and len({x.get("section") for x in specs})==len(specs),
            "Distinct original sections (maximum 12) required")
    roots=[_fingerprint(s) for s in specs]
    original_dirs=[Path(r["lecture"]) for r in roots]
    outdir=Path(outdir).absolute()
    require(outdir.is_dir() and not outdir.is_symlink()
            and all(not outdir.is_relative_to(p)
                    and not p.is_relative_to(outdir) for p in original_dirs),
            "Immutable Windows campaign receipts must be outside originals")
    contract={
        "schema_version":1,
        "status":"SOURCEBOUND_WINDOWS_MULTISOURCE_ORIGINAL_VERSIONED_CAMPAIGN",
        "sections":roots,
        "new_model_tts_or_video_generation_permitted":False,
        "student_publication_authorized":False,
    }
    path=outdir/"original_campaign_contract.json"
    if path.exists() or path.is_symlink():
        require(_verified_json(path)==contract,
                "Different original source/evidence version: create NEW campaign")
    else:
        _new_atomic(path,contract)
    if inspector is None:
        from .original_source_e2e_acceptance import inspect_source_e2e
        inspector=inspect_source_e2e
    records=[]
    processed=0
    reused=0
    for spec,source in zip(specs,roots):
        section=spec["section"]
        require(section.replace(".","").replace("-","").isalnum(),
                "Unsafe original academic section label")
        target=outdir/("section_"+section.replace(".","_")+"_e2e.json")
        if target.exists() or target.is_symlink():
            saved=_verified_json(target)
            body={key:val for key,val in saved.items()
                  if key!="immutable_payload_sha256"}
            require(saved.get("immutable_payload_sha256")==_digest(body)
                    and saved.get("section")==section
                    and saved.get("source_fingerprint_sha256")==_digest(source),
                    "Original accepted section receipt modified or stale")
            records.append(saved["actual_readiness"])
            reused+=1
            continue
        pre_hash={n:file_sha256(Path(spec["lecture"])/n)
                  for n in ("source.pdf","slides.pdf","script.txt")}
        require(pre_hash==source["original_files_sha256"],
                "Publisher/author source changed during campaign")
        report=inspector(
            lecture=Path(spec["lecture"]),
            checkpoint=Path(spec["checkpoint"]),
            fallback_dir=Path(spec["fallback_dir"]),
            queue_dir=Path(spec["queue_dir"]),
            model_responses=(Path(spec["model_responses"])
                             if spec.get("model_responses") else None))
        after_hash={n:file_sha256(Path(spec["lecture"])/n)
                    for n in pre_hash}
        require(after_hash==pre_hash and type(report) is dict
                and report.get("new_model_or_tts_calls") is False
                and report.get("student_publication_authorized") is False,
                "Inspector changed original academic assets or performed paid calls")
        claimed=report.get("source_inputs_sha256",report.get("input_sha256"))
        require(claimed==pre_hash,"Source E2E report has wrong SHA-bound originals")
        body={
            "schema_version":1,
            "section":section,
            "source_fingerprint_sha256":_digest(source),
            "actual_readiness":report,
            "new_paid_generation_attempted":False,
            "student_publication_authorized":False,
        }
        result={**body,"immutable_payload_sha256":_digest(body)}
        _new_atomic(target,result)
        records.append(report)
        processed+=1
        if after_section is not None:
            after_section(section)
    final={
        "status":("ORIGINAL_MULTISOURCE_TECHNICAL_ACCEPTANCE_COMPLETE"
                  if all(x["status"] in {
                      "ORIGINAL_SOURCE_STRICT_MULTIPART_TECHNICAL_PASS",
                      "REUSED_PHYSICALLY_VERIFIED_MULTIPART_TECHNICAL_ONLY"}
                      for x in records) else
                  "ORIGINAL_MULTISOURCE_CAMPAIGN_INCOMPLETE_SOURCE_GATES"),
        "original_sections":len(specs),
        "reused_prior_section_receipts_without_rerunning":reused,
        "new_original_sections_inspected":processed,
        "original_source_unchanged":True,
        "new_paid_generation_performed":False,
        "student_publication_authorized":False,
        "results":[{"section":spec["section"],
                    "status":record["status"]}
                   for spec,record in zip(specs,records)],
    }
    return final


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec",type=Path,required=True)
    p.add_argument("--outdir",type=Path,required=True)
    a=p.parse_args(argv)
    require(a.spec.is_file() and not a.spec.is_symlink(),
            "Actual native Windows source campaign specification required")
    data=json.loads(a.spec.read_text("utf8"))
    require(type(data) is dict and type(data.get("sections")) is list,
            "Expected exact source-bound section evidence manifest")
    print(json.dumps(run_campaign(specs=data["sections"],
                                  outdir=a.outdir),indent=2))
if __name__=="__main__":
    main()
