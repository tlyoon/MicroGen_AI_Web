"""Independent G3 figure crop/caption metadata integrity, not semantic QA."""
from selenium_pipeline.g3_captioned_png_asset_coverage_v1 import compare_g3_captioned_png_asset_coverage

def test_exact_source_figure_list_technical_only():
    x=compare_g3_captioned_png_asset_coverage([["Figure 8.2","Figure 8.3"],["Figure 8.4"]],[["Figure 8.2","Figure 8.3"],["Figure 8.4"]])
    assert x["technical_asset_coverage_match"] is True
    assert x["mismatched_slides"] == []
    assert x["independent_scientific_acceptance"] is False
    assert x["independent_visual_semantic_acceptance"] is False
    assert x["student_publication_authorized"] is False

def test_missing_crop_flagged():
    x=compare_g3_captioned_png_asset_coverage([["Figure 8.2","Figure 8.3"]],[["Figure 8.2"]])
    assert x["technical_asset_coverage_match"] is False
    assert x["mismatched_slides"] == [1]

def test_extra_crop_flagged():
    x=compare_g3_captioned_png_asset_coverage([["Figure 8.2"]],[["Figure 8.2","Figure 8.3"]])
    assert x["mismatched_slides"] == [1]

def test_wrong_caption_on_second_slide_flagged():
    x=compare_g3_captioned_png_asset_coverage([["Figure 8.2"],["Figure 8.4"]],[["Figure 8.2"],["Figure 8.3"]])
    assert x["mismatched_slides"] == [2]

def test_malformed_ids_cannot_pass():
    for value in ("",None,True,9):
        x=compare_g3_captioned_png_asset_coverage([["Figure 8.2",value]],[["Figure 8.2",value]])
        assert x["technical_asset_coverage_match"] is False
        assert 1 in x["mismatched_slides"]

def test_duplicate_caption_ids_fail_closed():
    x=compare_g3_captioned_png_asset_coverage([["Figure 8.2","Figure 8.2"]],[["Figure 8.2","Figure 8.2"]])
    assert x["technical_asset_coverage_match"] is False

def test_missing_and_extra_slides_flagged():
    assert compare_g3_captioned_png_asset_coverage([["Figure 8.2"],["Figure 8.3"]],[["Figure 8.2"]])["mismatched_slides"] == [2]
    assert compare_g3_captioned_png_asset_coverage([["Figure 8.2"]],[["Figure 8.2"],["Figure 8.3"]])["mismatched_slides"] == [2]

def test_no_campaign_input_cannot_be_complete():
    x=compare_g3_captioned_png_asset_coverage([],[])
    assert x["technical_asset_coverage_match"] is False
    assert x["student_publication_authorized"] is False
