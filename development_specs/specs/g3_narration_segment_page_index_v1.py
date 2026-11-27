"""Independent narration-to-slide index integrity, not academic acceptance."""
from selenium_pipeline.g3_narration_segment_page_index_v1 import compare_g3_narration_segment_page_index

def test_ordered_page_segments_pass_technical_only():
    x=compare_g3_narration_segment_page_index([1,2,3],[1,2,3])
    assert x["technical_page_index_match"] is True
    assert x["mismatched_positions"] == []
    assert x["independent_scientific_acceptance"] is False
    assert x["independent_acoustic_acceptance"] is False
    assert x["student_publication_authorized"] is False

def test_missing_page_reports_position():
    x=compare_g3_narration_segment_page_index([1,2,3],[1,3])
    assert x["technical_page_index_match"] is False
    assert x["mismatched_positions"] == [2,3]

def test_extra_generated_page_reports_position():
    assert compare_g3_narration_segment_page_index([1,2],[1,2,3])["mismatched_positions"] == [3]

def test_reordered_pages_flagged():
    assert compare_g3_narration_segment_page_index([1,2,3],[1,3,2])["mismatched_positions"] == [2,3]

def test_invalid_page_indexes_fail_closed():
    for item in (False,-1,0,None,"2"):
        x=compare_g3_narration_segment_page_index([1,item],[1,item])
        assert x["technical_page_index_match"] is False
        assert 2 in x["mismatched_positions"]

def test_duplicate_page_index_never_valid():
    assert compare_g3_narration_segment_page_index([1,1,2],[1,1,2])["technical_page_index_match"] is False

def test_no_data_cannot_claim_completion():
    x=compare_g3_narration_segment_page_index([],[])
    assert x["technical_page_index_match"] is False
    assert x["mismatched_positions"] == []
