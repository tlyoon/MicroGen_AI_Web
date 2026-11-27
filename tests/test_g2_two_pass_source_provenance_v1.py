from selenium_pipeline.g2_two_pass_source_provenance_v1 import compare_g2_two_pass_source_provenance

FLAGS = ('independent_reviewer_agreement_established', 'independent_scientific_acceptance', 'student_publication_authorized')
MATCH = "technical_two_pass_provenance_match"
HASH = "a" * 64
OTHER = "b" * 64
KEYS = {"reviewer_id", "request_id", "source_sha256", "evidence_sha256"}
REQUIRED = {MATCH, "conflicting_fields", "invalid_input"} | set(FLAGS)

def _pass(reviewer, request, source=HASH, evidence=HASH):
    return {"reviewer_id": reviewer, "request_id": request,
            "source_sha256": source, "evidence_sha256": evidence}

def _shape(row):
    assert type(row) is dict and set(row) == REQUIRED
    assert type(row[MATCH]) is bool and type(row["invalid_input"]) is bool
    assert type(row["conflicting_fields"]) is list
    assert row["conflicting_fields"] == sorted(set(row["conflicting_fields"]))
    assert all(row[k] is False for k in FLAGS)

def test_two_distinct_owned_responses_have_technical_provenance_not_approval():
    row = compare_g2_two_pass_source_provenance(HASH, _pass("neon", "send-one"),
                       _pass("hydrogen", "send-two", evidence=OTHER))
    _shape(row)
    assert row[MATCH] is True and row["invalid_input"] is False
    assert row["conflicting_fields"] == []

def test_original_source_hash_mismatches_are_reported_not_approved():
    for first, second, expected in (
        (_pass("neon", "send-one", source=OTHER),
         _pass("hydrogen", "send-two"), ["first_source_sha256"]),
        (_pass("neon", "send-one"),
         _pass("hydrogen", "send-two", source=OTHER), ["second_source_sha256"]),
        (_pass("neon", "send-one", source=OTHER),
         _pass("hydrogen", "send-two", source=OTHER),
         ["first_source_sha256", "second_source_sha256"]),
    ):
        row = compare_g2_two_pass_source_provenance(HASH, first, second)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is False
        assert row["conflicting_fields"] == expected

def test_same_reviewer_or_same_send_cannot_claim_independent_review():
    for first, second in (
        (_pass("neon", "send-one"), _pass("neon", "send-two")),
        (_pass("neon", "send-one"), _pass("hydrogen", "send-one")),
        (_pass("neon", "send-one"), _pass("neon", "send-one")),
    ):
        row = compare_g2_two_pass_source_provenance(HASH, first, second)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is True
        assert row["conflicting_fields"] == []

def test_invalid_hash_or_malformed_model_evidence_fails_closed():
    valid = _pass("neon", "send-one")
    another = _pass("hydrogen", "send-two")
    bad = (
        ("ABC", valid, another),
        (HASH.upper(), valid, another),
        (HASH, dict(valid, evidence_sha256="x"), another),
        (HASH, dict(valid, source_sha256="x"), another),
        (HASH, dict(valid, reviewer_id="../escape"), another),
        (HASH, dict(valid, request_id=" "), another),
        (HASH, dict(valid, extra="surprise"), another),
        (HASH, {"request_id": "send-one"}, another),
        (HASH, None, another),
        (HASH, valid, "wrong"),
    )
    for source, first, second in bad:
        row = compare_g2_two_pass_source_provenance(source, first, second)
        _shape(row)
        assert row[MATCH] is False and row["invalid_input"] is True
        assert row["conflicting_fields"] == []
