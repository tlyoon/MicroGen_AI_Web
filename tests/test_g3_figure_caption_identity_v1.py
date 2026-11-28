"""G3 source/slide figure-caption identifier integrity, NOT semantic QA."""
from selenium_pipeline.g3_figure_caption_identity_v1 import compare_g3_figure_caption_identity


def test_ordered_source_captions_survive_rendering():
    result = compare_g3_figure_caption_identity(
        [["Figure 8.2", "Figure 8.3"], ["Figure 8.4"]],
        [["Figure 8.2", "Figure 8.3"], ["Figure 8.4"]])
    assert result["technical_caption_identity_match"] is True
    assert result["mismatched_slides"] == []
    assert result["independent_scientific_acceptance"] is False
    assert result["independent_visual_semantic_acceptance"] is False
    assert result["student_publication_authorized"] is False


def test_captionless_slide_with_source_figure_is_rejected():
    result = compare_g3_figure_caption_identity(
        [["Figure 8.2"]], [[]])
    assert result["technical_caption_identity_match"] is False
    assert result["mismatched_slides"] == [1]


def test_order_change_is_not_accepted():
    result = compare_g3_figure_caption_identity(
        [["Figure 8.2", "Figure 8.3"]],
        [["Figure 8.3", "Figure 8.2"]])
    assert result["technical_caption_identity_match"] is False
    assert result["mismatched_slides"] == [1]


def test_missing_and_extra_slides_report_one_based_indices():
    result = compare_g3_figure_caption_identity(
        [["Figure 8.2"], ["Figure 8.3"], ["Figure 8.4"]],
        [["Figure 8.2"]])
    assert result["mismatched_slides"] == [2, 3]
    assert result["technical_caption_identity_match"] is False


def test_duplicate_source_identifiers_require_review():
    result = compare_g3_figure_caption_identity(
        [["Figure 8.2", "Figure 8.2"]],
        [["Figure 8.2", "Figure 8.2"]])
    assert result["technical_caption_identity_match"] is False
    assert result["mismatched_slides"] == [1]


def test_blank_and_nonstring_caption_id_fails_closed():
    for value in ("", None, 123, True):
        result = compare_g3_figure_caption_identity(
            [["Figure 8.2", value]],
            [["Figure 8.2", value]])
        assert result["technical_caption_identity_match"] is False
        assert result["mismatched_slides"] == [1]


def test_case_or_spacing_drift_is_not_silently_normalized():
    result = compare_g3_figure_caption_identity(
        [["Figure 8.2"]], [["figure 8.2 "]])
    assert result["technical_caption_identity_match"] is False
    assert result["mismatched_slides"] == [1]


def test_no_source_figure_evidence_is_not_counted_as_match():
    result = compare_g3_figure_caption_identity([], [])
    assert result["technical_caption_identity_match"] is False
    assert result["mismatched_slides"] == []
    assert result["student_publication_authorized"] is False
