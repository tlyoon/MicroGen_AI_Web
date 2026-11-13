"""Versioned, on-flight independent source math proof for CACHED stages.

A previously accepted script_qa stage is valid and MUST NOT be regenerated
merely because a new independent math engine is installed. On every real
script_qa/TTS/video handoff, create or reuse an immutable SHA-locked sidecar
OUTSIDE the original textbook folder, separate from old runner receipts.
Never reset previously accepted upstream work, synthesize audio, or convert
an analytic identity into independent narration/figure/release approval.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from .figure_source_identity import _sha, require
from .source_physics_drag_symbolic_qa import inspect as inspect_drag


REVISION = 1
NAME = "source_math_symbolic_proof_v1.json"
MANIFEST = "receipt.json"


def _pack(value: dict) -> bytes:
    return (json.dumps(value,indent=2,sort_keys=True,
                      ensure_ascii=False)+"\n").encode("utf8")


def _safe_dir(path: Path) -> Path:
    path=Path(path).absolute()
    require(not path.is_symlink(), "Symlinked source math evidence folder")
    path.mkdir(parents=True, exist_ok=True)
    require(path.is_dir() and not path.is_symlink(),
            "Unsafe source math checkpoint root")
    return path


def _verify_cache(*,folder: Path,source_hash: str,
                  script_hash: str,fingerprint: str)->dict:
    require(folder.is_dir() and not folder.is_symlink(),
            "Missing or symlinked versioned source mathematics checkpoint")
    proof=folder/NAME
    receipt=folder/MANIFEST
    require(proof.is_file() and receipt.is_file()
            and not proof.is_symlink() and not receipt.is_symlink(),
            "Corrupt historical mathematics checkpoint: preserve, do not overwrite")
    record=json.loads(receipt.read_text("utf8"))
    report=json.loads(proof.read_text("utf8"))
    require(type(record) is dict and type(report) is dict
            and record.get("schema_version")==1
            and record.get("engine_revision")==REVISION
            and record.get("source_sha256")==source_hash
            and record.get("script_sha256")==script_hash
            and record.get("fingerprint")==fingerprint
            and record.get("sha256")==_sha(proof)
            and report.get("schema_version")==1
            and report.get("source_sha256")==source_hash
            and report.get("script_sha256")==script_hash
            and report.get("G2_approved") is False
            and report.get("audio_or_TTS_authorized") is False
            and report.get("source_script_math_equations_all_semantically_verified") is False,
            "Previously verified source math proof changed or claims unsupported approval")
    return {"schema_version":1,
            "status":"REUSED_IMMUTABLE_SOURCE_MATH_PROOF"
                     if report["source_physically_has_relevant_model_headings"]
                     else "REUSED_IMMUTABLE_NOT_APPLICABLE_MATH_PROOF",
            "checkpoint":str(folder),"engine_revision":REVISION,
            "source_sha256":source_hash,
            "script_sha256":script_hash,
            "proof_sha256":record["sha256"],
            "symbolic_proof_available":report["proof"] is not None,
            "new_model_or_tts_requests":0,
            "all_narration_mathematics_verified":False,
            "G2_approved":False,
            "student_publication_authorized":False}


def ensure(*,source: Path,script: Path,
           checkpoint_root: Path | None=None)->dict:
    source,script=Path(source).absolute(),Path(script).absolute()
    require(source.name=="source.pdf" and script.name=="script.txt"
            and script.parent==source.parent and source.is_file()
            and script.is_file() and not source.is_symlink()
            and not script.is_symlink(),
            "Only original source-adjacent PDF and script can witness math")
    source_hash,script_hash=_sha(source),_sha(script)
    root_path=(Path(checkpoint_root).absolute() if checkpoint_root is not None
          else (Path(os.environ.get("LOCALAPPDATA") or
                   str(Path.home()/".cache"))/
                "MicroGen_AI_Web_Checkpoints"/"_source_math_gate").absolute())
    # Reject unsafe caller-supplied roots BEFORE mkdir; even a failed
    # recovery preflight may not create artifacts inside original source.
    require(not root_path.is_relative_to(source.parent)
            and not source.parent.is_relative_to(root_path),
            "Source math stage receipts must be outside the lecture folder")
    root=_safe_dir(root_path)
    fingerprint=hashlib.sha256(_pack({
        "engine_revision":REVISION,"source_sha256":source_hash,
        "script_sha256":script_hash})).hexdigest()[:28]
    folder=root/("source_math_"+fingerprint)
    if folder.exists() or folder.is_symlink():
        return _verify_cache(folder=folder,source_hash=source_hash,
                             script_hash=script_hash,fingerprint=fingerprint)
    report=inspect_drag(source=source,script=script)
    require(_sha(source)==source_hash and _sha(script)==script_hash
            and report["source_sha256"]==source_hash
            and report["script_sha256"]==script_hash
            and report["G2_approved"] is False
            and report["audio_or_TTS_authorized"] is False,
            "Source math proof changed original source or granted improper approval")
    temp=Path(tempfile.mkdtemp(prefix="source_math_unaccepted_",dir=root))
    try:
        proof=temp/NAME
        with proof.open("xb") as f:
            f.write(_pack(report))
            f.flush()
            os.fsync(f.fileno())
        receipt={"schema_version":1,"engine_revision":REVISION,
                 "source_sha256":source_hash,"script_sha256":script_hash,
                 "fingerprint":fingerprint,"sha256":_sha(proof),
                 "original_source_modified":False,
                 "math_verification_scope":"ANALYTIC_IDENTITIES_ONLY",
                 "G2_approved":False,"student_publication_authorized":False}
        with (temp/MANIFEST).open("xb") as f:
            f.write(_pack(receipt))
            f.flush()
            os.fsync(f.fileno())
        require(_sha(source)==source_hash and _sha(script)==script_hash,
                "Original lecture changed during math receipt transaction")
        installed=False
        try:
            os.rename(temp,folder)
            installed=True
        except FileExistsError:
            # Another worker may have finished the identical proof first.
            # Its source-locked evidence must independently verify; the
            # losing worker never claims it created the accepted proof.
            pass
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    result=_verify_cache(folder=folder,source_hash=source_hash,
                         script_hash=script_hash,fingerprint=fingerprint)
    return ({**result,
             "status":("CREATED_SOURCE_SHA_LOCKED_MATH_PROOF"
                       if report["source_physically_has_relevant_model_headings"]
                       else "CREATED_NOT_APPLICABLE_SOURCE_MATH_PROOF")}
            if installed else result)


def main(argv=None)->int:
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--script",required=True,type=Path)
    p.add_argument("--checkpoint-root",type=Path)
    a=p.parse_args(argv)
    print(json.dumps(ensure(source=a.source,script=a.script,
                            checkpoint_root=a.checkpoint_root),indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
