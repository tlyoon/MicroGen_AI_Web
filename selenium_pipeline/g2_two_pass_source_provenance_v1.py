import re


def compare_g2_two_pass_source_provenance(expected_source_sha256, first_review, second_review):
    sha_pattern = r"[0-9a-f]{64}"
    id_pattern = r"[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*"
    required_keys = {"reviewer_id", "request_id", "source_sha256", "evidence_sha256"}

    valid = (
        type(expected_source_sha256) is str
        and re.fullmatch(sha_pattern, expected_source_sha256) is not None
        and type(first_review) is dict
        and type(second_review) is dict
        and set(first_review.keys()) == required_keys
        and set(second_review.keys()) == required_keys
    )

    if valid:
        for record in (first_review, second_review):
            reviewer_id = record["reviewer_id"]
            request_id = record["request_id"]
            source_sha = record["source_sha256"]
            evidence_sha = record["evidence_sha256"]
            if (
                type(reviewer_id) is not str
                or type(request_id) is not str
                or type(source_sha) is not str
                or type(evidence_sha) is not str
                or re.fullmatch(id_pattern, reviewer_id) is None
                or re.fullmatch(id_pattern, request_id) is None
                or re.fullmatch(sha_pattern, source_sha) is None
                or re.fullmatch(sha_pattern, evidence_sha) is None
            ):
                valid = False
                break

    if valid and (
        first_review["reviewer_id"] == second_review["reviewer_id"]
        or first_review["request_id"] == second_review["request_id"]
    ):
        valid = False

    if not valid:
        return {
            "technical_two_pass_provenance_match": False,
            "conflicting_fields": [],
            "invalid_input": True,
            "independent_reviewer_agreement_established": False,
            "independent_scientific_acceptance": False,
            "student_publication_authorized": False,
        }

    conflicting_fields = []
    if first_review["source_sha256"] != expected_source_sha256:
        conflicting_fields.append("first_source_sha256")
    if second_review["source_sha256"] != expected_source_sha256:
        conflicting_fields.append("second_source_sha256")

    return {
        "technical_two_pass_provenance_match": len(conflicting_fields) == 0,
        "conflicting_fields": conflicting_fields,
        "invalid_input": False,
        "independent_reviewer_agreement_established": False,
        "independent_scientific_acceptance": False,
        "student_publication_authorized": False,
    }
