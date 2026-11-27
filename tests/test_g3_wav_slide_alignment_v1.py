from selenium_pipeline.g3_wav_slide_alignment_v1 import compare_g3_wav_slide_alignment

FLAGS = ('independent_acoustic_acceptance', 'independent_scientific_acceptance', 'student_publication_authorized')
MATCH = "technical_wav_slide_match"
REQUIRED = {MATCH, "mismatched_positions", "invalid_input"} | set(FLAGS)

def _shape(result):
    assert type(result) is dict and set(result) == REQUIRED
    assert type(result[MATCH]) is bool
    assert type(result["invalid_input"]) is bool
    assert type(result["mismatched_positions"]) is list
    assert all(result[name] is False for name in FLAGS)

def test_exact_order_is_technical_match_only():
    observed = compare_g3_wav_slide_alignment([1, 2, 3], [1, 2, 3])
    _shape(observed)
    assert observed[MATCH] is True and observed["invalid_input"] is False
    assert observed["mismatched_positions"] == []

def test_reordered_valid_ids_never_accepted():
    observed = compare_g3_wav_slide_alignment([1, 2, 3], [1, 3, 2])
    _shape(observed)
    assert observed[MATCH] is False and observed["invalid_input"] is False
    assert observed["mismatched_positions"] == [2, 3]

def test_missing_or_extra_tail_produces_one_based_positions():
    for first, second, positions in (
        ([1, 2, 3], [1, 2], [3]),
        ([1, 2], [1, 2, 3], [3]),
        ([1, 2, 3], [1, 3], [2, 3]),
    ):
        observed = compare_g3_wav_slide_alignment(first, second)
        _shape(observed)
        assert observed[MATCH] is False and observed["invalid_input"] is False
        assert observed["mismatched_positions"] == positions

def test_duplicate_or_empty_sequences_are_invalid():
    for first, second in (([], []), ([1, 1], [1]),
                          ([1], [1, 1]), ([], [1])):
        observed = compare_g3_wav_slide_alignment(first, second)
        _shape(observed)
        assert observed[MATCH] is False and observed["invalid_input"] is True
        assert observed["mismatched_positions"] == []

def test_invalid_numeric_types_do_not_count_as_page_ids():
    for bad in (False, True, 0, -1, 1.0, "1", None):
        observed = compare_g3_wav_slide_alignment([bad], [1])
        _shape(observed)
        assert observed[MATCH] is False and observed["invalid_input"] is True
        assert observed["mismatched_positions"] == []

def test_wrong_container_types_are_invalid():
    for first, second in ((None, []), ("1", []),
                          ([], {1: 2}), ((1,), [1])):
        observed = compare_g3_wav_slide_alignment(first, second)
        _shape(observed)
        assert observed[MATCH] is False and observed["invalid_input"] is True
