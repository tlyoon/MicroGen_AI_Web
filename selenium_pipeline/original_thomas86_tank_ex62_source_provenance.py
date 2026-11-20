"""Independent publisher-source provenance for Thomas §8.6 Exercise 62.

Proves the original publisher source contains this *exercise and its figure*,
that the authored PNG reuses the same published illustration, and that the
presented tank-volume integral is mathematically correct. Does NOT certify
word timing, narration pronunciation, all figure label physics, or release.
"""
from __future__ import annotations
import hashlib
import io
import json
import re
from pathlib import Path

from .figure_source_identity import require, _sha

EXPECTED_SOURCE_SHA = "5c018ce8426dcf61eb3712fa1bf5dd707cf144c2a177bf83f3f736cebf7a5ab5"
EXPECTED_AUTHOR_PDF_SHA = "3e4c5abf0a9140c8f845439c076705b4b8677579bf7fe8cf806b1284c2ccdef1"
EXPECTED_TANK_PNG_SHA = "b1e379795edfadb88088fb41f63bfc5c4d1475e4d8dad3e11670b5336b8c340f"
EXPECTED_EMBEDDED_IMAGE_SHA = "870064e3c552b25cd0245fbb38d34f0fb2d9a842b7ed3c03f660bf4e449fa2a0"

def exercise_text_present(source_text: str) -> bool:
    compact = " ".join(source_text.lower().split())
    return all(term in compact for term in (
        "62. volume", "year-end inventory of gasoline",
        "right circular cylinder of radius", "depth d",
        "measuring stick", "d = depth of gasoline",
    ))


def source_image_match(source_encoded: bytes, authored_png: Path) -> dict:
    """Search a bounded image scale/translation; avoid declaring vague similarity."""
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        require(False, f"Independent native-Windows source figure visual matcher unavailable: {exc}")
    encoded = np.frombuffer(source_encoded, dtype=np.uint8)
    source = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    authored = cv2.imread(str(authored_png))
    require(source is not None and authored is not None,
            "Cannot decode exact publisher Exercise62 image or original authored PNG")
    best = (-1.0, None, None)
    for scale in np.linspace(0.65, 0.92, 28):
        reduced = cv2.resize(source, None, fx=float(scale), fy=float(scale))
        if (reduced.shape[0] > authored.shape[0]
                or reduced.shape[1] > authored.shape[1]):
            continue
        scores = cv2.matchTemplate(authored, reduced, cv2.TM_CCOEFF_NORMED)
        _, value, _, loc = cv2.minMaxLoc(scores)
        if float(value) > best[0]:
            best = float(value), float(scale), tuple(int(x) for x in loc)
    score, scale, location = best
    require(score >= 0.85 and 0.69 <= scale <= 0.76
            and location is not None and 0 <= location[0] <= 10
            and 24 <= location[1] <= 41,
            f"Exercise62 source image does not geometrically match original author: {best}")
    return {"normalized_matching_correlation": round(score, 6),
            "scale": round(scale, 4), "author_png_match_offset_xy": list(location),
            "author_source_image_same_publisher_visual_verified": True}


def exact_tank_math() -> dict:
    try:
        import sympy as s
    except ImportError as exc:
        require(False, f"Exact original tank volume mathematics requires SymPy: {exc}")
    r, d, L = s.symbols("r d L", positive=True)
    y = d-r
    volume = L*(y*s.sqrt(r*r-y*y) + r*r*(s.asin(y/r)+s.pi/2))
    section = 2*L*s.sqrt(r*r-y*y)
    require(s.simplify(s.diff(volume,d)-section)==0,
            "Tank indefinite-integral closed form fails the derivative identity")
    require(s.simplify(volume.subs(d,0))==0
            and s.simplify(volume.subs(d,2*r)-s.pi*r*r*L)==0,
            "Tank volume must range from zero to full right cylinder")
    return {"symbolic_volume_derivative_equals_2L_sqrt_2rd_minus_d_squared": True,
            "empty_and_full_tank_endpoints_verified": True,
            "depth_valid_range": "0 <= d <= 2r"}


def verify_tank_publisher_source(*, folder: Path) -> dict:
    import pymupdf
    folder = Path(folder)
    for filename in ("source.pdf", "slides.pdf", "slides.tex", "Exercise 62.png"):
        p=folder/filename
        require(p.is_file() and not p.is_symlink(), f"Original tank source missing: {p}")
    require(_sha(folder/"source.pdf")==EXPECTED_SOURCE_SHA
            and _sha(folder/"slides.pdf")==EXPECTED_AUTHOR_PDF_SHA
            and _sha(folder/"Exercise 62.png")==EXPECTED_TANK_PNG_SHA,
            "Tank publisher, authored PDF or image hash differs from frozen original")
    frames=re.findall(r"\\begin\{frame\}.*?\\end\{frame\}",
                      (folder/"slides.tex").read_text(encoding="utf8"),re.S)
    require(len(frames)==13, "Original §8.6 13-slide lecture missing")
    frame=frames[10]
    require("Exercise 62.png" in frame
            and r"V = 2L \int_{-r}^{-r+d} \sqrt{r^2 - y^2}" in frame,
            "Original tank mathematical source or authored figure missing on slide11")
    with pymupdf.open(folder/"source.pdf") as publisher:
        require(len(publisher)==6, "Original §8.6 six publisher pages required")
        exercise=publisher[5]
        require(exercise_text_present(exercise.get_text()),
                "Publisher-original Exercise62 text/labels not found; title match is insufficient")
        images=exercise.get_images(full=True)
        require(len(images)==1, "Publisher exercise62 figure image identity ambiguous")
        image_data=publisher.extract_image(images[0][0])["image"]
    require(hashlib.sha256(image_data).hexdigest()==EXPECTED_EMBEDDED_IMAGE_SHA,
            "Publisher Exercise62 embedded image changed")
    with pymupdf.open(folder/"slides.pdf") as author:
        require(len(author)==13 and bool(author[10].get_images(full=True)),
                "Original authored tank slide11 image is not rendered")
    image_match=source_image_match(image_data,folder/"Exercise 62.png")
    mathematics=exact_tank_math()
    return {
        "status":"ORIGINAL_THOMAS86_EXERCISE62_SOURCE_FIGURE_MATH_VERIFIED_NONPRODUCTION",
        "publisher_original_section_page":6, "publisher_original_exercise":62,
        "publisher_original_exercise_source_text_verified": True,
        "publisher_original_figure_image_sha256": EXPECTED_EMBEDDED_IMAGE_SHA,
        "author_exercise_62_png_sha256": EXPECTED_TANK_PNG_SHA,
        **image_match, **mathematics,
        "all_original_figure_panel_labels_word_timed":False,
        "complete_41_slide_math_figures_narration_accepted":False,
        "student_publication_authorized":False,
    }


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    require(a.out.parent.is_dir() and not a.out.exists(),
            "Original Exercise62 QA must use a new versioned output path")
    report=verify_tank_publisher_source(folder=a.folder)
    with a.out.open("x",encoding="utf8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False);f.write("\n")
    print(json.dumps(report))


if __name__=="__main__":
    main()
