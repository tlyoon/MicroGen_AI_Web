import re


def compare_g2_reviewer_source_coverage(
    source_slide_identifiers,
    reviewer_evidence_slide_identifiers,
):
    invalid_result = {
        "technical_reviewer_source_coverage_match": False,
        "missing_ids": [],
        "unexpected_ids": [],
        "invalid_input": True,
        "independent_reviewer_agreement_established": False,
        "independent_scientific_acceptance": False,
        "student_publication_authorized": False,
    }

    if (
        type(source_slide_identifiers) is not list
        or type(reviewer_evidence_slide_identifiers) is not list
    ):
        return invalid_result

    if (
        len(source_slide_identifiers) == 0
        or len(reviewer_evidence_slide_identifiers) == 0
    ):
        return invalid_result

    identifier_pattern = r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*"

    for identifier in source_slide_identifiers:
        if type(identifier) is not str:
            return invalid_result
        if identifier.lower().endswith(".png"):
            return invalid_result
        if re.fullmatch(identifier_pattern, identifier) is None:
            return invalid_result

    for identifier in reviewer_evidence_slide_identifiers:
        if type(identifier) is not str:
            return invalid_result
        if identifier.lower().endswith(".png"):
            return invalid_result
        if re.fullmatch(identifier_pattern, identifier) is None:
            return invalid_result

    source_set = set(source_slide_identifiers)
    reviewer_set = set(reviewer_evidence_slide_identifiers)

    if (
        len(source_set) != len(source_slide_identifiers)
        or len(reviewer_set) != len(reviewer_evidence_slide_identifiers)
    ):
        return invalid_result

    missing_ids = sorted(source_set - reviewer_set)
    unexpected_ids = sorted(reviewer_set - source_set)
    coverage_match = len(missing_ids) == 0 and len(unexpected_ids) == 0

    return {
        "technical_reviewer_source_coverage_match": coverage_match,
        "missing_ids": missing_ids,
        "unexpected_ids": unexpected_ids,
        "invalid_input": False,
        "independent_reviewer_agreement_established": False,
        "independent_scientific_acceptance": False,
        "student_publication_authorized": False,
    }
