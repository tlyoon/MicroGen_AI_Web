"""Preserve real textbook Figure 8.2 radical glyphs as source-tied raster evidence.

The source PDF's machine text maps some radical/absolute-value glyphs to
unreliable characters. Render the ORIGINAL glyphs, not guessed OCR or a
redrawn triangle. This is evidence for source review, not a second AI pass.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import pymupdf
from .original_slide4_math_correction_pilot import prepare_corrected_original_slide4
from .figure_source_identity import require,_sha

EXPECTED_SOURCE="b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068"
CROP=(205.0,480.0,595.0,647.0)
EQUATIONS=(
    "sqrt(a^2+x^2) = a*abs(sec(theta))",
    "sqrt(a^2-x^2) = a*abs(cos(theta))",
    "sqrt(x^2-a^2) = a*abs(tan(theta))",
)

def render_original_figure82_glyph_packet(*,folder:Path,output_dir:Path)->dict:
    root=Path(folder).absolute()
    out=Path(output_dir).absolute()
    require(root.is_dir() and not root.is_symlink()
            and out.parent.is_dir() and not out.exists()
            and not out.is_relative_to(root),
            "New external exclusive glyph-evidence directory required")
    source=root/"source.pdf"
    require(_sha(source)==EXPECTED_SOURCE,"Unrecognized actual Thomas 8.4 source PDF")
    plan=prepare_corrected_original_slide4(folder=root)
    require(plan["source_sha256"]==EXPECTED_SOURCE
            and plan["original_utterances"]==5
            and plan["corrected_mathematics_independently_ai_approved"] is False,
            "Corrected original sign/triangle/source binding unavailable")
    with pymupdf.open(source) as pdf:
        require(len(pdf)==6,"Unexpected genuine original textbook page count")
        p=pdf[0]
        caption=[b for b in p.get_text("blocks")
                 if len(b)>4 and isinstance(b[4],str) and
                 "FIGURE 8.2" in b[4] and
                 "Reference triangles" in b[4]]
        require(len(caption)==1 and 595>caption[0][2]
                and pymupdf.Rect(CROP).contains(pymupdf.Rect(caption[0][:4])),
                "Figure8.2 caption/source diagram position changed")
        raw=p.get_text()
        require(all(x in raw for x in
                    ('x = a tan u','x = a sin u','x = a sec u',
                     '"a2 + x2 = a 0 sec u 0',
                     '"a2 −x2 = a 0 cos u 0',
                     '"x2 −a2 = a 0 tan u 0')),
                "Original text extraction/glyph footprint is not recognized")
        pix=p.get_pixmap(matrix=pymupdf.Matrix(3,3),
                         clip=pymupdf.Rect(CROP),alpha=False)
    require(pix.width>=1000 and pix.height>=450,
            "Actual figure raster resolution insufficient")
    out.mkdir()
    image=out/"ORIGINAL_SOURCE_PAGE1_FIG82_UNRETOUCHED_GLYPHS.png"
    with image.open("xb") as stream:stream.write(pix.tobytes("png"))
    require(_sha(source)==EXPECTED_SOURCE,
            "Protected original textbook changed while rendering")
    record={
        "status":"GENUINE_FIGURE82_SOURCE_RADICAL_GLYPH_RASTER_AVAILABLE_UNAPPROVED",
        "source_sha256":EXPECTED_SOURCE,
        "source_physical_page":1,
        "page_crop_pdf_pt":list(CROP),
        "actual_source_png_sha256":_sha(image),
        "actual_source_png":"ORIGINAL_SOURCE_PAGE1_FIG82_UNRETOUCHED_GLYPHS.png",
        "original_source_glyphs_present_as_PIXELS":True,
        "text_extraction_cannot_reliably_reconstruct_radicals":True,
        "equations_to_visually_check_not_automatically_certified":list(EQUATIONS),
        "conditional_sign_and_domain_symbolic_checks":plan["proved_math_defects"],
        "source_glyph_math_independently_two_pass_approved":False,
        "corrected_TTS_generated":False,
        "source_originals_modified":False,
        "student_publication_authorized":False,
    }
    with (out/"SOURCE_GLYPH_EVIDENCE_UNAPPROVED.json").open("x",encoding="utf8") as f:
        json.dump(record,f,indent=2,ensure_ascii=False)
    return record

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    p.add_argument("--output-dir",required=True,type=Path)
    a=p.parse_args(argv)
    r=render_original_figure82_glyph_packet(
        folder=a.folder,output_dir=a.output_dir)
    print(json.dumps({"status":r["status"],"raster_sha":r["actual_source_png_sha256"],
                      "independent_math_approved":False,"output":str(a.output_dir)}))
if __name__=="__main__":main()
