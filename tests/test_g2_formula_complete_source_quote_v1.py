"""Reproduce the source-citation truncation that derailed a real G2 review.

A complete original formula is a retrieval preference, NOT academic approval.
No Selenium, model Send, paid API, response replay or publication.
"""
import hashlib
import json
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.pdf_text_source_span_witness import prove_source_quote_occurrence
from selenium_pipeline.recovery_registry import lookup_mechanism
from selenium_pipeline.source_verified_quote_candidates import (
    FORMULA_KIND, FORMULA_SIGNATURE, FORMULA_MECHANISM,
    _formula_source_relevance, _formula_tokens_from_visible_slide,
    build_verified_source_candidates,
)


def synthetic_source(tmp_path):
    folder = tmp_path / "source" / "1" / "1.3"
    folder.mkdir(parents=True)
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 75),
            "The physical dimensions of speed are based on length and time.\n"
            "For example, the symbol we use for speed is v, and in our notation\n"
            "the dimensions of speed are written [v] 5 L/T. This is one ratio.",
            fontsize=10)
        doc.save(folder / "source.pdf")
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 75), "Speed: [v] = L/T", fontsize=10)
        doc.save(folder / "slides.pdf")
    (folder / "script.txt").write_text(
        "We use v for speed and divide length by time.", encoding="utf8")
    words = "For example, the speed has dimensions of length divided by time."
    unit = {
        "id": "s003.utterance.005",
        "spoken_text": words,
        "spoken_sha256": hashlib.sha256(words.encode()).hexdigest(),
        "ranked_candidates": ["s003.text.005"],
    }
    job = {
        "source_sha256": _sha(folder / "source.pdf"),
        "slides_sha256": _sha(folder / "slides.pdf"),
        "script_sha256": _sha(folder / "script.txt"),
        "slides": [{
            "slide": 3,
            "visual_targets": [{
                "id": "s003.text.005",
                "visible_text": "Example for speed v: [v] = L/T",
                "kind": "text_block",
            }],
            "utterances": [unit],
        }],
        "student_publication_authorized": False,
        "academic_approval": False,
    }
    return folder, job


def test_recovery_is_registered_as_executable():
    assert lookup_mechanism(FORMULA_KIND, FORMULA_SIGNATURE) == FORMULA_MECHANISM


def test_slide_formula_tokens_are_literal_not_inferred():
    assert _formula_tokens_from_visible_slide(
        "Example for speed v: [v] = L/T") == frozenset({"[v]", "L/T"})
    assert _formula_source_relevance(
        "Example for speed v: [v] = L/T",
        "For example, the symbol we use for speed in this") == 0.0
    assert _formula_source_relevance(
        "Example for speed v: [v] = L/T",
        "the dimensions of speed are written [v] 5 L/T.") == 15.0
    assert _formula_source_relevance(
        "Example for speed v: [v] = L/T",
        "the dimensions are written [v] 5 L/M") < 15.0


def test_no_invented_formula_when_slide_has_none():
    assert _formula_tokens_from_visible_slide(
        "Length mass and time are fundamental dimensions.") == frozenset()
    assert _formula_source_relevance(
        "Length mass and time are fundamental dimensions.",
        "There is a ratio L/T") == 0.0
    assert _formula_source_relevance(None, "[v] = L/T") == 0.0
    assert _formula_source_relevance("x" * 8100, "[v] = L/T") == 0.0


def test_physically_witnessed_complete_formula_ranked_first(tmp_path):
    folder, job = synthetic_source(tmp_path)
    files = {
        n: (folder / n).read_bytes()
        for n in ("source.pdf", "slides.pdf", "script.txt")
    }
    packet = build_verified_source_candidates(folder=folder, job=job)
    assert packet["student_publication_authorized"] is False
    assert packet["citations_are_scientific_proof"] is False
    assert packet["all_mathematics_verified"] is False
    assert packet["status"] == "PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1"
    rows = packet["utterances"]
    assert len(rows) == 1
    assert rows[0]["utterance_id"] == "s003.utterance.005"
    assert rows[0]["allowed_citations"]
    first = rows[0]["allowed_citations"][0]
    quote = first["verbatim_source_quote"]
    assert "[v]" in quote
    assert "L/T" in quote
    assert first["source_page"] == 1
    original = prove_source_quote_occurrence(
        source_pdf=folder / "source.pdf",
        expected_sha256=_sha(folder / "source.pdf"),
        page_number=first["source_page"],
        verbatim_quote=quote,
    )
    assert original["quote_sha256"] == first["quote_sha256"]
    assert {n: (folder/n).read_bytes() for n in files} == files


def test_retrieval_cannot_forge_math_formula_absent_from_pdf(tmp_path):
    folder, job = synthetic_source(tmp_path)
    # Change the original source PDF only, and *independently* rehash it in
    # a new synthetic fixture. The output must not pretend [v] exists.
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50,75),
            "For example the dimensions of speed are explained with prose.\n"
            "No original symbolic equation is printed on this source page.",
            fontsize=10)
        doc.save(folder / "replacement.pdf")
    (folder / "source.pdf").write_bytes((folder/"replacement.pdf").read_bytes())
    job["source_sha256"] = _sha(folder / "source.pdf")
    packet = build_verified_source_candidates(folder=folder, job=job)
    for row in packet["utterances"]:
        for evidence in row["allowed_citations"]:
            assert "L/T" not in evidence["verbatim_source_quote"]
            assert "[v]" not in evidence["verbatim_source_quote"]
    assert packet["all_mathematics_verified"] is False
    assert packet["student_publication_authorized"] is False
