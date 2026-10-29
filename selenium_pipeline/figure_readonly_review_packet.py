"""Generate a NEW isolated, review-only original figure evidence packet.

This renders a copy of original PDF pages for visual review. Review marks
indicate geometry lacking feature-registration; they are NOT missing art.
It does not modify original PDFs, WAV, MP4 or publish teaching material.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil
from pathlib import Path
import pymupdf
from .figure_source_identity import require,_sha
from .figure_source_component_registration import audit_component_registration

def make_source_slide_review_packet(*,source:Path,slides:Path,
                                    source_page:int,slide_page:int,
                                    figure_id:str,output:Path)->dict:
    sources=[Path(source).absolute(),Path(slides).absolute()]
    dest=Path(output).absolute()
    for item in sources+[dest,dest.parent]:
        require(not item.is_symlink()
                and not getattr(item,"is_junction",lambda:False)(),
                "Review paths must not be symlinks or junctions")
    require(all(path.is_file() for path in sources)
            and sources[0]!=sources[1],
            "Require two independent original PDF files")
    require(not dest.exists() and dest.parent.is_dir(),
            "New review folder must not exist")
    require(all(not dest.is_relative_to(src.parent)
                and not src.is_relative_to(dest)
                for src in sources),
            "Review folder must be separate from all original lecture folders")
    before=[_sha(p) for p in sources]
    audited=audit_component_registration(
        source=sources[0],slides=sources[1],
        source_page=source_page,slide_page=slide_page,figure_id=figure_id)
    require(audited.get("source_sha256")==before[0]
            and audited.get("slides_sha256")==before[1],
            "Audit and file identities disagree")
    for key in ("original_complete_figure_verified",
                "original_panel_boundaries_verified",
                "original_stroke_to_slide_pixel_equality_verified",
                "encoded_highlighted_video_authorized",
                "publication_authorized"):
        require(audited.get(key) is False,
                "Invalid prior technical review authorization")
    with pymupdf.open(sources[0]) as original, pymupdf.open(sources[1]) as deck:
        a=original[source_page-1]
        b=deck[slide_page-1]
        require(a.rect.width*a.rect.height <= 900_000
                and b.rect.width*b.rect.height <= 900_000,
                "Oversized original page render")
        with pymupdf.open() as temporary:
            review=temporary.new_page(width=a.rect.width,height=a.rect.height)
            review.show_pdf_page(review.rect,original,source_page-1)
            for observation in audited["observations"]:
                if observation["registration_groups_intersecting_bbox"]:
                    continue
                rect=pymupdf.Rect(observation["union_bbox"])
                require(rect.is_valid and not rect.is_infinite
                        and rect.width>=0 and rect.height>=0
                        and (rect.width>0 or rect.height>0),
                        "Malformed original vector region")
                box=pymupdf.Rect(max(0,rect.x0-2),max(0,rect.y0-2),
                                 min(a.rect.x1,rect.x1+2),
                                 min(a.rect.y1,rect.y1+2))
                require(box.is_valid and not box.is_empty
                        and a.rect.intersects(box),
                        "Original vector observation lies outside textbook page")
                review.draw_rect(box,color=(1,0,0),width=1.5)
            source_png=review.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),
                      alpha=False,colorspace=pymupdf.csRGB).tobytes("png")
        slide_png=b.get_pixmap(matrix=pymupdf.Matrix(2,2),
                    alpha=False,colorspace=pymupdf.csRGB).tobytes("png")
    require(len(source_png)<=8_000_000 and len(slide_png)<=8_000_000,
            "Excessive review rendering bytes")
    require([_sha(p) for p in sources]==before,
            "Original changed during review packet render")
    receipt={
        "schema_version":1,
        "status":"READ_ONLY_RENDERED_FIGURE_REVIEW_PACKET_NOT_APPROVED",
        "figure_id":figure_id,
        "source_page":source_page,"slide_page":slide_page,
        "source_sha256":before[0],"slides_sha256":before[1],
        "source_review_file":"original_source_review.png",
        "slide_review_file":"existing_slide_review.png",
        "isolated_source_vector_indices":[
            obj["drawing_indices"]
            for obj in audited["observations"]
            if not obj["registration_groups_intersecting_bbox"]],
        "source_render_sha256":hashlib.sha256(source_png).hexdigest(),
        "slide_render_sha256":hashlib.sha256(slide_png).hexdigest(),
        "author_intended_complete_figure_certified":False,
        "scientific_panel_label_mapping_certified":False,
        "source_to_slide_pixel_equivalence_certified":False,
        "narrated_highlight_accepted":False,
        "encoded_under_600s_video_accepted":False,
        "student_publication_authorized":False,
    }
    dest.mkdir()
    try:
        with (dest/receipt["source_review_file"]).open("xb") as f:
            f.write(source_png)
        with (dest/receipt["slide_review_file"]).open("xb") as f:
            f.write(slide_png)
        with (dest/"review_manifest.json").open("x",encoding="utf8") as f:
            json.dump(receipt,f,indent=2,sort_keys=True)
            f.write("\n")
        require([_sha(p) for p in sources]==before,
                "Original changed during review write")
    except Exception:
        shutil.rmtree(dest)
        raise
    return receipt

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--slides",type=Path,required=True)
    p.add_argument("--source-page",type=int,required=True)
    p.add_argument("--slide-page",type=int,required=True)
    p.add_argument("--figure-id",required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    print(json.dumps(make_source_slide_review_packet(
        source=a.source,slides=a.slides,source_page=a.source_page,
        slide_page=a.slide_page,figure_id=a.figure_id,output=a.output),
        indent=2,sort_keys=True))
    # A review image is NOT acceptance or TTS/MP4 authorization.
    return 2

if __name__=="__main__":
    raise SystemExit(main())
