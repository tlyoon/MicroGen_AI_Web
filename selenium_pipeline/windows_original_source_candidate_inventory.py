"""Read-only inventory of distinct original PDFs eligible for a NEW Windows pilot.

Never re-submit a prior attempted source, generate Gemini/TTS content, repair a
particular PDF, modify publisher files or infer globally complete job history.
Reports only absence from the *specified* immutable trial ledger, and leaves
source selection and any paid provider send separately authorized.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _verified_json, require,
)
from .windows_scoped_prior_full_media_acceptance import _PR362


def find_candidates(*, publisher_root: Path, trial_registry_root: Path,
                    max_source_pdfs: int = 500,
                    max_trial_receipts: int = 5000) -> dict:
    require(os.name == "nt", "Only native Windows original-source discovery")
    source_root = Path(publisher_root).absolute()
    registry = Path(trial_registry_root).absolute()
    require(source_root.is_dir() and not source_root.is_symlink()
            and registry.is_dir() and not registry.is_symlink()
            and source_root != registry
            and not source_root.is_relative_to(registry)
            and not registry.is_relative_to(source_root),
            "Independent original publisher and existing external registry required")
    require(type(max_source_pdfs) is int and 1 <= max_source_pdfs <= 1000
            and type(max_trial_receipts) is int
            and 1 <= max_trial_receipts <= 20000,
            "Bounded inventory required; refuse unlimited full-drive traversal")
    sections = sorted(source_root.glob("*/*/source.pdf"))
    require(len(sections) <= max_source_pdfs,
            "Publisher source inventory exceeds declared bound; narrow root")
    known_claims = sorted(registry.rglob("fresh_trial_contract.json"))
    require(len(known_claims) <= max_trial_receipts,
            "Immutable source trial ledger exceeds declared bound")
    historical_sha = _PR362["source_sha256"]
    require(re.fullmatch(r"[0-9a-f]{64}", historical_sha) is not None,
            "Historic accepted original-source anchor missing")
    seen = {}
    for claim in known_claims:
        require(claim.is_file() and not claim.is_symlink(),
                "Unsafe source trial ledger file")
        parent = claim.parent
        while parent != registry:
            require(parent.is_dir() and not parent.is_symlink()
                    and registry in parent.parents,
                    "Source ledger symlinked parent or out-of-root path")
            parent = parent.parent
        data = _verified_json(claim)
        digest = data.get("source_sha256")
        require(data.get("schema_version") == 1
                and data.get("status") ==
                    "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL"
                and type(digest) is str
                and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
                and data.get("student_publication_authorized") is False,
                "Untrusted existing trial source claim: no duplicate submission")
        seen.setdefault(digest, []).append(str(claim))
    result = []
    excluded = []
    deduplicated = set()
    for pdf in sections:
        section, chapter = pdf.parent.name, pdf.parent.parent.name
        require(re.fullmatch(r"[0-9]+\.[0-9]+", section) is not None
                and chapter == section.split(".")[0]
                and not pdf.is_symlink()
                and not pdf.parent.is_symlink()
                and not pdf.parent.parent.is_symlink()
                and pdf.is_file() and pdf.stat().st_size > 100,
                "Publisher inventory has an unsafe or malformed original section")
        digest = file_sha256(pdf)
        label = f"{chapter}/{section}"
        if digest in deduplicated:
            excluded.append({
                "section": section, "source_sha256": digest,
                "reason": "DUPLICATE_SOURCE_PDF_BYTES_IN_PUBLISHER",
            })
            continue
        deduplicated.add(digest)
        if digest == historical_sha:
            excluded.append({
                "section": section, "source_sha256": digest,
                "reason": "ALREADY_ACCEPTED_HISTORICAL_ORIGINAL_NOT_A_NEW_SOURCE",
            })
            continue
        if digest in seen:
            excluded.append({
                "section": section, "source_sha256": digest,
                "reason": "SAME_PDF_ALREADY_PRESENT_IN_PROVIDED_TRIAL_LEDGER",
                "number_of_known_trial_claims": len(seen[digest]),
            })
            continue
        result.append({
            "section": section,
            "relative_source_path": f"{label}/source.pdf",
            "source_sha256": digest,
            "source_bytes": pdf.stat().st_size,
            "classification": "NOT_IN_SPECIFIED_TRIAL_LEDGER_ONLY",
            "globally_never_attempted_proven": False,
            "model_or_tts_requests_authorized": False,
        })
    return {
        "schema_version": 1,
        "status": (
            "CANDIDATE_CATALOG_UNVERIFIED_WITHOUT_TRIAL_HISTORY"
            if not known_claims else
            "DIFFERENT_ORIGINAL_SOURCE_CANDIDATES_FOUND_READ_ONLY"
            if result else
            "NO_UNUSED_ORIGINAL_SOURCE_IN_SPECIFIED_PUBLISHER_AND_LEDGER"
        ),
        "publisher_root": str(source_root),
        "trial_registry_root": str(registry),
        "historic_accepted_source_excluded": historical_sha,
        "publisher_source_files_examined": len(sections),
        "known_trial_contracts_examined": len(known_claims),
        "known_distinct_trial_source_count": len(seen),
        "potential_new_candidates": result,
        "excluded_source_summaries": excluded,
        "registry_scope_covers_all_historical_attempts": False,
        "automatic_model_generation_allowed": False,
        "new_model_or_tts_calls": False,
        "existing_ambiguous_source_resubmission_authorized": False,
        "student_publication_authorized": False,
        "recommended_next_action": (
            "Confirm a DIFFERENT new source has no prior ambiguous send "
            "outside this limited registry, then use a NEW exact-source trial "
            "and one explicit stage with user-approved provider cost."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--publisher-root", type=Path, required=True)
    ap.add_argument("--trial-registry-root", type=Path, required=True)
    ap.add_argument("--max-source-pdfs", type=int, default=500)
    ap.add_argument("--max-trial-receipts", type=int, default=5000)
    a = ap.parse_args(argv)
    try:
        output = find_candidates(
            publisher_root=a.publisher_root, trial_registry_root=a.trial_registry_root,
            max_source_pdfs=a.max_source_pdfs,
            max_trial_receipts=a.max_trial_receipts)
    except (CampaignRecoveryBlocked, OSError, ValueError) as exc:
        output = {"status": "ORIGINAL_SOURCE_CANDIDATE_DISCOVERY_REJECTED",
                  "reason": str(exc), "new_model_or_tts_calls": False,
                  "student_publication_authorized": False}
        print(json.dumps(output, indent=2))
        return 2
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
