"""Guard against resending a previously refused identical original textbook page.

This is a SOURCE-PAGE no-Send guard, not a mapping or science acceptance tool.
It compares original PDF page RGB pixels, exact rendered page PNG bytes, exact
original figure crop bytes and a prior immutable owned Gemini refusal. A failed
prior page never becomes an accepted figure mapping.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re

import pymupdf

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import _verified_json, require


class DuplicateOriginalPageSendBlocked(ValueError):
    pass


def _render_digest(pdf: Path, page: int) -> str:
    with pymupdf.open(pdf) as source:
        require(0 < page <= len(source) <= 250, "Invalid source PDF page")
        pix = source[page-1].get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False)
        digest = hashlib.sha256()
        digest.update(str((pix.width, pix.height, pix.n)).encode())
        digest.update(pix.samples)
        return digest.hexdigest()


def _page_and_crops(workspace: Path, page: int) -> tuple[Path, dict[str, str]]:
    path = workspace / "pages" / f"page_{page}" / f"page_{page}.png"
    crop_dir = workspace / "crops" / f"page_{page}"
    require(path.is_file() and not path.is_symlink()
            and crop_dir.is_dir() and not crop_dir.is_symlink(),
            "Current source page or crops not uniquely grounded")
    crops = sorted(p for p in crop_dir.iterdir()
                   if p.is_file() and re.fullmatch(r"fig_[0-9]+\.png", p.name)
                   and not p.is_symlink())
    require(crops and len(crops) <= 30, "Unbounded or missing original crops")
    return path, {p.name: file_sha256(p) for p in crops}


def inspect_prior_identical_refusal(*, workspace: Path, page_number: int,
                                   max_trials: int = 600) -> dict:
    """Fail closed on a duplicate previous owned page-level model refusal.

    The distinct whole-PDF hash is deliberately NOT a reason to bypass a
    verified identical page. An absent or untrustworthy prior receipt is never
    reinterpreted as successful figure extraction.
    """
    workspace = Path(workspace).absolute()
    require(os.name == "nt" and workspace.name == ".microgen_work"
            and re.fullmatch(r"[0-9]+\.[0-9]+", workspace.parent.name)
            and workspace.parent.parent.name == workspace.parent.name.split(".")[0]
            and workspace.parent.parent.parent.name == "source_tree"
            and type(page_number) is int and 0 < page_number <= 250,
            "Not an authentic local original-source figure workspace")
    trial = workspace.parents[3]
    registry = trial.parent
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(local.is_dir() and registry.is_relative_to(local)
            and registry.is_dir() and not registry.is_symlink()
            and trial.is_dir() and not trial.is_symlink(),
            "Source registry must be Windows-local and immutable")
    source = workspace / "source.pdf"
    require(source.is_file() and not source.is_symlink(), "Staged PDF unavailable")
    actual = _render_digest(source, page_number)
    page_image, crops = _page_and_crops(workspace, page_number)
    page_image_sha = file_sha256(page_image)
    # All prior receipts are inspected read-only and bounded. The previous
    # claim is recognized only if both Send attribution and exact refusal hold.
    candidates = sorted(registry.rglob("figures_attempt_result.json"))
    require(len(candidates) <= max_trials, "Historical source registry unbounded")
    examined = 0
    for result_path in candidates:
        prior = result_path.parent
        if prior == trial:
            continue
        require(result_path.is_file() and not result_path.is_symlink(),
                "Invalid prior result receipt")
        old_result = _verified_json(result_path)
        if (old_result.get("status") != "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY"
                or old_result.get("source_section") == workspace.parent.name):
            continue
        triage = prior / "figures_transport_triage.json"
        contract = prior / "fresh_trial_contract.json"
        if not triage.is_file() or not contract.is_file():
            continue
        checked = _verified_json(triage)
        old = _verified_json(contract)
        if (checked.get("owned_browser_send_registered") is not True
                or checked.get("registered_browser_send_count_in_stage_log", 0) < 1
                or checked.get("terminal_result_sha256") != file_sha256(result_path)
                or checked.get("original_submission_resend_authorized") is not False
                or old.get("source_sha256") != old_result.get("original_source_sha256")):
            continue
        old_source = Path(old["staged_source_path"])
        old_work = old_source.parent / ".microgen_work"
        if not old_source.is_file() or old_source.is_symlink() or not old_work.is_dir():
            continue
        require(file_sha256(old_source) == old["source_sha256"],
                "Historical original-source PDF changed")
        examined += 1
        pages = sorted((old_work / "pages").glob("page_*/page_*.png"))
        require(len(pages) <= 250, "Unbounded historical PDF page inventory")
        for old_png in pages:
            found = re.fullmatch(r"page_([0-9]+)\.png", old_png.name)
            if not found:
                continue
            n = int(found.group(1))
            old_reply = old_png.with_name(f"page_{n}_mapping.txt")
            if not old_reply.is_file() or old_reply.is_symlink():
                continue
            if old_reply.read_bytes().strip() != b"MAPPING_REVIEW_REQUIRED":
                continue
            if file_sha256(old_png) != page_image_sha:
                continue
            old_crop_path = old_work / "crops" / f"page_{n}"
            if not old_crop_path.is_dir() or old_crop_path.is_symlink():
                continue
            old_crops = sorted(p for p in old_crop_path.iterdir()
                               if p.is_file() and re.fullmatch(r"fig_[0-9]+\.png", p.name)
                               and not p.is_symlink())
            # Figure crop indices may change when the same printed PDF page
            # occurs as page 3 of one subsection and page 1 of another.
            # Compare the complete multiset of actual crop BYTES, not names.
            if (len(old_crops) != len(crops)
                    or sorted(file_sha256(p) for p in old_crops)
                        != sorted(crops.values())):
                continue
            if _render_digest(old_source, n) != actual:
                continue
            return {
                "status": "PREVIOUS_IDENTICAL_SOURCE_PAGE_GEMINI_REFUSAL_NO_RESEND",
                "page_number": page_number,
                "page_rgb_sha256": actual,
                "page_png_sha256": page_image_sha,
                "crop_sha256": crops,
                "prior_source_sha256": old["source_sha256"],
                "prior_source_page": n,
                "prior_trial": str(prior),
                "new_model_sends": 0,
                "figure_mapping_accepted": False,
            }
    return {"status": "NO_VERIFIED_IDENTICAL_REFUSAL_IN_SCOPED_REGISTRY",
            "page_number": page_number, "page_rgb_sha256": actual,
            "prior_trials_examined": examined, "new_model_sends": 0,
            "figure_mapping_accepted": False}


def block_duplicate_page_send(*, workspace: Path, page_number: int) -> dict:
    result = inspect_prior_identical_refusal(workspace=workspace,
                                             page_number=page_number)
    if result["status"] == "PREVIOUS_IDENTICAL_SOURCE_PAGE_GEMINI_REFUSAL_NO_RESEND":
        raise DuplicateOriginalPageSendBlocked(
            "Already refused identical original source page "
            f"{result['prior_source_page']} in separately SHA-bound trial; "
            "no second Gemini Send and no figure mapping acceptance")
    return result
