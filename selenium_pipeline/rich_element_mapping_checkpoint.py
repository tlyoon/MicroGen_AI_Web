"""Idempotent, no-cost preflight and recovery worklist for rich lecture mapping.

This is an application *failure-recovery* mechanism, not another graph
scientific audit and not a route to paid synthesis. Previously generated
source-/author-SHA-bound evidence is reused exactly on the next invocation.
Unresolved narrative-to-figure/Math focus remains blocked until independently
source-proven; it is never approved merely by a text-similarity score.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


class ElementMappingCheckpointBlocked(ValueError):
    """An existing mapping needs completion; no TTS or video may run."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ElementMappingCheckpointBlocked(message)


def _sha(path: Path) -> str:
    _require(path.is_file() and not path.is_symlink(),
             "Original source/author/narration evidence missing or unsafe")
    d = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            d.update(chunk)
    return d.hexdigest()


FILES = ("full_deck_gap_diagnostic.json", "element_mapping_candidates.json",
         "element_mapping_worklist.md")


def _source_hashes(source: Path, slides: Path, script: Path) -> dict:
    return {"source.pdf": _sha(source), "slides.pdf": _sha(slides),
            "script.txt": _sha(script)}


def _receipt(cache: Path, input_hashes: dict) -> dict:
    manifest = cache / "mapping_checkpoint.json"
    _require(manifest.is_file() and not manifest.is_symlink(),
             "Cached rich-element mapping checkpoint is incomplete; "
             "preserve it for targeted recovery")
    try:
        value = json.loads(manifest.read_text(encoding="utf8"))
    except (OSError, ValueError) as exc:
        raise ElementMappingCheckpointBlocked(
            "Cached rich-element mapping receipt cannot be decoded") from exc
    _require(value.get("schema_version") == 1
             and value.get("status") ==
                  "SOURCEBOUND_RICH_ELEMENT_MAPPING_REVIEW_REQUIRED"
             and value.get("source_inputs_sha256") == input_hashes
             and value.get("student_publication_authorized") is False
             and value.get("paid_tts_authorized") is False,
             "Cached rich-element plan has wrong source/hash or approval status")
    _require(value.get("artifact_sha256") ==
             {name: _sha(cache / name) for name in FILES},
             "Accepted rich-element mapping worklist was modified; "
             "stop rather than redoing original source analysis")
    return value


def require_automatic_mapping_or_checkpoint(*, source: Path, slides: Path,
                                             script: Path,
                                             checkpoint_root: Path) -> dict:
    """Return only if the existing EXACT automatic-element mapper will pass.

    On any incomplete figure-/math-rich slide, write an immutable, complete
    lecture worklist with pinned source/slides/script SHA and stop BEFORE TTS.
    The next retry loads the same worklist and never recomputes prior analysis.
    """
    source, slides, script = (Path(p).absolute()
                             for p in (source, slides, script))
    _require(source.name == "source.pdf"
             and slides == source.parent / "slides.pdf"
             and script == source.parent / "script.txt",
             "Expected original canonical source-adjacent PDF/slide/narration")
    root = Path(checkpoint_root).absolute()
    _require(root.is_dir() and not root.is_symlink()
             and not root.is_relative_to(source.parent)
             and not source.parent.is_relative_to(root),
             "Mapping checkpoints must be outside source and author assets")
    before = _source_hashes(source, slides, script)
    fingerprint = hashlib.sha256(json.dumps(
        before, sort_keys=True).encode("utf8")).hexdigest()[:24]
    cache = root / ("rich_element_map_" + fingerprint)
    if cache.exists() or cache.is_symlink():
        _require(cache.is_dir() and not cache.is_symlink(),
                 "Unsafe existing mapping checkpoint")
        _receipt(cache, before)
        raise ElementMappingCheckpointBlocked(
            "Source-bound rich-element mapping remains unresolved; "
            "reused immutable complete-deck worklist: " + str(cache))
    from .automatic_element_narration import (
        AutomaticElementAudioError, inspect_text_only)
    try:
        exact = inspect_text_only(source=source, slides=slides, script=script)
    except AutomaticElementAudioError as exc:
        # The existing exact-text planner is only appropriate for simple
        # lectures; do not pay for TTS while graph/figure mapping is missing.
        from .visual_element_mapping_readiness import inspect_all
        from .element_plan_autodraft import propose
        from .element_plan_review_worklist import worklist
        diagnostic = inspect_all(source=source, slides=slides, script=script)
        proposal = propose(source_pdf=source, slides_pdf=slides,
                           script_txt=script)
        _require(diagnostic.get("status") ==
                 "READ_ONLY_FULL_DECK_FIGURE_SOURCE_NARRATION_GAP_DIAGNOSTIC"
                 and proposal.get("status") == "REVIEW_REQUIRED_NOT_TTS_READY"
                 and diagnostic["slide_count"] == proposal["slide_count"]
                 and proposal.get("can_stage_or_synthesize_audio") is False
                 and proposal.get("academic_approval") is False
                 and proposal.get("student_publication") is False,
                 "Unreviewed source/author mapping cannot be an approved TTS plan")
        for label, report in (("diagnostic", diagnostic), ("proposal", proposal)):
            _require([report.get(key) for key in
                      ("source_sha256", "slides_sha256", "script_sha256")]
                     == list(before.values()),
                     f"{label} changed original publisher/author/narration inputs")
        _require(_source_hashes(source, slides, script) == before,
                 "Source or author material changed during no-cost mapping review")
        # A temporary directory under the checkpoint root is the sole
        # permitted write location; never modify the original lecture.
        temp = Path(tempfile.mkdtemp(prefix="rich_element_map_incomplete_",
                                     dir=root))
        try:
            rows = {
                FILES[0]: json.dumps(diagnostic, indent=2, ensure_ascii=False) + "\n",
                FILES[1]: json.dumps(proposal, indent=2, ensure_ascii=False) + "\n",
                FILES[2]: worklist(proposal),
            }
            for name, payload in rows.items():
                (temp / name).write_text(payload, encoding="utf8")
            summary = {
                "schema_version": 1,
                "status": "SOURCEBOUND_RICH_ELEMENT_MAPPING_REVIEW_REQUIRED",
                "source_inputs_sha256": before,
                "artifact_sha256": {name: _sha(temp / name) for name in FILES},
                "automatic_exact_text_mapper_blocker": str(exc),
                "slide_count": diagnostic["slide_count"],
                "slides_with_graphics": diagnostic["slides_with_graphics"],
                "slides_without_exact_source_paragraph_match":
                    diagnostic["slides_without_single_source_verbatim_match"],
                "unreviewed_candidate_targets":
                    proposal["candidate_target_count"],
                "utterance_mapping_ambiguities":
                    proposal["ambiguous_utterance_count"],
                "paid_tts_authorized": False,
                "student_publication_authorized": False,
                "next_action":
                    "Provide independently source-proven rich figure/equation "
                    "element mapping; reruns must reuse this worklist, not "
                    "repeat source QA or synthesize speculative per-element WAVs",
            }
            (temp / "mapping_checkpoint.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf8")
            _require(_source_hashes(source, slides, script) == before,
                     "Original lecture modified during mapping checkpoint")
            try:
                os.rename(temp, cache)
            except FileExistsError:
                _receipt(cache, before)
            else:
                _receipt(cache, before)
        finally:
            if temp.exists():
                shutil.rmtree(temp)
        raise ElementMappingCheckpointBlocked(
            "Full-deck mapping checkpoint created before paid TTS; "
            "figure/mathematical narration requires real source anchors: " +
            str(cache)) from exc
    _require(exact.get("status") ==
             "EXACT_TEXT_ONLY_ELEMENT_MATCH_TECHNICAL"
             and exact.get("human_review_required") is False
             and exact.get("figure_semantic_mapping_assumed") is False
             and [exact.get(key) for key in
                  ("source_sha256", "slides_sha256", "script_sha256")]
                 == list(before.values()),
             "Exact-text automatic map provenance is incomplete")
    _require(_source_hashes(source, slides, script) == before,
             "Source/author/narration hashes changed before element-TTS")
    return {"status": "EXACT_TEXT_SOURCE_MAPPING_CAN_PROCEED",
            "source_inputs_sha256": before,
            "paid_tts_authorized_by_this_preflight": False}
