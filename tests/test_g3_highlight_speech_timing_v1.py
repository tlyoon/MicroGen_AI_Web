from selenium_pipeline.g3_highlight_speech_timing_v1 import compare_g3_highlight_speech_timing

FLAGS = ('independent_video_acceptance', 'independent_acoustic_acceptance', 'independent_scientific_acceptance', 'student_publication_authorized')
MATCH = "technical_highlight_segment_timing_match"
REQUIRED = {MATCH, "mismatched_segments", "invalid_input"} | set(FLAGS)

def seg(element, narration, start, end):
    return {"element_id": element, "narration_id": narration,
            "start_ms": start, "end_ms": end}

def _shape(row):
    assert type(row) is dict and set(row) == REQUIRED
    assert type(row[MATCH]) is bool and type(row["invalid_input"]) is bool
    assert type(row["mismatched_segments"]) is list
    assert row["mismatched_segments"] == sorted(set(row["mismatched_segments"]))
    assert all(type(i) is int and i > 0 for i in row["mismatched_segments"])
    assert all(row[k] is False for k in FLAGS)

def test_nonoverlapping_source_anchored_segments_are_technical_only():
    row = compare_g3_highlight_speech_timing(10000, [seg("Fig_8-4", "spoken_1", 0, 1500),
                               seg("Equation_8-3", "spoken_2", 1600, 4900)])
    _shape(row)
    assert row[MATCH] is True and row["invalid_input"] is False
    assert row["mismatched_segments"] == []

def test_overlapping_or_outside_slide_time_is_reported():
    for segments, expected in (
        ([seg("A", "spoken_1", 0, 6000),
          seg("B", "spoken_2", 5000, 8000)], [2]),
        ([seg("A", "spoken_1", 0, 5000),
          seg("B", "spoken_2", 5000, 11000)], [2]),
        ([seg("A", "spoken_1", 0, 15000)], [1]),
    ):
        row = compare_g3_highlight_speech_timing(10000, segments)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is False
        assert row["mismatched_segments"] == expected

def test_missing_provenance_or_invalid_timing_never_passes():
    valid = seg("A", "spoken_1", 0, 100)
    for duration, segments in (
        (0, [valid]), (True, [valid]), ("1000", [valid]),
        (1000, []), (1000, None), (1000, [None]),
        (1000, [dict(valid, element_id="")]),
        (1000, [dict(valid, element_id="../source")]),
        (1000, [dict(valid, narration_id="file.wav")]),
        (1000, [dict(valid, start_ms=-1)]),
        (1000, [dict(valid, start_ms=True)]),
        (1000, [dict(valid, end_ms=0)]),
        (1000, [dict(valid, end_ms=1.0)]),
        (1000, [dict(valid, extra=1)]),
        (1000, [valid, dict(valid, element_id="B")]),
    ):
        row = compare_g3_highlight_speech_timing(duration, segments)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is True
        assert row["mismatched_segments"] == []
