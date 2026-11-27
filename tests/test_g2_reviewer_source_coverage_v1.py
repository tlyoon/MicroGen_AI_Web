from selenium_pipeline.g2_reviewer_source_coverage_v1 import compare_g2_reviewer_source_coverage

FLAGS = ('independent_reviewer_agreement_established', 'independent_scientific_acceptance', 'student_publication_authorized')
MATCH = "technical_reviewer_source_coverage_match"
REQUIRED = {MATCH, "missing_ids", "unexpected_ids", "invalid_input"} | set(FLAGS)

def _shape(result):
    assert type(result) is dict and set(result) == REQUIRED
    assert type(result[MATCH]) is bool
    assert type(result["invalid_input"]) is bool
    assert type(result["missing_ids"]) is list
    assert type(result["unexpected_ids"]) is list
    assert all(result[name] is False for name in FLAGS)

def test_complete_source_evidence_out_of_order():
    observed = compare_g2_reviewer_source_coverage(["Fig_8-4", "8.2", "8.3A"],
                            ["8.3A", "Fig_8-4", "8.2"])
    _shape(observed)
    assert observed[MATCH] is True and observed["invalid_input"] is False
    assert observed["missing_ids"] == []
    assert observed["unexpected_ids"] == []

def test_gaps_are_sorted_without_acceptance():
    observed = compare_g2_reviewer_source_coverage(["8.3A", "8.1", "Fig_8-4"],
                            ["Fig_8-4", "8.5", "8.7"])
    _shape(observed)
    assert observed[MATCH] is False and observed["invalid_input"] is False
    assert observed["missing_ids"] == ["8.1", "8.3A"]
    assert observed["unexpected_ids"] == ["8.5", "8.7"]

def test_extra_rendered_asset_without_source_is_detected():
    observed = compare_g2_reviewer_source_coverage(["8.1"], ["8.1", "8.2"])
    _shape(observed)
    assert observed[MATCH] is False
    assert observed["missing_ids"] == []
    assert observed["unexpected_ids"] == ["8.2"]

def test_empty_and_duplicate_evidence_is_invalid_not_success():
    cases = (([], []), (["8.1", "8.1"], ["8.1"]),
             (["8.1"], ["8.1", "8.1"]))
    for first, second in cases:
        observed = compare_g2_reviewer_source_coverage(first, second)
        _shape(observed)
        assert observed["invalid_input"] is True
        assert observed[MATCH] is False
        assert observed["missing_ids"] == []
        assert observed["unexpected_ids"] == []

def test_malformed_source_identifiers_never_count_as_acceptance():
    for bad in ("", " ", " 8.2", "8.2 ", "../8.2",
                "8/2", "8.2.png", "A\\B", "8..2", 23, False, None):
        observed = compare_g2_reviewer_source_coverage([bad], ["8.1"])
        _shape(observed)
        assert observed["invalid_input"] is True
        assert observed[MATCH] is False

def test_wrong_container_types_never_count_as_acceptance():
    for first, second in ((None, []), ("8.1", []), ({}, ["8.1"]),
                          ([], None), ([], ("8.1",))):
        observed = compare_g2_reviewer_source_coverage(first, second)
        _shape(observed)
        assert observed["invalid_input"] is True and observed[MATCH] is False
