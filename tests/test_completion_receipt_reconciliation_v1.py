import json,hashlib
import pytest
from pathlib import Path
from selenium_pipeline.completion_receipt_reconciliation_v1 import reconcile

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def fixture(folder:Path,save_original=True):
    folder.mkdir(exist_ok=True,parents=True)
    for name in ("source.pdf","slides.tex","slides.pdf","script.txt","slides.mp4"):
        (folder/name).write_bytes((name+"-current").encode("utf8"))
    old_video=b"slides.mp4-previous"
    history=folder/".history"/"earlier"
    history.mkdir(parents=True)
    if save_original:(history/"slides.mp4").write_bytes(old_video)
    original_hashes={name:sha(folder/name) for name in ("slides.tex","slides.pdf","script.txt","slides.mp4")}
    original_hashes["slides.mp4"]=hashlib.sha256(old_video).hexdigest()
    receipt={"source_sha256":sha(folder/"source.pdf"),"final_sha256":original_hashes}
    (folder/".microgen_completion.json").write_text(json.dumps(receipt))
    manifest={"status":"technical_length_control_passed","source_sha256":sha(folder/"source.pdf"),
        "slides_sha256":sha(folder/"slides.pdf"),"script_sha256":sha(folder/"script.txt"),
        "parts":[{"filename":"slides.mp4","sha256":sha(folder/"slides.mp4"),"duration_seconds":301}]}
    return manifest

def test_reconciles_only_when_original_media_archived(tmp_path):
    manifest=fixture(tmp_path)
    result=reconcile(tmp_path,manifest)
    assert result["status"]=="reconciled_preserving_archived_original"
    receipt=json.loads((tmp_path/".microgen_completion.json").read_text())
    assert receipt["final_sha256"]["slides.mp4"]==sha(tmp_path/"slides.mp4")
    history=receipt["historical_receipt_media_reconciliation"]
    assert history["previous_video_sha256"]==hashlib.sha256(b"slides.mp4-previous").hexdigest()
    assert (tmp_path/history["previous_receipt_path"]).is_file()
    assert reconcile(tmp_path,manifest)["status"]=="already_consistent"

def test_refuses_missing_original_archive(tmp_path):
    manifest=fixture(tmp_path,save_original=False)
    with pytest.raises(RuntimeError,match="recoverably archived"):
        reconcile(tmp_path,manifest)

def test_refuses_modified_script(tmp_path):
    manifest=fixture(tmp_path)
    (tmp_path/"script.txt").write_text("CHANGED")
    with pytest.raises(RuntimeError,match="script.txt"):
        reconcile(tmp_path,manifest)
