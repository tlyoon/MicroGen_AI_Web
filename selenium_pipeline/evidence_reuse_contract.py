"""Mandatory source-identity-and-scope preflight before repeated MicroGen QA.

No Gemini/TTS/network/lecture file mutations. This classifies a *requested
verification*, not the truth of any untested scientific claim. Proofs require
a physically unchanged JSON witness with an explicitly true accepted claim.
Untrusted/stale receipts fail closed instead of triggering costly rework.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_HASH = re.compile(r"^[a-f0-9]{64}$")
_VERDICTS = frozenset({
    "REUSE_VERIFIED", "COMPLETE_UNVERIFIED_SCOPE",
    "TARGETED_REVALIDATION", "BLOCK_UNJUSTIFIED_REOPEN",
    "BLOCK_STALE_EVIDENCE",
})


class EvidenceReuseBlocked(ValueError):
    """Malformed or forged evidence cannot authorize a new development task."""


def _check_digest(value: str, label: str) -> str:
    if not isinstance(value, str) or _HASH.fullmatch(value) is None:
        raise EvidenceReuseBlocked(f"Invalid {label}: expected SHA-256")
    return value


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class AcceptedClaim:
    component_id: str
    scope: str
    standard: str
    source_sha256: str
    author_sha256: str
    artifact_sha256: str
    receipt_path: Path
    receipt_sha256: str
    evidence_claim_path: tuple[str, ...]
    previous_pr: str
    # "accepted" means the selected claim is source/independently supported,
    # not an all-purpose pass for this figure or entire lecture.
    state: str = "verified"

    def validate(self) -> None:
        if not all(isinstance(v, str) and v.strip() and len(v) <= 180 for v in
                   (self.component_id, self.scope, self.standard, self.previous_pr)):
            raise EvidenceReuseBlocked("Claim must identify component, scope, standard and prior PR")
        for name in ("source_sha256", "author_sha256", "artifact_sha256", "receipt_sha256"):
            _check_digest(getattr(self, name), name)
        if self.state not in ("verified", "partial", "unverified"):
            raise EvidenceReuseBlocked("Unrecognized evidence acceptance state")
        if not self.evidence_claim_path or any(
                not isinstance(p, str) or not p for p in self.evidence_claim_path):
            raise EvidenceReuseBlocked("A precise accepted claim in the source receipt is necessary")
        path = Path(self.receipt_path)
        if not path.is_file() or path.is_symlink() or file_sha256(path) != self.receipt_sha256:
            raise EvidenceReuseBlocked("Historical source evidence missing, tampered or replaced")
        try:
            obj = json.loads(path.read_text(encoding="utf8"))
            for key in self.evidence_claim_path:
                obj = obj[key]
        except (KeyError, TypeError, ValueError, IndexError, UnicodeError) as exc:
            raise EvidenceReuseBlocked("Previous receipt claim does not exist") from exc
        if self.state == "verified" and obj is not True:
            raise EvidenceReuseBlocked("Previous report never established this exact verification scope")
        if self.state == "partial" and obj is True:
            raise EvidenceReuseBlocked("Verified claim must not masquerade as partial")


@dataclass(frozen=True)
class ProposedCheck:
    component_id: str
    scope: str
    standard: str
    source_sha256: str
    author_sha256: str
    artifact_sha256: str
    reopen_reason: str = ""
    # New contrary data must have a verifiable file and independent witness;
    # a different similarity threshold or detector error alone is insufficient.
    contradiction_path: Path | None = None
    contradiction_sha256: str | None = None

    def validate(self) -> None:
        if not all(isinstance(x, str) and x.strip() and len(x) <= 180 for x in
                   (self.component_id, self.scope, self.standard)):
            raise EvidenceReuseBlocked("Proposed check must specify exact component/scope/standard")
        for key in ("source_sha256", "author_sha256", "artifact_sha256"):
            _check_digest(getattr(self, key), key)


@dataclass(frozen=True)
class Preflight:
    decision: str
    component_id: str
    scope: str
    reason: str
    reused_from_pr: str | None = None
    reused_receipt_sha256: str | None = None
    original_verified_scope_preserved: bool = True
    new_production_release_granted: bool = False

    def __post_init__(self):
        if self.decision not in _VERDICTS or self.new_production_release_granted:
            raise EvidenceReuseBlocked("Preflight cannot grant production or invent a verdict")


def _independent_contradiction(task: ProposedCheck) -> bool:
    if task.contradiction_path is None and task.contradiction_sha256 is None:
        return False
    if task.contradiction_path is None or task.contradiction_sha256 is None:
        return False
    _check_digest(task.contradiction_sha256, "contradiction_sha256")
    p = Path(task.contradiction_path)
    if not p.is_file() or p.is_symlink() or file_sha256(p) != task.contradiction_sha256:
        return False
    try:
        data = json.loads(p.read_text("utf8"))
    except (UnicodeError, ValueError):
        return False
    return (
        data.get("status") == "INDEPENDENT_SOURCE_CONTRADICTION"
        and data.get("source_sha256") == task.source_sha256
        and data.get("author_sha256") == task.author_sha256
        and data.get("artifact_sha256") == task.artifact_sha256
        and data.get("scope") == task.scope
        and data.get("reproducible_physical_source_discrepancy") is True
        and isinstance(data.get("observed_difference"), str)
        and len(data["observed_difference"].strip()) >= 24
        and data.get("student_publication_authorized") is False
    )


def preflight(task: ProposedCheck, history: Iterable[AcceptedClaim]) -> Preflight:
    """Fail closed on accepted same-identity/scope; permit *scoped* new work.

    Code callers MUST obtain history by inspecting GitHub and prior versioned
    QA receipts; an empty fabricated history must not bypass this requirement.
    The decision cannot itself authorize paid TTS, main merge or publication.
    """
    task.validate()
    prior = list(history)
    for record in prior:
        record.validate()
    relevant = [r for r in prior if r.component_id == task.component_id]
    accepted = [r for r in relevant if r.state == "verified"]
    if not relevant:
        return Preflight("COMPLETE_UNVERIFIED_SCOPE", task.component_id, task.scope,
                         "No independently accepted claim for this component; verify anew")
    exact_input = [
        r for r in accepted if (
            r.source_sha256, r.author_sha256, r.artifact_sha256
        ) == (task.source_sha256, task.author_sha256, task.artifact_sha256)
    ]
    exact_scope = [r for r in exact_input if r.scope == task.scope]
    exact_standard = [r for r in exact_scope if r.standard == task.standard]
    if exact_standard:
        original = exact_standard[-1]
        if _independent_contradiction(task):
            return Preflight("TARGETED_REVALIDATION", task.component_id, task.scope,
                             "Physical independently sourced contradiction; review targeted claim only",
                             original.previous_pr, original.receipt_sha256)
        if task.reopen_reason:
            return Preflight("BLOCK_UNJUSTIFIED_REOPEN", task.component_id, task.scope,
                             "Prior exact source/artifact/scope already proved; "
                             "new detector or unsupported reason cannot invalidate it",
                             original.previous_pr, original.receipt_sha256)
        return Preflight("REUSE_VERIFIED", task.component_id, task.scope,
                         "Identical source/author/artifact SHA, acceptance scope and standard",
                         original.previous_pr, original.receipt_sha256)
    if exact_scope:
        return Preflight("TARGETED_REVALIDATION", task.component_id, task.scope,
                         "Acceptance standard changed: preserve former scope proof as versioned",
                         exact_scope[-1].previous_pr, exact_scope[-1].receipt_sha256)
    if accepted and not exact_input:
        old = accepted[-1]
        return Preflight("TARGETED_REVALIDATION", task.component_id, task.scope,
                         "Material source/author/artifact checksum changed; "
                         "invalidate only dependent verification",
                         old.previous_pr, old.receipt_sha256)
    if exact_input:
        old = exact_input[-1]
        return Preflight("COMPLETE_UNVERIFIED_SCOPE", task.component_id, task.scope,
                         f"Different, still-unproven scope; retain prior verified {old.scope}",
                         old.previous_pr, old.receipt_sha256)
    return Preflight("COMPLETE_UNVERIFIED_SCOPE", task.component_id, task.scope,
                     "Only partial or unverified historical evidence exists")


def source_artwork_preflight(
    *, ledger: Path, frozen_original_root: Path, figure_id: str,
    requested_scope: str = "publisher_artwork_identity",
    requested_standard: str = "frozen_original_pdf_author_v1",
) -> Preflight:
    """Real ledger adapter: Figure8.2–8.6 and tank source-artwork claims.

    This MUST be called before re-doing accepted figure-source similarity.
    It deliberately does not mark mathematical labels or WAV sync accepted.
    """
    from .recover_pinned_original_thomas_corpus import ORIGINAL_PINS

    ledger = Path(ledger).absolute()
    if not ledger.is_file() or ledger.is_symlink():
        raise EvidenceReuseBlocked("Physical immutable six-figure source ledger absent")
    data = json.loads(ledger.read_text(encoding="utf8"))
    if (data.get("status") !=
            "ALL_SIX_ORIGINAL_AUTHOR_IMAGES_PUBLISHER_VISUAL_PROVEN_FULL_SCIENCE_STILL_PENDING"
            or data.get("student_publication_authorized") is not False
            or data.get("original_frozen_41_source_slides") != 41):
        raise EvidenceReuseBlocked("Unaccepted or wrong original figure evidence ledger")
    entries = data["six_independently_version_bound_figure_identity_receipts"]
    if figure_id not in entries:
        raise EvidenceReuseBlocked("Figure has no previously verified publisher-artwork claim")
    row = entries[figure_id]
    if row.get("source_artwork_correspondence_proven") is not True:
        raise EvidenceReuseBlocked("Previous figure source-artwork claim was not verified")
    section = "8.6" if figure_id == "Exercise 62" else "8.4"
    filename = "Exercise 62.png" if section == "8.6" else f"Figure {figure_id}.png"
    folder = Path(frozen_original_root).absolute() / section
    original_pdf, author_pdf = ORIGINAL_PINS[section]
    input_paths = [folder / "source.pdf", folder / "slides.pdf", folder / filename]
    if (not all(p.is_file() and not p.is_symlink() for p in input_paths)
            or file_sha256(input_paths[0]) != original_pdf
            or file_sha256(input_paths[1]) != author_pdf):
        raise EvidenceReuseBlocked(
            "Frozen accepted original source/author lineage changed; "
            "new revisions require separate versioned target-specific revalidation")
    artifact_sha = file_sha256(input_paths[2])
    if artifact_sha != row["author_png_sha256"]:
        raise EvidenceReuseBlocked(
            "Original author image differs from historically verified source artwork")
    history = [AcceptedClaim(
        component_id=f"Thomas {section}/{figure_id}",
        scope="publisher_artwork_identity",
        standard="frozen_original_pdf_author_v1",
        source_sha256=original_pdf,
        author_sha256=author_pdf,
        artifact_sha256=artifact_sha,
        receipt_path=ledger,
        receipt_sha256=file_sha256(ledger),
        evidence_claim_path=(
            "six_independently_version_bound_figure_identity_receipts",
            figure_id, "source_artwork_correspondence_proven",
        ),
        previous_pr="#454",
    )]
    return preflight(ProposedCheck(
        component_id=f"Thomas {section}/{figure_id}",
        scope=requested_scope,
        standard=requested_standard,
        source_sha256=original_pdf,
        author_sha256=author_pdf,
        artifact_sha256=artifact_sha,
    ), history)


def main(argv=None) -> int:
    import argparse
    from dataclasses import asdict
    parser = argparse.ArgumentParser(
        description="Source-artwork evidence reuse decision; never edits lecture sources")
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--frozen-original-root", required=True, type=Path)
    parser.add_argument("--figure", required=True,
                        choices=("8.2", "8.3", "8.4", "8.5", "8.6", "Exercise 62"))
    parser.add_argument("--scope", default="publisher_artwork_identity")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if (not args.out.parent.is_dir() or args.out.exists()
            or args.out.is_relative_to(args.frozen_original_root.absolute())):
        raise EvidenceReuseBlocked(
            "Evidence preflight report must be new and outside protected source files")
    decision = source_artwork_preflight(
        ledger=args.ledger,
        frozen_original_root=args.frozen_original_root,
        figure_id=args.figure, requested_scope=args.scope)
    with args.out.open("x", encoding="utf8") as f:
        json.dump(asdict(decision), f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(asdict(decision), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
