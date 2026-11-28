"""Technical comparison of source figure captions to Beamer slides.

One-based slide mismatch indices, exact caption identity, no semantic verdict.
This source is an independently tested offline replacement for a saved,
unparseable original browser response. No response was replayed.
"""


def compare_g3_figure_caption_identity(expected_by_slide, rendered_by_slide):
    """Compare ordered caption IDs on ordered slides; never grant review."""
    flag = {
        "independent_scientific_acceptance": False,
        "independent_visual_semantic_acceptance": False,
        "student_publication_authorized": False,
    }
    if (type(expected_by_slide) not in (list, tuple)
            or type(rendered_by_slide) not in (list, tuple)):
        return {"technical_caption_identity_match": False,
                "mismatched_slides": [], **flag}
    count = max(len(expected_by_slide), len(rendered_by_slide))
    mismatched = []
    seen_expected = set()
    seen_rendered = set()
    total_expected = 0
    for index in range(count):
        if index >= len(expected_by_slide) or index >= len(rendered_by_slide):
            mismatched.append(index + 1)
            continue
        expected = expected_by_slide[index]
        actual = rendered_by_slide[index]
        valid = True
        for slide, globally_seen in (
                (expected, seen_expected), (actual, seen_rendered)):
            if type(slide) not in (list, tuple):
                valid = False
                continue
            for caption in slide:
                if type(caption) is not str or not caption.strip():
                    valid = False
                    continue
                if caption in globally_seen:
                    valid = False
                globally_seen.add(caption)
        if type(expected) in (list, tuple):
            total_expected += len(expected)
        if not valid or expected != actual:
            mismatched.append(index + 1)
    matched = (count > 0 and total_expected > 0 and not mismatched)
    return {"technical_caption_identity_match": matched,
            "mismatched_slides": mismatched, **flag}
