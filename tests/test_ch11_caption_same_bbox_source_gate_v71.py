"""Original real-source regression: same caption bbox is not citation proof."""
from selenium_pipeline.source_caption_figure_chain_v1 import (
    _caption_block_parser_parity,
)
from selenium_pipeline.recovery_registry import lookup_mechanism


def row():
    return {
        "id":"11.2", "page":1,
        "caption_bbox":[35.051,537.247,158.107,579.113],
        "caption_text":"Figure 11.2 The vector product of two vectors.",
        "expected_panels":[],
    }


def test_exact_same_bbox_and_source_text_remains_valid():
    original=row()
    candidate=row()
    assert _caption_block_parser_parity("f"*64,candidate,original,None)
    candidate["caption_text"]="Figure 11.2   The vector product of two vectors."
    assert _caption_block_parser_parity("f"*64,candidate,original,None)


def test_same_bbox_does_not_accept_unrelated_source_caption_words():
    original=row()
    candidate=dict(original,caption_text="unrelated source figure claim")
    assert not _caption_block_parser_parity("f"*64,candidate,original,None)


def test_same_bbox_cannot_hide_mismatched_figure_or_page_identity():
    original=row()
    for field,value in (("id","11.7"),("page",2),
                        ("expected_panels",["a"])):
        candidate=dict(original,**{field:value})
        assert not _caption_block_parser_parity("f"*64,candidate,original,None)


def test_caption_grounding_repair_is_registered():
    assert lookup_mechanism(
        "caption_identity_parity",
        "CH11_SAME_BBOX_DIFFERENT_CAPTION_TEXT_FALSE_ACCEPT",
    )=="REQUIRE_EXACT_SOURCE_WORDS_AND_FIGURE_ID_FOR_EQUAL_BBOX"
