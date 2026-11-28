"""Figure crop/caption coverage is technical metadata, not science QA.

This is a no-Send, independently tested implementation for a previously
quarantined browser reply with unrecoverable original indentation.
"""


def compare_g3_captioned_png_asset_coverage(expected_figures_by_slide,
                                            exported_figures_by_slide):
    flag = {
        "independent_scientific_acceptance": False,
        "independent_visual_semantic_acceptance": False,
        "student_publication_authorized": False,
    }
    if (type(expected_figures_by_slide) is not list
            or type(exported_figures_by_slide) is not list):
        return {"technical_asset_coverage_match": False,
                "mismatched_slides": [], **flag}
    count = max(len(expected_figures_by_slide),
                len(exported_figures_by_slide))
    bad = []
    seen_expected = set()
    seen_actual = set()
    for index in range(count):
        if (index >= len(expected_figures_by_slide)
                or index >= len(exported_figures_by_slide)):
            bad.append(index + 1)
            continue
        expected = expected_figures_by_slide[index]
        actual = exported_figures_by_slide[index]
        valid = True
        for slide, global_ids in ((expected, seen_expected),
                                  (actual, seen_actual)):
            if type(slide) is not list:
                valid = False
                continue
            for caption in slide:
                if type(caption) is not str or not caption.strip():
                    valid = False
                    continue
                if caption in global_ids:
                    valid = False
                global_ids.add(caption)
        if not valid or expected != actual:
            bad.append(index + 1)
    matched = (len(expected_figures_by_slide) > 0
               and len(exported_figures_by_slide) > 0
               and not bad)
    return {"technical_asset_coverage_match": matched,
            "mismatched_slides": bad, **flag}
