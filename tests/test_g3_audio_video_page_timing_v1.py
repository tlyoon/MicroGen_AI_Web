"""Independent G3 source-aligned audio/video timing checks, NOT academic QA.

The source-only/technical timing check may flag page drift, but must never
claim independent physics, acoustic pronunciation or highlight acceptance.
"""
from selenium_pipeline.g3_audio_video_page_timing_v1 import (
    compare_g3_audio_video_page_durations,
)


def test_matching_page_duration_is_technical_only():
    result = compare_g3_audio_video_page_durations(
        [2000, 3000, 1500], [2005, 2988, 1511], 20)
    assert result["technical_timing_match"] is True
    assert result["mismatched_pages"] == []
    assert result["independent_scientific_acceptance"] is False
    assert result["independent_acoustic_acceptance"] is False
    assert result["independent_video_highlight_acceptance"] is False
    assert result["student_publication_authorized"] is False


def test_one_real_mismatch_not_masked_by_other_pages():
    result = compare_g3_audio_video_page_durations(
        [2000, 3000, 1500], [2010, 3200, 1499], 25)
    assert result["technical_timing_match"] is False
    assert result["mismatched_pages"] == [2]


def test_cross_page_reordering_detected_by_index():
    result = compare_g3_audio_video_page_durations(
        [1000, 3000, 500], [3000, 1000, 500], 100)
    assert result["technical_timing_match"] is False
    assert result["mismatched_pages"] == [1, 2]


def test_missing_slide_audio_cue_never_passes():
    result = compare_g3_audio_video_page_durations(
        [300, 800, 900], [300, 800], 50)
    assert result["technical_timing_match"] is False
    assert result["mismatched_pages"] == [3]


def test_extra_slide_video_page_never_passes():
    result = compare_g3_audio_video_page_durations(
        [300, 800], [300, 800, 900], 50)
    assert result["technical_timing_match"] is False
    assert result["mismatched_pages"] == [3]


def test_negative_and_bool_duration_is_not_accepted():
    for value in (-1, False, None, "100"):
        result = compare_g3_audio_video_page_durations(
            [100, value], [100, 100], 20)
        assert result["technical_timing_match"] is False
        assert 2 in result["mismatched_pages"]


def test_invalid_tolerance_cannot_authorize_timing():
    for tolerance in (-1, False, "5"):
        result = compare_g3_audio_video_page_durations(
            [100], [100], tolerance)
        assert result["technical_timing_match"] is False
        assert result["mismatched_pages"] == [1]


def test_exact_tolerance_boundary_inclusive():
    result = compare_g3_audio_video_page_durations(
        [1000, 2000], [1020, 1980], 20)
    assert result["technical_timing_match"] is True


def test_no_input_cannot_be_called_complete():
    result = compare_g3_audio_video_page_durations([], [], 20)
    assert result["technical_timing_match"] is False
    assert result["mismatched_pages"] == []
    assert result["student_publication_authorized"] is False
