"""Narrow physics-point-label pronunciation risk regression.

A clearly *labeled* point A is not an ambiguous capitalized article.
Unexplained mid-sentence A remains a blocking ambiguity.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / (
    "selenium_pipeline/vendor_template_v2/script_tts_risk.py")
SPEC = spec_from_file_location("microgen_tts_risk_under_test", MODULE)
RISK = module_from_spec(SPEC)
SPEC.loader.exec_module(RISK)


def kinds(text):
    return [(r["kind"], r["severity"], r["text"])
            for r in RISK.collect_tts_risks(text, slide=6)]


def test_explicit_physics_label_a_is_nonblocking_contextual_letter():
    for phrase in (
        "A particle travels from a position labeled A at time t.",
        "The point labelled A moves through an arc.",
        "We find the coordinate marked A at the axis.",
    ):
        results = kinds(phrase)
        assert ("ambiguous_capital_a", "blocking", "A") not in results
        assert ("contextual_letter", "warning", "A") in results


def test_unexplained_mid_sentence_capital_a_still_blocks():
    results = kinds("The object moves until A changing direction becomes likely.")
    assert ("ambiguous_capital_a", "blocking", "A") in results


def test_actual_hp_rejected_10_1_narration_has_no_blocking_a_after_repair():
    actual = Path(r"G:\My Drive\Serway\Serway_8_14\10\10.1\.microgen_work\script.rejected_api_attempt_1.txt")
    if not actual.is_file():
        return  # optional physical acceptance; no Drive dependency in CI
    content = actual.read_text(encoding="utf-8")
    blocks = RISK.parse_blocks(content)
    assert len(blocks) == 14
    rejected = [(slide, risk) for slide, body in blocks
                for risk in RISK.collect_tts_risks(body, slide=slide)
                if risk["severity"] == "blocking"]
    assert rejected == []


def test_source_labeled_part_corner_and_triangle_a_are_nonblocking():
    for phrase in (
        "The result in Part A is unchanged.",
        "The moment arm is measured about corner A of the curb.",
        "The source geometry uses triangle O A C to find d.",
    ):
        results = kinds(phrase)
        assert ("ambiguous_capital_a", "blocking", "A") not in results
        assert ("contextual_letter", "warning", "A") in results
