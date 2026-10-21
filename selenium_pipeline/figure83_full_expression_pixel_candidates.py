"""Real PDF source-equation glyph template vs existing slide bitmap review.

This complements the inverse operator only match. It is a read-only
comparison, not theorem-level or graph-semantic mathematical verification.
"""
from __future__ import annotations
import io,math
from pathlib import Path
import pymupdf
from PIL import Image
from .figure83_fraction_spatial_identity import disambiguate_original_fraction
from .figure_original_math_labels import audit_original_graph_labels
from .figure83_slide_inverse_glyph_correspondence import _black,_best_template,validate_glyph_matrix
from .figure_three_graph_color_reflow import _dependencies,audit_real_three_graph_reflow
from .figure_source_identity import _sha,require

def extract_real_equation_pixel_matrix(*,source:Path,slides:Path,
                   source_page:int=2,slide_page:int=5,figure_id:str="8.3")->dict:
    source,slides=Path(source).absolute(),Path(slides).absolute()
    before=(_sha(source),_sha(slides))
    words=audit_original_graph_labels(source=source,slides=slides,
                 source_page=source_page,slide_page=slide_page,figure_id=figure_id)
    equations=disambiguate_original_fraction(words["panels"])
    geometry=audit_real_three_graph_reflow(source=source,slides=slides,
                 source_page=source_page,slide_page=slide_page,figure_id=figure_id)
    require((words["source_sha256"],words["slides_sha256"])==before
            and (geometry["original_pdf_sha256"],geometry["existing_slides_pdf_sha256"])==before
            and geometry["detected_graph_count"]==3,
            "Source or actual slide PDF geometry not independently bound")
    cv2,np=_dependencies()
    with pymupdf.open(source) as book,pymupdf.open(slides) as deck:
        require(1<=source_page<=len(book) and 1<=slide_page<=len(deck),
                "Untrusted source/slide page")
        pix=book[source_page-1].get_pixmap(matrix=pymupdf.Matrix(3,3),
                       colorspace=pymupdf.csRGB,alpha=False)
        src=np.asarray(Image.frombytes("RGB",(pix.width,pix.height),pix.samples))
        shown=[x for x in deck[slide_page-1].get_image_info(xrefs=True)
               if int(x["width"])>=48 and int(x["height"])>=48
               and int(x.get("xref",0))>0
               and pymupdf.Rect(x["bbox"]).width>=50
               and pymupdf.Rect(x["bbox"]).height>=25]
        require(len(shown)==1,"Original slide figure bitmap ambiguous")
        with Image.open(io.BytesIO(deck.extract_image(shown[0]["xref"])["image"])) as img:
            require(img.width*img.height<=2_000_000,"Oversized original slide bitmap")
            slide=np.asarray(img.convert("RGB"))
    templates=[]
    for equation in equations:
        x0,y0,x1,y1=equation["source_equation_bbox_pt"]
        l,t,r,b=(int(math.floor(x0*3)),int(math.floor(y0*3)),
                  int(math.ceil(x1*3)),int(math.ceil(y1*3)))
        require(0<=l<r<=src.shape[1] and 0<=t<b<=src.shape[0],
                "Original equation text crop not bounded")
        templates.append(_black(src[t:b,l:r],np))
    bands=[entry["slide_bitmap_scan_band_px"]
           for entry in geometry["graph_correspondence_evidence"]]
    regions=[]
    for start,end in bands:
        require(type(start) is int and type(end) is int
                and 0<=start<end<=slide.shape[1],
                "Invalid independently detected slide graph band")
        regions.append(_black(slide[:,start:end],np))
    matched=[[_best_template(a,b,cv2,np) for b in regions] for a in templates]
    matrix=[[v["normalized_correlation"] for v in row] for row in matched]
    diagnostic=validate_glyph_matrix(matrix)
    require((_sha(source),_sha(slides))==before,
            "Original lecture source/slides altered during equation image inspection")
    return {"schema_version":1,"status":"FULL_SOURCE_EXPRESSION_PIXEL_CANDIDATES_REVIEW_ONLY",
            "source_sha256":before[0],"slides_sha256":before[1],
            "printed_source_equations":equations,
            "image_match_score_matrix":matrix,
            "image_match_details":matched,
            "unambiguous_full_equation_pixel_matching_detected":
                diagnostic["all_three_source_inverse_operator_glyphs_in_slide_verified"],
            "strict_full_equation_template_diagnostics":diagnostic["operator_glyph_matches"],
            "existing_slide_bitmap_bounds":bands,
            "full_equation_mathematically_verified":False,
            "source_equation_math_equivalence_to_slide_verified":False,
            "narration_word_alignment_verified":False,
            "paid_tts_authorized":False,
            "student_publication_authorized":False}
