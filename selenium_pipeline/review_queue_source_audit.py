"""Read-only integrity inventory for an immutable original-source review queue."""
import json
from pathlib import Path
from .figure_source_identity import _sha
def inspect_source_bound_queue(queue_root:Path)->dict:
    q=Path(queue_root)
    if not q.is_dir() or q.is_symlink() or (q/"queue.json").is_symlink():
        raise ValueError("Original queue not a regular directory")
    p=json.loads((q/"queue.json").read_text(encoding="utf8"))
    if (p.get("status")!="IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE"
        or p.get("student_publication_authorized") is not False
        or type(p.get("slide_jobs")) is not list or not p["slide_jobs"]):
        raise ValueError("Wrong or empty immutable review queue")
    folder=Path(p["original_source_folder"])
    if not folder.is_dir() or not folder.is_absolute() or folder.resolve()==q.resolve():
        raise ValueError("Original source folder identity invalid")
    for name in ("source.pdf","slides.pdf","script.txt"):
        x=folder/name
        if not x.is_file() or x.is_symlink():raise ValueError("Source must remain unmodified regular file")
    sha={name:_sha(folder/name) for name in ("source.pdf","slides.pdf","script.txt")}
    nums=[];covered=0
    for row in p["slide_jobs"]:
        n=row.get("slide")
        c=row.get("utterance_count")
        if type(n) is not int or type(c) is not int or not 1<=n<=200 or c<=0:
            raise ValueError("Invalid slide or original utterance count")
        nums.append(n);covered+=c
        for key,ref in (("original_source_sha256","source.pdf"),
                        ("original_slides_sha256","slides.pdf"),
                        ("original_script_sha256","script.txt")):
            if row.get(key)!=sha[ref]:raise ValueError("Original textbook/slide/script drift detected")
    if (nums!=sorted(set(nums)) or type(p.get("expected_utterances")) is not int
        or covered!=p["expected_utterances"]):
        raise ValueError("Original immutable queue coverage altered")
    return {"status":"ORIGINAL_QUEUE_SOURCE_ASSETS_VERIFIED",
        "slides":len(nums),"original_utterances":covered,
        "source_sha256":sha["source.pdf"],
        "student_publication_authorized":False}
