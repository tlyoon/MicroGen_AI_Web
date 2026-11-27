import re

def compare_g3_pdf_caption_png_inventory(source_caption_ids, png_caption_ids):
    if type(source_caption_ids) is not list or type(png_caption_ids) is not list:
        return {
            "technical_caption_coverage_match": False,
            "missing_png_caption_ids": [],
            "orphan_png_caption_ids": [],
            "invalid_input": True,
            "independent_scientific_acceptance": False,
            "student_publication_authorized": False,
        }

    if not all(
        type(item) is str
        and not item.lower().endswith(".png")
        and re.fullmatch(r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*", item) is not None
        for item in source_caption_ids
    ) or not all(
        type(item) is str
        and not item.lower().endswith(".png")
        and re.fullmatch(r"[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*", item) is not None
        for item in png_caption_ids
    ):
        return {
            "technical_caption_coverage_match": False,
            "missing_png_caption_ids": [],
            "orphan_png_caption_ids": [],
            "invalid_input": True,
            "independent_scientific_acceptance": False,
            "student_publication_authorized": False,
        }

    source_set = set(source_caption_ids)
    png_set = set(png_caption_ids)

    if len(source_set) != len(source_caption_ids) or len(png_set) != len(png_caption_ids):
        return {
            "technical_caption_coverage_match": False,
            "missing_png_caption_ids": [],
            "orphan_png_caption_ids": [],
            "invalid_input": True,
            "independent_scientific_acceptance": False,
            "student_publication_authorized": False,
        }

    missing_png_caption_ids = sorted(source_set - png_set)
    orphan_png_caption_ids = sorted(png_set - source_set)

    return {
        "technical_caption_coverage_match": source_set == png_set,
        "missing_png_caption_ids": missing_png_caption_ids,
        "orphan_png_caption_ids": orphan_png_caption_ids,
        "invalid_input": False,
        "independent_scientific_acceptance": False,
        "student_publication_authorized": False,
    }
