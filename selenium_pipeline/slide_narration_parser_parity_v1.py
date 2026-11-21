"""Read-only PDF text-extraction ABI parity for a completed, byte-identical lecture.

Only a *derived page-text digest* may vary between PyMuPDF versions.
Do NOT accept changed PDF/script/WAV bytes, source hashes, page counts or
an unanchored structural receipt. Does not approve acoustic or scientific QA.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path


def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_parser_text_abi(*,folder:Path,saved:dict,actual:dict,
                           sync_receipt:Path)->dict:
    from .cross_pc_artifact_recovery_registry import require_cross_pc_handler
    require_cross_pc_handler("PUBLISHED_PDF_TEXT_HASH_DIFFERS_ACROSS_RENDERERS")
    folder=Path(folder)
    sync_receipt=Path(sync_receipt)
    expected={"version","pdf_sha256","script_sha256","pages",
              "page_text_sha256","narration_sha256","wav"}
    if (type(saved) is not dict or type(actual) is not dict
        or set(saved)!=expected or set(actual)!=expected
        or saved["version"]!=1 or actual["version"]!=1
        or type(saved["pages"]) is not int or saved["pages"]<=0
        or saved["pages"]!=actual["pages"]
        or type(saved["page_text_sha256"]) is not list
        or type(actual["page_text_sha256"]) is not list
        or len(saved["page_text_sha256"])!=saved["pages"]
        or len(actual["page_text_sha256"])!=saved["pages"]):
        raise ValueError("Untrusted parser ABI or changed slide count")
    for key in expected-{"page_text_sha256"}:
        if saved[key]!=actual[key]:
            raise ValueError("PDF, narration, script or audio changed: not parser ABI")
    pages_changed=[
        i+1 for i,(first,second) in enumerate(zip(
            saved["page_text_sha256"],actual["page_text_sha256"]))
        if first!=second]
    if not pages_changed or len(pages_changed)>max(
            1,math.ceil(saved["pages"]*0.10)):
        raise ValueError("Unbounded/absent text parser ABI discrepancy")
    anchor=folder/".microgen_completion.json"
    source=folder/"source.pdf"
    pdf=folder/"slides.pdf"
    script=folder/"script.txt"
    files=(anchor,source,pdf,script,sync_receipt)
    if any(not p.is_file() or p.is_symlink() for p in files):
        raise ValueError("Parser ABI recovery requires completed original lecture")
    receipt=json.loads(anchor.read_text(encoding="utf8"))
    if type(receipt) is not dict:
        raise ValueError("Published completion receipt is not a dictionary")
    finals=receipt.get("final_sha256")
    if (type(receipt) is not dict or type(finals) is not dict
        or receipt.get("source_sha256")!=_sha(source)
        or receipt.get("structural_sync_sha256")!=_sha(sync_receipt)
        or finals.get("slides.pdf")!=saved["pdf_sha256"]==_sha(pdf)
        or finals.get("script.txt")!=saved["script_sha256"]==_sha(script)):
        raise ValueError("Published source/sync receipt not anchored to exact bytes")
    return {
        "status":"SOURCE_LOCKED_PDF_PARSER_ABI_DRIFT_ONLY",
        "changed_text_pages":pages_changed,
        "unchanged_original_pdf_sha256":saved["pdf_sha256"],
        "unchanged_original_source_sha256":receipt["source_sha256"],
        "unchanged_original_script_sha256":saved["script_sha256"],
        "wav_and_narration_hashes_unchanged":True,
        "independent_scientific_or_acoustic_approval":False,
        "student_publication_authorized":False,
    }
