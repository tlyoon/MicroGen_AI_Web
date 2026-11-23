"""Strict, byte-anchored PDF text parser ABI recovery for Chapter 11 video-only stage.

Only a DERIVED page.get_text digest may differ. Every original source,
slides, script, numbered WAV, narration sequence, approved structural receipt
and existing technical preview must match exact SHA. NO completed-lecture
receipt is allowed; neither this route nor its callers approve visual
highlights, scientific meaning or student release.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .slide_narration_sync import inspect as inspect_sync, RECEIPT
from .cross_pc_artifact_recovery_registry import require_cross_pc_handler
from .recovery_registry import lookup_mechanism

SIGNATURE = "STAGE_ONLY_NARRATED_MP4_DERIVED_PDF_TEXT_HASH_DRIFT"
MECHANISM = "VERIFY_EXACT_STAGE_ONLY_SOURCE_WAV_PREVIEW_NO_RELEASE"
KIND = "ch11_stage_only_pdf_text_parity"
STAGE_STATUS = "TECHNICAL_NARRATED_MP4_CHAIN_COMPLETE_HIGHLIGHTS_EXPLICITLY_NOT_REQUESTED"
PREVIEW_STATUS = "TECHNICAL_PREVIEW_SLIDE_AUDIO_SYNC_NO_ELEMENT_HIGHLIGHTS_NOT_RELEASED"
CROSS_SIGNATURE = "UNRELEASED_NARRATED_PREVIEW_DERIVED_TEXT_DIFFERS_ACROSS_PYMUPDF"
CROSS_MECHANISM = "VERIFY_STAGE_ONLY_UNCHANGED_PDF_SCRIPT_WAV_PREVIEW_AND_RETAIN_REVIEW_GATE"


def require(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError(why)


def _json(file: Path) -> dict:
    require(file.is_file() and not file.is_symlink(),
            "Missing or linked stage-only original evidence")
    value=json.loads(file.read_text(encoding="utf8"))
    require(type(value) is dict,"Invalid stage-only JSON evidence")
    return value


def _sha(file: Path) -> str:
    require(file.is_file() and not file.is_symlink(),
            "Missing or linked original source asset")
    digest=hashlib.sha256()
    with file.open("rb") as stream:
        for part in iter(lambda:stream.read(1024*1024),b""):
            digest.update(part)
    return digest.hexdigest()


def verify_stage_only_parser_drift(*,folder:Path,preview:Path) -> dict:
    """Return original technical sync receipt; never grant full QA or release."""
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Unregistered stage-only parser recovery")
    require(require_cross_pc_handler(CROSS_SIGNATURE)==CROSS_MECHANISM,
            "Unregistered exact cross-PC stage-only source recovery")
    folder,preview=Path(folder).absolute(),Path(preview).absolute()
    require(folder.is_dir() and not folder.is_symlink()
            and preview.is_dir() and not preview.is_symlink()
            and folder!=preview and not preview.is_relative_to(folder)
            and not folder.is_relative_to(preview),
            "Stage-only and preview folders not independently isolated")
    require(not (folder/".microgen_completion.json").exists()
            and not (folder/".microgen_completion.json").is_symlink(),
            "Published completed lecture must use strict original validator")
    require((folder/"source.pdf").is_file()
            and (folder/"slides.tex").is_file()
            and not (folder/"source.pdf").is_symlink()
            and not (folder/"slides.tex").is_symlink(),
            "Missing original publisher or authored source")
    saved=_json(folder/RECEIPT)
    actual=inspect_sync(folder)
    required={"version","pdf_sha256","script_sha256","pages",
              "page_text_sha256","narration_sha256","wav"}
    require(set(saved)==required and set(actual)==required
            and saved["version"]==actual["version"]==1
            and type(saved["pages"]) is int and saved["pages"]>0
            and saved["pages"]==actual["pages"]
            and type(saved["page_text_sha256"]) is list
            and type(actual["page_text_sha256"]) is list
            and len(saved["page_text_sha256"])==saved["pages"]
            and len(actual["page_text_sha256"])==saved["pages"],
            "Parser reconciliation must retain exact slide count and schema")
    require(all(saved[k]==actual[k] for k in required-{"page_text_sha256"}),
            "Source PDF, script, narration or WAV changed; not parser-only drift")
    changed=[n for n,(old,new) in enumerate(zip(
        saved["page_text_sha256"],actual["page_text_sha256"]),1)
        if old!=new]
    require(bool(changed),"No derived PDF text hash discrepancy exists")
    stage=_json(folder/".microgen_narrated_video_chain.json")
    require(stage.get("schema_version")==1
            and stage.get("status")==STAGE_STATUS
            and stage.get("full_g3_release_accepted") is False
            and stage.get("student_publication_authorized_by_this_receipt") is False
            and stage.get("independent_visual_highlight_acceptance")=="not_performed"
            and stage.get("highlight_verification_scope")=="explicitly_skipped_by_user"
            and stage.get("narration_synced_structurally") is True
            and stage.get("original_source_pdf_sha256")==_sha(folder/"source.pdf")
            and stage.get("slides_pdf_sha256")==saved["pdf_sha256"]
            and stage.get("script_txt_sha256")==saved["script_sha256"],
            "Existing stage-only receipt is not byte-pinned or is overapproved")
    preview_manifest=_json(preview/"preview_manifest.json")
    require(preview_manifest.get("status")==PREVIEW_STATUS
            and preview_manifest.get("preview_has_element_highlights") is False
            and preview_manifest.get("independent_encoded_highlight_qa_passed") is False
            and preview_manifest.get("student_published") is False,
            "Original preview is not independently unreleased stage-only content")
    names=("source.pdf","slides.pdf","script.txt",RECEIPT,
           "tts_fidelity_report.json")
    require(preview_manifest.get("original_sha256")=={
        name:_sha(folder/name) for name in names},
        "Original preview source or approved sync receipt SHA changed")
    wavs={f"slide{n}.wav":_sha(folder/f"slide{n}.wav")
          for n in range(1,saved["pages"]+1)}
    require(preview_manifest.get("original_wav_sha256")==wavs,
            "Original audio differs from approved technical preview")
    require(len(saved["wav"])==saved["pages"]
            and [row.get("file") for row in saved["wav"]]==list(wavs)
            and all(row.get("sha256")==wavs[row["file"]]
                    for row in saved["wav"]),
            "Original numbered WAV receipts do not match original bytes")
    # Both exact publisher and original rendering are source-verified.
    # No new receipt, PDF, WAV, model call, TTS or video is generated.
    return {
        "status":"SOURCE_SHA_PINNED_STAGE_ONLY_PDF_TEXT_ABI_RECOVERED_NOT_RELEASED",
        "technical_sync_original":saved,
        "derived_text_hash_changed_pages":changed,
        "original_source_sha256":_sha(folder/"source.pdf"),
        "original_slide_pdf_sha256":saved["pdf_sha256"],
        "original_sync_receipt_sha256":_sha(folder/RECEIPT),
        "original_wav_shas":wavs,
        "paid_model_sends":0,
        "independent_scientific_accepted":False,
        "independent_visual_highlight_accepted":False,
        "student_publication_authorized":False,
    }
