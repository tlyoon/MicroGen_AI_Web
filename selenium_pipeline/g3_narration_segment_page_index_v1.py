"""Independent-test-pinned technical narration/page-index comparator only.

A positive match never establishes spoken content, acoustic or physics QA.
"""


def compare_g3_narration_segment_page_index(expected_page_ids,
                                            observed_page_ids):
    flag = {
        "independent_scientific_acceptance": False,
        "independent_acoustic_acceptance": False,
        "student_publication_authorized": False,
    }
    if (type(expected_page_ids) not in (list, tuple)
            or type(observed_page_ids) not in (list, tuple)):
        return {"technical_page_index_match": False,
                "mismatched_positions": [], **flag}
    problems = []
    seen_expected = set()
    seen_observed = set()
    for index in range(max(len(expected_page_ids), len(observed_page_ids))):
        if index >= len(expected_page_ids) or index >= len(observed_page_ids):
            problems.append(index + 1)
            continue
        expected, observed = (expected_page_ids[index],
                              observed_page_ids[index])
        valid_expected = (type(expected) is int and expected > 0
                          and expected not in seen_expected)
        valid_observed = (type(observed) is int and observed > 0
                          and observed not in seen_observed)
        if type(expected) is int and expected > 0:
            seen_expected.add(expected)
        if type(observed) is int and observed > 0:
            seen_observed.add(observed)
        if not (valid_expected and valid_observed and expected == observed):
            problems.append(index + 1)
    matched = (len(expected_page_ids) > 0
               and len(expected_page_ids) == len(observed_page_ids)
               and not problems)
    return {"technical_page_index_match": matched,
            "mismatched_positions": problems, **flag}
