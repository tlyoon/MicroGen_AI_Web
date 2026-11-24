"""Visible G3 questions require their own publisher and scientific QA."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from selenium_pipeline import g3_original_visual_question_source_audit_v1 as review
from selenium_pipeline.recovery_registry import lookup_mechanism
from selenium_pipeline.g3_semantic_source_repair_v1 import _write_once


def test_visual_source_review_recovery_registered():
    assert lookup_mechanism(review.KIND,review.SIGNATURE)==review.MECHANISM


def test_exact_two_numbered_original_rendered_questions_not_fake_narration():
    text=(
        "1 In Example 8.3, why does cable length R cancel in the maximum "
        "swing angle calculation? Explain the physical reason. "
        "2 Why does the object plus Earth form an isolated system for "
        "gravity, while a single object can be treated as nonisolated?")
    questions=review._questions(text)
    assert len(questions)==2
    assert questions[0].startswith("In Example 8.3")
    assert questions[1].startswith("Why does the object")
    assert review._questions("Summary and Review Questions")==[]
    assert review._questions("1 Newton says f=ma, therefore true")==[]


def test_separate_original_pdf_physical_evidence_is_not_math_approval(tmp_path):
    folder=tmp_path/"serway_source"
    folder.mkdir()
    with pymupdf.open() as pdf:
        a=pdf.new_page()
        a.insert_text((40,80),
            "The cable length R cancels from the final maximum swing angle equation.",
            fontsize=10)
        b=pdf.new_page()
        b.insert_text((40,80),
            "The object plus Earth is an isolated system because gravity is internal.",
            fontsize=10)
        pdf.save(folder/"source.pdf")
    sha=hashlib.sha256((folder/"source.pdf").read_bytes()).hexdigest()
    one=review._proof(
        folder=folder,source_sha=sha,
        question="Why does cable length R cancel from the final maximum swing angle equation?")
    two=review._proof(
        folder=folder,source_sha=sha,
        question="Why is the object plus Earth an isolated system where gravity is internal?")
    assert one and two
    assert one[0]["original_publisher_page"]==1
    assert two[0]["original_publisher_page"]==2
    assert all(x["is_a_physical_source_witness"] is True
               and x["is_a_verified_scientific_answer"] is False
               for x in one+two)


def test_scientific_source_pdf_tamper_rejected(tmp_path):
    folder=tmp_path/"serway_source"
    folder.mkdir()
    with pymupdf.open() as pdf:
        page=pdf.new_page()
        page.insert_text((40,80),"The actor swings on a cable of length R.")
        pdf.save(folder/"source.pdf")
    wrong_sha="f"*64
    with pytest.raises(Exception):
        review._proof(
            folder=folder,source_sha=wrong_sha,
            question="Why does the cable length R change the maximum swing angle?")


def test_immutable_rendered_visual_audit_cannot_be_promoted(tmp_path):
    task=tmp_path/"original_source_review.json"
    row={
        "status":review.STATUS,
        "source_scientific_QA_complete":False,
        "rendered_visual_QA_complete":False,
        "student_publication_authorized":False,
        "new_provider_sends":0}
    _write_once(task,row)
    assert json.loads(task.read_text("utf8"))==row
    task.write_text('{"student_publication_authorized":true}')
    with pytest.raises(ValueError,match="modified"):
        _write_once(task,row)
