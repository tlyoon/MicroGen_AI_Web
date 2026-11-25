"""Reconcile a historical completion receipt after an independently validated media split.

Fail closed unless source, all unchanged artifacts, manifest part hashes and the
exact prior MP4 bytes are preserved in .history. No media or source modification.
"""
from __future__ import annotations
import hashlib,json,os,shutil
from pathlib import Path
from datetime import datetime,timezone

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fd:
        for chunk in iter(lambda:fd.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def reconcile(folder:Path,manifest:dict)->dict:
    folder=Path(folder)
    receipt_path=folder/".microgen_completion.json"
    if not receipt_path.is_file() or receipt_path.is_symlink():
        return {"status":"absent"}
    old=json.loads(receipt_path.read_text(encoding="utf8"))
    original=old.get("final_sha256",{})
    if not isinstance(original,dict):
        raise RuntimeError("Invalid completion receipt")
    required=("slides.tex","slides.pdf","script.txt","slides.mp4")
    if any(not (folder/n).is_file() or (folder/n).is_symlink() for n in required):
        raise RuntimeError("Missing completion artifact")
    actual={n:_sha(folder/n) for n in required}
    if old.get("source_sha256")!=_sha(folder/"source.pdf"):
        raise RuntimeError("Changed textbook source; refuse receipt repair")
    for name in required[:-1]:
        if original.get(name)!=actual[name]:
            raise RuntimeError(f"Changed historical receipt artifact {name}; refuse repair")
    expected_parts=manifest.get("parts")
    if not isinstance(expected_parts,list) or not expected_parts:
        raise RuntimeError("Missing verified parts")
    if manifest.get("source_sha256")!=old["source_sha256"]:
        raise RuntimeError("Manifest textbook source mismatch")
    if manifest.get("slides_sha256")!=actual["slides.pdf"] or manifest.get("script_sha256")!=actual["script.txt"]:
        raise RuntimeError("Manifest slide or narration mismatch")
    if expected_parts[0].get("filename")!="slides.mp4" or expected_parts[0].get("sha256")!=actual["slides.mp4"]:
        raise RuntimeError("Manifest video mismatch")
    for part in expected_parts:
        file=folder/part["filename"]
        if (not file.is_file() or file.is_symlink() or _sha(file)!=part["sha256"] or
            not 0<float(part["duration_seconds"])<600):
            raise RuntimeError("Invalid video part source or duration")
    if original.get("slides.mp4")==actual["slides.mp4"]:
        return {"status":"already_consistent","parts":len(expected_parts)}
    oldhash=original.get("slides.mp4")
    if not isinstance(oldhash,str) or len(oldhash)!=64:
        raise RuntimeError("Historical source video checksum missing")
    history=folder/".history"
    if not history.is_dir() or history.is_symlink():
        raise RuntimeError("No preserved original video history")
    archived=[]
    for candidate in history.rglob("*.mp4"):
        if candidate.is_file() and not candidate.is_symlink() and _sha(candidate)==oldhash:
            archived.append(candidate)
    if not archived:
        raise RuntimeError("Original completion video not recoverably archived")
    archive=history/("receipt_reconciliation_"+datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f"))
    archive.mkdir(parents=True,exist_ok=False)
    backup=archive/"prior_completion_receipt.json"
    shutil.copy2(receipt_path,backup)
    if _sha(backup)!=_sha(receipt_path):
        raise RuntimeError("Backup receipt failed hash check")
    original["slides.mp4"]=actual["slides.mp4"]
    old["historical_receipt_media_reconciliation"]={
        "status":"ORIGINAL_MP4_ARCHIVED_AND_VERIFIED",
        "previous_video_sha256":oldhash,
        "current_video_sha256":actual["slides.mp4"],
        "archived_video_path":str(archived[0].relative_to(folder)),
        "previous_receipt_path":str(backup.relative_to(folder)),
        "multipart_video_count":len(expected_parts),
        "reconciled_utc":datetime.now(timezone.utc).isoformat()}
    old["multipart_video_count"]=len(expected_parts)
    stage=receipt_path.with_name("."+receipt_path.name+".reconciling")
    if stage.exists():
        raise RuntimeError("Unresolved receipt reconciliation stage")
    try:
        stage.write_text(json.dumps(old,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
        os.replace(stage,receipt_path)
    finally:
        stage.unlink(missing_ok=True)
    assert _sha(receipt_path)!=_sha(backup)
    return {"status":"reconciled_preserving_archived_original","parts":len(expected_parts),
            "archived_original_sha256":oldhash,"current_sha256":actual["slides.mp4"]}
