"""Independent source.pdf figure-caption ID vs cropped PNG ID inventory contract.

Only technical metadata reconciliation; never scientific or visual acceptance.
This source-pinned test is deliberately independent of the code-author model.
"""
from selenium_pipeline.g3_pdf_caption_png_inventory_v1 import (
    compare_g3_pdf_caption_png_inventory,
)


def _assert_shape(data):
    assert type(data) is dict
    assert set(data)=={
        "technical_caption_coverage_match",
        "missing_png_caption_ids",
        "orphan_png_caption_ids",
        "invalid_input",
        "independent_scientific_acceptance",
        "student_publication_authorized",
    }
    assert type(data["technical_caption_coverage_match"]) is bool
    assert type(data["invalid_input"]) is bool
    assert type(data["missing_png_caption_ids"]) is list
    assert type(data["orphan_png_caption_ids"]) is list
    assert data["independent_scientific_acceptance"] is False
    assert data["student_publication_authorized"] is False


def test_complete_unordered_original_caption_inventory():
    result=compare_g3_pdf_caption_png_inventory(
        ["8.2", "8.3A", "Fig_8-4"], ["Fig_8-4", "8.3A", "8.2"])
    _assert_shape(result)
    assert result["technical_caption_coverage_match"] is True
    assert result["invalid_input"] is False
    assert result["missing_png_caption_ids"]==[]
    assert result["orphan_png_caption_ids"]==[]


def test_missing_and_orphan_identifiers_sorted_without_false_acceptance():
    result=compare_g3_pdf_caption_png_inventory(
        ["8.1", "8.3B", "8.2", "8.3A"],
        ["8.3B", "8.7", "8.5", "8.2"])
    _assert_shape(result)
    assert result["technical_caption_coverage_match"] is False
    assert result["invalid_input"] is False
    assert result["missing_png_caption_ids"]==["8.1", "8.3A"]
    assert result["orphan_png_caption_ids"]==["8.5", "8.7"]


def test_empty_original_and_png_inventory_is_technically_consistent():
    result=compare_g3_pdf_caption_png_inventory([], [])
    _assert_shape(result)
    assert result["technical_caption_coverage_match"] is True
    assert result["invalid_input"] is False


def test_empty_original_with_unexpected_png_is_not_success():
    result=compare_g3_pdf_caption_png_inventory([], ["8.1"])
    _assert_shape(result)
    assert result["technical_caption_coverage_match"] is False
    assert result["orphan_png_caption_ids"]==["8.1"]


def test_duplicates_are_invalid_not_silently_collapsed():
    for original, cropped in (
        (["8.2", "8.2"], ["8.2"]),
        (["8.2"], ["8.2", "8.2"]),
    ):
        result=compare_g3_pdf_caption_png_inventory(original,cropped)
        _assert_shape(result)
        assert result["invalid_input"] is True
        assert result["technical_caption_coverage_match"] is False
        assert result["missing_png_caption_ids"]==[]
        assert result["orphan_png_caption_ids"]==[]


def test_invalid_identifiers_do_not_produce_technical_acceptance():
    invalids=(""," "," 8.2","8.2 ","../8.2","8/2","8.2.png","A\\B","8..2",23,False,None)
    for bad in invalids:
        result=compare_g3_pdf_caption_png_inventory([bad],[])
        _assert_shape(result)
        assert result["invalid_input"] is True
        assert result["technical_caption_coverage_match"] is False
        assert result["missing_png_caption_ids"]==[]
        assert result["orphan_png_caption_ids"]==[]


def test_invalid_container_types_are_rejected():
    for a,b in ((None,[]),("8.2",[]),([],("8.2",)),({},[]),([],None)):
        result=compare_g3_pdf_caption_png_inventory(a,b)
        _assert_shape(result)
        assert result["invalid_input"] is True
        assert result["technical_caption_coverage_match"] is False
        assert result["missing_png_caption_ids"]==[]
        assert result["orphan_png_caption_ids"]==[]
