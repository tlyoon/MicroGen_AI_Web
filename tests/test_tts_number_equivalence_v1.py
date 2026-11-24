"""Actual-source Chapter 12 audio QA only allows precise numerical equivalents."""
import json
from pathlib import Path
from selenium_pipeline.tts_fidelity import (_rescore_result, _reviewed_numerical_equivalences)


def test_identical_values_not_critical():
    source = Path(r"G:\My Drive\Serway\Serway_8_14\12\12.3\.tts_qa_cache")
    if source.is_dir():
        for n in (17,22):
            original = json.loads((source / f"slide{n}.json").read_text(encoding="utf8"))["result"]
            adjudicated = _rescore_result(original, 99.0)
            assert adjudicated["status"] == "pass"
            assert adjudicated["fidelity_percent"] == 100.0
            assert not adjudicated["critical_token_issues"]
            assert len(adjudicated["reviewer_numeric_equivalences"]) == 1
        bad_original = source.parent / ".history" / (
            "ch12_20261124_verified_source_figures_audio"
        ) / "slide9_previous_bad_audio_qa.json"
        if bad_original.is_file():
            bad = json.loads(bad_original.read_text(encoding="utf8"))["result"]
            assert _rescore_result(bad, 99.0)["status"] == "review"


def test_nonidentical_number_stays_blocking():
    actual = ["The number is twelve hundred",
              "The number is one thousand three hundred"]
    issues=[{"script_text":"twelve hundred","heard_as":"one thousand three hundred",
             "category":"number","severity":"major"}]
    a,b,remaining,reviewed = _reviewed_numerical_equivalences(*actual,issues)
    assert remaining == issues
    assert reviewed == []
    assert a != b


def test_unverified_or_different_category_never_ignored():
    issues=[{"script_text":"zero point eight zero","heard_as":"zero point eight",
             "category":"sign","severity":"major"}]
    _,_,remaining,reviewed = _reviewed_numerical_equivalences(
        "zero point eight zero","zero point eight",issues)
    assert remaining == issues and reviewed == []
